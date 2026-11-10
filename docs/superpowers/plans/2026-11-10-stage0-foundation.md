# Этап 0: фундамент и закрытый стенд — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `arcanadiary.com` отдаётся с этого сервера закрытым паролем и `noindex`, `api.arcanadiary.com/health` отвечает, а `deploy/check-indexing.sh` проверяет это на живом домене.

**Architecture:** Docker Compose из двух контейнеров: Caddy (HTTPS, раздача собранного Astro, Basic Auth, заголовки) и API на FastAPI. Режим «до/после запуска» переключается одной переменной `LAUNCHED` в `deploy/.env`: Caddyfile импортирует фрагмент `noindex-{$LAUNCHED}.caddy` и `auth-{$LAUNCHED}.caddy`. Домен тоже берётся из `.env` (`SITE_DOMAIN`), поэтому всё проверяется сначала на тестовом `arcana.test` с локальными сертификатами, без риска открыть боевой домен.

**Tech Stack:** Caddy 2.8.4 (Docker), Python 3.12 + FastAPI 0.115.6 + uvicorn 0.34.0, pytest 8.3.4, Astro 5 (сборка в `node:22`), bash + curl.

Спецификация: `docs/superpowers/specs/2026-11-10-stage0-foundation-design.md`.

## Global Constraints

