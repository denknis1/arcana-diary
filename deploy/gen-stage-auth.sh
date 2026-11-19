#!/usr/bin/env bash
# Пишет deploy/caddy/stage_auth.caddy (в git не попадает): bcrypt-хэш пароля стенда из deploy/.env и новый
# случайный секрет куки стенда ad_stage. Кука ставится только на страницы, которые открылись после пароля; с ней
# запросы к /api/* проходят без Basic, поэтому вошедший может слать Authorization: Bearer (этап 4.3, решение
# владельца 19.11.2026). Секрет меняется при каждом деплое — после деплоя страница один раз снова просит пароль.
# ENV_FILE и OUT — только для deploy/test-stage-auth.sh.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${ENV_FILE:-$DIR/.env}"
OUT="${OUT:-$DIR/caddy/stage_auth.caddy}"
set -a; . "$ENV_FILE"; set +a
hash="$(docker run --rm caddy:2.8.4 caddy hash-password --plaintext "$STAGE_PASSWORD")"
secret="$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
[ ${#secret} -eq 64 ] || { echo "no secret" >&2; exit 1; }
umask 077
tmp="$(mktemp "$OUT.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
{
  printf 'vars stage_cookie "ad_stage=%s; Path=/; Max-Age=604800; Secure; HttpOnly; SameSite=Lax"\n' "$secret"
  printf '@stage_locked not header_regexp Cookie `(^|;\\s*)ad_stage=%s(;|$)`\n' "$secret"
  printf 'basic_auth @stage_locked {\n\t%s %s\n}\n' "$STAGE_USER" "$hash"
} > "$tmp"
chmod 600 "$tmp"
mv "$tmp" "$OUT"
echo "stage_auth.caddy обновлён"
