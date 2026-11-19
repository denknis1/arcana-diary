# Arcana Diary API

FastAPI-сервис расклада и ИИ-чтеца (этап 4.2), входа, дневника и аккаунта (этап 4.3). Спецификации —
`docs/superpowers/specs/2026-11-14-stage4-2-reader-design.md` (раздел 8 — решения после проверки Fable 5.2) и
`docs/superpowers/specs/2026-11-19-stage4-3-accounts-diary-design.md`; планы —
`docs/superpowers/plans/2026-11-14-stage4-2-reader.md` и `docs/superpowers/plans/2026-11-19-stage4-3-accounts-diary.md`.

## Тесты

```bash
cd ~/arcana-diary/api
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

Тесты с базой поднимают временный контейнер `postgres:16.10-alpine` (нужен Docker) и удаляют его в конце; без Docker
они пропускаются с причиной. Свою пустую базу можно задать через `TEST_DATABASE_URL` — тесты очищают её таблицы.
Ни один тест не обращается к Anthropic, Supabase или Cloudflare: поставщик модели — `FakeProvider`, Turnstile — подделка,
токены входа подписываются тестовым ключом ES256, а ключи подставляются вместо сети (`helpers.FakeJwks`).
`TEST_DATABASE_URL`, похожий на Supabase (`supabase.co`, `pooler.supabase.com`), тесты не трогают — выход с кодом 4,
если не задано `TEST_DATABASE_ALLOW_SUPABASE=yes`.

## Запуск без ключей

```bash
docker run -d --rm --name arcana-dev-pg -e POSTGRES_PASSWORD=dev -p 127.0.0.1:55432:5432 postgres:16.10-alpine
cd ~/arcana-diary/api
READER_PROVIDER=fake DATABASE_URL=postgresql://postgres:dev@127.0.0.1:55432/postgres .venv/bin/uvicorn app.main:app --reload
```

Миграции из `api/migrations/` применяются при старте (если база недоступна — повтор каждые 30 секунд, запросы до
этого получают `503`). `READER_PROVIDER=fake` отвечает заготовленным текстом без вызова модели.

## Переменные окружения

Секреты — только в `deploy/.env` на сервере, в репозиторий не попадают (шаблон — `deploy/.env.example`).

| Переменная | По умолчанию | Что это |
|---|---|---|
| `DATABASE_URL` | пусто | строка подключения Postgres (Supabase: пулер в режиме transaction); пусто — `503` на всё, кроме `/health` |
| `ANTHROPIC_API_KEY` | пусто | ключ Claude API; нужен и при `READER_PROVIDER=openai` или `gemini`: проверка вопроса всегда на Claude |
| `OPENAI_API_KEY` | пусто | ключ OpenAI; обязателен при `READER_PROVIDER=openai` |
| `GOOGLE_AI_API_KEY` | пусто | ключ Google AI (Gemini); обязателен при `READER_PROVIDER=gemini` |
| `READER_PROVIDER` | `claude` | `claude`, `openai`, `gemini` или `fake`; `READER_MODEL` должна быть моделью этого поставщика |
| `READER_MODEL` | `claude-haiku-5-5` | модель чтеца, уточнений и карты дня |
| `READER_EFFORT` | `medium` | `output_config.effort` чтеца (`low` … `max`); сравнить уровни на тестовом наборе |
| `GUARD_MODEL` | `claude-haiku-5-5` | модель проверки вопроса (effort `low`) |
| `JUDGE_MODEL` | `claude-sonnet-5-5` | модель-судья, только для `api/evals` |
| `TURNSTILE_SITEKEY`, `TURNSTILE_SECRET` | пусто | ключи Cloudflare Turnstile; без секрета запрос после порога получает `403` |
| `TRUST_CLOUDFLARE` | `false` | ровно `true` или `false`; `true` — только когда прокси Cloudflare включён: Caddy пускает лишь адреса Cloudflare, API читает `CF-Connecting-IP` и `CF-IPCountry` (см. ниже) |
| `DAILY_BUDGET_USD` | `5` | суточный предел расходов на модель по `llm_calls`; сверх — значения карт из базы (проверка вопроса работает дальше) |
| `GUARD_BUDGET_USD` | `1` | суточный предел расходов на проверку вопроса моделью; сверх — только стоп-фразы, остальные вопросы получают `503 {"reason": "unavailable"}` |
| `FIRST_TOKEN_TIMEOUT_S` | `15` | сколько ждать первых слов чтеца до запасного ответа |
| `GUARD_TIMEOUT_S` | `5` | тайм-аут проверки вопроса (решение владельца 19.11.2026, спецификация §10.10) |
| `CLEANUP_INTERVAL_S` | `3600` | как часто удалять просроченное (гостевые расклады, токены переноса) и возвращать слоты за оборванные платные уточнения |
| `SUPABASE_URL` | пусто | открытый адрес проекта Supabase (`https://<ref>.supabase.co`, не секрет); пусто — вход выключен, любой `Authorization: Bearer` получает `401` |
| `DAILY_JOB_INTERVAL_S` | `3600` | как часто задача карты дня дописывает недостающие тексты; `0` — выключить |
| `RUN_MIGRATIONS` | `true` | применять миграции при старте |
| `CONTENT_DIR`, `BANNED_TERMS_PATH`, `MIGRATIONS_DIR` | пути в репозитории | в образе заданы в `api/Dockerfile` |

