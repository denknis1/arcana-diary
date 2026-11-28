#!/usr/bin/env bash
# Проверяет deploy/gen-vapid.sh на временном файле: две строки VAPID_ дописаны, прежние строки целы, ключ не попал
# в вывод, пара ключей годится для API, повторный запуск ничего не меняет (код 3). deploy/.env не трогает.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# never the real secrets: the generator must take ENV_FILE, or it would write into deploy/.env
grep -q 'ENV_FILE' "$DIR/gen-vapid.sh" || { echo "gen-vapid.sh has no ENV_FILE: stop"; exit 2; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
printf 'SITE_DOMAIN=arcana.test\nLAUNCHED=false' > "$TMP/.env"  # no newline at the end, as an editor may leave it
fails=0
expect() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1: ожидалось '$3', получено '$2'"; fails=$((fails + 1)); fi; }

out="$(ENV_FILE="$TMP/.env" "$DIR/gen-vapid.sh" 2>&1)"
private="$(sed -n 's/^VAPID_PRIVATE_KEY=//p' "$TMP/.env")"
public="$(sed -n 's/^VAPID_PUBLIC_KEY=//p' "$TMP/.env")"
expect "одна строка VAPID_PRIVATE_KEY" "$(grep -c '^VAPID_PRIVATE_KEY=' "$TMP/.env")" 1
expect "одна строка VAPID_PUBLIC_KEY" "$(grep -c '^VAPID_PUBLIC_KEY=' "$TMP/.env")" 1
expect "прежние строки целы" "$(grep -c -e '^SITE_DOMAIN=arcana.test$' -e '^LAUNCHED=false$' "$TMP/.env")" 2
expect "ключа нет в выводе" "$(printf '%s' "$out" | grep -c -F "$private" || true)" 0
expect "вывод — одна строка" "$out" "ключи VAPID дописаны в .env"
expect "пара годится для API" "$(cd "$DIR/../api" && "${PYTHON:-$DIR/../api/.venv/bin/python}" -c "
from app.webpush import load_vapid
print(load_vapid('$private', '$public') is not None)")" True
before="$(sha256sum "$TMP/.env")"
set +e
ENV_FILE="$TMP/.env" "$DIR/gen-vapid.sh" >/dev/null 2>&1
code=$?
set -e
expect "повтор — код 3" "$code" 3
expect "повтор ничего не меняет" "$(sha256sum "$TMP/.env")" "$before"
expect "временных файлов не осталось" "$(find "$TMP" -name '.env.vapid.*' | wc -l)" 0

# the .env made from .env.example: empty VAPID_ lines are "no key" and are filled in place, with no duplicates
printf 'SITE_DOMAIN=arcana.test\nVAPID_PRIVATE_KEY=\nVAPID_PUBLIC_KEY=\nVAPID_SUBJECT=mailto:a@arcana.test\nLAUNCHED=false\n' > "$TMP/empty.env"
chmod 640 "$TMP/empty.env"
out2="$(ENV_FILE="$TMP/empty.env" "$DIR/gen-vapid.sh" 2>&1)"
private2="$(sed -n 's/^VAPID_PRIVATE_KEY=//p' "$TMP/empty.env")"
public2="$(sed -n 's/^VAPID_PUBLIC_KEY=//p' "$TMP/empty.env")"
expect "пустые строки: одна VAPID_PRIVATE_KEY" "$(grep -c '^VAPID_PRIVATE_KEY=' "$TMP/empty.env")" 1
expect "пустые строки: одна VAPID_PUBLIC_KEY" "$(grep -c '^VAPID_PUBLIC_KEY=' "$TMP/empty.env")" 1
expect "пустые строки: ключи непустые" "$([ -n "$private2" ] && [ -n "$public2" ] && echo yes)" yes
expect "пустые строки: остальные строки и порядок целы" "$(grep -v '^VAPID_P' "$TMP/empty.env" | tr '\n' ' ')" "SITE_DOMAIN=arcana.test VAPID_SUBJECT=mailto:a@arcana.test LAUNCHED=false "
expect "пустые строки: строки на своих местах" "$(grep -n '^VAPID_P' "$TMP/empty.env" | cut -d: -f1 | tr '\n' ' ')" "2 3 "
expect "пустые строки: права файла прежние" "$(stat -c %a "$TMP/empty.env")" 640
expect "пустые строки: ключа нет в выводе" "$(printf '%s' "$out2" | grep -c -F "$private2" || true)" 0
expect "пустые строки: пара годится для API" "$(cd "$DIR/../api" && "${PYTHON:-$DIR/../api/.venv/bin/python}" -c "
from app.webpush import load_vapid
print(load_vapid('$private2', '$public2') is not None)")" True
before2="$(sha256sum "$TMP/empty.env")"
set +e
ENV_FILE="$TMP/empty.env" "$DIR/gen-vapid.sh" >/dev/null 2>&1
code2=$?
set -e
expect "заполненные строки: повтор — код 3" "$code2" 3
expect "заполненные строки: ничего не меняется" "$(sha256sum "$TMP/empty.env")" "$before2"
# only the private line is empty and the public one is missing: the private is filled in place, the public added
printf 'A=1\nVAPID_PRIVATE_KEY=\nB=2\n' > "$TMP/half.env"
ENV_FILE="$TMP/half.env" "$DIR/gen-vapid.sh" >/dev/null 2>&1
expect "половина: по одной строке каждого ключа" "$(grep -c '^VAPID_P[A-Z]*_KEY=.' "$TMP/half.env")" 2
expect "временных файлов не осталось (пустые строки)" "$(find "$TMP" -name '*.vapid.*' | wc -l)" 0
[ "$fails" -eq 0 ] && echo "OK: gen-vapid.sh" || { echo "FAIL: $fails"; exit 1; }
