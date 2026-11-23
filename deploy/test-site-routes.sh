#!/usr/bin/env bash
# Проверяет адреса страниц 4.4а на временном контейнере caddy:2.8.4 (тот же образ, что в бою) с этим Caddyfile и
# собранным site/dist: страницы открываются без .html и без слэша в конце, неизвестный адрес получает 404 на своём
# языке, редиректы не принимают чужие адреса (open redirect). Вместо API — временная заглушка (caddy:2.8.4,
# сеть и контейнеры arcana-routetest-<pid>), отвечающая 404. LAUNCHED=true — без пароля стенда (его проверяет
# deploy/test-stage-auth.sh). Боевые контейнеры, deploy/.env и deploy/caddy/stage_auth.caddy не трогает;
# всё временное удаляется в конце. Сначала собрать сайт: deploy/build-site.sh.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
DIST="$(cd "${DIST:-$DIR/../site/dist}" && pwd)"
[ -f "$DIST/index.html" ] || { echo "нет $DIST/index.html: сначала deploy/build-site.sh"; exit 2; }
TMP="$(mktemp -d)"
NAME="arcana-routetest-$$"
cleanup() {
  docker rm -f "$NAME" "$NAME-api" >/dev/null 2>&1 || true
  docker network rm "$NAME" >/dev/null 2>&1 || true
  rm -rf "$TMP"
}
trap cleanup EXIT

mkdir -p "$TMP/parts"
cp "$DIR/Caddyfile" "$TMP/Caddyfile"
for f in "$DIR"/caddy/*.caddy; do
  [ "$(basename "$f")" = stage_auth.caddy ] || cp "$f" "$TMP/parts/"
done
# заглушка API: любой путь — 404 с телом "api-404" и заголовком X-Stub-Api
printf ':8000 {\n\theader X-Stub-Api yes\n\trespond "api-404" 404\n}\n' > "$TMP/stub.Caddyfile"
chmod -R a+rX "$TMP"

docker network create "$NAME" >/dev/null
docker run -d --rm --name "$NAME-api" --network "$NAME" --network-alias api \
  -v "$TMP/stub.Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.8.4 >/dev/null
docker run -d --rm --name "$NAME" --network "$NAME" -e SITE_DOMAIN=arcana.test -e TLS_MODE=local -e LAUNCHED=true \
  -e TRUST_CLOUDFLARE=false -v "$TMP/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$TMP/parts:/etc/caddy/parts:ro" \
  -v "$DIST:/srv/site:ro" -p 127.0.0.1::443 caddy:2.8.4 >/dev/null
PORT="$(docker port "$NAME" 443/tcp | head -1 | sed 's/.*://')"
URL="https://arcana.test:$PORT"
CURL=(curl -sS -k --max-time 10 --path-as-is --resolve "arcana.test:$PORT:127.0.0.1")
for _ in $(seq 1 50); do "${CURL[@]}" -o /dev/null "$URL/" 2>/dev/null && break; sleep 0.2; done

fails=0
expect() { if [ "$2" = "$3" ]; then echo "PASS $1 ($2)"; else echo "FAIL $1: ожидалось '$3', получено '$2'"; fails=$((fails + 1)); fi; }
status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$URL$1"; }
html_lang() { "${CURL[@]}" "$URL$1" | grep -o '<html lang="[a-z]*"' | head -1; }
moved_to() { "${CURL[@]}" -o /dev/null -w '%{http_code} %{redirect_url}' "$URL$1"; }
location() { "${CURL[@]}" -o /dev/null -D - "$URL$1" | tr -d '\r' | awk 'tolower($0) ~ /^location:/ { print }'; }
robots() { "${CURL[@]}" -o /dev/null -D - "$URL$1" | tr -d '\r' | awk 'tolower($0) ~ /^x-robots-tag:/ { sub(/^[^:]*: */, ""); print }'; }
referrer() { "${CURL[@]}" -o /dev/null -D - "$URL$1" | tr -d '\r' | awk 'tolower($0) ~ /^referrer-policy:/ { sub(/^[^:]*: */, ""); print }'; }
cache() { "${CURL[@]}" -o /dev/null -D - "$URL$1" | tr -d '\r' | awk 'tolower($0) ~ /^cache-control:/ { sub(/^[^:]*: */, ""); print }'; }
# переключатель языка: куда ведут все ссылки «EN»/«ES» страницы (одна строка — у всех один адрес)
switch_to() { "${CURL[@]}" "$URL$1" | grep -o "<a href=\"[^\"]*\" lang=\"$2\">${2^^}</a>" | sort -u | sed 's/^<a href="\([^"]*\)".*/\1/'; }
no_location() {  # ответ вообще без заголовка Location
  if [ -z "$(location "$1")" ]; then echo ok; else echo "has-location:$(location "$1")"; fi
}