## Адреса

`POST /api/readings`, `GET /api/readings/{id}`, `GET /api/readings/{id}/stream` (SSE), `POST /api/readings/{id}/retry`
(SSE), `POST /api/readings/{id}/followups` (SSE), `GET /api/daily?lang=&tz=`, `GET /api/limits?tz=`. Поддомен `api.`
отдаёт только `GET /health`, остальное — `404`. События потока: `meta`, `section`, `text`, `replace`, `fallback`,
`crisis`, `done`, `error`. Все ответы `/api/*`: `Cache-Control: no-store`, `Referrer-Policy: no-referrer`,
`X-Robots-Tag: noindex, nofollow`. Уточнения: два бесплатных к каждому раскладу (обрезанное или заменённое из базы не
считается); каждое следующее тратит один расклад из «3 в день» и только с `"use_reading": true` в запросе — без него
`402 {"reason": "confirm", "remaining": N}`, раскладов не осталось — `402 {"reason": "plus", "remaining": 0}`. Платное
уточнение, которое не удалось (обрыв, замена из базы, по словарю, без ответа), возвращает расклад; кризисный ответ
проверки вопроса расклад не тратит, метка чтеца `[[crisis]]` — тратит; `done` платного уточнения несёт `used_reading`.
Не больше 8 попыток на расклад и 40 в сутки с адреса — `429 {"reason": "attempts"}` / `{"reason": "ip_limit"}`. Сверх
`GUARD_BUDGET_USD` вопрос, которому нужна модель, — `503 {"reason": "unavailable"}` (попытка не тратится). Проверок
вопроса моделью при создании расклада — не больше 60 в сутки с адреса, кризисные ответы тоже считаются и вместе с
раскладами ведут к Turnstile с 20-й; сверх 60 — только стоп-фразы, остальное — `503 {"reason": "unavailable"}`.
Любой `422` — `{"reason": "invalid", "fields": [...]}`.

**Этап 4.3.** Вошедший шлёт `Authorization: Bearer <access token Supabase>`; без заголовка (или с `Basic` пароля
стенда) — гость, как раньше. Токен проверяется на каждом адресе `/api/*` до разбора запроса (и на
`GET /api/daily`). Неверный или просроченный токен — `401 {"reason": "auth"}`, ключи Supabase
недоступны — `503 {"reason": "auth_unavailable"}`, адрес только для вошедших без токена — `401 {"reason": "sign_in"}`.
Лимит: гость — 3 расклада в день на устройство, вошедший — 5 на аккаунт на всех устройствах (`GET /api/limits`
отвечает по аккаунту); платное уточнение берёт слот у владельца расклада. Расклад в аккаунте принадлежит только
аккаунту, гостевой — устройству (кука `ad_guest`); владельцу `GET /api/readings/{id}` отдаёт ещё `in_diary`,
`outcome`, `note`. Перенос:
`POST /api/readings/{id}/claim-token` (только устройство, где сделан расклад; `201 {"token", "expires_at"}`, 7 дней, не больше
5 живых на расклад) и `POST /api/account/claim {"tokens": [...]}` → `{"claimed": [id, ...]}`. Дневник:
`GET /api/diary?before=&limit=` (20, не больше 50; `next_before` — начало следующей страницы),
`PATCH /api/diary/{id} {"outcome": "yes" | "partly" | "no" | null, "note": "…" | null}` (заметка до 1000 знаков,
хранится как есть, отдаётся только в JSON), `DELETE /api/diary/{id}` → `204`; чужой расклад — `404`. Аккаунт:
`GET /api/account?tz=`, `PATCH /api/account {"reminders_consent": bool}`, `GET /api/account/export` (файл JSON),
`DELETE /api/account {"confirm": "DELETE"}` — сразу; журналы `llm_calls` остаются. Список Plus:
`POST /api/plus/waitlist {"email", "lang"}` — повтор без ошибки, не больше 5 заявок с адреса в сутки. Память чтеца:
вошедшему в ввод чтеца и его уточнений добавляется `<history>` — до 5 прошлых раскладов той же темы только с
обычными вопросами (группа `ok`; дата, вопрос, заголовок; без заметок и отметок), промпты `reader.*.v5`,
`followup.*.v5`.