- Сервер: 206.189.104.166, Ubuntu 24.04, Docker и Compose есть, Node на хост не ставить.
- До запуска (`LAUNCHED=false`): `arcanadiary.com` — 401 без пароля, `X-Robots-Tag: noindex, nofollow` на всех ответах, включая 401.
- `www.arcanadiary.com` → 301 на `https://arcanadiary.com{uri}` в любом режиме, без пароля; до запуска с `noindex`.
- `api.arcanadiary.com` — `X-Robots-Tag: noindex, nofollow` всегда, без пароля.
- `robots.txt` никогда не содержит `Disallow: /`.
- Пароль стенда только в `deploy/.env` и сгенерированном `deploy/caddy/stage_auth.caddy`; оба в `.gitignore`.
- Коммиты от имени «Arcana Diary», в конце сообщения строка `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Push: `git push` (remote `origin` = `git@github-arcana:denknis1/arcana-diary.git`).

## Карта файлов

| Файл | Ответственность |
|---|---|
| `.gitignore` | Секреты, сборки, окружения |
| `api/app/main.py` | FastAPI-приложение, `GET /health` |
| `api/tests/test_health.py` | Тест `/health` |
| `api/requirements.txt`, `api/requirements-dev.txt`, `api/pytest.ini` | Зависимости и настройки тестов |
| `api/Dockerfile`, `api/.dockerignore` | Образ API |
| `site/package.json`, `site/astro.config.mjs` | Проект Astro |
| `site/src/pages/index.astro` | Страница-заглушка |
| `site/public/robots.txt` | robots без запретов |
| `deploy/build-site.sh` | Сборка сайта в контейнере `node:22` |
| `deploy/check-indexing.sh` | Проверка живого домена по режиму из `.env` |
| `deploy/Caddyfile` | Три сайта: apex, www, api |
| `deploy/caddy/*.caddy` | Фрагменты режимов: `global-{local,acme}`, `noindex-{false,true}`, `auth-{false,true}` |
| `deploy/gen-stage-auth.sh` | Генерация `deploy/caddy/stage_auth.caddy` с хэшем пароля |
| `deploy/docker-compose.yml` | Контейнеры caddy и api |
| `deploy/.env.example` | Шаблон переменных без секретов |
| `deploy/deploy.sh` | Pull → пароль → сборка → compose → проверка |
| `README.md` | Как деплоить и как запускать сайт |

---

### Task 1: API с `/health`

**Files:**
- Create: `.gitignore`, `api/requirements.txt`, `api/requirements-dev.txt`, `api/pytest.ini`, `api/app/__init__.py`, `api/app/main.py`, `api/Dockerfile`, `api/.dockerignore`
- Test: `api/tests/test_health.py`

**Interfaces:**
- Produces: ASGI-приложение `app.main:app`; `GET /health` → `200 {"status": "ok"}`; образ слушает порт 8000.

- [ ] **Step 1: Создать `.gitignore` и зависимости**

`.gitignore`:
```
deploy/.env
deploy/caddy/stage_auth.caddy
site/node_modules/
site/dist/
site/.astro/
api/.venv/
__pycache__/
.pytest_cache/
```

`api/requirements.txt`:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
```

`api/requirements-dev.txt`:
```
-r requirements.txt
pytest==8.3.4
httpx==0.28.1
```

`api/pytest.ini`:
```
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 2: Написать падающий тест**

`api/tests/test_health.py`:
```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Поставить окружение и убедиться, что тест падает**

Run:
```bash
cd ~/arcana-diary/api && python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt && .venv/bin/pytest -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 4: Минимальная реализация**

`api/app/__init__.py` — пустой файл.

`api/app/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Arcana Diary API", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Тест проходит**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q`
Expected: `1 passed`.

- [ ] **Step 6: Образ API**

`api/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
USER nobody
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`api/.dockerignore`:
```
.venv
tests
__pycache__
.pytest_cache
```

Run:
```bash
cd ~/arcana-diary/api && docker build -q -t arcana-api:test . && docker run -d --rm --name arcana-api-test -p 127.0.0.1:18000:8000 arcana-api:test && sleep 3 && curl -s http://127.0.0.1:18000/health; docker stop arcana-api-test
```
Expected: `{"status":"ok"}`.

- [ ] **Step 7: Commit**

```bash
cd ~/arcana-diary && git add .gitignore api && git commit -m "feat(api): health endpoint with test and image

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Сайт-заглушка на Astro

**Files:**
- Create: `site/package.json`, `site/astro.config.mjs`, `site/src/pages/index.astro`, `site/public/robots.txt`, `deploy/build-site.sh`
- Generated and committed: `site/package-lock.json`

**Interfaces:**
- Produces: `deploy/build-site.sh` (без аргументов) собирает `site/dist/` с `index.html` и `robots.txt`.

- [ ] **Step 1: Файлы проекта**

`site/package.json`:
```json
{
  "name": "arcana-diary-site",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "astro build"
  },
  "dependencies": {
    "astro": "^5.1.0"
  }
}
```

`site/astro.config.mjs`:
```js
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://arcanadiary.com',
  output: 'static',
});
```

`site/src/pages/index.astro`:
```astro
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Arcana Diary</title>
  </head>
  <body>
    <main>
      <h1>Arcana Diary</h1>
      <p>Coming soon.</p>
    </main>
  </body>
</html>
```

`site/public/robots.txt` (пустой `Disallow:` = разрешить всё, `c02.02`):
```
User-agent: *
Disallow:
```

- [ ] **Step 2: Скрипт сборки**

`deploy/build-site.sh`:
```bash
#!/usr/bin/env bash
# Собирает site/dist в контейнере node:22; Node на хост не ставится.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
docker run --rm -u "$(id -u):$(id -g)" \
  -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 \
  -v "$ROOT/site:/app" -w /app node:22 \
  sh -c 'if [ -f package-lock.json ]; then npm ci; else npm install; fi && npm run build'
```

Run: `chmod +x ~/arcana-diary/deploy/build-site.sh`

- [ ] **Step 3: Собрать и проверить результат**

Run:
```bash
~/arcana-diary/deploy/build-site.sh && ls ~/arcana-diary/site/dist && cat ~/arcana-diary/site/dist/robots.txt && grep -c 'Coming soon' ~/arcana-diary/site/dist/index.html
```
Expected: в `dist` есть `index.html` и `robots.txt`; robots из двух строк выше; `1`. Появился `site/package-lock.json`.

- [ ] **Step 4: Commit**

```bash
cd ~/arcana-diary && git add site deploy/build-site.sh && git commit -m "feat(site): Astro stub page and allow-all robots.txt

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Шлюз Caddy и проверка индексации

Проверочный скрипт пишется первым: это тест, который падает, пока Caddy не настроен. Всё прогоняется на `arcana.test` с `TLS_MODE=local`, боевой домен не трогаем.

**Files:**
- Create: `deploy/check-indexing.sh`, `deploy/.env.example`, `deploy/Caddyfile`, `deploy/caddy/global-local.caddy`, `deploy/caddy/global-acme.caddy`, `deploy/caddy/noindex-false.caddy`, `deploy/caddy/noindex-true.caddy`, `deploy/caddy/auth-false.caddy`, `deploy/caddy/auth-true.caddy`, `deploy/gen-stage-auth.sh`, `deploy/docker-compose.yml`
- Local only (gitignored): `deploy/.env`, `deploy/caddy/stage_auth.caddy`

**Interfaces:**
- Consumes: образ из `api/Dockerfile` (порт 8000), `site/dist/` из Task 2.
- Produces: `deploy/.env` с ключами `SITE_DOMAIN`, `TLS_MODE` (`local`|`acme`), `LAUNCHED` (`false`|`true`), `STAGE_USER`, `STAGE_PASSWORD`; `deploy/check-indexing.sh` (код выхода 0 = все проверки прошли); `deploy/gen-stage-auth.sh`.

- [ ] **Step 1: Проверочный скрипт**

`deploy/check-indexing.sh`:
```bash
#!/usr/bin/env bash
# Проверяет закрытие от индексации на живом домене. Режим и домен — из deploy/.env.
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$DIR/.env"; set +a
D="$SITE_DOMAIN"

CURL=(curl -sS --max-time 15)
if [ "$TLS_MODE" = "local" ]; then
  CURL+=(-k --resolve "$D:443:127.0.0.1" --resolve "www.$D:443:127.0.0.1" --resolve "api.$D:443:127.0.0.1")
fi
AUTH=(-u "$STAGE_USER:$STAGE_PASSWORD")

fails=0
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; fails=$((fails + 1)); }
expect() { if [ "$2" = "$3" ]; then pass "$1 ($2)"; else fail "$1: ожидалось '$3', получено '$2'"; fi; }
status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$@"; }
# header <Имя> <аргументы curl...> — значение заголовка ответа
header() {
  local name; name="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"; shift
  "${CURL[@]}" -o /dev/null -D - "$@" | tr -d '\r' \
    | awk -v h="$name" 'index(tolower($0), h ": ") == 1 { print substr($0, length(h) + 3) }'
}
has_noindex() { case "$1" in *noindex*) echo yes ;; *) echo no ;; esac; }

expect "api /health" "$(status "https://api.$D/health")" 200
expect "api noindex" "$(has_noindex "$(header X-Robots-Tag "https://api.$D/health")")" yes
expect "www -> 301" "$(status "https://www.$D/some/path")" 301
expect "www Location" "$(header Location "https://www.$D/some/path")" "https://$D/some/path"

if [ "$LAUNCHED" = "false" ]; then
  expect "сайт без пароля" "$(status "https://$D/")" 401
  expect "401 несёт noindex" "$(has_noindex "$(header X-Robots-Tag "https://$D/")")" yes
  expect "401 просит пароль" "$( [ -n "$(header WWW-Authenticate "https://$D/")" ] && echo yes || echo no)" yes
  expect "сайт с паролем" "$(status "${AUTH[@]}" "https://$D/")" 200
  expect "сайт с паролем noindex" "$(has_noindex "$(header X-Robots-Tag "${AUTH[@]}" "https://$D/")")" yes
  expect "www noindex" "$(has_noindex "$(header X-Robots-Tag "https://www.$D/")")" yes
else
  expect "сайт открыт" "$(status "https://$D/")" 200
  expect "нет noindex в заголовке" "$(has_noindex "$(header X-Robots-Tag "https://$D/")")" no
  expect "нет noindex в HTML" "$(has_noindex "$("${CURL[@]}" "https://$D/")")" no
  expect "robots.txt" "$(status "https://$D/robots.txt")" 200
  if "${CURL[@]}" "https://$D/robots.txt" | tr -d '\r' | grep -qiE '^Disallow:[[:space:]]*/[[:space:]]*$'; then
    fail "robots.txt содержит Disallow: /"
  else
    pass "robots.txt без Disallow: /"
  fi
