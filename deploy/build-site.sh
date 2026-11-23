#!/usr/bin/env bash
# Собирает site/dist в контейнере node:22; Node на хост не ставится. До сборки — данные сайта совпадают с
# источниками (tools/site/sync_site_data.py --check: тексты, факты из api/app/config.py), после — проверка
# собранного сайта (tools/site/check_dist.py: страницы, head, hreflang, JSON-LD, метки, sitemap.xml, robots.txt); ссылки матрицы этапа 2 (tools/site/check_links.py).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/tools/site/sync_site_data.py" --check
docker run --rm -u "$(id -u):$(id -g)" \
  -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 \
  -v "$ROOT/site:/app" -w /app node:22 \
  sh -c 'if [ -f package-lock.json ]; then npm ci; else npm install; fi && npm run build'
# открытый сайт (LAUNCHED=true в deploy/.env; grep -qx ничего не печатает): скрытая служебная страница и robots.txt
# с «Disallow: /» — ошибка сборки (решения 13 и 35)
LAUNCHED_FLAG=""
if [ -f "$ROOT/deploy/.env" ] && grep -qx 'LAUNCHED=true' "$ROOT/deploy/.env"; then LAUNCHED_FLAG="--launched"; fi
python3 "$ROOT/tools/site/check_dist.py" $LAUNCHED_FLAG
python3 "$ROOT/tools/site/check_links.py"
