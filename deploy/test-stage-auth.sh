#!/usr/bin/env bash
# Проверяет пароль стенда и куку стенда на временном контейнере caddy:2.8.4 (тот же образ, что в бою) с этим
# Caddyfile, шаблонами deploy/caddy/ и фиктивным паролем. Боевые контейнеры, deploy/.env и
# deploy/caddy/stage_auth.caddy не трогает; контейнеры проверки удаляются в конце. API за ним нет: запрос,
# прошедший Caddy, получает 502, остановленный паролем — 401.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# never the real secrets: the generator must take ENV_FILE / OUT (stage 4.3), or it would read deploy/.env
grep -q 'ENV_FILE' "$DIR/gen-stage-auth.sh" || { echo "gen-stage-auth.sh has no ENV_FILE: stop"; exit 2; }
TMP="$(mktemp -d)"
NAME="arcana-stagetest-$$"
cleanup() { docker rm -f "$NAME-false" "$NAME-true" >/dev/null 2>&1 || true; rm -rf "$TMP"; }
trap cleanup EXIT

mkdir -p "$TMP/parts" "$TMP/site"
cp "$DIR/Caddyfile" "$TMP/Caddyfile"
for f in "$DIR"/caddy/*.caddy; do
  [ "$(basename "$f")" = stage_auth.caddy ] || cp "$f" "$TMP/parts/"
done
printf '<!doctype html><title>stage</title>\n' > "$TMP/site/index.html"
mkdir -p "$TMP/site/es"
printf '<!doctype html><html lang="es"><title>404 es</title>\n' > "$TMP/site/es/404.html"
printf '<!doctype html><html lang="en"><title>404</title>\n' > "$TMP/site/404.html"
printf 'STAGE_USER=tester\nSTAGE_PASSWORD=dummy-password\n' > "$TMP/.env"
ENV_FILE="$TMP/.env" OUT="$TMP/parts/stage_auth.caddy" "$DIR/gen-stage-auth.sh" >/dev/null
chmod 644 "$TMP/parts/stage_auth.caddy"  # the caddy user in the container must read it; a dummy secret
chmod -R a+rX "$TMP"

start() {  # start <LAUNCHED> -> prints the local port
  docker run -d --rm --name "$NAME-$1" -e SITE_DOMAIN=arcana.test -e TLS_MODE=local -e LAUNCHED="$1" \
    -e TRUST_CLOUDFLARE=false -v "$TMP/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$TMP/parts:/etc/caddy/parts:ro" \
    -v "$TMP/site:/srv/site:ro" -p 127.0.0.1::443 caddy:2.8.4 >/dev/null
  docker port "$NAME-$1" 443/tcp | head -1 | sed 's/.*://'
}

fails=0
expect() { if [ "$2" = "$3" ]; then echo "PASS $1 ($2)"; else echo "FAIL $1: ожидалось '$3', получено '$2'"; fails=$((fails + 1)); fi; }

for launched in false true; do
  docker run --rm -e SITE_DOMAIN=arcana.test -e TLS_MODE=local -e LAUNCHED="$launched" -e TRUST_CLOUDFLARE=false \
    -v "$TMP/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$TMP/parts:/etc/caddy/parts:ro" caddy:2.8.4 \
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1 \
    && expect "caddy validate (LAUNCHED=$launched)" ok ok || expect "caddy validate (LAUNCHED=$launched)" failed ok
done

PORT="$(start false)"
URL="https://arcana.test:$PORT"
CURL=(curl -sS -k --max-time 10 --resolve "arcana.test:$PORT:127.0.0.1")
for _ in $(seq 1 50); do "${CURL[@]}" -o /dev/null "$URL/" 2>/dev/null && break; sleep 0.2; done
status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$@"; }
cookies() { "${CURL[@]}" -o /dev/null -D - "$@" | tr -d '\r' | grep -i '^set-cookie:' || true; }

expect "страница без пароля" "$(status "$URL/")" 401
expect "401 не ставит куку стенда" "$(cookies "$URL/" | grep -c ad_stage)" 0
expect "чужой пароль" "$(status -u tester:wrong "$URL/")" 401
expect "чужой пароль без куки" "$(cookies -u tester:wrong "$URL/" | grep -c ad_stage)" 0
expect "страница с паролем" "$(status -u tester:dummy-password "$URL/")" 200
SET="$(cookies -u tester:dummy-password "$URL/")"
PAIR="$(printf '%s' "$SET" | grep -o 'ad_stage=[0-9a-f]*' | head -1)"
expect "кука стенда выдана" "$([ ${#PAIR} -eq 73 ] && echo yes || echo no)" yes
for attr in HttpOnly Secure SameSite=Lax Path=/; do
  expect "кука стенда: $attr" "$(printf '%s' "$SET" | grep -c "$attr")" 1
done
expect "/api без пароля и куки" "$(status "$URL/api/limits")" 401
expect "/api с одним Bearer" "$(status -H 'Authorization: Bearer x' "$URL/api/limits")" 401
expect "/api с кукой стенда" "$(status -H "Cookie: $PAIR" "$URL/api/limits")" 502
expect "/api с кукой и Bearer (вход)" "$(status -H "Cookie: $PAIR" -H 'Authorization: Bearer x' "$URL/api/limits")" 502
expect "/api с кукой среди других" "$(status -H "Cookie: ad_guest=1; $PAIR; x=2" "$URL/api/limits")" 502
expect "/api с кукой по HTTP/1.1" "$(status --http1.1 -H "Cookie: $PAIR" "$URL/api/limits")" 502
expect "/api с чужой кукой" "$(status -H 'Cookie: ad_stage=0000' "$URL/api/limits")" 401
expect "/api с удлинённой кукой" "$(status -H "Cookie: ${PAIR}0" "$URL/api/limits")" 401
expect "страница с кукой без пароля" "$(status -H "Cookie: $PAIR" "$URL/")" 200
expect "/api не ставит куку" "$(cookies -u tester:dummy-password "$URL/api/limits" | grep -c ad_stage)" 0
# stage 4.4a: the new addresses are closed too; an unknown address is a 404 (with noindex) only after the password
location() { "${CURL[@]}" -o /dev/null -D - "$@" | tr -d '\r' | awk 'tolower($0) ~ /^location:/ { print }'; }
expect "/nope без пароля" "$(status "$URL/nope")" 401
expect "/one-card/ без пароля" "$(status "$URL/one-card/")" 401
expect "/one-card/ без пароля: нет Location" "$(location "$URL/one-card/" | wc -l)" 0
expect "/one-card.html без пароля" "$(status "$URL/one-card.html")" 401
expect "/one-card.html без пароля: нет Location" "$(location "$URL/one-card.html" | wc -l)" 0
expect "/nope с паролем" "$(status -u tester:dummy-password "$URL/nope")" 404
expect "/nope с паролем: noindex" "$("${CURL[@]}" -o /dev/null -D - -u tester:dummy-password "$URL/nope" | tr -d '\r' | grep -i '^x-robots-tag:' | grep -ci noindex)" 1
expect "/es/nope с паролем" "$(status -u tester:dummy-password "$URL/es/nope")" 404
expect "/es/nope с паролем: страница ES" "$("${CURL[@]}" -u tester:dummy-password "$URL/es/nope" | grep -c '<html lang="es"')" 1
expect "/one-card/ с паролем → 308" "$(status -u tester:dummy-password "$URL/one-card/")" 308
expect "/one-card/ с паролем: Location" "$(location -u tester:dummy-password "$URL/one-card/" | sed 's/^[Ll]ocation: *//')" "/one-card"
docker rm -f "$NAME-false" >/dev/null

PORT="$(start true)"
URL="https://arcana.test:$PORT"
CURL=(curl -sS -k --max-time 10 --resolve "arcana.test:$PORT:127.0.0.1")
for _ in $(seq 1 50); do "${CURL[@]}" -o /dev/null "$URL/" 2>/dev/null && break; sleep 0.2; done
expect "после запуска страница открыта" "$(status "$URL/")" 200
expect "после запуска куки стенда нет" "$(cookies "$URL/" | grep -c ad_stage)" 0

if [ "$fails" -eq 0 ]; then echo "OK: пароль и кука стенда работают"; else echo "ПРОВАЛ: $fails"; exit 1; fi