## Ограничения, о которых надо помнить

- **Один процесс uvicorn** (`--workers 1` в `api/Dockerfile`): соль адреса и счётчики всплеска живут в памяти; каждый
  деплой обнуляет счётчик всплеска и меняет соль (счёт по адресу за день начинается заново).
- Маршруты синхронные и работают в пуле потоков Starlette (40 потоков): около 40 одновременных генераций, дальше —
  очередь, включая `/health`. Генерация идёт в своей нити и дописывается, даже если человек закрыл страницу.
- Новое соединение с базой на каждую операцию (3–4 на запрос); пул соединений — когда будет видна нагрузка.
- День гостя — по поясу из браузера: меняя `tz`, один гость может получить расклады «за три дня» сразу (до 9). Это
  допустимо; жёсткий предел — 60 раскладов в сутки с адреса и бюджет `DAILY_BUDGET_USD`.
- Уточнение без `tz` считает день по UTC: сайт должен передавать тот же `tz`, что и при создании расклада. Это то же известное
  ограничение, что и при смене часового пояса.
- Вызов модели, прерванный до отчёта о токенах (тайм-аут, обрыв после текста), пишется в `llm_calls` с верхней
  оценкой цены: `max_tokens` по цене выхода (чтец около $0.002, проверка вопроса около $0.0005) — потолок ошибается в
  безопасную сторону. Ошибка до первого текста (нет соединения, неверный ключ, `429` поставщика) пишется без цены.
- Любой UUID в cookie — «вернувшийся гость»: `GET /api/daily` пишет строку `daily_draws` для каждого нового номера (до
  30 запросов в минуту с адреса), у `GET /api/readings/{id}` и `GET /api/limits` своего предела частоты нет. До запуска
  этого достаточно; после включения прокси — правило ограничения частоты для `/api/*` в Cloudflare.
- Карта дня: первый старт пишет 936 текстов (около $0.30), сначала сегодняшние, потом завтрашние и вчерашние; в первые
  10–20 минут после первого старта `GET /api/daily` может отдавать `"source": "fallback"`. После 5 неудачных вызовов
  подряд (пустой ключ, кончился баланс) задача останавливается до следующего часа.
- Токен доступа Supabase действует до своего `exp` (по умолчанию час), в том числе после удаления аккаунта: сайт
  выходит из аккаунта сразу после `DELETE /api/account`, а API отказывает такому токену (см. ниже).
- Страницы дневника идут по времени создания (`before`): два расклада одного аккаунта с одинаковым до микросекунды
  временем на границе страницы могут разойтись по страницам или пропасть из выдачи.
- Токен аккаунта, удалённого меньше 8 дней назад, получает `401 {"reason": "auth"}` на любую запись (таблица
  `deleted_accounts`); через 8 дней запись о нём стирается — дольше любой срок токена Supabase не бывает.
- Реальный потолок на человека — 3 расклада гостем и 5 вошедшим, то есть 8 в день; новые адреса почты (в том числе
  с `+`) дают новые аккаунты. Ограничивают это, как и смену куки гостем, только предел адреса (60 в сутки, Turnstile
  с 20-го) и суточные бюджеты.

## Перед включением `TRUST_CLOUDFLARE=true`

