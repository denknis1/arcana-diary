#!/usr/bin/env bash
# Собирает site/dist в контейнере node:22; Node на хост не ставится.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
docker run --rm -u "$(id -u):$(id -g)" \
  -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 \
  -v "$ROOT/site:/app" -w /app node:22 \
  sh -c 'if [ -f package-lock.json ]; then npm ci; else npm install; fi && npm run build'