fi

if [ "$fails" -eq 0 ]; then echo "OK: все проверки пройдены"; else echo "ПРОВАЛ: $fails"; exit 1; fi
```

`deploy/.env.example`:
```
# arcana.test + local — локальная проверка; arcanadiary.com + acme — боевой режим
SITE_DOMAIN=arcanadiary.com
TLS_MODE=acme
# false — до запуска (пароль + noindex), true — после запуска
LAUNCHED=false
STAGE_USER=arcana
STAGE_PASSWORD=
```

Run:
```bash
cd ~/arcana-diary/deploy && chmod +x check-indexing.sh \
  && cp .env.example .env && chmod 600 .env \
  && sed -i "s/^STAGE_PASSWORD=.*/STAGE_PASSWORD=$(openssl rand -hex 16)/; s/^SITE_DOMAIN=.*/SITE_DOMAIN=arcana.test/; s/^TLS_MODE=.*/TLS_MODE=local/" .env
```

- [ ] **Step 2: Проверка падает**

Run: `~/arcana-diary/deploy/check-indexing.sh; echo "exit=$?"`
Expected: строки `FAIL` (статусы `000`, сервер не запущен), `exit=1`.

- [ ] **Step 3: Caddyfile и фрагменты режимов**

`deploy/Caddyfile`:
```
{
	import /etc/caddy/parts/global-{$TLS_MODE}.caddy
}