for path in / /one-card /yes-no /love /daily /cards/the-moon /cards/ace-of-cups /es /es/si-o-no /es/amor \
  /es/carta-del-dia /es/cartas/la-luna /data/daily-en.json /data/daily-es.json /cards/back.svg \
  /diary /es/diario /account /es/cuenta; do
  expect "$path" "$(status "$path")" 200
done
expect "/es — испанская главная" "$(html_lang /es)" '<html lang="es"'
# stage 6: новые адреса, sitemap.xml и robots.txt
for path in /cards /cards/major-arcana /yes-no/cards /es/cartas /es/cartas/arcanos-mayores /es/tiradas/3-cartas \
  /sitemap.xml /robots.txt; do
  expect "$path" "$(status "$path")" 200
done
canonical() { "${CURL[@]}" "$URL$1" | grep -o '<link rel="canonical" href="[^"]*"' | head -1 | sed 's/.*href="\([^"]*\)"/\1/'; }
# файл и папка с одним именем (cards.html и cards/, yes-no.html и yes-no/, es/cartas.html и es/cartas/): Caddy
# отдаёт файл, адреса внутри папки — свои страницы, слэш в конце уводит на адрес без слэша
expect "/cards — хаб, не папка" "$(canonical /cards)" "https://arcanadiary.com/cards"
expect "/cards/the-moon — страница карты" "$(canonical /cards/the-moon)" "https://arcanadiary.com/cards/the-moon"
expect "/cards/major-arcana — старшие арканы" "$(canonical /cards/major-arcana)" "https://arcanadiary.com/cards/major-arcana"
expect "/yes-no — инструмент" "$(canonical /yes-no)" "https://arcanadiary.com/yes-no"
expect "/yes-no/cards — справочник" "$(canonical /yes-no/cards)" "https://arcanadiary.com/yes-no/cards"
expect "/es/cartas — хаб ES" "$(canonical /es/cartas)" "https://arcanadiary.com/es/cartas"
expect "/es/cartas/la-luna — карта ES" "$(canonical /es/cartas/la-luna)" "https://arcanadiary.com/es/cartas/la-luna"
expect "/cards/ → /cards" "$(moved_to /cards/)" "308 $URL/cards"
expect "/yes-no/cards/ → /yes-no/cards" "$(moved_to /yes-no/cards/)" "308 $URL/yes-no/cards"
expect "/es/cartas/ → /es/cartas" "$(moved_to /es/cartas/)" "308 $URL/es/cartas"
expect "/es/tiradas/3-cartas.html → без .html" "$(moved_to /es/tiradas/3-cartas.html)" "308 $URL/es/tiradas/3-cartas"
# папка без своей страницы — 404 на своём языке, без перенаправления
expect "/es/tiradas — только папка" "$(status /es/tiradas)" 404
expect "/es/tiradas — страница 404 ES" "$(html_lang /es/tiradas)" '<html lang="es"'
expect "robots.txt называет sitemap" "$("${CURL[@]}" "$URL/robots.txt" | grep -c '^Sitemap: https://arcanadiary.com/sitemap.xml$')" 1
expect "sitemap.xml без дневника" "$("${CURL[@]}" "$URL/sitemap.xml" | grep -c '/diary<')" 0
expect "/nope" "$(status /nope)" 404
expect "/nope — страница 404 EN" "$(html_lang /nope)" '<html lang="en"'
expect "/es/nope" "$(status /es/nope)" 404
expect "/es/nope — страница 404 ES" "$(html_lang /es/nope)" '<html lang="es"'
for path in /index /404 /es/404; do
  expect "$path — дубль, 404" "$(status "$path")" 404
