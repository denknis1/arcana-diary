#!/usr/bin/env bash
# Деплой: код из main → пароль стенда → сборка сайта → контейнеры → проверка индексации.
set -euo pipefail
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"  # до любого cd
ROOT="$(cd "$(dirname "$SELF")/.." && pwd)"
cd "$ROOT"
before="$(sha256sum "$SELF")"
git pull --ff-only
# git pull мог заменить сам deploy.sh: тогда запускаем свежую версию (один раз), иначе новые строки не сработают
if [ -z "${DEPLOY_REEXEC:-}" ] && [ "$before" != "$(sha256sum "$SELF")" ]; then
  DEPLOY_REEXEC=1 exec "$SELF" "$@"
fi
deploy/gen-stage-auth.sh
deploy/build-site.sh
cd deploy
docker compose up -d --build
# одиночный bind-mount Caddyfile держит старый файл после git pull: при отличии пересоздаём Caddy, иначе reload
if docker compose exec -T caddy cat /etc/caddy/Caddyfile | cmp -s - Caddyfile; then
  docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
else
  docker compose up -d --force-recreate caddy
fi
# Первый выпуск сертификата Let's Encrypt может занять до минуты.
for attempt in 1 2 3 4 5 6; do
  if ./check-indexing.sh; then exit 0; fi
  echo "Попытка $attempt не прошла, жду 10 секунд"
  sleep 10
done
echo "Проверка индексации не прошла — деплой считается проваленным"
exit 1