{$SITE_DOMAIN} {
	import /etc/caddy/parts/noindex-{$LAUNCHED}.caddy
	import /etc/caddy/parts/auth-{$LAUNCHED}.caddy
	root * /srv/site
	file_server
	handle_errors {
		import /etc/caddy/parts/noindex-{$LAUNCHED}.caddy
		respond "{err.status_code} {err.status_text}"
	}
}

www.{$SITE_DOMAIN} {
	import /etc/caddy/parts/noindex-{$LAUNCHED}.caddy
	redir https://{$SITE_DOMAIN}{uri} permanent
}

api.{$SITE_DOMAIN} {
	header X-Robots-Tag "noindex, nofollow"
	reverse_proxy api:8000
}
```

`deploy/caddy/global-local.caddy` (самоподписанные сертификаты для `arcana.test`):
```
local_certs
```

`deploy/caddy/global-acme.caddy` (Let's Encrypt по умолчанию; строка нужна, чтобы файл не был пустым):
```
admin localhost:2019
```

`deploy/caddy/noindex-false.caddy`:
```
header X-Robots-Tag "noindex, nofollow"
```

`deploy/caddy/noindex-true.caddy` (после запуска заголовка нет):
```
vars noindex_off true
```

`deploy/caddy/auth-false.caddy`:
```
import /etc/caddy/parts/stage_auth.caddy
```

`deploy/caddy/auth-true.caddy` (после запуска пароля нет):
```
vars auth_off true
```

- [ ] **Step 4: Генерация пароля для Caddy и compose**

`deploy/gen-stage-auth.sh`:
```bash
#!/usr/bin/env bash
# Пишет deploy/caddy/stage_auth.caddy с bcrypt-хэшем пароля стенда из deploy/.env.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
set -a; . "$DIR/.env"; set +a
hash="$(docker run --rm caddy:2.8.4 caddy hash-password --plaintext "$STAGE_PASSWORD")"
printf 'basic_auth {\n\t%s %s\n}\n' "$STAGE_USER" "$hash" > "$DIR/caddy/stage_auth.caddy"
chmod 600 "$DIR/caddy/stage_auth.caddy"
echo "stage_auth.caddy обновлён"
```

`deploy/docker-compose.yml`:
```yaml
name: arcana

services:
  caddy:
    image: caddy:2.8.4
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    environment:
      SITE_DOMAIN: ${SITE_DOMAIN}
      TLS_MODE: ${TLS_MODE}
      LAUNCHED: ${LAUNCHED}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./caddy:/etc/caddy/parts:ro
      - ../site/dist:/srv/site:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - api

  api:
    build: ../api
    restart: unless-stopped
    expose:
      - "8000"

volumes:
  caddy_data:
  caddy_config:
```

Run:
```bash
cd ~/arcana-diary/deploy && chmod +x gen-stage-auth.sh && ./gen-stage-auth.sh \
  && docker run --rm --env-file .env -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$PWD/caddy:/etc/caddy/parts:ro" \
     caddy:2.8.4 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```
Expected: `Valid configuration`.

- [ ] **Step 5: Режим «до запуска» на тестовом домене проходит**

Run:
```bash
cd ~/arcana-diary/deploy && docker compose up -d --build && sleep 5 && ./check-indexing.sh
```
Expected: все строки `PASS`, `OK: все проверки пройдены`.

- [ ] **Step 6: Режим «после запуска» на тестовом домене проходит**

Run:
```bash
cd ~/arcana-diary/deploy && sed -i 's/^LAUNCHED=.*/LAUNCHED=true/' .env && docker compose up -d && sleep 5 && ./check-indexing.sh
```
Expected: все `PASS`, включая «robots.txt без Disallow: /».

- [ ] **Step 7: Вернуть «до запуска» и остановить тестовый стек**

Run:
```bash
cd ~/arcana-diary/deploy && sed -i 's/^LAUNCHED=.*/LAUNCHED=false/' .env && docker compose up -d && sleep 5 && ./check-indexing.sh && docker compose down
```
Expected: `OK: все проверки пройдены`, затем контейнеры остановлены.