done
expect "/index — страница 404 EN" "$(html_lang /index)" '<html lang="en"'
expect "/404 — страница 404 EN" "$(html_lang /404)" '<html lang="en"'
expect "/es/404 — страница 404 ES" "$(html_lang /es/404)" '<html lang="es"'
expect "/cards/no-such-card" "$(status /cards/no-such-card)" 404
expect "/es/ → /es" "$(moved_to /es/)" "308 $URL/es"
expect "/one-card/ → /one-card" "$(moved_to /one-card/)" "308 $URL/one-card"
expect "/one-card.html → /one-card" "$(moved_to /one-card.html)" "308 $URL/one-card"
expect "/cards/the-moon.html → /cards/the-moon" "$(moved_to /cards/the-moon.html)" "308 $URL/cards/the-moon"
expect "/es/cartas/la-luna/ → без слэша" "$(moved_to /es/cartas/la-luna/)" "308 $URL/es/cartas/la-luna"
expect "/index.html → /" "$(moved_to /index.html)" "308 $URL/"
# R4: строка запроса сохраняется
expect "/es/?utm_source=x → /es?utm_source=x" "$(moved_to '/es/?utm_source=x')" "308 $URL/es?utm_source=x"
expect "/one-card.html?a=1&b=2 → /one-card?a=1&b=2" "$(moved_to '/one-card.html?a=1&b=2')" "308 $URL/one-card?a=1&b=2"
expect "/index.html?utm_source=x → /?utm_source=x" "$(moved_to '/index.html?utm_source=x')" "308 $URL/?utm_source=x"
# в самом заголовке нет лишнего "?" без запроса
expect "Location /es/ без хвоста ?" "$(location /es/ | sed 's/^[Ll]ocation: *//')" "/es"
expect "Location /index.html без хвоста ?" "$(location /index.html | sed 's/^[Ll]ocation: *//')" "/"
expect "Location /es/?utm_source=x" "$(location '/es/?utm_source=x' | sed 's/^[Ll]ocation: *//')" "/es?utm_source=x"
# R1: чужие адреса не попадают в Location
expect "/%5Cexample.com/ → 404" "$(status /%5Cexample.com/)" 404
expect "/%5Cexample.com/ без Location" "$(location /%5Cexample.com/ | wc -l)" 0
expect "/%5Cexample.com/x.html → 404" "$(status /%5Cexample.com/x.html)" 404
expect "/%5Cexample.com/x.html без Location" "$(location /%5Cexample.com/x.html | wc -l)" 0
expect "//example.com/ без Location" "$(no_location //example.com/)" ok
expect "//example.com/ не уходит на чужой адрес" "$(status //example.com/ | grep -c '^30')" 0
expect "/%2F%2Fexample.com/ без Location" "$(no_location /%2F%2Fexample.com/)" ok
expect "/%2F%2Fexample.com/ не уходит на чужой адрес" "$(status /%2F%2Fexample.com/ | grep -c '^30')" 0
expect "//example.com/x.html без Location" "$(no_location //example.com/x.html)" ok
expect "/%2F%2Fexample.com/x.html без Location" "$(no_location /%2F%2Fexample.com/x.html)" ok
expect "/..%2F..%2Fexample.com/ без Location" "$(no_location /..%2F..%2Fexample.com/)" ok
# stage 4.4b: дневник и аккаунт — noindex и в заголовке, и в HTML; no-store (кнопка «Назад» после выхода не
# показывает почту из кэша); строгие адреса и 404 по языку, как у остальных
for path in /diary /es/diario /account /es/cuenta; do
  expect "$path — X-Robots-Tag" "$(robots "$path")" "noindex, nofollow"
  expect "$path — Referrer-Policy" "$(referrer "$path")" "same-origin"
  expect "$path — Cache-Control" "$(cache "$path")" "no-store"
  expect "$path — meta robots" "$("${CURL[@]}" "$URL$path" | grep -c 'name="robots" content="noindex, nofollow"')" 1
