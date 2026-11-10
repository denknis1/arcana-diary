# Этап 0: фундамент и закрытый стенд — дизайн

Дата: 10.11.2026. Статус: утверждён пользователем в чате 10.11.2026.
План продукта: https://claude.ai/artifact/PtJFSSX4C16tHKvTEqWM7R (запуск EN и ES — 14.12.2026).

## Цель

До запуска сайт на `arcanadiary.com` закрыт паролем и запретом индексации, API отвечает на
`api.arcanadiary.com`, и одна команда проверяет на живом домене, что закрытие на месте.

## Принятые решения

| Решение | Выбор |
|---|---|
| Хостинг | Этот VPS (206.189.104.166, Ubuntu 24.04, Docker), Cloudflare перед ним — позже |
| Стенд | Сразу основной домен `arcanadiary.com`, отдельного staging нет |
| Код | Приватный GitHub `denknis1/arcana-diary`, сервер пушит ключом `~/.ssh/arcana_diary_deploy` |
| Объём страниц | По плану продукта (180 к запуску), не волнами книги — решение пользователя |

## Структура репозитория

```
site/      Astro; на этапе 0 — одна страница-заглушка
api/       FastAPI; на этапе 0 — только GET /health
content/   каталог карт и база значений (этапы 3–4)
deploy/    Caddyfile, docker-compose.yml, deploy.sh, check-indexing.sh, .env.example
docs/      спецификации и планы
```

## Компоненты

**Caddy** (контейнер, порты 80 и 443) — HTTPS через Let's Encrypt, раздаёт собранный `site/dist`,
проксирует `api.arcanadiary.com` в контейнер API.

- `www.arcanadiary.com` → 301 на `https://arcanadiary.com{uri}` в любом режиме, без пароля (редирект
  ничего не раскрывает); до запуска ответ редиректа тоже несёт `X-Robots-Tag: noindex, nofollow`.
- Переменная `LAUNCHED` в `deploy/.env`:
  - `false` (до запуска): на `arcanadiary.com` — Basic Auth (ответ 401 без пароля) и заголовок
    `X-Robots-Tag: noindex, nofollow` на всех ответах, включая 401;
  - `true` (после запуска): ни пароля, ни заголовка.
- `api.arcanadiary.com` — `X-Robots-Tag: noindex, nofollow` всегда, без пароля.
- `robots.txt` сайта никогда не содержит `Disallow: /`.

**API** (контейнер, Python 3.12, FastAPI + uvicorn) — `GET /health` → `200 {"status":"ok"}`. Наружу
порт не открыт, доступ только через Caddy.

**Сборка сайта** — в одноразовом контейнере `node:22`, на хост Node не ставится. Результат — `site/dist`.

**`deploy/deploy.sh`** — `git pull` → сборка сайта → `docker compose up -d --build` → `check-indexing.sh`.
Ненулевой код выхода проверки = провал деплоя.

**`deploy/check-indexing.sh`** — проверка живого домена по режиму из `.env`:

| Режим | Проверка | Ожидание |
|---|---|---|
| до запуска | `GET https://arcanadiary.com/` без пароля | 401 |
| до запуска | то же с паролем | 200 и `X-Robots-Tag` содержит `noindex` |
| до запуска | `GET https://www.arcanadiary.com/` | 301 на apex |
| после запуска | `GET https://arcanadiary.com/` | 200, `X-Robots-Tag` без `noindex`, в HTML нет `noindex` |
| после запуска | `GET /robots.txt` | 200, нет строки `Disallow: /` |
| всегда | `GET https://api.arcanadiary.com/health` | 200 и `noindex` в `X-Robots-Tag` |

## Секреты

Пароль стенда генерируется на сервере и хранится только в `deploy/.env` (в `.gitignore`); в репозитории —
`deploy/.env.example` без значений. Хэш пароля для Caddy вычисляется при деплое.

## Основание (база SEO, «SEO Монстр 2027»)

- 401 — норма для стендов: `textbook-2027/c02.03`, группа В, п. 12.
- noindex и Disallow одновременно нельзя — noindex не будет прочитан: `c02.02`, `c02.03`.
- Забытый `Disallow: /` со staging — вылет из выдачи; проверять robots.txt в первые 5 минут после деплоя:
  `c02.02`, ошибка 13.
- `X-Robots-Tag` для массовой настройки на уровне сервера: `c02.03`.

## Зависимости от пользователя

- DNS: `A @` и `A www` → 206.189.104.166, DNS only (вручную или новым токеном Edit zone DNS).

## Готово, когда

`deploy/check-indexing.sh` в режиме «до запуска» проходит на живом домене, код в `main` на GitHub.

## Вне этапа 0

Cloudflare-прокси, мониторинг, бэкапы базы, GitHub Actions, Supabase, всё содержимое сайта.