- [ ] **Step 8: Commit**

```bash
cd ~/arcana-diary && git add deploy \
  && if git diff --cached --name-only | grep -E '(^|/)\.env$|stage_auth'; then echo "СЕКРЕТ В ИНДЕКСЕ — СТОП"; git reset -q deploy; false; else true; fi \
  && git commit -m "feat(deploy): Caddy gate with LAUNCHED switch and indexing check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: коммит создан, строки «СЕКРЕТ В ИНДЕКСЕ» нет (оба файла в `.gitignore`).

---

### Task 4: Деплой и боевой домен

Требует DNS: `A @` и `A www` → 206.189.104.166, DNS only. Перед Step 3 проверить, что записи есть; если нет — остановиться и попросить пользователя.

**Files:**
- Create: `deploy/deploy.sh`, `README.md`
- Modify (local only): `deploy/.env` — `SITE_DOMAIN=arcanadiary.com`, `TLS_MODE=acme`

**Interfaces:**
- Consumes: `deploy/gen-stage-auth.sh`, `deploy/build-site.sh`, `deploy/check-indexing.sh`, `deploy/docker-compose.yml`.
- Produces: `deploy/deploy.sh` — одна команда деплоя, код выхода 0 только при пройденной проверке.

- [ ] **Step 1: Скрипт деплоя**

`deploy/deploy.sh`:
```bash
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
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
# Первый выпуск сертификата Let's Encrypt может занять до минуты.
for attempt in 1 2 3 4 5 6; do
  if ./check-indexing.sh; then exit 0; fi
  echo "Попытка $attempt не прошла, жду 10 секунд"
  sleep 10
done
echo "Проверка индексации не прошла — деплой считается проваленным"
exit 1
```

`README.md`:
````markdown
# Arcana Diary

ИИ-таро с дневником. План продукта: https://claude.ai/artifact/PtJFSSX4C16tHKvTEqWM7R

## Деплой

```bash
deploy/deploy.sh
```

Скрипт подтягивает `main`, собирает сайт, перезапускает контейнеры и запускает `deploy/check-indexing.sh`.
Настройки — в `deploy/.env` (шаблон `deploy/.env.example`, в git не попадает).

## До запуска

`LAUNCHED=false`: сайт закрыт паролем (`STAGE_USER` / `STAGE_PASSWORD` из `deploy/.env`)
и отдаёт `X-Robots-Tag: noindex, nofollow`. `Disallow: /` в robots.txt не используется никогда.

## Запуск (снятие закрытия)

1. В `deploy/.env` поставить `LAUNCHED=true`.
2. `deploy/deploy.sh` — проверка должна пройти в режиме «после запуска».
3. В первые 5 минут открыть `https://arcanadiary.com/robots.txt` и проверить сайт в Search Console.
````

Run: `chmod +x ~/arcana-diary/deploy/deploy.sh`

- [ ] **Step 2: Commit и push**

```bash
cd ~/arcana-diary && git add deploy/deploy.sh README.md && git commit -m "feat(deploy): one-command deploy with indexing check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push
```

- [ ] **Step 3: Проверить DNS**

Run:
```bash
for h in arcanadiary.com www.arcanadiary.com; do curl -s -H 'accept: application/dns-json' "https://cloudflare-dns.com/dns-query?name=$h&type=A"; echo; done
```
Expected: в обоих ответах `"data":"206.189.104.166"`. Иначе — стоп, попросить пользователя добавить записи.

- [ ] **Step 4: Переключить на боевой домен и задеплоить**

Run:
```bash
cd ~/arcana-diary/deploy && sed -i 's/^SITE_DOMAIN=.*/SITE_DOMAIN=arcanadiary.com/; s/^TLS_MODE=.*/TLS_MODE=acme/; s/^LAUNCHED=.*/LAUNCHED=false/' .env && ./deploy.sh
```
Expected: `OK: все проверки пройдены`, код выхода 0.

- [ ] **Step 5: Проверить снаружи вручную**

Run:
```bash
curl -sI https://arcanadiary.com/ | grep -iE '^HTTP|x-robots|www-auth'; curl -sI https://www.arcanadiary.com/x | grep -iE '^HTTP|location'
```
Expected: `HTTP/2 401`, `x-robots-tag: noindex, nofollow`, `www-authenticate: Basic ...`; для www — `301` и `location: https://arcanadiary.com/x`.