Флаг включает две вещи сразу: Caddy закрывает соединение с любого адреса вне диапазонов Cloudflare
(`deploy/caddy/cf-true.caddy`, до пароля, сайта и API; на порту 80 фильтра нет — там только перенаправление на HTTPS),
а API берёт адрес клиента из `CF-Connecting-IP` и страну для
контактов помощи из `CF-IPCountry`. Правила `ufw` здесь не помогают: порты 80 и 443 публикует Docker, и его правила
идут в обход цепочек `ufw`. Пока флаг `false`, оба заголовка не читаются: адрес — из соединения (Caddy пишет его в
`X-Real-IP`), контакты — по часовому поясу и языку. Значение — ровно `true` или `false`: API с другим значением не
стартует, Caddy не находит файл `cf-<значение>.caddy`. Если у домена появится запись AAAA, а в Docker не включён IPv6,
соединения Cloudflare по IPv6 придут с адреса моста Docker и будут сброшены: AAAA не добавлять, пока IPv6 в Docker
не включён.

1. Сверить диапазоны в `deploy/caddy/cf-true.caddy` со страницей https://www.cloudflare.com/ips/ на день включения;
   при расхождении поправить файл и закоммитить.
2. За один заход: включить прокси (оранжевое облако) для `arcanadiary.com`, `www` и `api`, SSL/TLS — Full (strict),
   затем `TRUST_CLOUDFLARE=true` в `deploy/.env` и `deploy/deploy.sh`. Между этими действиями все посетители
   приходят с адресов Cloudflare и делят один счётчик адреса (60 раскладов в сутки) — не растягивать.
3. Проверить с любой машины: `curl -sS --max-time 10 --resolve arcanadiary.com:443:<IP сервера> https://arcanadiary.com/`
   — ошибка curl (`Empty reply from server` или `HTTP/2 stream 1 was not closed cleanly`), HTTP-ответа нет; через
   Cloudflare `curl -sS -o /dev/null -w '%{http_code}\n' https://arcanadiary.com/` — `401` до запуска, `200` после.
4. Сертификат: Caddy продлевает его у Let's Encrypt проверкой HTTP-01 на порту 80, а там фильтра нет (только
   перенаправление на HTTPS и ответ на проверку). Через сутки после включения и за 30 дней до конца срока сертификата проверить
   `docker compose logs caddy | grep -iE 'obtain|renew|error'`; если продление не проходит — на время продления
   выключить прокси (серое облако) и вернуть `TRUST_CLOUDFLARE=false`, затем включить обратно по шагу 2.

## Supabase: права после первой миграции

RLS включён на всех таблицах без политик, а `migrate()` отзывает права на таблицы у ролей `anon` и `authenticated`.
Проверка в SQL Editor: `select has_table_privilege('anon', 'public.readings', 'select');` — `false`.

## Вход через Supabase (этап 4.3): шаги владельца

Сервер не хранит паролей и не шлёт писем входа: браузер (экраны 4.4) входит через Supabase JS, API только проверяет
токен (ES256 по ключам `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`, кэш 10 минут).

1. **Google.** Google Cloud Console → APIs & Services → OAuth consent screen: тип External, название Arcana Diary,
   почта поддержки, домен `arcanadiary.com`, области `openid`, `email`, `profile`. Затем Credentials → Create
   credentials → OAuth client ID → Web application: Authorized JavaScript origins — `https://arcanadiary.com`,
   Authorized redirect URIs — `https://<ref>.supabase.co/auth/v1/callback` (точный адрес показан в Supabase на
   странице провайдера). Client ID и Client secret — в Supabase → Authentication → Providers → Google, включить.
2. **Адреса возврата.** Supabase → Authentication → URL Configuration: Site URL — `https://arcanadiary.com`;
   Redirect URLs — `https://arcanadiary.com/diary` и `https://arcanadiary.com/es/diario` (адреса с `?claim=…` им
   соответствуют).
3. **`SUPABASE_URL`** в `deploy/.env` — Project Settings → API → Project URL (не секрет), затем `deploy/deploy.sh`.
4. **До запуска** — почтовый сервис для писем входа (Authentication → SMTP Settings); встроенная почта Supabase —
   только для проверки, несколько писем в час.
5. **Настройки, на которые опирается API** (Authentication → Sign In / Providers и Settings): анонимный вход
   выключен (API всё равно отвечает `401` на токен с `is_anonymous`), «Confirm email» включено (иначе в токене
   может оказаться чужая неподтверждённая почта), срок токена (JWT expiry) — 3600 секунд.
