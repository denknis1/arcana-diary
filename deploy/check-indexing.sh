#!/usr/bin/env bash
# Проверяет закрытие от индексации на живом домене. Режим и домен — из deploy/.env.
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$DIR/.env"; set +a
D="$SITE_DOMAIN"

CURL=(curl -sS --max-time 15)
if [ "$TLS_MODE" = "local" ]; then
  CURL+=(-k --resolve "$D:443:127.0.0.1" --resolve "www.$D:443:127.0.0.1" --resolve "api.$D:443:127.0.0.1")
fi
AUTH=(-u "$STAGE_USER:$STAGE_PASSWORD")

fails=0
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; fails=$((fails + 1)); }
expect() { if [ "$2" = "$3" ]; then pass "$1 ($2)"; else fail "$1: ожидалось '$3', получено '$2'"; fi; }
status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$@"; }
# header <Имя> <аргументы curl...> — значение заголовка ответа
header() {
  local name; name="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"; shift
  "${CURL[@]}" -o /dev/null -D - "$@" | tr -d '\r' \
    | awk -v h="$name" 'index(tolower($0), h ": ") == 1 { print substr($0, length(h) + 3) }'
}
has_noindex() { case "$1" in *noindex*) echo yes ;; *) echo no ;; esac; }

expect "api /health" "$(status "https://api.$D/health")" 200
expect "api noindex" "$(has_noindex "$(header X-Robots-Tag "https://api.$D/health")")" yes
expect "api. только /health" "$(status "https://api.$D/api/limits")" 404
expect "www -> 301" "$(status "https://www.$D/some/path")" 301
expect "www Location" "$(header Location "https://www.$D/some/path")" "https://$D/some/path"

if [ "$LAUNCHED" = "false" ]; then
  expect "сайт без пароля" "$(status "https://$D/")" 401
  expect "401 несёт noindex" "$(has_noindex "$(header X-Robots-Tag "https://$D/")")" yes
  expect "401 просит пароль" "$( [ -n "$(header WWW-Authenticate "https://$D/")" ] && echo yes || echo no)" yes
  expect "сайт с паролем" "$(status "${AUTH[@]}" "https://$D/")" 200
  # stage 4.4a: the new Caddyfile is live — a page without .html opens, an unknown address is a 404 page
  expect "страница без .html с паролем" "$(status "${AUTH[@]}" "https://$D/one-card")" 200
  expect "неизвестный адрес с паролем" "$(status "${AUTH[@]}" "https://$D/no-such-page")" 404
  expect "сайт с паролем noindex" "$(has_noindex "$(header X-Robots-Tag "${AUTH[@]}" "https://$D/")")" yes
  expect "www noindex" "$(has_noindex "$(header X-Robots-Tag "https://www.$D/")")" yes
  expect "/api без пароля" "$(status "https://$D/api/limits")" 401
  expect "/api noindex" "$(has_noindex "$(header X-Robots-Tag "https://$D/api/limits")")" yes
  # stage 4.3: the stage cookie (set after the password) lets /api/* requests with Authorization: Bearer through
  stage_pair="$(header Set-Cookie "${AUTH[@]}" "https://$D/" | grep -o 'ad_stage=[0-9a-f]*' | head -1)"
  expect "пароль ставит куку стенда" "$([ -n "$stage_pair" ] && echo yes || echo no)" yes
  expect "401 без куки стенда" "$(header Set-Cookie "https://$D/" | grep -c ad_stage)" 0
  expect "/api с кукой стенда" "$([ "$(status -H "Cookie: $stage_pair" "https://$D/api/limits")" != 401 ] && echo yes || echo no)" yes
  expect "/api с чужой кукой стенда" "$(status -H "Cookie: ad_stage=0" "https://$D/api/limits")" 401
else
  expect "сайт открыт" "$(status "https://$D/")" 200
  expect "нет noindex в заголовке" "$(has_noindex "$(header X-Robots-Tag "https://$D/")")" no
  expect "нет noindex в HTML" "$(has_noindex "$("${CURL[@]}" "https://$D/")")" no
  expect "robots.txt" "$(status "https://$D/robots.txt")" 200
  if "${CURL[@]}" "https://$D/robots.txt" | tr -d '\r' | grep -qiE '^Disallow:[[:space:]]*/[[:space:]]*$'; then
    fail "robots.txt содержит Disallow: /"
  else
    pass "robots.txt без Disallow: /"
  fi
fi

if [ "$fails" -eq 0 ]; then echo "OK: все проверки пройдены"; else echo "ПРОВАЛ: $fails"; exit 1; fi
