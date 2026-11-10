#!/usr/bin/env bash
# Пишет deploy/caddy/stage_auth.caddy с bcrypt-хэшем пароля стенда из deploy/.env.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$DIR/.env"; set +a
hash="$(docker run --rm caddy:2.8.4 caddy hash-password --plaintext "$STAGE_PASSWORD")"
printf 'basic_auth {\n\t%s %s\n}\n' "$STAGE_USER" "$hash" > "$DIR/caddy/stage_auth.caddy"
chmod 600 "$DIR/caddy/stage_auth.caddy"
echo "stage_auth.caddy обновлён"