done
expect "/ — без X-Robots-Tag (LAUNCHED=true)" "$(robots /)" ""
expect "/ — без Referrer-Policy" "$(referrer /)" ""
expect "/ — без Cache-Control: no-store" "$(cache /)" ""
expect "/diary?claim=… — X-Robots-Tag" "$(robots '/diary?claim=abc_DEF-1&remind=1')" "noindex, nofollow"
expect "/diary?claim=… — Cache-Control" "$(cache '/diary?claim=abc_DEF-1&remind=1')" "no-store"
expect "/es/diario — страница ES" "$(html_lang /es/diario)" '<html lang="es"'
expect "/es/cuenta — страница ES" "$(html_lang /es/cuenta)" '<html lang="es"'
expect "/diary — страница EN" "$(html_lang /diary)" '<html lang="en"'
expect "/account — страница EN" "$(html_lang /account)" '<html lang="en"'
# пары языков в переключателе: /diary ↔ /es/diario, /account ↔ /es/cuenta
expect "/diary — переключатель на /es/diario" "$(switch_to /diary es)" /es/diario
expect "/es/diario — переключатель на /diary" "$(switch_to /es/diario en)" /diary
expect "/account — переключатель на /es/cuenta" "$(switch_to /account es)" /es/cuenta
expect "/es/cuenta — переключатель на /account" "$(switch_to /es/cuenta en)" /account
expect "/diary?claim=…&remind=1" "$(status '/diary?claim=abc_DEF-1&remind=1')" 200
expect "/diary/ → /diary" "$(moved_to /diary/)" "308 $URL/diary"
expect "/es/cuenta.html → /es/cuenta" "$(moved_to /es/cuenta.html)" "308 $URL/es/cuenta"
expect "/diary/?claim=x → /diary?claim=x" "$(moved_to '/diary/?claim=x')" "308 $URL/diary?claim=x"
expect "/es/diario/nada" "$(status /es/diario/nada)" 404
expect "/es/diario/nada — страница 404 ES" "$(html_lang /es/diario/nada)" '<html lang="es"'
expect "/diary/nope" "$(status /diary/nope)" 404
expect "/diary/nope — страница 404 EN" "$(html_lang /diary/nope)" '<html lang="en"'
# /api/* идёт к API раньше этих правил, 404 API проходит без изменений
expect "/api/ с заглушкой: 404 API без изменений" "$(status /api/limits)" 404
expect "/api/ тело ответа API" "$("${CURL[@]}" "$URL/api/limits")" "api-404"
expect "/api/ заголовок API" "$("${CURL[@]}" -o /dev/null -D - "$URL/api/limits" | grep -ci '^x-stub-api: yes')" 1
expect "/api/limits/ не перенаправляется" "$(status /api/limits/)" 404
expect "/api/x.html не перенаправляется" "$(status /api/x.html)" 404
expect "/api/limits/ идёт к API" "$("${CURL[@]}" "$URL/api/limits/")" "api-404"

if [ "$fails" -eq 0 ]; then echo "OK: адреса страниц и 404"; else echo "ПРОВАЛ: $fails"; exit 1; fi
