#!/usr/bin/env bash
# Деплой: код из main → пароль стенда → сборка сайта → контейнеры → проверка индексации.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
git pull --ff-only
deploy/gen-stage-auth.sh
deploy/build-site.sh
cd deploy
docker compose up -d --build
# одиночный bind-mount Caddyfile держит старый файл после git pull: при отличии пересоздаём Caddy
docker compose exec -T caddy cat /etc/caddy/Caddyfile | cmp -s - Caddyfile || docker compose up -d --force-recreate caddy
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
# Первый выпуск сертификата Let's Encrypt может занять до минуты.
for attempt in 1 2 3 4 5 6; do
  if ./check-indexing.sh; then exit 0; fi
  echo "Попытка $attempt не прошла, жду 10 секунд"
  sleep 10
done
echo "Проверка индексации не прошла — деплой считается проваленным"
exit 1