6. **Перед первым развёртыванием 4.3** — в SQL Editor:
   `select to_regclass('public.profiles'), to_regclass('public.claim_tokens'), to_regclass('public.plus_waitlist'), to_regclass('public.deleted_accounts');`
   — все четыре `NULL`. Если какая-то таблица уже есть (`profiles` бывает в шаблонах Supabase), миграция 002 будет
   повторяться каждые 30 секунд: сначала переименовать или удалить ту таблицу.
7. Удаление аккаунта стирает и пользователя Supabase (`DELETE FROM auth.users` через `DATABASE_URL`). До того как
   открыть вход кому-либо, проверить в SQL Editor: `select has_table_privilege(current_user, 'auth.users', 'delete');`
   — `true`. Если пользователь Supabase не удалился, в журнале API будет строка уровня `ERROR` с номером аккаунта
   («Supabase user was not deleted») — удалить его вручную в Authentication → Users.

## Передача в 4.4 (экраны)

- Заметки, вопросы, заголовки и всё из выгрузки — сырой текст: выводить через `textContent`, никогда через
  `innerHTML` или `set:html`.
- Поток расклада и уточнений читать через `fetch` с заголовком `Authorization`: `EventSource` не умеет слать
  заголовки.
- На `401 {"reason": "auth"}` — один раз обновить токен и повторить; не помогло — выйти из сессии и повторить как
  гость. `401 {"reason": "sign_in"}` — показать вход.
- 401 без JSON-причины на стенде — перезагрузить страницу (кука стенда устарела), не обновлять токен.
- Сразу после `DELETE /api/account` выйти из сессии Supabase на этом устройстве.
- `next_before` передавать в адресе закодированным (`+00:00` → `%2B00%3A00`, `URLSearchParams` делает это сам).
- После `POST /api/account/claim` убрать `?claim=…` из адресной строки (`history.replaceState`).
- Расклад в аккаунте принадлежит только аккаунту: после выхода из аккаунта это устройство видит его как чужую
  ссылку (карты и ответ, без вопроса и заметки).

## Тестовый набор чтеца

`api/evals/` — 50 вопросов на язык, 10 попыток взлома, по 10 уточнений и 10 текстов карты дня на язык, 76 вопросов
только для проверки вопроса, 8 заведомо плохих ответов для проверки судьи; оценка — около $2.22. Каждый прогон стоит денег: `.venv/bin/python -m evals.run` печатает оценку цены и без
`--yes` не запускается; `--yes` — только после «да» владельца, ключ — из `deploy/.env`
(`set -a && . deploy/.env && set +a`); пустой ключ останавливает прогон до первого вызова. Результаты —
`api/evals/results/` (в git не попадают).

## Сравнение чтецов (Claude / ChatGPT / Gemini)

Спецификация: `docs/superpowers/specs/2026-11-19-reader-model-comparison-design.md`. Каждый платный шаг — только после
«да» владельца с названной суммой; потолок `--max-usd` общий на этап (ответы + судья Gemini), расходы пишутся после
каждого вызова (`calls.jsonl`, `spend.json`). Перед каждым платным шагом цены сверяются с официальными страницами.

1. `python -m evals.compare --stage A` — оценка цены; `--yes --max-usd 0.2 --limit 1` — пробный прогон на первых
   элементах; `--yes --max-usd 5` — ответы трёх моделей на 50 элементов `evals/compare_set.json` в
   `evals/results/compare-<время>-A/` (существующая папка не перезаписывается).
2. `python -m evals.compare_judges export <папка>` — слепые партии для Fable в отдельной папке
   `evals/results/judging-<8 знаков>/` (путь — в `blind-key.json`); контроллер раздаёт их помощникам Fable по
   `FABLE-INSTRUCTIONS.md` из этой папки; `check-fable <папка>` проверяет оценки.
3. `python -m evals.compare_judges judge2 <папка> --yes` — второй судья Gemini 4 Argon в пределах того же потолка;
   сначала 8 заведомо плохих ответов, при пропуске хотя бы одного — остановка (код 6, `--force` — продолжить).
4. `python -m evals.compare_judges merge <папка>`, затем `python -m evals.compare_report <папка>` — `report.html`.
