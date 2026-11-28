#!/usr/bin/env bash
# Дописывает в deploy/.env ключи VAPID для напоминаний в браузере (этап 8.1): VAPID_PRIVATE_KEY (секрет) и
# VAPID_PUBLIC_KEY. Ключи не печатаются: их пишет Python прямо во временный файл с правами 600, который затем
# дописывается в конец .env; пустые строки `VAPID_PRIVATE_KEY=` / `VAPID_PUBLIC_KEY=` (как в .env.example) считаются
# «ключа нет» и заполняются на месте, без дублей. Если непустой ключ уже есть — ничего не меняет и выходит с кодом 3: новые ключи молча
# отрезали бы все уже оформленные подписки. Запуск — шаг оператора по слову владельца, затем выкладка.
# ENV_FILE и PYTHON — только для deploy/test-gen-vapid.sh.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${ENV_FILE:-$DIR/.env}"
PYTHON="${PYTHON:-$DIR/../api/.venv/bin/python}"
[ -f "$ENV_FILE" ] || { echo "нет файла $(basename "$ENV_FILE")" >&2; exit 1; }
if grep -q '^VAPID_PRIVATE_KEY=.' "$ENV_FILE" || grep -q '^VAPID_PUBLIC_KEY=.' "$ENV_FILE"; then
  echo "ключи VAPID уже есть в $(basename "$ENV_FILE"): ничего не изменено" >&2
  exit 3
fi
umask 077
tmp="$(mktemp "$ENV_FILE.vapid.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
(cd "$DIR/../api" && "$PYTHON" -c '
import sys
from app.webpush import generate_vapid
private, public = generate_vapid()
with open(sys.argv[1], "w", encoding="ascii") as out:
    out.write(f"VAPID_PRIVATE_KEY={private}\nVAPID_PUBLIC_KEY={public}\n")
' "$tmp")
[ "$(grep -c '^VAPID_' "$tmp")" -eq 2 ] || { echo "ключи не созданы" >&2; exit 1; }
if grep -q '^VAPID_\(PRIVATE\|PUBLIC\)_KEY=' "$ENV_FILE"; then
  # empty lines from .env.example: fill them in place, add the missing one; the new file replaces .env atomically
  new="$(mktemp "$ENV_FILE.vapid.XXXXXX")"
  trap 'rm -f "$tmp" "$new"' EXIT
  cp -p "$ENV_FILE" "$new"
  : > "$new"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      VAPID_PRIVATE_KEY=*) grep '^VAPID_PRIVATE_KEY=' "$tmp" ;;
      VAPID_PUBLIC_KEY=*) grep '^VAPID_PUBLIC_KEY=' "$tmp" ;;
      *) printf '%s\n' "$line" ;;
    esac
  done < "$ENV_FILE" >> "$new"
  for name in VAPID_PRIVATE_KEY VAPID_PUBLIC_KEY; do
    grep -q "^$name=" "$new" || grep "^$name=" "$tmp" >> "$new"
  done
  mv "$new" "$ENV_FILE"
else
  { printf '\n# stage 8.1: browser reminders (Web Push, VAPID), made by deploy/gen-vapid.sh; never print or commit\n'; cat "$tmp"; } >> "$ENV_FILE"
fi
echo "ключи VAPID дописаны в $(basename "$ENV_FILE")"
