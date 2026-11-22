# Stage 4.4b: Save to Diary, Sign-in, Diary, Account Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On the closed stage a person saves a reading to the diary, signs in by e-mail link or Google, sees and marks their readings, writes a note, manages the account, and puts tomorrow's Card of the Day into a calendar — in English and Mexican Spanish, on a phone and a desktop.

**Architecture:** The API (FastAPI + Postgres, built in 4.3) gets small changes only: limits 2/3, the free diary capped at the 10 newest readings with `hidden_count`, `GET /api/auth-config` with the public sign-in settings, the event `remind_click` (migration 007), error logs in the three stream handlers and `"device": false` for `POST /api/account/claim` (owner decision 12). The site (Astro static pages + Preact islands) signs in with `@supabase/auth-js` (implicit flow), loaded with `import()` from one file (`src/lib/supabaseClient.ts`) only when a sheet, the diary, the account or an existing session needs it; a `fetch` wrapper (`authFetch`) adds `Authorization: Bearer` to every `/api/*` request of a signed-in person and handles `401`. New static pages `/diary`, `/es/diario`, `/account`, `/es/cuenta` (noindex) host the diary and account islands; the night room gets "Save to diary" and the Card of the Day gets a calendar file.

**Tech Stack:** Python 3.12, FastAPI 0.115.6, psycopg 3.3.9, pytest 8.3.4 in `api/.venv` (nothing new); Astro 5.18.2, @astrojs/preact 4.1.3, preact 10.29.8, Vitest 5.1.0 (in `site/package-lock.json`); new after the owner's yes (Task 7): `@supabase/auth-js` 2.119.0, `@astrojs/check` 0.9.12, `typescript` 5.9.3, `happy-dom` 21.0.4 and the peer `@emnapi/runtime` 1.11.3 that `astro check` needs; Node 22 only in Docker; Postgres 16.10 in a throwaway Docker container for the API tests.

**Spec:** `docs/superpowers/specs/2026-11-22-stage4-4b-account-screens-design.md` (approved by the owner 22.11.2026; decisions in `.superpowers/sdd/progress-s44b.md`). Server contract: `docs/superpowers/specs/2026-11-19-stage4-3-accounts-diary-design.md`, `api/README.md` sections «Вход через Supabase» and «Передача в 4.4 (экраны)». Copy deferred from 4.4a: `docs/superpowers/specs/2026-11-19-stage4-4a-reading-screens-design.md` §11.

## Global Constraints

Binding text of the spec (copied verbatim; spec §2 decisions 1–10 and §3–§9):

- Decision 1: «**«Remind me tomorrow»** под картой дня — событие в календарь на завтра в 9:00 со ссылкой на карту дня; без входа и почты.»
- Decision 2: «**Вход — почта (ссылка) и Google.** Кнопка Google видна, только когда вход через Google включён в настройках.»
- Decision 3: «**Вернувшийся входит прямо в дневнике** (`/diary`, `/es/diario`); отдельной страницы входа нет.»
- Decision 4: «**Удаление аккаунта** — окно «Удалить навсегда?» с пояснением и кнопками «Скачать», «Удалить навсегда», «Отмена»; слово вводить не нужно.»
- Decision 5: «**Гость исчерпал лимит — только карточка Plus**, как сейчас; о входе в этом месте не говорим.»
- Decision 6: «**«Сбылось / Отчасти / Нет»** появляется в записи **через 7 дней** после расклада; до этого — строка «Вернитесь через неделю».»
- Decision 7: «**Лимит гостя — 2 расклада в день** (было 3)» — `DAILY_LIMIT = 2`.
- Decision 8: «**Лимит вошедшего — 3 расклада в день** (было 5)» — `USER_DAILY_LIMIT = 3`.
- Decision 9: «**Бесплатный дневник показывает 10 последних раскладов.** Более старые не удаляются, а скрыты под строкой «Ещё N раскладов — в Plus»; в Plus — весь дневник. Третье преимущество Plus («Your whole diary, with no limit» / «Todo tu diario, sin límite») показывается в карточке Plus.»
- Decision 10: «Карта дня в дневник не сохраняется: на сервере это не расклад; под ней остаётся только «Remind me tomorrow».»
- Decisions 11–14 (22.11.2026, «после проверки плана Fable», spec §2):
  - 11: «**Напоминание со звуком.** В файле календаря — оповещение (`VALARM`, `DISPLAY`) в начале события, в 9:00 по местному времени; название — «Card of the Day — Arcana Diary» / «Carta del día — Arcana Diary».»
  - 12: «**Ссылка из письма на чужом устройстве переносит только расклад своего токена.** Гостевые расклады устройства переносятся, только если вход начат на этом устройстве. Небольшая правка сервера 4.3: `POST /api/account/claim` получает поле `"device"`.»
  - 13: «**«Сбылось?» открывается с начала названного дня:** в 00:00 по местному времени дня «местная дата расклада + 7 дней»; строка «Вернитесь …» и кнопки всегда совпадают.»
  - 14: «**Кнопка «Назад» телефона при открытом листе сохранения закрывает только лист**; ночная комната и ответ остаются.»
- §3: «Библиотека — `@supabase/auth-js` (только вход; таблицы Supabase браузер не читает). Загружается отдельным куском и только когда нужна: открыт лист сохранения, страница дневника или аккаунта, либо на устройстве уже есть вход. Страница расклада гостя её не грузит.»
- §3: `GET /api/auth-config` → `{"enabled": bool, "supabase_url": "…", "anon_key": "…", "google": bool}`; settings `SUPABASE_URL`, `SUPABASE_ANON_KEY` («открытый ключ проекта, не секрет»), `GOOGLE_SIGNIN` (`true`/пусто); «Нет адреса или ключа — `enabled: false`: кнопка «Save to diary» не показывается, на странице дневника — строка «вход скоро откроется».»
- §3 (added after the Fable check): «Из-за этих настроек API не останавливается (после проверки плана Fable): `GOOGLE_SIGNIN` не `true` — Google выключен; секретный ключ (`sb_secret_…` или JWT с ролью не `anon`) не отдаётся — вход выключен; в обоих случаях строка в журнале.»
- §3: «Ссылка на почту: `signInWithOtp` с адресом возврата на страницу дневника языка страницы. Поток — implicit (токен в `#…` адреса): ссылку можно открыть на любом устройстве (решение 14.11.2026); PKCE этого не даёт. Google: `signInWithOAuth` с тем же адресом возврата.»
- §3: «Сессию хранит библиотека (`localStorage`). Признак «на устройстве есть вход» — свой ключ `ad_signed_in`.»
- §3: «Каждый запрос вошедшего к `/api/*` несёт `Authorization: Bearer`. … `401 {"reason": "auth"}` — один раз обновить токен и повторить; не помогло — выйти и повторить как гость; `401 {"reason": "sign_in"}` — показать вход; `401` без JSON на стенде — перезагрузить страницу; `503 auth_unavailable` — строка «попробуйте позже».»
- §3: «Выход — кнопка в аккаунте: сессия и `ad_signed_in` удаляются, страница — главная.»
- §4: «Кнопка — под ответом чтеца в ночной комнате (экраны 2e, 5b, 8b, 13d) во всех инструментах, кроме карты дня.»
- §4 guest: `save_click` → bottom sheet: e-mail, «Remind me in 7 days: did it come true?» (off), Google (if on); `POST /api/readings/{id}/claim-token` → `/diary?claim=<token>` (+ `&remind=1`); «Check your e-mail» (3b) with «отправить ещё раз» after 60 seconds; Supabase errors «понятной строкой».
- §4 after sign-in: «один раз `POST /api/account/claim {"tokens": […], "device": …}` — с токеном из адреса, если он есть, — затем `?claim=…&remind=…` убираются из адресной строки (`history.replaceState`); при `remind=1` — `PATCH /api/account {"reminders_consent": true}`; событие `signup_done` (`method`: `email` или `google`). Перенос зовётся только после входа, начатого явным действием на этом устройстве (метка в `localStorage`, ставится при отправке почты или нажатии Google) либо при токене в адресе, — не при каждой загрузке страницы. `"device": true` (перенести и гостевые расклады устройства) — только при метке; с одним токеном в адресе — `"device": false`, переносится только расклад токена (решение 12). Согласие и `signup_done` — только при метке или если что-то перенесено: повторный заход по той же ссылке (кнопка «Назад») ничего не включает.»
- §4 signed in: «Вместо кнопки — «Saved to your diary ✓» со ссылкой на запись.» «Расклад в ночной комнате при этом не теряется: лист закрывается, ответ остаётся на экране. Кнопка «Назад» телефона при открытом листе закрывает только лист (решение 14): открытый лист — своя запись истории, закрытие крестиком или Escape её снимает.»
- §5: `/diary`, `/es/diario` «статические, `noindex`, вне карты сайта; содержимое рисует островок Preact»; list «до 10 записей, новые сверху: дата, вид расклада, вопрос (или «без вопроса»), маленькие карты, заголовок ответа, отметка «сбылось?», значок заметки. Кризисная запись — без текста»; empty — a line and a button «сделать расклад».
- §5 cap: `GET /api/diary` returns at most `FREE_DIARY_VISIBLE = 10` newest and `hidden_count`; «`next_before` за пределом — `null`»; `hidden_count > 0` → «Ещё N раскладов — в Plus» and the Plus card (`plus_view`, `place: diary`); «выгрузка отдаёт все расклады; запись, открытая по своей ссылке, открывается»; «после удаления записи на её место приходит более старая».
- §5 entry `?r=<id>`: cards, answer by sections, follow-ups; note ≤ 1000 with a counter and «сохранить» (`PATCH /api/diary/{id}`); «удалить запись» with confirmation (`DELETE`); «Сбылось / Отчасти / Нет» — «с 00:00 по местному времени дня «местная дата расклада + 7 дней» (решение 13)», changeable and clearable; `outcome_answered` (`after_days`: 7 up to 30 days, else 30); earlier — «строка с этим днём, когда вернуться; строка и кнопки считаются по одному правилу».
- §5: «Все тексты из API выводятся как текст (`textContent`), никогда как разметка.»
- §6: `/account`, `/es/cuenta` noindex, linked from the diary; e-mail, readings left today, sign-out; consent switch (`PATCH /api/account`) «с пояснением, что письма начнутся позже»; «Скачать мои расклады» (`GET /api/account/export`); delete dialog → `DELETE /api/account {"confirm": "DELETE"}`; «После удаления — выход и главная со строкой «аккаунт удалён».»
- §7: `.ics` made in the browser: one event tomorrow 9:00 local, 15 minutes, «Card of the Day — Arcana Diary» / «Carta del día — Arcana Diary», link `/daily` or `/es/carta-del-dia`, «оповещение в начале события (решение 11)»; event `remind_click` (`tool: daily`, `lang`).
- §8: menu «Your diary» / «Tu diario», desktop header «Diary» / «Diario»; «Free · save it to your diary after»; home step 3 «Save it, and check later what came true.»; Plus third benefit; Plus diary line «Your diary keeps your last 10 readings. Plus keeps all of them.» / «Tu diario guarda tus últimas 10 tiradas. Plus las guarda todas.»; events `save_click`, `signup_done`, `outcome_answered`, `plus_view` with `place: diary`, new `remind_click`; Caddy: the four addresses like the other pages, `deploy/test-site-routes.sh` and `check_dist` know them, language pairs in the switch; «Испанские тексты — черновик Claude в словаре сайта».
- §9: `@astrojs/check` and `typescript`; «Try again» of a follow-up lost more than an hour ago — `GET` only; logs in the three API stream handlers on a break; DOM tests (save sheet, diary, entry, account, yes/no votes) with a DOM library for Vitest; yes/no votes on a 360 px phone.
- §9: «Все новые пакеты ставятся после «да» владельца с названными версиями и размерами; версии — закреплённые, не моложе двух недель.»
- §11: «Библиотека входа в тестах подменяется, в сеть тесты не ходят.» Build: diary and account pages noindex, not in the sitemap; «библиотека входа не попадает в код страниц расклада; `astro check` без ошибок.»

Working rules (owner, unchanged from 4.4a / 4.5):

- Install nothing outside Task 7, and Task 7 only after the owner's explicit yes (the controller supplies it). The API uses only `api/requirements*.txt`; the site only `site/package-lock.json`. Node commands only in Docker `node:22`.
- No paid API calls in any task. Tests never reach the network: the sign-in library is replaced by a fake (`vi.mock('../lib/supabaseClient', …)` or a fake client factory), `fetch` by `fakeFetch` / `routeFetch`, analytics by `vi.mock`.
- Never read, print or commit `deploy/.env` or `deploy/caddy/stage_auth.caddy*`; never touch, reload or restart `arcana-caddy-1` / `arcana-api-1`; never run `deploy/deploy.sh`, `deploy/check-indexing.sh` or `docker compose` in `deploy/` — deploying is the owner's step. `deploy/test-site-routes.sh` and the API tests start their own throwaway containers and remove them.
- Security: every text from the API is a text node (no `innerHTML`, `set:html`, `dangerouslySetInnerHTML`; `site/src/lib/guards.test.ts` scans the sources); `POST /api/account/claim` once, only after a sign-in started on this device or with `?claim=` in the address, with `"device": true` only after a sign-in started on this device, then `history.replaceState` drops `claim`/`remind`; consent and `signup_done` only with that mark or when something was claimed (review I1); implicit flow; the library only through `import('./supabaseClient')` from `src/lib/auth.ts` (guards test + `tools/site/check_dist.py`); sign-out right after `DELETE /api/account`.
- Copy: strings not in the prototypes and every new Spanish string are drafts — listed in `enDrafts` / `esDrafts` (`// draft — review with stage 5 texts`). Spanish: Mexican, `tú`, no gendered forms for the person. Colours, fonts, spacing, radii only from `tokens.css` (`docs/design/00-design.md` «Правила для кода»); touch targets ≥ 44 px; real `<button>`, `<a>`, `<label>`.
- Commands (from the repository root unless noted):
  - API: `cd ~/arcana-diary/api && .venv/bin/pytest -q [files]` — baseline `1493 passed`.
  - Site tools: `cd ~/arcana-diary && api/.venv/bin/pytest -q tools/site tools/cards` — baseline `80 passed` (`tools/site` alone `7 passed`).
  - Vitest: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run [files]` — baseline `198 passed` in 18 files (needs `site/node_modules`: run `deploy/build-site.sh` once first, it runs `npm ci`).
  - Build: `deploy/build-site.sh`, then `python3 tools/site/check_dist.py` — baseline `OK: 167 pages`.
  - Type check (from Task 8 on, in the verification step of every site task, expected `- 0 errors`): `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 npx astro check`.
- Counts — measured again while amending the plan after the Fable check (22.11.2026): the plan's code applied to scratch copies of `stage4-4b-account` at 318a286 with the real `api/.venv` and a throwaway Postgres (the API suite's own `arcana-test-pg-*` container), and with `site/node_modules` plus the five packages of Task 7 installed in the copy with `--no-save --before=2026-11-08T23:59:59Z`, so this time the DOM tests ran too (happy-dom 21.0.4): API `1493` → T1 `1494` → T2 `1500` → T3 `1512` → T4 `1524` → T5 `1528` → T6 `1531 passed`. Vitest `198/18 files` → T7 `204/19` → T8 `204/19` → T9 `223/22` → T10 `233/23` → T11 `238/24` → T12 `250/25` → T13 `266/29` → T14 `280/30` → T15 `291/31` → T16 `305/35` → T17 `312/37` → T18 `313/37` → T19 `316/37` → T20 `317/37` (T18 and T19 derived: Tasks 18–20 were applied together and `317/37` measured). `astro check`: `9 errors` on the existing code (Task 8, step 2) → `0 errors` after Task 8 and after each of Tasks 9–20. `tools/site tools/cards`: `80` → T21 `86 passed` (`tools/site` `7` → `13`). Build: `167` → T14 `169` (`/diary`, `/es/diario`; derived) → T16 `171` HTML pages (measured after T20); `check_dist` `OK: 171 pages` on that build. Not measured: `deploy/test-site-routes.sh` (it starts Caddy containers) and the "see it fail" counts of the site tasks' step 2 (derived from the tests).
- `api/tests/test_api_followups.py::test_two_followups_at_once_make_one` is timing-based (two threads, 0.3 s guard delay) and failed once in five full runs of the measuring copy, before and after these changes; if it fails, run it alone three times — it is not caused by this plan.
- Every commit message ends with a `Co-Authored-By:` trailer. The commit steps below show `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the model that runs this stage); an implementer running on another model writes its own model name there (review M24).

---

## Packages (Task 7, owner's yes required)

Read from `https://registry.npmjs.org/<package>` on 22.11.2026 (read-only). Rule: exact pins, each version published on or before 08.11.2026 (two weeks before 22.11.2026), the newest such version that fits the others' peer ranges.

| Package | Version | Published | Unpacked size | Direct deps | Why |
|---|---|---|---|---|---|
| `@supabase/auth-js` | 2.119.0 | 2026-11-04 | 2,946,649 B (2.9 MB) | 1 (`tslib` 2.8.1) | sign-in only (e-mail link, Google, session, refresh); not `@supabase/supabase-js` (that adds PostgREST, Storage, Realtime, Functions clients the site must not use — the browser never reads Supabase tables) |
| `@astrojs/check` | 0.9.12 | 2026-10-21 | 15,663 B | 4 (`@astrojs/language-server` ^2.17.3, `chokidar` ^5, `yargs` ^18.2, `kleur` ^4.1.5) | `astro check` (owner decision 20.11.2026); development only, never shipped |
| `typescript` | 5.9.3 | 2025-09-30 | 23,625,066 B (23.6 MB) | 0 | peer of `@astrojs/check` (`^5.0.0 \|\| ^6.0.0`, so 7.x is out); 5.x and not 6.0.3 (16.04.2026) because Astro 5.18.2's own dependencies declare TypeScript ^5 (`tsconfck` 3.1.6 `^5.0.0`, `zod-to-ts` 1.2.0 `^4.9.4 \|\| ^5.0.2` in `site/package-lock.json`); 5.9.3 is the newest 5.x; development only |
| `happy-dom` | 21.0.4 | 2026-10-20 | 9,185,190 B (9.2 MB) | 7 (`ws`, `entities`, `whatwg-mimetype`, `buffer-image-size`, `@types/node`, `@types/ws`, `@types/whatwg-mimetype`) | a DOM for the screen tests; Vitest 5.1.0 lists `happy-dom: *` as an optional peer; development only |
| `@emnapi/runtime` | 1.11.3 | 2026-07-25 | 436,901 B | 1 (`tslib` ^2.4.0, already in the tree through auth-js) | added while amending the plan: `@astrojs/check` 0.9.12 → `@astrojs/language-server` 2.17.3 → `@astrojs/astro2tsx` 0.1.3 → `@napi-rs/wasm-runtime` 1.2.4, whose **peer** `@emnapi/runtime` npm does not install under `site/.npmrc` `legacy-peer-deps=true`. Without it `astro check` cannot load (measured in a scratch copy, 22.11.2026: `ERR_MODULE_NOT_FOUND: Cannot find package '@emnapi/runtime'`, and `npx astro check` then asks to install `@astrojs/check`); with it the check runs. 1.11.3 is the newest version and matches `@emnapi/core` 1.11.3 that `astro2tsx` pins; development only |

Why happy-dom alone and not `jsdom` + `@testing-library/preact`: the tests render with Preact's own `render` and `act` (`preact/test-utils`, part of preact 10.29.8) and query the DOM directly (`site/src/lib/testing/dom.ts`), so no testing library is needed. jsdom 31.0.0 (05.11.2026) has 18 direct dependencies and needs Node `^22.22.2`; `@testing-library/preact` 3.2.6 adds `@testing-library/dom` 10 and its tree. happy-dom is one package with 7 small dependencies. Transitive dependencies (`@astrojs/language-server` and its Volar packages are the largest) are resolved by npm's `--before=2026-11-08T23:59:59Z`, so no installed package is younger than the cut-off either.

How it is installed (Task 7): the same Docker `node:22` as `deploy/build-site.sh`, inside `site/`, with `site/.npmrc` (`legacy-peer-deps=true`, unchanged since 4.4a) and `--save-exact --before=…`; `site/package.json` and `site/package-lock.json` are committed. The four versions of the Fable plan check are unchanged; the fifth row is a peer that the check did not see (it read the registry, not an install). The owner's yes has to name it too.

---

## File Structure

| File | Responsibility |
|---|---|
| `api/app/config.py` | `DAILY_LIMIT = 2`, `USER_DAILY_LIMIT = 3`, `FREE_DIARY_VISIBLE = 10`; settings `supabase_anon_key` (a secret key is dropped), `google_signin` (never an error) |
| `api/app/routes/claim.py` | `POST /api/account/claim` with `"device": false` (owner decision 12) |
| `api/app/routes/diary.py`, `api/app/account_repo.py` | the list capped at 10 + `hidden_count`; `diary_count` |
| `api/app/reader/flow.py` | the owner view carries `created_at`; logs in the reading stream |
| `api/app/routes/auth_config.py` (new), `api/app/main.py` | `GET /api/auth-config` |
| `api/app/events.py`, `api/migrations/007_remind_click.sql` (new) | `remind_click` (daily only) |
| `api/app/reader/followups.py` | logs in the follow-up stream and its replay |
| `api/README.md`, `deploy/docker-compose.yml`, `deploy/.env.example`, `docs/design/analytics-events.md` | the contract and the new settings |
| `site/package.json`, `site/package-lock.json`, `site/vitest.config.ts` | the packages; `.test.tsx` files and the happy-dom URL |
| `site/src/lib/testing/dom.ts`, `site/src/lib/testing/auth.ts`, `site/src/lib/testing/night.ts` (new), `site/src/lib/testing/fakes.ts` | DOM test helpers (`mount`, `cleanup`, `waitFor`); fake storage and sign-in client; a shown night room; `routeFetch` |
| `site/src/lib/authState.ts` (new) | `ad_signed_in` and the "sign-in started here" mark |
| `site/src/lib/authConfig.ts` (new) | `GET /api/auth-config`, once per page |
| `site/src/lib/auth.ts` (new) | the sign-in wrapper (`Auth`), `openSession`, Supabase error kinds; loads the library with `import()` |
| `site/src/lib/supabaseClient.ts` (new) | the only importer of `@supabase/auth-js` (implicit flow) |
| `site/src/lib/authFetch.ts`, `site/src/lib/siteApi.ts` (new) | Bearer on `/api/*` and the `401` rules; the islands' API client |
| `site/src/lib/api.ts` | `callJson`, `jsonBody`, `readingPath` exported for the account client |
| `site/src/lib/accountApi.ts` (new) | claim token, claim, diary, entry, patch, delete, account, consent, export, delete account |
| `site/src/lib/claim.ts` (new) | return address, `finishSignIn` (claim once, consent, `signup_done`, clean address), expired link |
| `site/src/lib/diary.ts`, `site/src/lib/ics.ts`, `site/src/lib/notice.ts`, `site/src/lib/download.ts`, `site/src/lib/sheetHistory.ts`, `site/src/lib/timeZone.ts` (new) | diary rules (the local-day rule of decision 13, `after_days`, names, dates); the calendar file (with its alarm); the home notice (with its sessionStorage mark); saving a file; the save sheet's history entry (decision 14); the device's time zone |
| `site/src/lib/routes.ts`, `site/src/lib/analytics.ts`, `site/src/lib/readingFlow.ts`, `site/src/lib/nightRoom.ts`, `site/src/lib/followups.ts` | the four pages and their pairs, the menu; new events; "Try again" GET-only after an hour |
| `site/src/components/ui/SignInBlock.tsx`, `SaveSheet.tsx`, `useSaveToDiary.tsx`, `DiaryList.tsx`, `DiaryEntry.tsx`, `DeleteAccountDialog.tsx` (new) | the screens 3, 3b, 4a, 4b and the delete dialog; the night room's save wiring |
| `site/src/components/ui/NightRoom.tsx`, `PlusCard.tsx`, `icons.tsx` | "Save to diary" / "Saved ✓" and the sheet in the room; Plus in the diary; `NoteIcon` |
| `site/src/islands/DiaryIsland.tsx`, `AccountIsland.tsx`, `HomeNotice.tsx` (new); `ReadingIsland.tsx`, `DailyIsland.tsx` | the pages' islands; the save flow; "Remind me tomorrow" |
| `site/src/views/DiaryView.astro`, `AccountView.astro`, `site/src/pages/diary.astro`, `account.astro`, `es/diario.astro`, `es/cuenta.astro` (new); `layouts/Base.astro`, `components/Header.astro`, `views/HomeView.astro` | the pages (noindex), the menu and header, the home notice |
| `site/src/i18n/en.ts`, `es.ts`, `i18n.test.ts`, `site/src/styles/global.css` | copy and drafts; styles from tokens |
| `tools/site/check_dist.py`, `tools/site/test_check_dist.py` (new), `tools/site/test_sync_site_data.py` | 171 pages, noindex only on the four, no sign-in library at start on reading pages |
| `deploy/Caddyfile`, `deploy/test-site-routes.sh`, `deploy/check-indexing.sh` | `X-Robots-Tag` on the four pages; route checks |

Task order: 1 → 6 (API; Task 6 is owner decision 12), 7 (packages, gated), 8 (`astro check` on the existing code — before any new screen code, review I10), 9 → 12 (site plumbing), 13 → 18 (screens), 19 → 21 (tails), 22 (final verification), then the owner's steps and the walk-through (not a task). Renumbered after the Fable plan check: old 6 → 7, old 19 → 8, old 7–18 → 9–20, old 20 → 21, old 21 → 22; Task 6 is new.

---
### Task 1: API — daily limits 2 (guest) and 3 (signed in)

**Files:**
- Modify: `api/app/config.py:13-14`, comments in `api/app/limits.py:1-2,39`, `api/app/routes/common.py:49`, `api/app/routes/limits.py:1-2`, `api/app/routes/readings.py:90`, `api/README.md:69,84,197`, `docs/design/00-design.md:99` (the stage 3 decision row that names «3 в день», Fable plan review M4)
- Test: `api/tests/test_limits.py`, `test_api_limits.py`, `test_api_user_limits.py`, `test_api_account.py`, `test_api_auth.py`, `test_api_daily.py`, `test_api_request_ids.py`, `test_api_followups.py`, `test_api_readings.py` (numbers only; the guest's concurrency test races two requests for the last of two slots instead of three) and one new test in `test_api_user_limits.py` that keeps the three-way race for an account (review M5)

**Interfaces:**
- Consumes: `app.limits.guest_quota`, `user_quota` (unchanged; they read the constants).
- Produces: `DAILY_LIMIT == 2`, `USER_DAILY_LIMIT == 3`; `GET /api/limits` and `GET /api/account` answer `limit` 2 / 3. Later tasks do not depend on the numbers.

- [ ] **Step 1: Change the tests to the new numbers**

Write this patch to `/tmp/s44b-t1-tests.diff` (for example `cat > /tmp/s44b-t1-tests.diff <<'PATCH'` … `PATCH`), then apply it:

```diff
diff --git a/api/tests/test_api_account.py b/api/tests/test_api_account.py
index d508cbc..9a280dc 100644
--- a/api/tests/test_api_account.py
+++ b/api/tests/test_api_account.py
@@ -44,7 +44,7 @@ def test_the_account_shows_the_email_its_first_day_and_the_limit(api):
     body = api.client.get("/api/account", params={"tz": MX}, headers=bearer(ANA, email="Ana@Example.com")).json()
     assert body["email"] == "ana@example.com" and body["created_at"].startswith("2026-11-20T18:01:00")
     assert (body["reminders_consent"], body["consent_at"]) == (False, None)
-    assert (body["limit"], body["used"], body["remaining"], body["day"]) == (5, 1, 4, "2026-11-20")
+    assert (body["limit"], body["used"], body["remaining"], body["day"]) == (3, 1, 2, "2026-11-20")
     api.clock.advance(days=1)
     assert api.client.get("/api/account", headers=bearer(ANA)).json()["created_at"] == body["created_at"]
 
diff --git a/api/tests/test_api_auth.py b/api/tests/test_api_auth.py
index 184c841..1d7431e 100644
--- a/api/tests/test_api_auth.py
+++ b/api/tests/test_api_auth.py
@@ -19,7 +19,7 @@ def account_reading(api, **overrides) -> dict:
 
 
 def test_no_header_and_the_stage_password_are_guests(api):
-    assert api.client.get("/api/limits", params={"tz": MX}).json()["limit"] == 3
+    assert api.client.get("/api/limits", params={"tz": MX}).json()["limit"] == 2
     stage = {"Authorization": "Basic YXJjYW5hOnNlY3JldA=="}  # Caddy's stage password passes through to the API
     assert post_reading(api.client, headers=stage, kind="one", tz=MX).status_code == 201
     assert api.jwks.calls == 0
diff --git a/api/tests/test_api_daily.py b/api/tests/test_api_daily.py
index e34044d..d364fe6 100644
--- a/api/tests/test_api_daily.py
+++ b/api/tests/test_api_daily.py
@@ -82,7 +82,7 @@ def test_daily_new_card_and_text_after_local_midnight(api):
 def test_daily_does_not_count_and_new_guests_leave_no_draw(api):
     response = api.client.get("/api/daily", params={"lang": "es", "tz": MX})
     assert response.status_code == 200 and "ad_guest=" in response.headers["set-cookie"]
-    assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 3
+    assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 2
     with api.db.connect() as conn:
         assert conn.execute("SELECT count(*) AS n FROM daily_draws").fetchone()["n"] == 0
 
diff --git a/api/tests/test_api_followups.py b/api/tests/test_api_followups.py
index 09a3226..f0a76f4 100644
--- a/api/tests/test_api_followups.py
+++ b/api/tests/test_api_followups.py
@@ -43,7 +43,7 @@ def followups(api, reading_id) -> list[dict]:
 def test_full_guest_path(api):
     c = api.client
     created = post_reading(c, kind="three", question="How can I settle into my new team?", topic="work", tz=MX)
-    assert created.status_code == 201 and created.json()["remaining"] == 2
+    assert created.status_code == 201 and created.json()["remaining"] == 1
     reading_id = created.json()["id"]
     assert parse_sse(c.get(f"/api/readings/{reading_id}/stream").text)[-1] == ("done", {"answer_shown": "model"})
     for n in (1, 2):
@@ -52,10 +52,9 @@ def test_full_guest_path(api):
         assert followup.headers["content-type"].startswith("text/event-stream")
         assert fin(parse_sse(followup.text)) == ("done", {"answer_shown": "model", "followups_left": 2 - n})
     third = ask(c, reading_id, "And one more thing?", tz=MX)
-    assert third.status_code == 402 and third.json() == {"reason": "confirm", "remaining": 2}
+    assert third.status_code == 402 and third.json() == {"reason": "confirm", "remaining": 1}
     paid = ask(c, reading_id, "And one more thing?", tz=MX, use_reading=True)
     assert fin(parse_sse(paid.text)) == ("done", {"answer_shown": "model", "followups_left": 0, "used_reading": True})
-    assert post_reading(c, kind="one", tz=MX).json()["remaining"] == 0
     fourth = ask(c, reading_id, "Anything else?", tz=MX, use_reading=True)
     assert fourth.status_code == 402 and fourth.json() == {"reason": "plus", "remaining": 0}
     reading = post_reading(c, kind="one", tz=MX)
@@ -363,7 +362,7 @@ def test_third_followup_without_confirmation_is_402_and_takes_no_reading_or_atte
     free_used(api, reading_id)
     guard_calls = len(api.guard.json_calls())
     response = ask(api.client, reading_id, "And one more?", tz=MX)
-    assert response.status_code == 402 and response.json() == {"reason": "confirm", "remaining": 2}
+    assert response.status_code == 402 and response.json() == {"reason": "confirm", "remaining": 1}
     assert (guest_used(api, reading_id), attempts_of(api, reading_id)) == (1, 2)
     # stage 4.5 §3: the question is checked before the 402, so a crisis question gets help instead
     assert len(api.guard.json_calls()) == guard_calls + 1 and len(followups(api, reading_id)) == 2
@@ -376,23 +375,22 @@ def test_confirmed_followup_uses_a_reading(api):
     assert events[0][1]["paid"] is True and events[0][1]["followup"] == 3
     assert fin(events) == ("done", {"answer_shown": "model", "followups_left": 0, "used_reading": True})
     assert guest_used(api, reading_id) == 2
-    assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 1
+    assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 0
     row = followups(api, reading_id)[-1]
     assert (row["n"], row["counted"], row["paid_day"]) == (3, True, limits.local_day(limits.resolve_tz(MX),
                                                                                     api.clock()))
     again = ask(api.client, reading_id, "And another?", tz=MX)
-    assert again.status_code == 402 and again.json() == {"reason": "confirm", "remaining": 1}
+    assert again.status_code == 402 and again.json() == {"reason": "plus", "remaining": 0}
 
 
 def test_no_readings_left_is_402_plus(api):
     reading_id = ready_reading(api, kind="one")
     free_used(api, reading_id)
-    for _ in range(2):
-        assert post_reading(api.client, kind="one", tz=MX).status_code == 201
+    assert post_reading(api.client, kind="one", tz=MX).status_code == 201
     for extra in ({}, {"use_reading": True}):
         response = ask(api.client, reading_id, "And one more?", tz=MX, **extra)
         assert response.status_code == 402 and response.json() == {"reason": "plus", "remaining": 0}
-    assert attempts_of(api, reading_id) == 2 and guest_used(api, reading_id) == 3
+    assert attempts_of(api, reading_id) == 2 and guest_used(api, reading_id) == 2
 
 
 @pytest.mark.parametrize("reply, reason", [
@@ -439,15 +437,14 @@ def test_a_stale_paid_followup_gives_its_reading_back(api):
         limits.take_slot(conn, limits.guest_subject(reading["guest_id"]), day, limits.DAILY_LIMIT)
     assert guest_used(api, reading_id) == 2
     response = ask(api.client, reading_id, "Can I ask again?", tz=MX)
-    assert response.json() == {"reason": "confirm", "remaining": 2} and guest_used(api, reading_id) == 1
+    assert response.json() == {"reason": "confirm", "remaining": 1} and guest_used(api, reading_id) == 1
 
 
 def test_paid_followups_at_once_cannot_overspend_the_day(api):
-    first, second = ready_reading(api, kind="one"), ready_reading(api, kind="one")
+    first = ready_reading(api, kind="one")  # one of the guest's two readings: one is left
     free_used(api, first)
-    free_used(api, second)
-    api.guard.json_delay = 0.3  # all three requests wait in the guard, then race for the last reading
-    start = threading.Barrier(3)
+    api.guard.json_delay = 0.3  # both requests wait in the guard, then race for the last reading
+    start = threading.Barrier(2)
     codes = []
 
     def worker(action):
@@ -455,18 +452,17 @@ def test_paid_followups_at_once_cannot_overspend_the_day(api):
         codes.append(action().status_code)
 
     actions = [lambda: ask(api.client, first, "One more?", tz=MX, use_reading=True),
-               lambda: ask(api.client, second, "One more?", tz=MX, use_reading=True),
                lambda: post_reading(api.client, kind="one", tz=MX, question="What helps me focus?")]
     threads = [threading.Thread(target=worker, args=(a,)) for a in actions]
     for t in threads:
         t.start()
     for t in threads:
         t.join()
-    assert len([c for c in codes if c in (200, 201)]) == 1 and len(codes) == 3
-    assert guest_used(api, first) == 3
+    assert len([c for c in codes if c in (200, 201)]) == 1 and len(codes) == 2
+    assert guest_used(api, first) == 2
     with api.db.connect() as conn:
         assert conn.execute("SELECT count(*) AS n FROM followups WHERE paid_day IS NOT NULL").fetchone()["n"] + \
-            conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 3
+            conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 2
 
 
 # --- Fable plan check: attempts before confirm, attempts_left in done, м10 stale deletion during a live stream ---
@@ -516,7 +512,7 @@ def test_stale_deletion_during_a_slow_stream_refunds_once_and_a_cut_does_not_ref
     reading_id, events = slow_paid_followup(api, reply)
     api.clock.advance(seconds=181)
     again = ask(api.client, reading_id, "Can I ask again?", tz=MX)
-    assert again.json() == {"reason": "confirm", "remaining": 2} and guest_used(api, reading_id) == 1
+    assert again.json() == {"reason": "confirm", "remaining": 1} and guest_used(api, reading_id) == 1
     assert events.join(timeout=10)
     assert guest_used(api, reading_id) == 1  # no second refund
     assert len(followups(api, reading_id)) == 2
@@ -571,15 +567,15 @@ def test_crisis_at_exhausted_attempts_gets_the_crisis_answer(api):
     assert attempts_of(api, reading_id) == FOLLOWUP_ATTEMPTS
 
 
-@pytest.mark.parametrize("readings_left", [2, 0])  # 402 confirm, 402 plus
+@pytest.mark.parametrize("readings_left", [1, 0])  # 402 confirm, 402 plus
 def test_crisis_where_a_402_would_come_gets_the_crisis_answer(api, readings_left):
     reading_id = ready_reading(api, kind="one")
     free_used(api, reading_id)
-    for _ in range(2 - readings_left):
+    for _ in range(1 - readings_left):
         assert post_reading(api.client, kind="one", tz=MX).status_code == 201
     response = ask(api.client, reading_id, "Honestly I want to die.", tz=MX)
     assert response.status_code == 200 and response.json()["group"] == "crisis"
-    assert attempts_of(api, reading_id) == 2 and guest_used(api, reading_id) == 3 - readings_left
+    assert attempts_of(api, reading_id) == 2 and guest_used(api, reading_id) == 2 - readings_left
 
 
 def test_a_followup_number_is_never_used_twice(api):
diff --git a/api/tests/test_api_limits.py b/api/tests/test_api_limits.py
index d34a033..380ab9b 100644
--- a/api/tests/test_api_limits.py
+++ b/api/tests/test_api_limits.py
@@ -7,28 +7,28 @@ MX = "America/Mexico_City"
 
 def test_limits_endpoint_new_guest(api):
     response = api.client.get("/api/limits", params={"tz": MX})
-    assert response.json() == {"limit": 3, "used": 0, "remaining": 3, "day": "2026-11-20"}
+    assert response.json() == {"limit": 2, "used": 0, "remaining": 2, "day": "2026-11-20"}
     assert "ad_guest=" in response.headers["set-cookie"]
 
 
 def test_limit_resets_at_local_midnight(api):
     api.clock.now = datetime(2026, 11, 21, 5, 30, tzinfo=timezone.utc)  # 23:30 on the 20th in Mexico City
-    for _ in range(3):
+    for _ in range(2):
         assert post_reading(api.client, kind="one", tz=MX).status_code == 201
     assert post_reading(api.client, kind="one", tz=MX).status_code == 429
     api.clock.advance(minutes=40)  # 00:10 on the 21st
     assert post_reading(api.client, kind="one", tz=MX).status_code == 201
-    assert api.client.get("/api/limits", params={"tz": MX}).json() == {"limit": 3, "used": 1, "remaining": 2,
+    assert api.client.get("/api/limits", params={"tz": MX}).json() == {"limit": 2, "used": 1, "remaining": 1,
                                                                        "day": "2026-11-21"}
 
 
 def test_limit_day_depends_on_tz(api):
     api.clock.now = datetime(2026, 11, 21, 5, 30, tzinfo=timezone.utc)
-    for _ in range(3):
+    for _ in range(2):
         post_reading(api.client, kind="one", tz=MX)
     assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 0
-    assert api.client.get("/api/limits", params={"tz": "Asia/Tokyo"}).json() == {"limit": 3, "used": 0,
-                                                                                 "remaining": 3, "day": "2026-11-21"}
+    assert api.client.get("/api/limits", params={"tz": "Asia/Tokyo"}).json() == {"limit": 2, "used": 0,
+                                                                                 "remaining": 2, "day": "2026-11-21"}
 
 
 def test_invalid_tz_uses_utc(api):
@@ -40,5 +40,5 @@ def test_invalid_tz_uses_utc(api):
 
 def test_crisis_does_not_use_the_limit(api):
     response = post_reading(api.client, kind="one", question="I want to end my life", tz=MX)
-    assert response.status_code == 200 and response.json()["remaining"] == 3
+    assert response.status_code == 200 and response.json()["remaining"] == 2
     assert api.client.get("/api/limits", params={"tz": MX}).json()["used"] == 0
diff --git a/api/tests/test_api_readings.py b/api/tests/test_api_readings.py
index 96dabeb..b81e8ae 100644
--- a/api/tests/test_api_readings.py
+++ b/api/tests/test_api_readings.py
@@ -61,7 +61,7 @@ def test_create_three_sets_cookie_and_returns_cards(api):
     body = response.json()
     assert [c["position"] for c in body["cards"]] == ["past", "present", "path"]
     assert all(c["name"] for c in body["cards"]) and body["verdict"] is None
-    assert (body["guard_group"], body["remaining"], body["soft_line"], body["owner"]) == ("ok", 2, None, True)
+    assert (body["guard_group"], body["remaining"], body["soft_line"], body["owner"]) == ("ok", 1, None, True)
     assert api.guard.json_calls() == []  # no question, no guard call
 
 
@@ -180,7 +180,7 @@ def test_crisis_returns_help_and_stores_nothing(api, caplog):
         response = post_reading(api.client, kind="three", question=question, tz=MX, headers={"CF-IPCountry": "US"})
     assert response.status_code == 200
     body = response.json()
-    assert body["group"] == "crisis" and body["remaining"] == 3
+    assert body["group"] == "crisis" and body["remaining"] == 2
     assert (body["helplines"]["country"], body["helplines"]["source"]) == ("MX", "timezone")  # CF-* ignored
     assert [line["topic"] for line in body["helplines"]["lines"]] == ["crisis", "violence"]
     assert body["crisis"]["title"] == api.ctx.texts["en"]["crisis"]["title"]
@@ -463,10 +463,10 @@ def test_daily_limit_is_atomic_under_concurrency(api):
         t.start()
     for t in threads:
         t.join()
-    assert sorted(codes) == [201, 201, 201, 429, 429, 429]
-    assert guest_usage(api) == 3
+    assert sorted(codes) == [201, 201, 429, 429, 429, 429]
+    assert guest_usage(api) == 2
     with api.db.connect() as conn:
-        assert conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 3
+        assert conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 2
 
 
 def test_spent_budget_gives_base_meanings(api):
@@ -654,8 +654,8 @@ def test_guard_answer_that_is_unusable_still_costs_something(api):
     api.guard.json_replies.extend([ProviderError("max_tokens: structured output truncated", cut),
                                    ProviderError("no text block", silent),
                                    ProviderError("APIConnectionError")])
-    for i in range(3):
-        body = create(api, kind="one", question=f"What helps me rest, attempt {i}?")
+    for i in range(3):  # three devices: a guest has two readings a day
+        body = create(api, client=api.new_client(), kind="one", question=f"What helps me rest, attempt {i}?")
         assert body["guard_group"] == "ok"
         api.clock.advance(seconds=13)
     with api.db.connect() as conn:
@@ -716,7 +716,7 @@ def test_a_failed_save_frees_the_claim(api, monkeypatch):
 # --- stage 4.5 §3: help first, then the limit ---
 
 def use_up_the_day(api, client=None, headers=None):
-    for _ in range(3):
+    for _ in range(2):
         assert post_reading(client or api.client, kind="one", tz=MX, headers=headers).status_code == 201
 
 
@@ -731,7 +731,7 @@ def test_a_stop_phrase_at_the_daily_limit_gets_the_crisis_answer(api):
     assert response.status_code == 200
     body = response.json()
     assert (body["group"], body["remaining"]) == ("crisis", 0)
-    assert api.guard.json_calls() == [] and guest_usage(api) == 3
+    assert api.guard.json_calls() == [] and guest_usage(api) == 2
     assert guard_rows(api) == [{"lang": "en", "guard_group": "crisis", "source": "terms", "count": 1}]
 
 
@@ -750,7 +750,7 @@ def test_a_crisis_found_by_the_check_model_at_the_daily_limit_gets_the_crisis_an
     assert response.status_code == 200 and response.json()["group"] == "crisis"
     assert len(api.guard.json_calls()) == 1 and guard_calls_logged(api) == 1
     with api.db.connect() as conn:
-        assert conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 3
+        assert conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 2
 
 
 def test_an_ordinary_question_at_the_daily_limit_is_checked_then_refused(api):
@@ -758,7 +758,7 @@ def test_an_ordinary_question_at_the_daily_limit_is_checked_then_refused(api):
     response = post_reading(api.client, kind="one", tz=MX, question="Should I take the pottery class?")
     assert response.status_code == 429 and response.json() == {"reason": "limit", "remaining": 0}
     assert len(api.guard.json_calls()) == 1  # the check first; its call is logged for the guard budget
-    assert guard_calls_logged(api) == 1 and guest_usage(api) == 3
+    assert guard_calls_logged(api) == 1 and guest_usage(api) == 2
     with api.db.connect() as conn:  # ...for no reading: none is made
         assert conn.execute("SELECT reading_id FROM llm_calls WHERE purpose = 'guard'").fetchone()["reading_id"] is None
     assert guard_rows(api) == [{"lang": "en", "guard_group": "ok", "source": "model", "count": 1}]
@@ -809,19 +809,19 @@ def test_the_same_request_number_returns_the_same_reading(api):
     first = post_reading(api.client, **ask)
     again = post_reading(api.client, **ask)
     assert (first.status_code, again.status_code) == (201, 201)
-    assert again.json() == first.json() and first.json()["remaining"] == 2
+    assert again.json() == first.json() and first.json()["remaining"] == 1
     assert (reading_count(api), guest_usage(api), len(api.guard.json_calls())) == (1, 1, 1)
     assert saved(api, first.json()["id"])["request_id"] == uuid.UUID(number)
 
 
 def test_a_repeat_of_the_last_reading_of_the_day_is_not_refused(api):
     use_up_the_day(api)
-    with api.db.connect() as conn:  # the third reading was made with a number
+    with api.db.connect() as conn:  # the second (last) reading was made with a number
         conn.execute("UPDATE readings SET request_id = %s WHERE id = (SELECT id FROM readings LIMIT 1)",
                      (uuid.UUID("00000000-0000-4000-8000-000000000003"),))
     again = post_reading(api.client, kind="one", tz=MX, request_id="00000000-0000-4000-8000-000000000003")
     assert again.status_code == 201 and again.json()["remaining"] == 0
-    assert (reading_count(api), guest_usage(api)) == (3, 3)
+    assert (reading_count(api), guest_usage(api)) == (2, 2)
 
 
 def test_another_owners_number_finds_nothing(api):
@@ -837,7 +837,7 @@ def test_an_account_finds_its_reading_from_any_device(api):
     first = post_reading(phone, kind="one", tz=MX, request_id=number, headers=bearer(user))
     again = post_reading(laptop, kind="one", tz=MX, request_id=number, headers=bearer(user))
     as_guest = post_reading(phone, kind="one", tz=MX, request_id=number)
-    assert again.json()["id"] == first.json()["id"] and again.json()["remaining"] == 4
+    assert again.json()["id"] == first.json()["id"] and again.json()["remaining"] == 2
     assert as_guest.json()["id"] != first.json()["id"]  # the device's guest is another owner
 
 
@@ -920,7 +920,7 @@ def test_yes_no_on_three_cards_has_votes_and_the_majority(api):
     assert [c["vote"] for c in body["cards"]] == [api.ctx.cards.vote(c) for c in body["cards"]]
     expected = api.ctx.cards.verdict(body["cards"])
     assert body["verdict"] == {"value": expected, "label": api.ctx.cards.rules["labels"]["en"][expected]}
-    assert (body["remaining"], guest_usage(api)) == (2, 1)  # three cards are one reading
+    assert (body["remaining"], guest_usage(api)) == (1, 1)  # three cards are one reading
     events = stream(api, body["id"])
     assert [d["name"] for e, d in events if e == "section"] == ["headline", "card1", "card2", "card3", "synthesis",
                                                                  "step", "why"]
@@ -943,7 +943,7 @@ def test_the_decisive_cards_decide_and_a_tie_is_unclear(api, monkeypatch):
     assert ([c["vote"] for c in body["cards"]], body["verdict"]["value"]) == (["yes", "no", "unclear"], "unclear")
     one_decides = [cards[2], {**cards[0], "reversed": True}, {**cards[1], "reversed": True}]  # no, unclear, unclear
     monkeypatch.setattr("app.routes.readings.draw_spread", lambda seed, kind, order, count=None: one_decides)
-    body = create(api, kind="yes_no", count=3)
+    body = create(api, client=api.new_client(), kind="yes_no", count=3)  # a guest has two readings a day
     assert ([c["vote"] for c in body["cards"]], body["verdict"]["value"]) == (["no", "unclear", "unclear"], "no")
 
 
diff --git a/api/tests/test_api_request_ids.py b/api/tests/test_api_request_ids.py
index 95b79a7..9f75335 100644
--- a/api/tests/test_api_request_ids.py
+++ b/api/tests/test_api_request_ids.py
@@ -26,7 +26,7 @@ def test_twins_at_the_last_slot_both_get_the_reading(api):
     """Pins "insert before slots": the winner takes the guest's last slot; the loser waits on the insert, then
     finds the winner's reading. With the slots taken first the loser would be refused with 429 limit."""
     guest, number = uuid.uuid4(), str(uuid.uuid4())
-    for _ in range(2):  # two of the three daily slots are used
+    for _ in range(1):  # one of the two daily slots is used
         assert post_reading(api.new_client(), kind="one", tz=MX, headers=guest_headers(guest)).status_code == 201
     api.guard.json_delay = 0.3  # both wait in the question check, then race to insert
     start = threading.Barrier(2)
@@ -46,7 +46,7 @@ def test_twins_at_the_last_slot_both_get_the_reading(api):
     assert [a.status_code for a in answers] == [201, 201]
     assert answers[0].json()["id"] == answers[1].json()["id"]
     assert [a.json()["remaining"] for a in answers] == [0, 0]
-    assert (guest_usage(api), reading_count(api)) == (3, 3)
+    assert (guest_usage(api), reading_count(api)) == (2, 2)
 
 
 def test_a_crisis_question_repeated_with_one_number_is_checked_again(api):
diff --git a/api/tests/test_api_user_limits.py b/api/tests/test_api_user_limits.py
index c606986..776d403 100644
--- a/api/tests/test_api_user_limits.py
+++ b/api/tests/test_api_user_limits.py
@@ -1,5 +1,5 @@
-"""Daily limits with accounts (spec 4.3 §5): a guest has 3 per device, a signed-in person 5 per account on every
-device; a paid follow-up uses a slot of the reading's owner and gives it back there."""
+"""Daily limits with accounts (spec 4.3 §5, stage 4.4b §2): a guest has 2 per device, a signed-in person 3 per
+account on every device; a paid follow-up uses a slot of the reading's owner and gives it back there."""
 import uuid
 from datetime import timedelta
 
@@ -22,26 +22,26 @@ def guest_rows(api) -> int:
         return conn.execute("SELECT count(*) AS n FROM usage WHERE subject LIKE 'guest:%'").fetchone()["n"]
 
 
-def test_a_guest_still_has_three(api):
-    assert [post_reading(api.client, kind="one", tz=MX).json()["remaining"] for _ in range(3)] == [2, 1, 0]
+def test_a_guest_has_two(api):
+    assert [post_reading(api.client, kind="one", tz=MX).json()["remaining"] for _ in range(2)] == [1, 0]
     assert post_reading(api.client, kind="one", tz=MX).json() == {"reason": "limit", "remaining": 0}
 
 
-def test_signed_in_has_five_per_account_on_every_device(api):
+def test_signed_in_has_three_per_account_on_every_device(api):
     phone, laptop = api.new_client(), api.new_client()
     token = bearer(USER)
     remaining = []
-    for client in (phone, laptop, phone, laptop, phone):
+    for client in (phone, laptop, phone):
         api.clock.advance(minutes=1)  # one address: stay under the burst threshold (Turnstile after 5 a minute)
         remaining.append(post_reading(client, headers=token, kind="one", tz=MX).json()["remaining"])
-    assert remaining == [4, 3, 2, 1, 0]
+    assert remaining == [2, 1, 0]
     api.clock.advance(minutes=1)
-    sixth = post_reading(laptop, headers=token, kind="one", tz=MX)
-    assert sixth.status_code == 429 and sixth.json() == {"reason": "limit", "remaining": 0}
+    fourth = post_reading(laptop, headers=token, kind="one", tz=MX)
+    assert fourth.status_code == 429 and fourth.json() == {"reason": "limit", "remaining": 0}
     assert laptop.get("/api/limits", params={"tz": MX}, headers=token).json() == {
-        "limit": 5, "used": 5, "remaining": 0, "day": "2026-11-20"}
+        "limit": 3, "used": 3, "remaining": 0, "day": "2026-11-20"}
     assert guest_rows(api) == 0
-    assert laptop.get("/api/limits", params={"tz": MX}).json()["remaining"] == 3  # the device as a guest
+    assert laptop.get("/api/limits", params={"tz": MX}).json()["remaining"] == 2  # the device as a guest
     api.clock.advance(minutes=1)
     assert post_reading(laptop, kind="one", tz=MX).status_code == 201
 
@@ -56,18 +56,18 @@ def test_an_account_reading_is_kept_and_a_guest_reading_expires(api):
 
 
 def test_guest_slots_stay_with_the_guest_after_sign_in(api):
-    for _ in range(3):
+    for _ in range(2):
         post_reading(api.client, kind="one", tz=MX)
     assert post_reading(api.client, kind="one", tz=MX).status_code == 429
     signed_in = post_reading(api.client, headers=bearer(USER), kind="one", tz=MX)
-    assert signed_in.status_code == 201 and signed_in.json()["remaining"] == 4
+    assert signed_in.status_code == 201 and signed_in.json()["remaining"] == 2
     assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 0
 
 
 def test_a_crisis_answer_shows_what_the_account_has_left(api):
     post_reading(api.client, headers=bearer(USER), kind="one", tz=MX)
     response = post_reading(api.client, headers=bearer(USER), kind="one", question="I want to end my life", tz=MX)
-    assert response.status_code == 200 and response.json()["remaining"] == 4
+    assert response.status_code == 200 and response.json()["remaining"] == 2
     assert used(api, limits.user_subject(USER)) == 1
 
 
@@ -89,7 +89,7 @@ def test_a_paid_followup_uses_the_account_slot_from_any_device(api):
     reading_id = account_reading_with_free_followups_used(api.new_client())
     laptop = api.new_client()
     confirm = ask(laptop, reading_id)
-    assert confirm.status_code == 402 and confirm.json() == {"reason": "confirm", "remaining": 4}
+    assert confirm.status_code == 402 and confirm.json() == {"reason": "confirm", "remaining": 2}
     events = parse_sse(ask(laptop, reading_id, use_reading=True).text)
     assert events[-1][1]["used_reading"] is True
     assert used(api, limits.user_subject(USER)) == 2 and guest_rows(api) == 0
diff --git a/api/tests/test_limits.py b/api/tests/test_limits.py
index c5113fc..8378c43 100644
--- a/api/tests/test_limits.py
+++ b/api/tests/test_limits.py
@@ -222,7 +222,7 @@ def test_take_reading_slots_counts_guest_and_address(db):
 
 def test_guest_limit_raises(db):
     with db.connect() as conn:
-        for _ in range(3):
+        for _ in range(2):
             take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", DAY)
         with pytest.raises(LimitReached) as info:
             take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", DAY)
@@ -242,7 +242,7 @@ def test_ip_limit_rolls_back_the_guest_slot(db):
 
 def test_remaining_and_midnight_reset(db):
     with db.connect() as conn:
-        for _ in range(3):
+        for _ in range(2):
             take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", date(2026, 11, 21))
         assert remaining(conn, guest_quota(GID), DAY) == 0
         assert remaining(conn, guest_quota(GID), date(2026, 11, 21)) == limits.DAILY_LIMIT
@@ -276,7 +276,7 @@ def test_a_rolled_back_attempt_is_given_back(db):
 
 def test_give_back_slot_never_goes_below_zero(db):
     with db.connect() as conn:
-        for _ in range(3):
+        for _ in range(2):
             take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", DAY)
         give_back_slot(conn, guest_subject(GID), DAY)
         assert remaining(conn, guest_quota(GID), DAY) == 1
@@ -292,20 +292,20 @@ def test_question_checks_are_counted_apart():
 
 
 
-# --- stage 4.3 §5: the guest's 3 or the account's 5 ---
+# --- stage 4.3 §5, stage 4.4b §2: the guest's 2 or the account's 3 ---
 
 def test_quotas():
     user = uuid.uuid4()
-    assert guest_quota(GID) == limits.Quota(f"guest:{GID}", 3)
-    assert limits.user_quota(user) == limits.Quota(f"user:{user}", 5)
+    assert guest_quota(GID) == limits.Quota(f"guest:{GID}", 2)
+    assert limits.user_quota(user) == limits.Quota(f"user:{user}", 3)
     assert limits.owner_quota({"guest_id": GID, "user_id": None}) == guest_quota(GID)
     assert limits.owner_quota({"guest_id": GID, "user_id": user}) == limits.user_quota(user)
 
 
-def test_an_account_takes_five_a_day(db):
+def test_an_account_takes_three_a_day(db):
     quota = limits.user_quota(uuid.uuid4())
     with db.connect() as conn:
-        assert [take_reading_slots(conn, quota, DAY, "hash-1", DAY) for _ in range(5)] == [1, 2, 3, 4, 5]
+        assert [take_reading_slots(conn, quota, DAY, "hash-1", DAY) for _ in range(3)] == [1, 2, 3]
         with pytest.raises(LimitReached):
             take_reading_slots(conn, quota, DAY, "hash-1", DAY)
-        assert remaining(conn, quota, DAY) == 0 and used(conn, ip_subject("hash-1"), DAY) == 5
+        assert remaining(conn, quota, DAY) == 0 and used(conn, ip_subject("hash-1"), DAY) == 3
```

Run: `cd ~/arcana-diary && git apply --check /tmp/s44b-t1-tests.diff && git apply /tmp/s44b-t1-tests.diff && git diff --stat`
Expected: `9 files changed, 71 insertions(+), 75 deletions(-)`, no rejects.

- [ ] **Step 1b: Keep the three-way race for an account (review M5)**

The guest's race above loses its third racer (a guest has only two readings a day). The same case stays covered with the account's three. In `api/tests/test_api_user_limits.py` (patched above) replace

```python
import uuid
from datetime import timedelta
```

with

```python
import threading
import uuid
from datetime import timedelta
```

and append to the end of the file (two blank lines before):

```python
# --- Fable plan review M5: the three-way race for the last reading of the day, with an account ---

def test_paid_followups_of_an_account_at_once_cannot_overspend_the_day(api):
    """test_api_followups.py races two requests since a guest has only two readings a day; the account's three keep
    the three-way race: two paid follow-ups and a new reading, from three devices, for the account's last reading."""
    first = account_reading_with_free_followups_used(api.new_client())
    second = account_reading_with_free_followups_used(api.new_client())  # two of the account's three are used
    api.guard.json_delay = 0.3  # all three requests wait in the guard, then race for the last reading
    start = threading.Barrier(3)
    codes = []

    def worker(action):
        start.wait()
        codes.append(action().status_code)

    actions = [lambda: ask(api.new_client(), first, use_reading=True),
               lambda: ask(api.new_client(), second, use_reading=True),
               lambda: post_reading(api.new_client(), headers=bearer(USER), kind="one", tz=MX,
                                    question="What helps me focus?")]
    threads = [threading.Thread(target=worker, args=(a,)) for a in actions]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len([c for c in codes if c in (200, 201)]) == 1 and len(codes) == 3
    assert used(api, limits.user_subject(USER)) == 3
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM followups WHERE paid_day IS NOT NULL").fetchone()["n"] + \
            conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 3
```

(`ask`, `account_reading_with_free_followups_used`, `used`, `bearer`, `post_reading`, `USER`, `MX` already exist in that file.)

- [ ] **Step 2: Run the changed tests against the old limits**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_limits.py tests/test_api_limits.py tests/test_api_user_limits.py tests/test_api_account.py tests/test_api_auth.py tests/test_api_daily.py tests/test_api_request_ids.py tests/test_api_followups.py tests/test_api_readings.py`
Expected: FAIL — `36 failed, 223 passed` (e.g. `assert {'limit': 3, …} == {'limit': 2, …}`; the new race test fails too: with five a day all three racers win).

- [ ] **Step 3: Change the limits and the texts that name them**

Write this patch to `/tmp/s44b-t1-code.diff` and apply it the same way (`git apply --check` first):

```diff
diff --git a/api/README.md b/api/README.md
index 986e7c8..34ad93e 100644
--- a/api/README.md
+++ b/api/README.md
@@ -66,7 +66,7 @@ READER_PROVIDER=fake DATABASE_URL=postgresql://postgres:dev@127.0.0.1:55432/post
 отдаёт только `GET /health`, остальное — `404`. События потока: `meta`, `section`, `text`, `replace`, `fallback`,
 `crisis`, `done`, `error`. Все ответы `/api/*`: `Cache-Control: no-store`, `Referrer-Policy: no-referrer`,
 `X-Robots-Tag: noindex, nofollow`. Уточнения: два бесплатных к каждому раскладу (обрезанное или заменённое из базы не
-считается); каждое следующее тратит один расклад из «3 в день» и только с `"use_reading": true` в запросе — без него
+считается); каждое следующее тратит один расклад из дневного лимита (гость — 2, вошедший — 3) и только с `"use_reading": true` в запросе — без него
 `402 {"reason": "confirm", "remaining": N}`, раскладов не осталось — `402 {"reason": "plus", "remaining": 0}`. Платное
 уточнение, которое не удалось (обрыв, замена из базы, по словарю, без ответа), возвращает расклад; кризисный ответ
 проверки вопроса расклад не тратит, метка чтеца `[[crisis]]` — тратит; `done` платного уточнения несёт `used_reading`.
@@ -81,7 +81,7 @@ READER_PROVIDER=fake DATABASE_URL=postgresql://postgres:dev@127.0.0.1:55432/post
 стенда) — гость, как раньше. Токен проверяется на каждом адресе `/api/*` до разбора запроса (и на
 `GET /api/daily`). Неверный или просроченный токен — `401 {"reason": "auth"}`, ключи Supabase
 недоступны — `503 {"reason": "auth_unavailable"}`, адрес только для вошедших без токена — `401 {"reason": "sign_in"}`.
-Лимит: гость — 3 расклада в день на устройство, вошедший — 5 на аккаунт на всех устройствах (`GET /api/limits`
+Лимит (этап 4.4б, решения владельца 22.11.2026): гость — 2 расклада в день на устройство, вошедший — 3 на аккаунт на всех устройствах (`GET /api/limits`
 отвечает по аккаунту); платное уточнение берёт слот у владельца расклада. Расклад в аккаунте принадлежит только
 аккаунту, гостевой — устройству (кука `ad_guest`); владельцу `GET /api/readings/{id}` отдаёт ещё `in_diary`,
 `outcome`, `note`. Перенос:
@@ -194,7 +194,7 @@ estar… + прилагательное или причастие», «a ti mism
   временем на границе страницы могут разойтись по страницам или пропасть из выдачи.
 - Токен аккаунта, удалённого меньше 8 дней назад, получает `401 {"reason": "auth"}` на любую запись (таблица
   `deleted_accounts`); через 8 дней запись о нём стирается — дольше любой срок токена Supabase не бывает.
-- Реальный потолок на человека — 3 расклада гостем и 5 вошедшим, то есть 8 в день; новые адреса почты (в том числе
+- Реальный потолок на человека — 2 расклада гостем и 3 вошедшим, то есть 5 в день; новые адреса почты (в том числе
   с `+`) дают новые аккаунты. Ограничивают это, как и смену куки гостем, только предел адреса (60 в сутки, Turnstile
   с 20-го) и суточные бюджеты.
 
diff --git a/api/app/config.py b/api/app/config.py
index 361a3dc..1bec6e8 100644
--- a/api/app/config.py
+++ b/api/app/config.py
@@ -10,8 +10,8 @@ REPO_ROOT = APP_DIR.parents[1]
 
 DEFAULT_MODEL = "claude-haiku-5-5"
 EFFORTS = ("low", "medium", "high", "xhigh", "max")
-DAILY_LIMIT = 3
-USER_DAILY_LIMIT = 5       # signed in: per account, on every device (spec 2026-11-19 stage 4.3 §5)
+DAILY_LIMIT = 2            # a guest, per device (stage 4.4b §2, decision 7: was 3)
+USER_DAILY_LIMIT = 3       # signed in: per account, on every device (spec 4.3 §5; 3 since stage 4.4b §2, decision 8)
 IP_HARD_LIMIT = 60
 FOLLOWUP_LIMIT = 2         # free follow-ups per reading; each next one uses a reading of DAILY_LIMIT (§10.1)
 FOLLOWUP_ATTEMPTS = 8      # §10.2: follow-up requests per reading; reader [[crisis]] marks, refusals and failures
diff --git a/api/app/limits.py b/api/app/limits.py
index df3758a..d8a9999 100644
--- a/api/app/limits.py
+++ b/api/app/limits.py
@@ -1,5 +1,5 @@
-"""Guest cookie, the visitor's local day, the daily limit (readings and paid follow-ups: 3 per guest, 5 per
-account, stage 4.3 §5), the IP counters, the follow-up attempts (§4.1, §4.2, §8.2, §8.4, §9.2, §10)."""
+"""Guest cookie, the visitor's local day, the daily limit (readings and paid follow-ups: 2 per guest, 3 per
+account, stage 4.3 §5 and 4.4b §2), the IP counters, the follow-up attempts (§4.1, §4.2, §8.2, §8.4, §9.2, §10)."""
 import hashlib
 import ipaddress
 import re
@@ -36,7 +36,7 @@ ZONE_ALIASES = {
 class LimitReached(Exception):
     """Raised inside the reading transaction, so the transaction rolls back and nothing is counted."""
 
-    def __init__(self, reason: str):  # "limit" (3 per guest) | "ip_limit" (per address) | "attempts" (per reading)
+    def __init__(self, reason: str):  # "limit" (the day's quota) | "ip_limit" (per address) | "attempts" (per reading)
         super().__init__(reason)
         self.reason = reason
 
diff --git a/api/app/routes/common.py b/api/app/routes/common.py
index db65eb2..f981b84 100644
--- a/api/app/routes/common.py
+++ b/api/app/routes/common.py
@@ -46,7 +46,7 @@ class Viewer:
 
     @property
     def quota(self) -> limits.Quota:
-        """Stage 4.3 §5: signed in — the account's 5 a day on every device; otherwise this device's 3."""
+        """Stage 4.3 §5, 4.4b §2: signed in — the account's 3 a day on every device; otherwise this device's 2."""
         return limits.user_quota(self.user.id) if self.user else limits.guest_quota(self.guest_id)
 
 
diff --git a/api/app/routes/limits.py b/api/app/routes/limits.py
index fa34552..de6e8fc 100644
--- a/api/app/routes/limits.py
+++ b/api/app/routes/limits.py
@@ -1,5 +1,5 @@
-"""How many readings are left today: for the account when signed in (5), else for this guest (3) (§1.1, §4.1,
-stage 4.3 §5)."""
+"""How many readings are left today: for the account when signed in (3), else for this guest (2) (§1.1, §4.1,
+stage 4.3 §5, stage 4.4b §2)."""
 from fastapi import APIRouter, Request
 
 from app import limits
diff --git a/api/app/routes/readings.py b/api/app/routes/readings.py
index 7e2992e..01e3450 100644
--- a/api/app/routes/readings.py
+++ b/api/app/routes/readings.py
@@ -87,7 +87,7 @@ def create_reading(body: ReadingIn, request: Request):
     ip = limits.client_ip(request, ctx.settings.trust_cloudflare)
     ip_hash = ctx.salt.hash_ip(ip, now)
     hits = ctx.burst.hit(ip_hash, now)
-    quota = who.quota  # stage 4.3 §5: the account's 5 when signed in, else this device's 3
+    quota = who.quota  # stage 4.3 §5, 4.4b §2: the account's 3 when signed in, else this device's 2
     owner_id = who.user.id if who.user else None
     with ctx.db.connect() as conn:
         if who.user:  # stage 4.3 §8: a token that outlived its account — before any model call
```

In `docs/design/00-design.md` (the stage 3 decisions table, row `| 3 | Лимиты и защита |`; spec §8 «тексты, где названо число», review M4) replace `3 расклада в день, карта дня вне лимита; лимит одинаковый для гостя и вошедшего;` with `3 расклада в день, карта дня вне лимита; лимит одинаковый для гостя и вошедшего *(заменено этапом 4.4б: гость — 2, вошедший — 3 в день, спецификация 2026-11-22 §2, решения 7–8)*;`.

- [ ] **Step 4: Run the full API suite**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q`
Expected: PASS — `1494 passed`.

- [ ] **Step 5: Commit**

```bash
rm -f /tmp/s44b-t1-tests.diff /tmp/s44b-t1-code.diff
git add api/app/config.py api/app/limits.py api/app/routes/common.py api/app/routes/limits.py api/app/routes/readings.py api/README.md api/tests docs/design/00-design.md
git commit -m "feat(api): stage 4.4b — daily limits 2 for a guest, 3 for an account

Owner decisions 7 and 8 (22.11.2026). Tests name the new numbers; the account keeps the
three-way race for its last reading (Fable plan review M5).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: API — the free diary lists the 10 newest readings, `hidden_count`, the entry's date

**Files:**
- Modify: `api/app/config.py` (after `NOTE_MAX_CHARS`), `api/app/account_repo.py` (before `DIARY_FIELDS`), `api/app/routes/diary.py` (docstring, import, `list_diary`), `api/app/reader/flow.py` (`full_view`, owner fields), `api/README.md:90`
- Test: `api/tests/test_api_diary.py`

**Interfaces:**
- Consumes: `account_repo.diary_page(conn, user_id, before, limit) -> list[dict]` (unchanged), `diary_item`.
- Produces:
  - `app.config.FREE_DIARY_VISIBLE = 10`.
  - `account_repo.diary_count(conn, user_id) -> int`.
  - `GET /api/diary?before=&limit=` → `{"items": [...], "next_before": str | null, "hidden_count": int}` — items only among the 10 newest readings; `next_before` is `null` when no visible item is left; `hidden_count = max(total − 10, 0)`.
  - `GET /api/readings/{id}` for its owner also carries `"created_at"` (ISO time; site Tasks 14–15 compute the named day of decision 13 from it). Not shown to anyone else.

- [ ] **Step 1: Write the failing tests**

Append to the end of `api/tests/test_api_diary.py` (two blank lines before):

```python
# --- stage 4.4b §5 (owner decision 9): the free diary lists the 10 newest readings ---

def insert_entries(api, n: int, user=ANA) -> list[str]:
    """n readings of the account, an hour apart; ids oldest first."""
    ids = []
    with api.db.connect() as conn:
        for i in range(n):
            reading = make_reading(user_id=user, expires_at=None, now=api.clock() - timedelta(hours=n - i))
            repo.insert_reading(conn, reading)
            ids.append(str(reading["id"]))
    return ids


def test_the_free_diary_lists_the_ten_newest_and_counts_the_hidden(api):
    ids = insert_entries(api, 12)
    body = diary(api.client, ANA).json()
    assert [i["id"] for i in body["items"]] == ids[::-1][:10]
    assert (body["hidden_count"], body["next_before"]) == (2, None)


def test_pages_stop_at_the_tenth_entry(api):
    newest = insert_entries(api, 12)[::-1]
    first = diary(api.client, ANA, limit=4).json()
    second = diary(api.client, ANA, limit=4, before=first["next_before"]).json()
    third = diary(api.client, ANA, limit=4, before=second["next_before"]).json()
    assert [i["id"] for i in first["items"] + second["items"] + third["items"]] == newest[:10]
    assert third["next_before"] is None and len(third["items"]) == 2
    assert [p["hidden_count"] for p in (first, second, third)] == [2, 2, 2]
    beyond = diary(api.client, ANA, before=third["items"][-1]["created_at"]).json()  # older than the 10th: hidden
    assert beyond == {"items": [], "next_before": None, "hidden_count": 2}


def test_ten_or_fewer_hide_nothing(api):
    insert_entries(api, 10)
    body = diary(api.client, ANA).json()
    assert (len(body["items"]), body["hidden_count"], body["next_before"]) == (10, 0, None)
    assert diary(api.client, BEN).json() == {"items": [], "next_before": None, "hidden_count": 0}


def test_a_hidden_entry_still_opens_by_its_link_and_is_exported(api):
    oldest = insert_entries(api, 11)[0]
    assert oldest not in [i["id"] for i in diary(api.client, ANA).json()["items"]]
    view = api.client.get(f"/api/readings/{oldest}", headers=bearer(ANA))
    assert view.status_code == 200 and view.json()["in_diary"] is True
    assert view.json()["created_at"].startswith("2026-11-20T07:00:00")  # T_API − 11 h
    assert len(api.client.get("/api/account/export", headers=bearer(ANA)).json()["readings"]) == 11


def test_deleting_a_listed_entry_brings_the_next_older_one_in(api):
    ids = insert_entries(api, 11)
    assert api.client.delete(f"/api/diary/{ids[-1]}", headers=bearer(ANA)).status_code == 204
    body = diary(api.client, ANA).json()
    assert [i["id"] for i in body["items"]] == ids[:10][::-1]
    assert body["hidden_count"] == 0


def test_the_view_of_someone_else_has_no_date_of_the_diary(api):
    reading_id = insert_entries(api, 1)[0]
    view = api.new_client().get(f"/api/readings/{reading_id}").json()
    assert "created_at" not in view and "in_diary" not in view
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_diary.py`
Expected: FAIL — 5 failed (`KeyError: 'hidden_count'`, 12 items instead of 10, `KeyError: 'created_at'`), 8 passed (`test_the_view_of_someone_else…` passes already).

- [ ] **Step 3: Implement**

In `api/app/config.py`, after the line `NOTE_MAX_CHARS = 1000          # stage 4.3 §6: the private note of a diary entry (never sent to a model)` add:

```python
FREE_DIARY_VISIBLE = 10        # stage 4.4b §5 (decision 9): the diary lists the newest 10; older ones are hidden, kept
```

In `api/app/account_repo.py`, replace `DIARY_FIELDS = "outcome, outcome_at, note, note_updated_at"` with:

```python
def diary_count(conn, user_id) -> int:
    """Stage 4.4b §5: every reading of the account, the ones hidden beyond the free diary's list included."""
    return conn.execute("SELECT count(*) AS n FROM readings WHERE user_id = %s", (user_id,)).fetchone()["n"]


DIARY_FIELDS = "outcome, outcome_at, note, note_updated_at"
```

In `api/app/routes/diary.py`, replace the first docstring line

```python
"""The diary (spec 2026-11-19 stage 4.3 §6): the account's readings, "did it come true?", a private note, delete.
```

with

```python
"""The diary (spec 2026-11-19 stage 4.3 §6): the account's readings, "did it come true?", a private note, delete.

Stage 4.4b §5 (owner decision 9): the list shows only the FREE_DIARY_VISIBLE newest readings, in pages; the older
ones are not deleted — `hidden_count` says how many there are, and the export and the entry's own link still show
them. There is no Plus flag on an account yet, so the cap applies to everyone.
```

replace `from app.config import NOTE_MAX_CHARS` with `from app.config import FREE_DIARY_VISIBLE, NOTE_MAX_CHARS`, and in `list_diary` replace

```python
    with ctx.db.connect() as conn:
        rows = account_repo.diary_page(conn, who.user.id, before, limit)
    return respond(200, {"items": [diary_item(ctx, row) for row in rows],
                         "next_before": rows[-1]["created_at"] if len(rows) == limit else None})
```

with

```python
    with ctx.db.connect() as conn:
        visible = account_repo.diary_page(conn, who.user.id, None, FREE_DIARY_VISIBLE)
        total = account_repo.diary_count(conn, who.user.id)
    rest = [row for row in visible if before is None or row["created_at"] < before]
    page = rest[:limit]
    return respond(200, {"items": [diary_item(ctx, row) for row in page],
                         "next_before": page[-1]["created_at"] if len(rest) > limit else None,
                         "hidden_count": max(total - len(visible), 0)})
```

In `api/app/reader/flow.py`, in `full_view`, replace

```python
            "outcome": reading.get("outcome"), "note": reading.get("note"),
```

with

```python
            "outcome": reading.get("outcome"), "note": reading.get("note"),
            "created_at": reading["created_at"],  # stage 4.4b §5: "did it come true?" opens 7 days after it
```

In `api/README.md`, replace `` `GET /api/diary?before=&limit=` (20, не больше 50; `next_before` — начало следующей страницы), `` with

```
`GET /api/diary?before=&limit=` (20, не больше 50; `next_before` — начало следующей страницы; этап 4.4б: только 10
последних раскладов — `FREE_DIARY_VISIBLE`, за ними `next_before: null`, и `hidden_count` — сколько более старых
скрыто; выгрузка и `GET /api/readings/{id}` их по-прежнему отдают, владельцу — ещё и `created_at`),
```

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_diary.py && .venv/bin/pytest -q`
Expected: PASS — `13 passed`, then `1500 passed`. (The list and the count are two queries: a reading inserted between them can make `hidden_count` one off in that one answer — accepted, review M3.)

- [ ] **Step 5: Commit**

```bash
git add api/app/config.py api/app/account_repo.py api/app/routes/diary.py api/app/reader/flow.py api/README.md api/tests/test_api_diary.py
git commit -m "feat(api): stage 4.4b — the free diary lists the 10 newest readings, hidden_count

Owner decision 9: older readings are kept, counted, exported and open by their link;
the owner's view of a reading carries created_at for the 7-day outcome.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 3: API — `GET /api/auth-config`, settings `SUPABASE_ANON_KEY` and `GOOGLE_SIGNIN`

**Files:**
- Create: `api/app/routes/auth_config.py`, `api/tests/test_api_auth_config.py`
- Modify: `api/app/config.py` (imports, `log`, `Settings`, `_flag`, `_public_key`, `load_settings`), `api/app/main.py` (import, router), `deploy/docker-compose.yml` (api environment), `deploy/.env.example` (after `SUPABASE_URL=`), `api/README.md` (settings table, «Адреса»)

**Interfaces:**
- Consumes: `Settings.supabase_url` (4.3), `routes.common.respond`, `main.API_AUTH` (a bad Bearer is `401` here too).
- Produces:
  - `Settings.supabase_anon_key: str` (stripped, `""` by default; a secret key is dropped — see below), `Settings.google_signin: bool` (`GOOGLE_SIGNIN` exactly `"true"` → on; empty → off; anything else → off and a `WARNING` line of logger `arcana.config`).
  - The settings are read when `app.main` is imported (`deploy/docker-compose.yml`: `restart: unless-stopped`), so neither setting may raise (review I12): a typo like `GOOGLE_SIGNIN=false` would otherwise stop every reading in a restart loop. A secret key in `SUPABASE_ANON_KEY` (`sb_secret_…`, or a three-part JWT whose payload `role` is not `"anon"`, e.g. `service_role`, or a dotted value that does not decode) is never published: `supabase_anon_key = ""` (sign-in off) and an `ERROR` line that does not print the key (review I3: the key goes to every visitor and a secret key passes row level security).
  - `GET /api/auth-config` → `200 {"enabled": bool, "supabase_url": str, "anon_key": str, "google": bool}`; `enabled = bool(supabase_url and supabase_anon_key)`; when off the strings are `""` and `google` is `false`. No cookie is set. Site Task 9 parses exactly these four keys.

- [ ] **Step 1: Write the failing tests**

Create `api/tests/test_api_auth_config.py`:

```python
"""GET /api/auth-config (spec 2026-11-22 stage 4.4b §3): the public sign-in settings for the browser."""
import base64
import json

import pytest

from app.config import load_settings
from helpers import AUTH_URL

ANON = "sb_publishable_test-key"  # a made-up public key; the real one is only in deploy/.env
SECRET = "sb_secret_test-key"  # a made-up secret key: it must never reach a browser


def jwt(role: str) -> str:
    """A made-up legacy Supabase key: a JWT whose payload names its role (the signature is not checked here)."""
    def part(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    return f"{part({'alg': 'HS256', 'typ': 'JWT'})}.{part({'iss': 'supabase', 'role': role})}.c2lnbmF0dXJl"


def test_on_with_the_address_and_the_key(api_factory):
    api = api_factory(supabase_anon_key=ANON)
    response = api.client.get("/api/auth-config")
    assert response.status_code == 200
    assert response.json() == {"enabled": True, "supabase_url": AUTH_URL, "anon_key": ANON, "google": False}
    assert response.headers["cache-control"] == "no-store" and "set-cookie" not in response.headers


def test_google_only_when_switched_on(api_factory):
    api = api_factory(supabase_anon_key=ANON, google_signin=True)
    assert api.client.get("/api/auth-config").json()["google"] is True


@pytest.mark.parametrize("overrides", [{}, {"supabase_url": "", "supabase_anon_key": ANON},
                                       {"supabase_url": "", "supabase_anon_key": "", "google_signin": True}])
def test_off_without_the_address_or_the_key(api_factory, overrides):
    api = api_factory(**overrides)
    assert api.client.get("/api/auth-config").json() == {"enabled": False, "supabase_url": "", "anon_key": "",
                                                         "google": False}


def test_a_bad_token_is_refused_here_too(api_factory):
    api = api_factory(supabase_anon_key=ANON)
    response = api.client.get("/api/auth-config", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401 and response.json() == {"reason": "auth"}


def test_the_settings():
    s = load_settings({})
    assert (s.supabase_anon_key, s.google_signin) == ("", False)
    s = load_settings({"SUPABASE_ANON_KEY": f" {ANON} ", "GOOGLE_SIGNIN": "true"})
    assert (s.supabase_anon_key, s.google_signin) == (ANON, True)
    assert load_settings({"GOOGLE_SIGNIN": ""}).google_signin is False


def test_google_signin_other_than_true_is_off_with_a_log_line_never_a_crash(caplog):
    """Fable plan review I12: the settings are read when the API starts; an error here would stop every reading."""
    for wrong in ("yes", "True", "1", "false", " on "):
        caplog.clear()
        with caplog.at_level("WARNING", logger="arcana.config"):
            assert load_settings({"GOOGLE_SIGNIN": wrong}).google_signin is False
        assert f"GOOGLE_SIGNIN={wrong.strip()!r} is not 'true': Continue with Google stays off" in caplog.text


@pytest.mark.parametrize("key", [SECRET, jwt("service_role"), "not.a.jwt"])
def test_a_secret_key_is_never_published(key, caplog):
    """Fable plan review I3: GET /api/auth-config shows the key to every visitor, and a secret key passes row level
    security. It is dropped (sign-in stays off) with a log line that never prints the key; the API still starts."""
    with caplog.at_level("ERROR", logger="arcana.config"):
        assert load_settings({"SUPABASE_ANON_KEY": key}).supabase_anon_key == ""
    assert "SUPABASE_ANON_KEY is not the public key" in caplog.text and key not in caplog.text


def test_the_public_keys_are_used(caplog):
    anon = jwt("anon")
    with caplog.at_level("WARNING", logger="arcana.config"):
        assert load_settings({"SUPABASE_ANON_KEY": anon}).supabase_anon_key == anon
        assert load_settings({"SUPABASE_ANON_KEY": ANON}).supabase_anon_key == ANON
    assert caplog.text == ""
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_auth_config.py`
Expected: FAIL — errors `TypeError: … unexpected keyword argument 'supabase_anon_key'` (the `replace` in `make_api`) and `AttributeError: 'Settings' object has no attribute 'supabase_anon_key'`.

- [ ] **Step 3: Implement**

In `api/app/config.py` replace

```python
"""API settings from environment variables; limits; model prices for the LLM call log."""
import os
```

with

```python
"""API settings from environment variables; limits; model prices for the LLM call log."""
import base64
import json
import logging
import os
```

replace `REPO_ROOT = APP_DIR.parents[1]` with

```python
REPO_ROOT = APP_DIR.parents[1]
log = logging.getLogger("arcana.config")
```

(`app/main.py` sets up logging before it calls `load_settings()`, so these lines reach the API log.) In `class Settings`, replace

```python
    supabase_url: str  # stage 4.3 §3: the project's public address; "" — sign-in is off
```

with

```python
    supabase_url: str  # stage 4.3 §3: the project's public address; "" — sign-in is off
    supabase_anon_key: str  # stage 4.4b §3: the project's public (anon / publishable) key for the browser; not a secret
    google_signin: bool  # stage 4.4b §3: GOOGLE_SIGNIN=true shows "Continue with Google"
```

before `def load_settings(env: Mapping[str, str] | None = None) -> Settings:` add

```python
def _flag(name: str, value: str) -> bool:
    """Stage 4.4b §3: exactly "true" switches it on; anything else is off with a log line, never an error — the
    settings are read when the API starts, and GOOGLE_SIGNIN=false must not stop the readings (Fable plan review I12)."""
    value = value.strip()
    if value not in ("", "true"):
        log.warning("%s=%r is not 'true': Continue with Google stays off", name, value)
    return value == "true"


def _public_key(value: str) -> str:
    """Stage 4.4b §3: SUPABASE_ANON_KEY goes to every visitor (GET /api/auth-config), so only the project's public key
    may be used. A secret key — sb_secret_…, or a legacy JWT key whose role is not "anon" (service_role) — passes row
    level security: it is dropped, sign-in stays off and the log says so without printing the key; the API still
    starts (Fable plan review I3). The JWT's signature is not checked: only the role it names matters here."""
    value = value.strip()
    secret = value.startswith("sb_secret_")
    parts = value.split(".")
    if not secret and len(parts) == 3:  # a legacy key: a JWT
        try:
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        except ValueError:  # bad base64 (binascii.Error) and bad JSON are both ValueErrors
            payload = None
        secret = not isinstance(payload, dict) or payload.get("role") != "anon"
    if secret:
        log.error("SUPABASE_ANON_KEY is not the public key (a secret key or a JWT whose role is not 'anon'): not used, "
                  "sign-in stays off — set the anon / publishable key (api/README.md)")
        return ""
    return value
```

Why not refuse to start, as `_true_or_false` does for `TRUST_CLOUDFLARE`: the compose service restarts on failure, so a wrong sign-in setting would turn into an API that never answers a reading; with the key dropped the site only shows «Signing in opens soon.» and the log names the setting.

and at the end of the `Settings(...)` call in `load_settings` replace

```python
        supabase_url=_supabase_url(env.get("SUPABASE_URL") or ""),
    )
```

with

```python
        supabase_url=_supabase_url(env.get("SUPABASE_URL") or ""),
        supabase_anon_key=_public_key(env.get("SUPABASE_ANON_KEY") or ""),
        google_signin=_flag("GOOGLE_SIGNIN", env.get("GOOGLE_SIGNIN") or ""),
    )
```

Create `api/app/routes/auth_config.py`:

```python
"""GET /api/auth-config (spec 2026-11-22 stage 4.4b §3): what the browser needs to sign in with Supabase — the
project's public address and public key (neither is a secret) and whether "Continue with Google" is on. Without the
address or the key sign-in is off: the site hides "Save to diary" and the diary says that sign-in opens soon."""
from fastapi import APIRouter, Request

from app.context import get_ctx
from app.routes.common import respond

router = APIRouter(prefix="/api")


@router.get("/auth-config")
def auth_config(request: Request):
    settings = get_ctx(request).settings
    enabled = bool(settings.supabase_url and settings.supabase_anon_key)
    return respond(200, {"enabled": enabled, "supabase_url": settings.supabase_url if enabled else "",
                         "anon_key": settings.supabase_anon_key if enabled else "",
                         "google": enabled and settings.google_signin})
```

In `api/app/main.py`, replace `from app.routes import account, claim, daily, diary, events, followups, plus, readings` with `from app.routes import account, auth_config, claim, daily, diary, events, followups, plus, readings`, and after `    app.include_router(events.router, dependencies=API_AUTH)` add:

```python
    app.include_router(auth_config.router, dependencies=API_AUTH)
```

In `deploy/docker-compose.yml`, under `api:` → `environment:`, after `      SUPABASE_URL: ${SUPABASE_URL:-}` add:

```yaml
      SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY:-}
      GOOGLE_SIGNIN: ${GOOGLE_SIGNIN:-}
```

In `deploy/.env.example`, after the line `SUPABASE_URL=` add:

```
# --- stage 4.4b: the browser's sign-in. Supabase → Project Settings → API Keys → the public (anon / publishable)
# key; public, not a secret — NEVER the service_role / sb_secret_… key (the API drops a secret key and logs it).
# Empty — sign-in is off: no "Save to diary" button, the diary says sign-in opens soon
SUPABASE_ANON_KEY=
# true — show "Continue with Google" (after Google is set up in Supabase, api/README.md); empty (or anything else,
# logged) — e-mail link only
GOOGLE_SIGNIN=
```

In `api/README.md`, in the settings table, before the row `` | `DAILY_JOB_INTERVAL_S` | `` add:

```
| `SUPABASE_ANON_KEY` | пусто | открытый ключ проекта Supabase (anon / publishable, не секрет) для входа в браузере; вместе с `SUPABASE_URL` включает вход на сайте (`GET /api/auth-config`), без него кнопки «Save to diary» нет. Никогда не `service_role` / `sb_secret_…`: такой ключ API не отдаёт (вход выключен, строка `SUPABASE_ANON_KEY is not the public key` в журнале) |
| `GOOGLE_SIGNIN` | пусто | `true` — на сайте видна кнопка «Continue with Google» (после шага 1 «Вход через Supabase»); пусто или что угодно другое — выключено (другое значение — строка в журнале, API работает) |
```

and in «Адреса» replace `` (этап 4.4а, ниже). `` (the end of the first sentence, after `` `POST /api/events` ``) with

```
(этап 4.4а, ниже), `GET /api/auth-config` (этап 4.4б: `{"enabled", "supabase_url", "anon_key", "google"}` — открытые
настройки входа для браузера; без `SUPABASE_URL` или `SUPABASE_ANON_KEY` — `enabled: false` и пустые строки).
```

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_auth_config.py tests/test_config.py && .venv/bin/pytest -q`
Expected: PASS — `44 passed`, then `1512 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/config.py api/app/routes/auth_config.py api/app/main.py api/tests/test_api_auth_config.py deploy/docker-compose.yml deploy/.env.example api/README.md
git commit -m "feat(api): stage 4.4b — GET /api/auth-config with the public sign-in settings

SUPABASE_ANON_KEY (public key, not a secret) and GOOGLE_SIGNIN (true, else off); without
the address or the key sign-in is off. A secret key is never published and neither
setting can stop the API (Fable plan review I3, I12).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 4: API — the event `remind_click` (migration 007) and the 4.4b events in the whitelist tests

**Files:**
- Create: `api/migrations/007_remind_click.sql`
- Modify: `api/app/events.py` (`EVENTS`, `ONLY_TOOL`, `check_event`), `docs/design/analytics-events.md` (table), `api/README.md` («Счётчик событий»: the table's migrations and the check of the constraint name before the deploy, review M2)
- Test: `api/tests/test_api_events.py` (`VALID`, `INVALID`), `api/tests/test_db.py` (migration lists, new 007 test)

**Interfaces:**
- Consumes: `events.check_event`, `record_event`; the table `events` (migration 004 has an inline `CHECK (name IN (...))`, named `events_name_check` by Postgres — the code alone cannot store a new name).
- Produces: `POST /api/events {"name": "remind_click", "tool": "daily", "lang": "en"|"es", "params": {}}` → `204`; any other tool or a parameter → `422`. `save_click`, `signup_done`, `outcome_answered`, `plus_view` `place: diary` were already accepted (4.4a) and are now covered by tests. Site Task 17 sends `remind_click`.

- [ ] **Step 1: Write the failing tests**

Write this patch to `/tmp/s44b-t4-tests.diff` and apply it (`git apply --check` first):

```diff
diff --git a/api/tests/test_api_events.py b/api/tests/test_api_events.py
index a5b1dc3..3e6b587 100644
--- a/api/tests/test_api_events.py
+++ b/api/tests/test_api_events.py
@@ -22,6 +22,12 @@ VALID = [
     {"name": "outcome_answered", "lang": "es", "params": {"after_days": 7, "answer": "partly"}},
     {"name": "plus_view", "lang": "en", "params": {"place": "limit"}},
     {"name": "tool_view", "tool": "daily", "lang": "es"},
+    {"name": "plus_view", "lang": "es", "params": {"place": "diary"}},
+    {"name": "remind_click", "tool": "daily", "lang": "en", "params": {}},
+    {"name": "remind_click", "tool": "daily", "lang": "es"},
+    {"name": "signup_done", "lang": "es", "params": {"method": "google"}},
+    {"name": "outcome_answered", "lang": "en", "params": {"after_days": 30, "answer": "no"}},
+    {"name": "save_click", "tool": "yes_no", "lang": "es", "params": {}},
 ]
 
 INVALID = [
@@ -38,6 +44,11 @@ INVALID = [
     ({"name": "reading_shown", "tool": "home", "lang": "en", "params": {"ms_from_draw": -1}}, "params.ms_from_draw"),
     ({"name": "reading_shown", "tool": "home", "lang": "en", "params": {"ms_from_draw": 1.5}}, "params.ms_from_draw"),
     ({"name": "outcome_answered", "lang": "en", "params": {"after_days": 14, "answer": "yes"}}, "params.after_days"),
+    ({"name": "remind_click", "lang": "en"}, "tool"),
+    ({"name": "remind_click", "tool": "home", "lang": "en"}, "tool"),
+    ({"name": "remind_click", "tool": "daily", "lang": "en", "params": {"at": "09:00"}}, "params.at"),
+    ({"name": "plus_view", "lang": "en", "params": {"place": "account"}}, "params.place"),
+    ({"name": "signup_done", "lang": "en", "params": {}}, "params.method"),
 ]
 
 
diff --git a/api/tests/test_db.py b/api/tests/test_db.py
index b078181..dbeb708 100644
--- a/api/tests/test_db.py
+++ b/api/tests/test_db.py
@@ -30,7 +30,7 @@ def test_split_sql():
 
 def test_migrate_creates_tables_with_rls_and_no_policies(fresh_db):
     assert migrate(fresh_db, MIGRATIONS) == ["001_init", "002_accounts", "003_guard_source", "004_events",
-                                           "005_request_ids", "006_rewrite_purpose"]
+                                           "005_request_ids", "006_rewrite_purpose", "007_remind_click"]
     with fresh_db.connect() as conn:
         rows = conn.execute("SELECT relname, relrowsecurity FROM pg_class"
                             " WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'").fetchall()
@@ -316,7 +316,7 @@ def test_002_applies_over_001_and_keeps_the_readings(fresh_db):
     with fresh_db.connect() as conn:
         insert_001_reading(conn, reading)
     assert migrate(fresh_db, MIGRATIONS) == ["002_accounts", "003_guard_source", "004_events", "005_request_ids",
-                                             "006_rewrite_purpose"]
+                                             "006_rewrite_purpose", "007_remind_click"]
     with fresh_db.connect() as conn:
         row = conn.execute("SELECT user_id, outcome, outcome_at, note, note_updated_at FROM readings WHERE id = %s",
                            (reading["id"],)).fetchone()
@@ -330,7 +330,8 @@ def test_003_applies_over_002_and_leaves_the_old_rows_without_a_source(fresh_db)
     apply_up_to(fresh_db, "001_init", "002_accounts")  # the live database after stage 4.3's first deploy
     with fresh_db.connect() as conn:
         insert_001_reading(conn, reading)
-    assert migrate(fresh_db, MIGRATIONS) == ["003_guard_source", "004_events", "005_request_ids", "006_rewrite_purpose"]
+    assert migrate(fresh_db, MIGRATIONS) == ["003_guard_source", "004_events", "005_request_ids", "006_rewrite_purpose",
+                                             "007_remind_click"]
     with fresh_db.connect() as conn:
         column = conn.execute("SELECT is_nullable, column_default FROM information_schema.columns"
                               " WHERE table_name = 'readings' AND column_name = 'guard_source'").fetchone()
@@ -419,7 +420,7 @@ def test_the_tests_refuse_a_supabase_database():
 
 def test_004_applies_over_003(fresh_db):
     apply_up_to(fresh_db, "001_init", "002_accounts", "003_guard_source")  # the live database after stage 4.3
-    assert migrate(fresh_db, MIGRATIONS) == ["004_events", "005_request_ids", "006_rewrite_purpose"]
+    assert migrate(fresh_db, MIGRATIONS) == ["004_events", "005_request_ids", "006_rewrite_purpose", "007_remind_click"]
     with fresh_db.connect() as conn:
         security = conn.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'events'").fetchone()
         names = {r["indexname"] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'events'")}
@@ -447,7 +448,7 @@ def test_005_applies_over_004_and_leaves_the_old_rows_without_a_number(fresh_db)
         insert_001_reading(conn, reading)
         conn.execute("INSERT INTO followups (id, reading_id, n, question, created_at) VALUES (%s, %s, 1, 'Q?', %s)",
                      (uuid.uuid4(), reading["id"], T0))
-    assert migrate(fresh_db, MIGRATIONS) == ["005_request_ids", "006_rewrite_purpose"]
+    assert migrate(fresh_db, MIGRATIONS) == ["005_request_ids", "006_rewrite_purpose", "007_remind_click"]
     with fresh_db.connect() as conn:
         columns = conn.execute("SELECT table_name, is_nullable, column_default FROM information_schema.columns"
                                " WHERE column_name = 'request_id' ORDER BY table_name").fetchall()
@@ -500,3 +501,21 @@ def test_a_follow_up_number_is_unique_per_reading(db):
         assert repo.insert_followup(conn, {**first, "id": uuid.uuid4(), "n": 2, "request_id": None}) is True
         rows = repo.list_followups(conn, reading["id"])
     assert [(r["n"], r["request_id"]) for r in rows] == [(1, number), (2, None)]
+
+
+# --- stage 4.4b §7: migration 007 ---
+
+def test_007_applies_over_006_keeps_the_events_and_takes_remind_click(fresh_db):
+    apply_up_to(fresh_db, "001_init", "002_accounts", "003_guard_source", "004_events", "005_request_ids",
+                "006_rewrite_purpose")  # the live database after stage 4.7
+    insert = ("INSERT INTO events (day, name, tool, lang, params, created_at) VALUES (%s, %s, %s, 'en', '{}', %s)")
+    with fresh_db.connect() as conn:
+        conn.execute(insert, (T0.date(), "plus_view", None, T0))
+    assert migrate(fresh_db, MIGRATIONS) == ["007_remind_click"]
+    with fresh_db.connect() as conn:
+        conn.execute(insert, (T0.date(), "remind_click", "daily", T0))
+        names = [r["name"] for r in conn.execute("SELECT name FROM events ORDER BY name")]
+    assert names == ["plus_view", "remind_click"]
+    with pytest.raises(psycopg.errors.CheckViolation):
+        with fresh_db.connect() as conn:
+            conn.execute(insert, (T0.date(), "page_view", None, T0))
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_events.py tests/test_db.py`
Expected: FAIL — `11 failed, 76 passed`: the five `remind_click` cases (`422 {"fields": ["name"]}` instead of `204` / `tool` / `params.at`), the five migration lists without `007_remind_click`, and `test_007_…` (`migrate` returns `[]`).

- [ ] **Step 3: Implement**

Create `api/migrations/007_remind_click.sql` (no comment line may end with `;` — `split_sql` splits there):

```sql
-- 007_remind_click: stage 4.4b (spec 2026-11-22 §7). The event counter accepts one more event, remind_click
-- ("Remind me tomorrow" under the Card of the Day). Only the CHECK constraint changes: the old list plus
-- 'remind_click', so every existing row fits. Re-adding it checks the existing rows under a short write lock
-- (events is small: one row per event, no texts). Row level security and APP_TABLES stay as they are.
ALTER TABLE events DROP CONSTRAINT events_name_check;
ALTER TABLE events ADD CONSTRAINT events_name_check
    CHECK (name IN ('tool_view', 'draw_click', 'night_open', 'cards_revealed', 'reading_shown', 'save_click',
                    'signup_done', 'more_about_cards', 'outcome_answered', 'plus_view', 'remind_click'));
```

In `api/app/events.py`, replace

```python
    "plus_view": (False, {"place": _one_of("limit", "diary")}),
}
```

with

```python
    "plus_view": (False, {"place": _one_of("limit", "diary")}),
    "remind_click": (True, {}),  # stage 4.4b §7: "Remind me tomorrow" under the Card of the Day
}
# events that belong to one tool only
ONLY_TOOL = {"remind_click": "daily"}
```

and in `check_event` replace

```python
    if with_tool != (tool is not None) or (tool is not None and tool not in TOOLS):
        raise InvalidEvent("tool")
```

with

```python
    if with_tool != (tool is not None) or (tool is not None and tool not in TOOLS):
        raise InvalidEvent("tool")
    if name in ONLY_TOOL and tool != ONLY_TOOL[name]:
        raise InvalidEvent("tool")
```

In `docs/design/analytics-events.md`, after the row of `plus_view` add:

```
| `remind_click` | «Remind me tomorrow» под картой дня (этап 4.4б) | `tool` (только daily), `lang` | нужна ли карта дня назавтра |
```

In `api/README.md` («Счётчик событий (этап 4.4а)») replace `` таблица `events` (миграция 004) — день UTC, имя, инструмент, язык, параметры, время. `` with

```
таблица `events` (миграции 004, 007) — день UTC, имя, инструмент, язык, параметры, время. Миграция 007 (этап 4.4б,
`remind_click`) пересоздаёт ограничение имени: перед выкладкой проверить его имя на живой базе —
`SELECT conname FROM pg_constraint WHERE conrelid = 'events'::regclass AND contype = 'c';` — ожидается
`events_name_check` (иначе миграция остановится на `DROP CONSTRAINT`, ничего не изменив: она идёт одной транзакцией).
```

The migration itself is safe on the live table (review M2): `migrate()` applies each file in one transaction (`api/app/db.py:67–78`) once per `schema_migrations`, only DROP/ADD CHECK, the list is the ten old names plus `remind_click`; the table is small, so `NOT VALID` is not needed.

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_events.py tests/test_db.py && .venv/bin/pytest -q`
Expected: PASS — `87 passed`, then `1524 passed`.

- [ ] **Step 5: Commit**

```bash
rm -f /tmp/s44b-t4-tests.diff
git add api/migrations/007_remind_click.sql api/app/events.py docs/design/analytics-events.md api/README.md api/tests/test_api_events.py api/tests/test_db.py
git commit -m "feat(api): stage 4.4b — event remind_click (migration 007), 4.4b events tested

The events table checks its names in the database, so the new name needs migration 007
(only the CHECK constraint changes). remind_click belongs to the daily tool only.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: API — log a database failure inside the three stream handlers

**Files:**
- Modify: `api/app/reader/flow.py` (`_reading_events`: two `except DatabaseUnavailable`), `api/app/reader/followups.py` (`_followup_events`: two; `replay_followup`: one)
- Test: `api/tests/test_api_readings.py`, `api/tests/test_api_followups.py` (append)

**Interfaces:**
- Consumes: logger `arcana.reader` (both modules already have `log = logging.getLogger("arcana.reader")`).
- Produces: `ERROR` lines `reading stream: database unavailable before the answer: <message>`, `reading stream: the answer was not saved: <message>`, `follow-up stream: database unavailable before the answer: <message>`, `follow-up stream: the answer was not saved: <message>`, `follow-up replay: database unavailable: <message>` — the PostgreSQL message only, never a question or an id (4.5 final review, Minor 3). The SSE answers do not change.

- [ ] **Step 1: Write the failing tests**

Append to the end of `api/tests/test_api_readings.py` (two blank lines before):

```python
# --- stage 4.4b §9: a database failure inside a stream is logged with its message ---

def test_a_database_failure_in_the_reading_stream_is_logged(api, monkeypatch, caplog):
    body = create(api, kind="one")

    def down(*args, **kwargs):
        raise DatabaseUnavailable("column readings.nope does not exist")

    monkeypatch.setattr(flow, "over_budget", down)
    with caplog.at_level("ERROR", logger="arcana.reader"):
        assert stream(api, body["id"]) == [("error", {"reason": "db"})]
    assert "reading stream: database unavailable before the answer: column readings.nope does not exist" in caplog.text
    monkeypatch.undo()
    caplog.clear()
    monkeypatch.setattr(repo, "save_answer", down)
    with caplog.at_level("ERROR", logger="arcana.reader"):
        assert stream(api, body["id"])[-1] == ("error", {"reason": "db"})
    assert "reading stream: the answer was not saved: column readings.nope does not exist" in caplog.text
```

In `api/tests/test_api_followups.py` replace `from app.reader.followups import stream_followup` with `from app.reader.followups import replay_followup, stream_followup`, and append to the end of the file (two blank lines before):

```python
# --- stage 4.4b §9: a database failure inside a follow-up stream is logged with its message ---

def down(*args, **kwargs):
    raise DatabaseUnavailable("column followups.nope does not exist")


def test_a_database_failure_before_a_followup_answer_is_logged(api, monkeypatch, caplog):
    reading_id = ready_reading(api, kind="one")
    monkeypatch.setattr("app.reader.followups.over_budget", down)
    with caplog.at_level("ERROR", logger="arcana.reader"):
        events = parse_sse(ask(api.client, reading_id, "What helps?", tz=MX).text)
    assert events[-1] == ("error", {"reason": "db"})
    assert "follow-up stream: database unavailable before the answer: column followups.nope does not exist" \
        in caplog.text


def test_a_followup_answer_that_could_not_be_saved_is_logged(api, monkeypatch, caplog):
    reading_id = ready_reading(api, kind="one")
    monkeypatch.setattr(repo, "save_followup_answer", down)
    with caplog.at_level("ERROR", logger="arcana.reader"):
        events = parse_sse(ask(api.client, reading_id, "What helps?", tz=MX).text)
    assert events[-1] == ("error", {"reason": "db"})
    assert "follow-up stream: the answer was not saved: column followups.nope does not exist" in caplog.text


def test_a_database_failure_in_a_followup_replay_is_logged(api, monkeypatch, caplog):
    reading_id = ready_reading(api, kind="one")
    assert parse_sse(ask(api.client, reading_id, "What helps?", tz=MX).text)[-1][0] == "done"
    with api.db.connect() as conn:
        reading = repo.get_reading(conn, uuid.UUID(reading_id), api.clock())
        [followup] = repo.list_followups(conn, reading["id"])
    monkeypatch.setattr(repo, "get_reading", down)
    with caplog.at_level("ERROR", logger="arcana.reader"):
        events = parse_sse("".join(replay_followup(api.ctx, reading, followup)))
    assert events[-1] == ("error", {"reason": "db"})
    assert "follow-up replay: database unavailable: column followups.nope does not exist" in caplog.text
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_readings.py tests/test_api_followups.py -k is_logged`
Expected: FAIL — `4 failed` (`assert 'reading stream: …' in ''` and the like), the rest deselected. (`-k is_logged` and not `-k logged`: the latter also picks `test_llm_cost_logged_for_priced_model`, review M1.)

- [ ] **Step 3: Implement**

In `api/app/reader/flow.py`, in `_reading_events`, replace

```python
        spent = claimed and over_budget(ctx)
    except DatabaseUnavailable:
        if claimed:
```

with

```python
        spent = claimed and over_budget(ctx)
    except DatabaseUnavailable as exc:
        log.error("reading stream: database unavailable before the answer: %s", exc)  # stage 4.4b §9
        if claimed:
```

and replace

```python
    except DatabaseUnavailable:
        release_claim(ctx, reading["id"])  # nothing was saved: the next stream may write the answer
```

with

```python
    except DatabaseUnavailable as exc:
        log.error("reading stream: the answer was not saved: %s", exc)  # stage 4.4b §9
        release_claim(ctx, reading["id"])  # nothing was saved: the next stream may write the answer
```

In `api/app/reader/followups.py`, in `_followup_events`, replace

```python
        history = load_history(ctx, reading)  # stage 4.3 §7: the same block as the reading had
    except DatabaseUnavailable:
        yield sse("error", {"reason": "db"})
```

with

```python
        history = load_history(ctx, reading)  # stage 4.3 §7: the same block as the reading had
    except DatabaseUnavailable as exc:
        log.error("follow-up stream: database unavailable before the answer: %s", exc)  # stage 4.4b §9
        yield sse("error", {"reason": "db"})
```

replace

```python
    except DatabaseUnavailable:
        if crisis:  # the helplines need no database: the client gets them first (as in the reading flow)
```

with

```python
    except DatabaseUnavailable as exc:
        log.error("follow-up stream: the answer was not saved: %s", exc)  # stage 4.4b §9
        if crisis:  # the helplines need no database: the client gets them first (as in the reading flow)
```

and in `replay_followup` replace

```python
            followups = repo.list_followups(conn, reading["id"])
    except DatabaseUnavailable:
        if crisis:
```

with

```python
            followups = repo.list_followups(conn, reading["id"])
    except DatabaseUnavailable as exc:
        log.error("follow-up replay: database unavailable: %s", exc)  # stage 4.4b §9
        if crisis:
```

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_readings.py tests/test_api_followups.py -k is_logged && .venv/bin/pytest -q`
Expected: PASS — `4 passed`, then `1528 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/reader/flow.py api/app/reader/followups.py api/tests/test_api_readings.py api/tests/test_api_followups.py
git commit -m "fix(api): stage 4.4b — log database failures inside the stream handlers

The reading stream, the follow-up stream and its replay answered SSE error: db without
a log line; now the PostgreSQL message is logged (4.5 final review, Minor 3).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: API — `POST /api/account/claim` can leave this device's guest readings alone (`"device": false`)

**Files:**
- Modify: `api/app/routes/claim.py` (docstring, `ClaimIn`, `claim`), `api/README.md` («Перенос» in «Адреса»; «Передача в 4.4»)
- Test: `api/tests/test_api_claim.py` (append)

**Interfaces:**
- Consumes: `account_repo.claim_device`, `account_repo.claim_by_tokens` (4.3, unchanged).
- Produces: `POST /api/account/claim {"tokens": [...], "device": true | false}` → `200 {"claimed": [...]}`. `"device"` is optional and `true` by default (the 4.3 contract and its tests stay as they are); `false` skips `claim_device`: only the readings of the tokens move. Anything but a JSON boolean is `422 {"reason": "invalid", "fields": ["device"]}` (`StrictBool`: Pydantic would otherwise read `"no"` as `false`). Site Task 11 sends it; Task 12 sets it to `true` only when the "sign-in started here" mark is on the device.

Why (owner decision 12, 22.11.2026, after the Fable plan check, question 2): the e-mail link may be opened on another device — a friend's computer. Without the field the claim there moves every guest reading of that browser into the person's account (someone else's questions in their diary). Why a body field and not a second address: one request and one transaction as before, the old body keeps its meaning, the site decides per request; a separate `POST /api/account/claim-tokens` would duplicate the route and its checks.

- [ ] **Step 1: Write the failing tests**

Append to the end of `api/tests/test_api_claim.py` (two blank lines before):

```python
# --- stage 4.4b §4 (owner decision 12): "device": false moves only the readings of the tokens ---

def claim_without_device(client, user, tokens):
    return client.post("/api/account/claim", headers=bearer(user), json={"tokens": tokens, "device": False})


def test_a_link_opened_on_another_device_moves_only_its_own_reading(api):
    reading_id = new_reading(api.client)
    token = claim_token(api.client, reading_id).json()["token"]
    other = api.new_client()  # someone else's computer, with a guest reading of its own
    theirs = new_reading(other)
    assert claim_without_device(other, ANA, [token]).json() == {"claimed": [reading_id]}
    assert reading_row(api, reading_id)["user_id"] == ANA and reading_row(api, theirs)["user_id"] is None
    assert claim(other, ANA).json() == {"claimed": [theirs]}  # without "device" the 4.3 behaviour is unchanged


def test_device_false_without_tokens_moves_nothing(api):
    mine = new_reading(api.client)
    response = claim_without_device(api.client, ANA, [])
    assert response.status_code == 200 and response.json() == {"claimed": []}
    assert reading_row(api, mine)["user_id"] is None


def test_device_is_true_or_false_only(api):
    response = api.client.post("/api/account/claim", headers=bearer(ANA), json={"tokens": [], "device": "no"})
    assert response.status_code == 422 and response.json() == {"reason": "invalid", "fields": ["device"]}
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_claim.py`
Expected: FAIL — `3 failed, 12 passed`: the first two move this device's reading too (`{'claimed': [<both>]}`, `user_id == ANA`), the third gets `200` (an unknown field is ignored).

- [ ] **Step 3: Implement**

In `api/app/routes/claim.py` replace

```python
- POST /api/account/claim {"tokens": [...]} (signed in): moves every unexpired guest reading of this device and the
  readings of the tokens into the account. A reading that already belongs to an account never moves; an unknown,
  used or expired token is skipped. A moved reading loses its expiry; the day slots the guest used stay with the
  guest.
"""
```

with

```python
- POST /api/account/claim {"tokens": [...], "device": true | false} (signed in): moves every unexpired guest reading
  of this device and the readings of the tokens into the account. A reading that already belongs to an account never
  moves; an unknown, used or expired token is skipped. A moved reading loses its expiry; the day slots the guest used
  stay with the guest. Stage 4.4b §4 (owner decision 12): "device": false moves only the readings of the tokens — the
  site sends it when the e-mail link is opened on a device where the sign-in was not started (someone else's guest
  readings stay there); left out, it is true, as in 4.3.
"""
```

replace `from pydantic import BaseModel, Field` with `from pydantic import BaseModel, Field, StrictBool`, replace

```python
class ClaimIn(BaseModel):
    tokens: list[ClaimToken] = Field(default_factory=list, max_length=20)
```

with

```python
class ClaimIn(BaseModel):
    tokens: list[ClaimToken] = Field(default_factory=list, max_length=20)
    device: StrictBool = True  # stage 4.4b §4: false — this device's guest readings stay where they are
```

and in `claim` replace

```python
    hashes = [account_repo.token_hash(token) for token in (body.tokens if body else [])]
    with ctx.db.connect() as conn:
        account_repo.ensure_profile(conn, who.user.id, now)
        moved = [] if who.new_guest is not None else account_repo.claim_device(conn, who.user.id, who.guest_id, now)
```

with

```python
    hashes = [account_repo.token_hash(token) for token in (body.tokens if body else [])]
    device = body.device if body else True
    with ctx.db.connect() as conn:
        account_repo.ensure_profile(conn, who.user.id, now)
        moved = account_repo.claim_device(conn, who.user.id, who.guest_id, now) \
            if device and who.new_guest is None else []
```

In `api/README.md` («Адреса», «Перенос») replace `` `POST /api/account/claim {"tokens": [...]}` → `{"claimed": [id, ...]}`. Дневник: `` with

```
`POST /api/account/claim {"tokens": [...], "device": true | false}` → `{"claimed": [id, ...]}` (этап 4.4б, решение
владельца 12: `"device": false` — переносятся только расклады токенов, гостевые расклады устройства остаются; без
поля — `true`, как в 4.3). Дневник:
```

and in «Передача в 4.4» replace `  («Сохранить в дневник» / «Войти»), а не при каждой загрузке страницы.` with

```
  («Сохранить в дневник» / «Войти»), а не при каждой загрузке страницы. Этап 4.4б (решение владельца 12): сайт
  шлёт `"device": true` только после входа, начатого на этом устройстве; ссылка из письма, открытая на другом
  устройстве, — `"device": false`, и переносится только расклад её токена.
```

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_claim.py && .venv/bin/pytest -q`
Expected: PASS — `15 passed`, then `1531 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/routes/claim.py api/tests/test_api_claim.py api/README.md
git commit -m "feat(api): stage 4.4b — claim with \"device\": false moves only the tokens' readings

Owner decision 12 (22.11.2026): an e-mail link opened on another device must not move
that browser's guest readings into the account. The field is optional and true by
default, so the 4.3 contract stays.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Packages and the DOM test setup

> **STOP — run only after the owner's explicit yes; the controller supplies it.** The yes covers exactly the packages and versions of the table «Packages» above (`@supabase/auth-js` 2.119.0, `@astrojs/check` 0.9.12, `typescript` 5.9.3, `happy-dom` 21.0.4 and the peer `@emnapi/runtime` 1.11.3). Any other version, package or a failed install → stop and report; do not try another version.

**Files:**
- Modify: `site/package.json`, `site/package-lock.json` (by npm), `site/vitest.config.ts`
- Create: `site/src/lib/testing/dom.ts`, `site/src/components/ui/HelpLine.test.tsx`

**Interfaces:**
- Consumes: `site/.npmrc` (`legacy-peer-deps=true`, unchanged), `preact` `render`, `preact/test-utils` `act`.
- Produces (every later DOM test uses these):
  - `*.test.tsx` files run in Vitest; a file that starts with `// @vitest-environment happy-dom` gets a DOM at `https://arcana.test/` (`location.origin === 'https://arcana.test'`, `localStorage`, `history`).
  - `site/src/lib/testing/dom.ts`: `mount(tree: ComponentChild): Promise<Mounted>` (`Mounted = { root: HTMLElement; unmount(): void }`; every mounted root is remembered), `cleanup(): void` (unmounts every root still mounted, then empties the body — **every DOM test file calls it in `afterEach`**, so listeners on `document` and timers never outlive a test), `settle(rounds?: number): Promise<void>`, `waitFor(check: () => unknown, timeoutMs = 2000): Promise<void>` (until `check` neither throws nor returns `false`; then its own error — use it instead of counting `settle` rounds), `byText<T>(root: ParentNode, text: string, selector?: string): T` (throws when missing), `queryText(root, text, selector?): HTMLElement | null`, `click(el: Element): Promise<void>`, `typeInto(el: Element, value: string): Promise<void>`, `submit(form: Element): Promise<void>`.
  - `vitest.config.ts`: `env: { TZ: 'UTC' }` — a date a test prints never depends on the machine (Docker is UTC; a laptop at UTC+6 is not); the local-day rules of Tasks 14–15 are still tested with local dates (`new Date(y, m, d, h)`), so they pass in any zone.
  - The smoke test pins the four happy-dom properties the screen tests rely on (review I11): `click()` on a checkbox fires `change`; `focus()` on `tabIndex = -1` moves `document.activeElement`; `pushState` / `replaceState` change `location` and `history.state`; `Response` behaves as the fakes use it (JSON, `clone()`, an empty `401` whose `json()` rejects). Measured: the six tests pass with happy-dom 21.0.4 (scratch copy, 22.11.2026); `history.back()` there also fires `popstate` asynchronously.

- [ ] **Step 1: Install the five packages (after the yes)**

Run from the repository root:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false \
  -v "$PWD/site:/app" -w /app node:22 sh -c '
    npm install --save-exact --before=2026-11-08T23:59:59Z @supabase/auth-js@2.119.0 &&
    npm install --save-dev --save-exact --before=2026-11-08T23:59:59Z @astrojs/check@0.9.12 typescript@5.9.3 happy-dom@21.0.4 @emnapi/runtime@1.11.3 &&
    npm ls --depth=0'
```

Expected: `npm ls` lists `@astrojs/check@0.9.12`, `@astrojs/preact@4.1.3`, `@emnapi/runtime@1.11.3`, `@supabase/auth-js@2.119.0`, `astro@5.18.2`, `happy-dom@21.0.4`, `preact@10.29.8`, `typescript@5.9.3`, `vitest@5.1.0`; no `ERR!`. `--before` makes npm pick every transitive dependency from versions published by 08.11.2026 too.

- [ ] **Step 2: Check what changed**

Run: `git diff site/package.json`
Expected: exactly these lines added — under `dependencies` `"@supabase/auth-js": "2.119.0",`; under `devDependencies` `"@astrojs/check": "0.9.12",`, `"@emnapi/runtime": "1.11.3",`, `"happy-dom": "21.0.4",`, `"typescript": "5.9.3",` (exact versions, no `^`). `astro` stays `^5.1.0` and resolves to 5.18.2 in the lockfile: `grep -A1 '"node_modules/astro"' site/package-lock.json` → `"version": "5.18.2"`. Report `du -sh site/node_modules` before (178M) and after.

- [ ] **Step 3: Write the first DOM test**

Create `site/src/components/ui/HelpLine.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { useEffect, useState } from 'preact/hooks';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, click, mount, waitFor } from '../../lib/testing/dom';
import { jsonResponse } from '../../lib/testing/fakes';
import { HelpLine } from './HelpLine';

afterEach(() => {
  cleanup();
  localStorage.clear();
  history.replaceState(null, '', '/');
});

// The screen tests of stage 4.4b lean on these properties of happy-dom; each is pinned here first (Fable plan review
// I11), so a difference shows up in this file and not halfway through a screen task.
describe('the DOM test setup (spec 4.4b §9)', () => {
  it('renders a component into a document with the stage address and a storage', async () => {
    const { root, unmount } = await mount(<HelpLine lang="es" />);
    const link = root.querySelector('a')!;
    expect(link.getAttribute('href')).toBe('https://findahelpline.com');
    expect(link.textContent).toBe('Líneas de ayuda gratuitas y confidenciales');
    expect(location.origin).toBe('https://arcana.test');
    localStorage.setItem('x', '1');
    expect(localStorage.getItem('x')).toBe('1');
    unmount();
    expect(document.body.textContent).toBe('');
  });

  it('click() on a checkbox ticks it and fires change (the save sheet, the account switch)', async () => {
    function Box() {
      const [on, setOn] = useState(false);
      return (
        <label>
          <input type="checkbox" checked={on} onChange={(e) => setOn((e.target as HTMLInputElement).checked)} />
          <span>{on ? 'on' : 'off'}</span>
        </label>
      );
    }
    const { root } = await mount(<Box />);
    await click(root.querySelector('input')!);
    expect(root.querySelector('input')!.checked).toBe(true);
    expect(root.querySelector('span')!.textContent).toBe('on');
  });

  it('focus() on a heading with tabIndex -1 moves document.activeElement (focus after a screen change)', async () => {
    const { root } = await mount(<h2 tabIndex={-1}>Check your e-mail</h2>);
    root.querySelector('h2')!.focus();
    expect(document.activeElement?.textContent).toBe('Check your e-mail');
  });

  it('pushState and replaceState change location and history.state (the diary address, the sheet entry)', () => {
    history.pushState({ arcanaNight: true }, '', '/diary?claim=t&remind=1');
    expect(`${location.pathname}${location.search}`).toBe('/diary?claim=t&remind=1');
    expect(history.state).toEqual({ arcanaNight: true });
    history.replaceState(null, '', '/diary');
    expect(`${location.pathname}${location.search}`).toBe('/diary');
    expect(history.state).toBeNull();
  });

  it('Response as the fakes use it: JSON, clone(), an empty 401 whose json() fails', async () => {
    const ok = jsonResponse(200, { a: 1 });
    expect(ok).toBeInstanceOf(Response);
    expect(await ok.clone().json()).toEqual({ a: 1 });
    expect(await ok.json()).toEqual({ a: 1 });
    const stage = new Response('', { status: 401 });
    expect(stage.status).toBe(401);
    await expect(stage.clone().json()).rejects.toThrow();
    expect(typeof fetch).toBe('function');
  });

  it('cleanup() unmounts what is still mounted, so its listeners go; waitFor waits for a condition', async () => {
    const keys: string[] = [];
    function Listener() {
      const [ready, setReady] = useState(false);
      useEffect(() => {
        const onKey = (event: KeyboardEvent) => keys.push(event.key);
        document.addEventListener('keydown', onKey);
        void Promise.resolve().then(() => setReady(true));
        return () => document.removeEventListener('keydown', onKey);
      }, []);
      return <p>{ready ? 'ready' : 'waiting'}</p>;
    }
    const { root } = await mount(<Listener />);
    await waitFor(() => expect(root.textContent).toBe('ready'));
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    cleanup();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b' }));
    expect(keys).toEqual(['a']);
    expect(document.body.childElementCount).toBe(0);
    await expect(waitFor(() => false, 50)).rejects.toThrow('waitFor: the check stayed false');
  });
});
```

Create `site/src/lib/testing/dom.ts`:

```ts
// Screen tests (happy-dom): mount a Preact tree, wait for effects and fetches, find and press things the way a
// person does — by their visible text or label. Every DOM test file calls cleanup() in afterEach: it unmounts what
// mount() rendered, so a test's listeners on document and its timers never outlive it (Fable plan review I11).
import { render, type ComponentChild } from 'preact';
import { act } from 'preact/test-utils';

export interface Mounted {
  root: HTMLElement;
  unmount: () => void;
}

const mounted = new Set<HTMLElement>();

function unmountRoot(root: HTMLElement): void {
  if (!mounted.delete(root)) return;
  render(null, root);
  root.remove();
}

export async function mount(tree: ComponentChild): Promise<Mounted> {
  const root = document.createElement('div');
  document.body.appendChild(root);
  mounted.add(root);
  await act(() => {
    render(tree, root);
  });
  await settle();
  return { root, unmount: () => unmountRoot(root) };
}

/** For afterEach: unmounts every tree that is still mounted (their effect cleanups run), then empties the body. */
export function cleanup(): void {
  for (const root of Array.from(mounted)) unmountRoot(root);
  document.body.replaceChildren();
}

/** Lets pending promises (fake fetches, effects) run, several rounds. */
export async function settle(rounds = 10): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await act(async () => {
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
    });
  }
}

/** Waits until `check` passes — it throws or returns false until then — for at most `timeoutMs`, then fails with
 * the check's own error. For screens that make several requests one after another (the diary). */
export async function waitFor(check: () => unknown, timeoutMs = 2000): Promise<void> {
  const start = Date.now();
  for (;;) {
    let failure: unknown;
    try {
      if (check() !== false) return;
      failure = new Error('waitFor: the check stayed false');
    } catch (error) {
      failure = error;
    }
    if (Date.now() - start > timeoutMs) throw failure;
    await settle(1);
  }
}

export function byText<T extends HTMLElement = HTMLElement>(root: ParentNode, text: string, selector = '*'): T {
  const found = Array.from(root.querySelectorAll<T>(selector)).filter((el) => el.textContent?.trim() === text);
  if (found.length === 0) throw new Error(`no element with the text "${text}"`);
  return found[found.length - 1]; // the innermost
}

export function queryText(root: ParentNode, text: string, selector = '*'): HTMLElement | null {
  try {
    return byText(root, text, selector);
  } catch {
    return null;
  }
}

export async function click(el: Element): Promise<void> {
  await act(() => {
    (el as HTMLElement).click();
  });
  await settle();
}

export async function typeInto(el: Element, value: string): Promise<void> {
  await act(() => {
    const input = el as HTMLInputElement | HTMLTextAreaElement;
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

export async function submit(form: Element): Promise<void> {
  await act(() => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
  await settle();
}
```

- [ ] **Step 4: Run it to see it fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/components/ui/HelpLine.test.tsx`
Expected: FAIL — `No test files found` (the config includes only `src/**/*.test.ts`).

- [ ] **Step 5: Let Vitest run `.test.tsx` files with a DOM**

Replace the whole `site/vitest.config.ts` with:

```ts
import { defineConfig } from 'vitest/config';

// Logic without a screen lives in src/lib and src/i18n and is tested here in Node. Screens (spec 4.4b §9, §11) are
// tested in *.test.tsx files that start with `// @vitest-environment happy-dom` (a DOM in memory, no browser, no
// network: fetch is replaced in every test). TZ is fixed, so a date a test names never depends on the machine; the
// day rules themselves are tested with local dates (spec 4.4b §2, decision 13).
export default defineConfig({
  esbuild: { jsx: 'automatic', jsxImportSource: 'preact' },
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    environment: 'node',
    environmentOptions: { happyDOM: { url: 'https://arcana.test/' } },
    env: { TZ: 'UTC' },
  },
});
```

- [ ] **Step 6: Run the test, then everything, then the build**

Run: the Vitest command of Step 4, then the same without a file, then `deploy/build-site.sh && python3 tools/site/check_dist.py`
Expected: `6 passed`; then `204 passed` in 19 files (both measured in the scratch copy); then the build ends with `167 page(s) built` and `OK: 167 pages` (`npm ci` installs from the new lockfile). `astro check` comes in Task 8.

- [ ] **Step 7: Commit**

```bash
git add site/package.json site/package-lock.json site/vitest.config.ts site/src/lib/testing/dom.ts site/src/components/ui/HelpLine.test.tsx
git commit -m "build(site): stage 4.4b — auth-js 2.119.0, astro check 0.9.12, TypeScript 5.9.3, happy-dom 21.0.4

Owner approved 22.11.2026. Exact versions published by 08.11.2026 (npm --before for the
transitive ones). TypeScript 5.x: Astro 5.18.2's tsconfck and zod-to-ts declare ^5.
@emnapi/runtime 1.11.3: a peer that legacy-peer-deps skips and astro check needs.
Vitest runs *.test.tsx screen tests in happy-dom at https://arcana.test/, TZ=UTC; the
smoke test pins the happy-dom behaviour the screen tests rely on.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 8: Site — `astro check` with no errors, before any new screen code

**Files:**
- Modify: `site/package.json` (`scripts.check`), `site/src/islands/ReadingIsland.tsx` (the `params` of the transition events), `site/src/lib/testing/fakes.ts` (`bytes`), `site/src/lib/readingFlow.test.ts` (the type of its `posts` helper)

**Interfaces:**
- Consumes: `@astrojs/check` 0.9.12, `typescript` 5.9.3 and `@emnapi/runtime` 1.11.3 (Task 7); `site/tsconfig.json` (`astro/tsconfigs/strict`, `jsxImportSource: preact`, unchanged).
- Produces: `npm run check` (= `astro check`) → `0 errors`. From here on every site task (9–21) runs the check in its verification step and expects `- 0 errors`; a type error is fixed in the task that makes it (Fable plan review I10).

Why this task comes here (review I10): run last, the check would meet twelve tasks of new TSX at once and its fixes would touch screens that were already reviewed. Measured while amending this plan (22.11.2026; a scratch copy of `stage4-4b-account` at 318a286 with Task 7's files and the five packages installed with `--no-save --before=2026-11-08T23:59:59Z`): the existing code has exactly 9 errors, all type-only, no bug among them:
- `src/islands/ReadingIsland.tsx:117` TS2345 — the union `{ cards_count } | { ms_from_draw } | {}` is not a `Params` (`ms_from_draw?: undefined` against the index signature);
- `src/lib/readingFlow.test.ts:241, 242, 250, 276` (seven errors) TS2339 — the helper `posts(h)` is typed `Array<{ url: string }>`, so `.body` does not exist for TypeScript;
- `src/lib/testing/fakes.ts:20` TS2345 — `bytes()` is declared `Uint8Array` (= `Uint8Array<ArrayBufferLike>`), which TypeScript 5.9's DOM types do not accept as a `BodyInit`.
Hints: 2 (unused `config` in `NightRoom.tsx:58`, unused `state` in `nightRoom.ts:61`); they may stay.

- [ ] **Step 1: Add the script**

In `site/package.json`, in `"scripts"`, after `"build": "astro build",` add `"check": "astro check",`.

- [ ] **Step 2: Run the check to see the errors**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 npx astro check`
Expected: FAIL — `Result (78 files):`, `- 9 errors`, `- 0 warnings`, `- 2 hints`, the nine errors listed above. If Astro instead asks «To continue, Astro requires the following dependency to be installed: @astrojs/check» — that is the missing `@emnapi/runtime` of Task 7 (the import of `@astrojs/check` fails and Astro reads it as "not installed"): stop and report. Other errors than the nine: copy the full list into the report and fix them by the rules of Step 3 as well.

- [ ] **Step 3: Fix the nine errors with type-only changes**

In `site/src/islands/ReadingIsland.tsx` replace

```tsx
      const params = name === 'cards_revealed' ? { cards_count: state.reading?.cards.length ?? 1 }
```

with

```tsx
      const params: Record<string, number> = name === 'cards_revealed' ? { cards_count: state.reading?.cards.length ?? 1 }
```

In `site/src/lib/testing/fakes.ts` replace `function bytes(text: string): Uint8Array {` with `function bytes(text: string): Uint8Array<ArrayBuffer> {`.

In `site/src/lib/readingFlow.test.ts` replace `import { brokenSseResponse, fakeFetch, jsonResponse, sseResponse, sseText } from './testing/fakes';` with `import { brokenSseResponse, fakeFetch, jsonResponse, sseResponse, sseText, type Call } from './testing/fakes';` and `  const posts = (h: { calls: Array<{ url: string }> }) => h.calls.filter((c) => c.url.endsWith('/followups'));` with `  const posts = (h: { calls: Call[] }) => h.calls.filter((c) => c.url.endsWith('/followups'));`.

Rules for any other error (now and in every later task):
- Fix the type, not the behaviour: a precise type, a narrowing (`if (!x) return`), a missing field in a test fixture, an `as` cast only where the value comes from JSON of the API. Never `any`, `// @ts-ignore`, `// @ts-expect-error`, and never weaken `tsconfig.json`.
- If an error shows a real bug (a wrong field name, a possibly undefined value used at run time), stop and report it to the controller with the file and line: it becomes its own small fix with a test.
- Warnings and hints may stay; list them in the report.

- [ ] **Step 4: Run the check, the tests and the build**

Run: the command of Step 2, then the Vitest command (no files), then `deploy/build-site.sh && python3 tools/site/check_dist.py`
Expected: `- 0 errors` (`- 2 hints`); `204 passed` in 19 files; `OK: 167 pages`. (All three measured in the scratch copy described above.)

- [ ] **Step 5: Commit**

```bash
git add site/package.json site/src/islands/ReadingIsland.tsx site/src/lib/testing/fakes.ts site/src/lib/readingFlow.test.ts
git commit -m "build(site): stage 4.4b — astro check with no errors

Owner decision 20.11.2026; run before the new screens (Fable plan review I10). Nine
type-only errors of the existing code: the transition event params, the SSE fake's bytes,
the follow-up test helper's call type.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Site — sign-in state, settings and the lazy sign-in library

**Files:**
- Create: `site/src/lib/authState.ts`, `site/src/lib/authConfig.ts`, `site/src/lib/auth.ts`, `site/src/lib/supabaseClient.ts`, `site/src/lib/testing/auth.ts`
- Test: `site/src/lib/authState.test.ts`, `site/src/lib/authConfig.test.ts`, `site/src/lib/auth.test.ts`; modify `site/src/lib/guards.test.ts`

**Interfaces:**
- Consumes: `FetchFn` from `site/src/lib/api.ts`; `fakeFetch`, `jsonResponse` from `site/src/lib/testing/fakes.ts`; `AuthClient` from `@supabase/auth-js` (Task 7) — in `supabaseClient.ts` only.
- Produces:
  - `authState.ts`: `SIGNED_IN_KEY = 'ad_signed_in'`, `STARTED_KEY = 'ad_signin_started'`, `STARTED_MAX_AGE_MS`, `type SignInMethod = 'email' | 'google'`, `interface StorageLike`, `browserStorage(): StorageLike | null`, `isSignedIn(storage?)`, `markSignedIn(storage?)`, `clearSignedIn(storage?)`, `markSignInStarted(method, now?, storage?)`, `signInStarted(now?, storage?): SignInMethod | null`, `clearSignInStarted(storage?)`.
  - `authConfig.ts`: `interface AuthConfig { enabled: boolean; supabase_url: string; anon_key: string; google: boolean }`, `AUTH_CONFIG_URL`, `parseAuthConfig(body: unknown): AuthConfig`, `fetchAuthConfig(fetchFn): Promise<AuthConfig | null>` (null = unreadable), `authConfig(fetchFn?)` (once per page), `forgetAuthConfig()` (tests).
  - `auth.ts`: `SessionLike`, `AuthErrorLike`, `AuthClientLike`, `type ClientFactory`, `loadSupabaseClient` (the only `import('./supabaseClient')`), `type SendError = 'tooOften' | 'badEmail' | 'unavailable'`, `type SendResult`, `sendError(error)`, `interface Auth { session(); token(); refresh(); sendLink(email, redirectTo); google(redirectTo); signOut() }`, `createAuth(config, factory?, storage?): Auth`, `methodOf(session, started): SignInMethod`, `sharedAuth(config): Auth`, `getAuth(): Promise<Auth | null>`, `type SessionStatus = {type:'off'} | {type:'unreachable'} | {type:'signedOut'; auth; google} | {type:'signedIn'; auth; google; session}`, `openSession(readConfig?, makeAuth?): Promise<SessionStatus>`, `forgetAuth()` (tests).
  - `supabaseClient.ts`: `AUTH_STORAGE_KEY = 'ad-auth'`, `createClient(config: AuthConfig): AuthClientLike` — `new AuthClient({ url: <supabase_url>/auth/v1, headers: { apikey }, storageKey, persistSession, autoRefreshToken, detectSessionInUrl: true, flowType: 'implicit' })`.
  - `testing/auth.ts`: `memoryStorage(initial?)`, `fakeClient(session?) : FakeClient` (records `calls`; `session`, `refreshed`, `sendError` settable), `session(token?, provider?, email?)`.

- [ ] **Step 1: Write the failing tests and the fakes**

Create `site/src/lib/testing/auth.ts`:

```ts
// Test doubles for signing in: an in-memory storage and a fake sign-in library client (no network, no
// @supabase/auth-js).
import type { AuthClientLike, AuthErrorLike, SessionLike } from '../auth';
import type { StorageLike } from '../authState';

export function memoryStorage(initial: Record<string, string> = {}): StorageLike & { data: Record<string, string> } {
  const data = { ...initial };
  return {
    data,
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => { data[key] = value; },
    removeItem: (key) => { delete data[key]; },
  };
}

export interface FakeClient extends AuthClientLike {
  calls: Array<{ method: string; args: unknown }>;
  session: SessionLike | null;
  refreshed: SessionLike | null;
  sendError: AuthErrorLike | null;
}

export function fakeClient(session: SessionLike | null = null): FakeClient {
  const client: FakeClient = {
    calls: [],
    session,
    refreshed: null,
    sendError: null,
    async getSession() {
      client.calls.push({ method: 'getSession', args: null });
      return { data: { session: client.session }, error: null };
    },
    async refreshSession() {
      client.calls.push({ method: 'refreshSession', args: null });
      client.session = client.refreshed;
      return { data: { session: client.refreshed }, error: client.refreshed ? null : { message: 'refresh failed' } };
    },
    async signInWithOtp(args) {
      client.calls.push({ method: 'signInWithOtp', args });
      return { error: client.sendError };
    },
    async signInWithOAuth(args) {
      client.calls.push({ method: 'signInWithOAuth', args });
      return { error: client.sendError };
    },
    async signOut(args) {
      client.calls.push({ method: 'signOut', args });
      client.session = null;
      return { error: null };
    },
  };
  return client;
}

export function session(token = 'tok-1', provider = 'email', email = 'ana@example.com'): SessionLike {
  return { access_token: token, user: { email, app_metadata: { provider } } };
}
```

Create `site/src/lib/authState.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  STARTED_KEY, STARTED_MAX_AGE_MS, clearSignInStarted, clearSignedIn, isSignedIn, markSignInStarted, markSignedIn,
  signInStarted, type StorageLike,
} from './authState';
import { memoryStorage } from './testing/auth';

describe('the signed-in flag', () => {
  it('is set, read and cleared', () => {
    const storage = memoryStorage();
    expect(isSignedIn(storage)).toBe(false);
    markSignedIn(storage);
    expect(isSignedIn(storage)).toBe(true);
    clearSignedIn(storage);
    expect(isSignedIn(storage)).toBe(false);
  });

  it('is simply off when there is no storage or it throws', () => {
    const broken: StorageLike = {
      getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); }, removeItem: () => {},
    };
    expect(isSignedIn(null)).toBe(false);
    expect(isSignedIn(broken)).toBe(false);
    expect(() => markSignedIn(broken)).not.toThrow();
    expect(signInStarted(0, broken)).toBeNull();
  });
});

describe('the started sign-in mark', () => {
  it('keeps the method for a day', () => {
    const storage = memoryStorage();
    markSignInStarted('google', 1000, storage);
    expect(signInStarted(1000 + STARTED_MAX_AGE_MS, storage)).toBe('google');
    expect(signInStarted(1001 + STARTED_MAX_AGE_MS, storage)).toBeNull();
    clearSignInStarted(storage);
    expect(signInStarted(1000, storage)).toBeNull();
  });

  it('ignores anything it did not write', () => {
    const storage = memoryStorage();
    for (const raw of ['nonsense', '{"method":"apple","at":1}', '{"method":"email"}']) {
      storage.setItem(STARTED_KEY, raw);
      expect(signInStarted(1, storage)).toBeNull();
    }
  });
});
```

Create `site/src/lib/authConfig.test.ts`:

```ts
import { afterEach, describe, expect, it } from 'vitest';
import { AUTH_CONFIG_URL, authConfig, fetchAuthConfig, forgetAuthConfig, parseAuthConfig } from './authConfig';
import { fakeFetch, jsonResponse } from './testing/fakes';

const ON = { enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: true };

afterEach(() => forgetAuthConfig());

describe('auth config', () => {
  it('reads the settings of GET /api/auth-config', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, ON));
    expect(await fetchAuthConfig(fetch)).toEqual(ON);
    expect(calls[0]).toMatchObject({ url: AUTH_CONFIG_URL, method: 'GET' });
  });

  it('is off without an https address or a key, whatever "enabled" says', () => {
    expect(parseAuthConfig({ ...ON, supabase_url: 'http://abc.supabase.co' }).enabled).toBe(false);
    expect(parseAuthConfig({ ...ON, anon_key: '' })).toEqual({ enabled: false, supabase_url: '', anon_key: '', google: false });
    expect(parseAuthConfig({ enabled: false, supabase_url: '', anon_key: '', google: false }).enabled).toBe(false);
    expect(parseAuthConfig('nonsense').enabled).toBe(false);
    expect(parseAuthConfig({ ...ON, google: 'yes' }).google).toBe(false);
  });

  it('is null when it cannot be read, and asks again next time', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(503, { reason: 'db' }), new TypeError('offline'), jsonResponse(200, ON));
    expect(await authConfig(fetch)).toBeNull();
    expect(await authConfig(fetch)).toBeNull();
    expect(await authConfig(fetch)).toEqual(ON);
    expect(await authConfig(fetch)).toEqual(ON); // cached: no fourth request
    expect(calls).toHaveLength(3);
  });
});
```

Create `site/src/lib/auth.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { createAuth, methodOf, openSession, sendError, type SessionLike } from './auth';
import type { AuthConfig } from './authConfig';
import { STARTED_KEY, SIGNED_IN_KEY, markSignInStarted } from './authState';
import { fakeClient, memoryStorage, session } from './testing/auth';

const CONFIG: AuthConfig = { enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: true };

function setup(current: SessionLike | null = session()) { // typed: setup(null) is a signed-out client
  const client = fakeClient(current);
  const storage = memoryStorage();
  let loads = 0;
  const auth = createAuth(CONFIG, async (config) => {
    loads += 1;
    expect(config).toEqual(CONFIG);
    return client;
  }, storage);
  return { auth, client, storage, loads: () => loads };
}

describe('createAuth', () => {
  it('loads the library once, on first use, and keeps the signed-in flag in step with the session', async () => {
    const { auth, client, storage, loads } = setup();
    expect(loads()).toBe(0);
    expect(await auth.token()).toBe('tok-1');
    expect(await auth.token()).toBe('tok-1');
    expect(loads()).toBe(1);
    expect(storage.data[SIGNED_IN_KEY]).toBe('1');
    client.session = null; // signed out in another tab
    expect(await auth.token()).toBeNull();
    expect(storage.data[SIGNED_IN_KEY]).toBeUndefined();
  });

  it('refreshes once and gives the new token, or null', async () => {
    const { auth, client } = setup();
    client.refreshed = session('tok-2');
    expect(await auth.refresh()).toBe('tok-2');
    client.refreshed = null;
    expect(await auth.refresh()).toBeNull();
  });

  it('sends the e-mail link back to the given address (implicit flow is set in supabaseClient.ts)', async () => {
    const { auth, client } = setup(null);
    expect(await auth.sendLink('ana@example.com', 'https://arcana.test/diary?claim=t')).toEqual({ ok: true });
    expect(client.calls.at(-1)).toEqual({ method: 'signInWithOtp', args: {
      email: 'ana@example.com', options: { emailRedirectTo: 'https://arcana.test/diary?claim=t', shouldCreateUser: true },
    } });
    expect(await auth.google('https://arcana.test/es/diario')).toEqual({ ok: true });
    expect(client.calls.at(-1)).toEqual({ method: 'signInWithOAuth', args: {
      provider: 'google', options: { redirectTo: 'https://arcana.test/es/diario' },
    } });
  });

  it('turns Supabase errors into one readable kind each', async () => {
    const { auth, client } = setup(null);
    client.sendError = { status: 429, code: 'over_email_send_rate_limit' };
    expect(await auth.sendLink('ana@example.com', 'x')).toEqual({ ok: false, error: 'tooOften' });
    expect(sendError({ status: 400, code: 'email_address_invalid' })).toBe('badEmail');
    expect(sendError({ status: 422, code: 'validation_failed' })).toBe('badEmail');
    expect(sendError({ status: 500 })).toBe('unavailable');
    expect(sendError({ code: 'over_request_rate_limit' })).toBe('tooOften');
  });

  it('a library that cannot load is "unavailable", never a thrown error', async () => {
    const auth = createAuth(CONFIG, async () => { throw new Error('chunk failed'); }, memoryStorage());
    expect(await auth.session()).toBeNull();
    expect(await auth.sendLink('ana@example.com', 'x')).toEqual({ ok: false, error: 'unavailable' });
  });

  it('signs out this device: the session, the flag and the started mark go', async () => {
    const { auth, client, storage } = setup();
    await auth.token();
    markSignInStarted('email', Date.now(), storage);
    await auth.signOut();
    expect(client.calls.at(-1)).toEqual({ method: 'signOut', args: { scope: 'local' } });
    expect(storage.data[SIGNED_IN_KEY]).toBeUndefined();
    expect(storage.data[STARTED_KEY]).toBeUndefined();
  });

  it('signs out this device even when the library answers an error or throws (review M6)', async () => {
    for (const signOut of [async () => ({ error: { message: 'offline' } }), async () => { throw new Error('offline'); }]) {
      const client = { ...fakeClient(session()), signOut };
      const storage = memoryStorage({ [SIGNED_IN_KEY]: '1' });
      markSignInStarted('email', Date.now(), storage);
      await createAuth(CONFIG, async () => client, storage).signOut();
      expect(storage.data[SIGNED_IN_KEY]).toBeUndefined();
      expect(storage.data[STARTED_KEY]).toBeUndefined();
    }
  });

  it('a library that failed to load is loaded again on the next use (review M7)', async () => {
    const client = fakeClient(session());
    let tries = 0;
    const auth = createAuth(CONFIG, async () => {
      tries += 1;
      if (tries === 1) throw new Error('chunk failed');
      return client;
    }, memoryStorage());
    expect(await auth.token()).toBeNull(); // offline for a moment
    expect(await auth.token()).toBe('tok-1');
    expect(tries).toBe(2);
  });
});

describe('methodOf', () => {
  it('takes the started mark first, then the provider of the session', () => {
    expect(methodOf(session('t', 'google'), 'email')).toBe('email');
    expect(methodOf(session('t', 'google'), null)).toBe('google');
    expect(methodOf(session('t', 'email'), null)).toBe('email');
    expect(methodOf(null, null)).toBe('email');
  });
});

describe('openSession', () => {
  it('is off, unreachable, signed out or signed in', async () => {
    expect(await openSession(async () => null)).toEqual({ type: 'unreachable' });
    expect(await openSession(async () => ({ ...CONFIG, enabled: false }))).toEqual({ type: 'off' });
    const out = setup(null);
    expect(await openSession(async () => CONFIG, () => out.auth)).toMatchObject({ type: 'signedOut', google: true });
    const signed = setup();
    expect(await openSession(async () => CONFIG, () => signed.auth)).toMatchObject({
      type: 'signedIn', google: true, session: { access_token: 'tok-1' },
    });
  });
});
```

In `site/src/lib/guards.test.ts`, before `  it('load the Turnstile script only from src/lib/turnstile.ts', () => {` add:

```ts
  it('import @supabase/auth-js only in src/lib/supabaseClient.ts (spec 4.4b §3: a chunk of its own)', () => {
    const users = SOURCES.filter((p) => /from\s*['"]@supabase\/|import\(\s*['"]@supabase\//.test(read(p)));
    expect(users.map(rel)).toEqual(['lib/supabaseClient.ts']);
  });

  it('load supabaseClient.ts only with import(), only from src/lib/auth.ts', () => {
    const users = SOURCES.filter((p) => /['"]\.{1,2}\/(?:[\w/]*\/)?supabaseClient['"]/.test(read(p)));
    expect(users.map(rel)).toEqual(['lib/auth.ts']);
    expect(read(join(SRC, 'lib/auth.ts'))).toMatch(/import\(\s*['"]\.\/supabaseClient['"]\s*\)/);
    expect(read(join(SRC, 'lib/auth.ts'))).not.toMatch(/from\s*['"]\.\/supabaseClient['"]/);
  });
```

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/authState.test.ts src/lib/authConfig.test.ts src/lib/auth.test.ts src/lib/guards.test.ts`
Expected: FAIL — `Failed to resolve import "./authState"` (and `./authConfig`, `./auth`); the two new guards tests fail with `expected [] to deeply equal [ 'lib/supabaseClient.ts' ]`.

- [ ] **Step 3: Implement**

Create `site/src/lib/authState.ts`:

```ts
// What this device remembers about signing in (spec 4.4b §3, §4), apart from the session the sign-in library keeps:
// `ad_signed_in` — there is a session here, so API requests load the library and carry the token; `ad_signin_started`
// — a sign-in was started by a button on this device (e-mail link sent, or Google), so the diary may move this
// device's guest readings into the account once (api/README.md "Передача в 4.4"). Never a token, never an e-mail.

export const SIGNED_IN_KEY = 'ad_signed_in';
export const STARTED_KEY = 'ad_signin_started';
/** An e-mail link opened later than this is not "started here" any more (the link itself lives an hour). */
export const STARTED_MAX_AGE_MS = 24 * 60 * 60 * 1000;

export type SignInMethod = 'email' | 'google';

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** localStorage, or null where it cannot be used (private mode, blocked): then the site works as a guest. */
export function browserStorage(): StorageLike | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage;
  } catch {
    return null;
  }
}

function safely<T>(fallback: T, action: () => T): T {
  try {
    return action();
  } catch {
    return fallback;
  }
}

export function isSignedIn(storage: StorageLike | null = browserStorage()): boolean {
  return safely(false, () => storage?.getItem(SIGNED_IN_KEY) === '1');
}

export function markSignedIn(storage: StorageLike | null = browserStorage()): void {
  safely(undefined, () => storage?.setItem(SIGNED_IN_KEY, '1'));
}

export function clearSignedIn(storage: StorageLike | null = browserStorage()): void {
  safely(undefined, () => storage?.removeItem(SIGNED_IN_KEY));
}

export function markSignInStarted(method: SignInMethod, now: number = Date.now(),
  storage: StorageLike | null = browserStorage()): void {
  safely(undefined, () => storage?.setItem(STARTED_KEY, JSON.stringify({ method, at: now })));
}

/** The method of a sign-in started on this device within STARTED_MAX_AGE_MS, or null. */
export function signInStarted(now: number = Date.now(), storage: StorageLike | null = browserStorage()): SignInMethod | null {
  return safely(null, () => {
    const raw = storage?.getItem(STARTED_KEY);
    if (!raw) return null;
    const mark = JSON.parse(raw) as { method?: unknown; at?: unknown };
    const fresh = typeof mark.at === 'number' && now - mark.at >= 0 && now - mark.at <= STARTED_MAX_AGE_MS;
    return fresh && (mark.method === 'email' || mark.method === 'google') ? mark.method : null;
  });
}

export function clearSignInStarted(storage: StorageLike | null = browserStorage()): void {
  safely(undefined, () => storage?.removeItem(STARTED_KEY));
}
```

Create `site/src/lib/authConfig.ts`:

```ts
// The public sign-in settings (spec 4.4b §3): GET /api/auth-config → {"enabled", "supabase_url", "anon_key",
// "google"}. Read once per page; nothing here loads the sign-in library.
import type { FetchFn } from './api';

export interface AuthConfig {
  enabled: boolean;
  supabase_url: string;
  anon_key: string;
  google: boolean;
}

export const AUTH_CONFIG_URL = '/api/auth-config';

/** The answer as the site may trust it: on only with an https address and a key. */
export function parseAuthConfig(body: unknown): AuthConfig {
  const b = (body && typeof body === 'object' ? body : {}) as Record<string, unknown>;
  const url = typeof b.supabase_url === 'string' ? b.supabase_url : '';
  const key = typeof b.anon_key === 'string' ? b.anon_key : '';
  const enabled = b.enabled === true && url.startsWith('https://') && key !== '';
  return { enabled, supabase_url: enabled ? url : '', anon_key: enabled ? key : '', google: enabled && b.google === true };
}

/** null when the settings could not be read (offline, the API down): the caller says "try later". */
export async function fetchAuthConfig(fetchFn: FetchFn): Promise<AuthConfig | null> {
  try {
    const response = await fetchFn(AUTH_CONFIG_URL, { method: 'GET' });
    if (!response.ok) return null;
    return parseAuthConfig(await response.json());
  } catch {
    return null;
  }
}

let cached: Promise<AuthConfig | null> | null = null;

/** One request per page; a failed one is asked again next time. */
export function authConfig(fetchFn: FetchFn = (input, init) => fetch(input, init)): Promise<AuthConfig | null> {
  if (!cached) {
    cached = fetchAuthConfig(fetchFn).then((config) => {
      if (config === null) cached = null;
      return config;
    });
  }
  return cached;
}

export function forgetAuthConfig(): void {
  cached = null;
}
```

Create `site/src/lib/auth.ts`:

```ts
// Signing in through Supabase in the browser (spec 4.4b §3): an e-mail link (implicit flow: the link works on any
// device) and Google, both back to the diary page of the page's language. The library itself lives in
// supabaseClient.ts and is loaded with import() only here, so a guest's reading page never downloads it; only the
// parts of it this site uses are typed below (tests pass a fake client).
import type { AuthConfig } from './authConfig';
import { authConfig } from './authConfig';
import {
  browserStorage, clearSignInStarted, clearSignedIn, markSignedIn, type SignInMethod, type StorageLike,
} from './authState';

export interface SessionLike {
  access_token: string;
  user?: { email?: string | null; app_metadata?: { provider?: string } };
}

export interface AuthErrorLike {
  status?: number;
  code?: string;
  message?: string;
}

type SessionAnswer = Promise<{ data: { session: SessionLike | null }; error: unknown }>;

/** The part of @supabase/auth-js's AuthClient that this site calls. */
export interface AuthClientLike {
  getSession(): SessionAnswer;
  refreshSession(): SessionAnswer;
  signInWithOtp(credentials: { email: string; options: { emailRedirectTo: string; shouldCreateUser: boolean } }):
    Promise<{ error: AuthErrorLike | null }>;
  signInWithOAuth(credentials: { provider: 'google'; options: { redirectTo: string } }):
    Promise<{ error: AuthErrorLike | null }>;
  signOut(options: { scope: 'local' }): Promise<{ error: unknown }>;
}

export type ClientFactory = (config: AuthConfig) => Promise<AuthClientLike>;

/** The real library, as its own chunk (the build checks that reading pages do not load it). */
export const loadSupabaseClient: ClientFactory = async (config) => (await import('./supabaseClient')).createClient(config);

export type SendError = 'tooOften' | 'badEmail' | 'unavailable';
export type SendResult = { ok: true } | { ok: false; error: SendError };

/** Supabase's errors as one readable line each (spec 4.4b §4: "too often", "wrong e-mail"). */
export function sendError(error: AuthErrorLike): SendError {
  const code = error.code ?? '';
  if (error.status === 429 || code.includes('rate_limit')) return 'tooOften';
  if (code === 'email_address_invalid' || code === 'validation_failed' || error.status === 400 || error.status === 422) {
    return 'badEmail';
  }
  return 'unavailable';
}

export interface Auth {
  /** The current session, or null; keeps the `ad_signed_in` flag in step with it. */
  session(): Promise<SessionLike | null>;
  token(): Promise<string | null>;
  /** One refresh after 401 {"reason": "auth"}; null when it did not help. */
  refresh(): Promise<string | null>;
  sendLink(email: string, redirectTo: string): Promise<SendResult>;
  google(redirectTo: string): Promise<SendResult>;
  /** This device only: the library's session, `ad_signed_in` and the started mark go. */
  signOut(): Promise<void>;
}

export function createAuth(config: AuthConfig, factory: ClientFactory = loadSupabaseClient,
  storage: StorageLike | null = browserStorage()): Auth {
  let client: Promise<AuthClientLike> | null = null;
  // a failed load (offline, a chunk that did not arrive) is not kept: the next use tries again (review M7)
  const lib = () => (client ??= factory(config).catch((error: unknown) => {
    client = null;
    throw error;
  }));

  const keep = (current: SessionLike | null) => {
    if (current?.access_token) markSignedIn(storage);
    else clearSignedIn(storage);
    return current?.access_token ? current : null;
  };

  const sent = async (answer: Promise<{ error: AuthErrorLike | null }>): Promise<SendResult> => {
    try {
      const { error } = await answer;
      return error ? { ok: false, error: sendError(error) } : { ok: true };
    } catch {
      return { ok: false, error: 'unavailable' };
    }
  };

  return {
    async session() {
      try {
        const { data } = await (await lib()).getSession();
        return keep(data.session);
      } catch {
        return null;
      }
    },
    async token() {
      return (await this.session())?.access_token ?? null;
    },
    async refresh() {
      try {
        const { data } = await (await lib()).refreshSession();
        return keep(data.session)?.access_token ?? null;
      } catch {
        return null;
      }
    },
    async sendLink(email, redirectTo) {
      return sent(lib().then((c) => c.signInWithOtp({ email, options: { emailRedirectTo: redirectTo, shouldCreateUser: true } })));
    },
    async google(redirectTo) {
      return sent(lib().then((c) => c.signInWithOAuth({ provider: 'google', options: { redirectTo } })));
    },
    async signOut() {
      clearSignedIn(storage); // first: this device is a guest at once, even if the library fails or hangs (review M6)
      clearSignInStarted(storage);
      try {
        await (await lib()).signOut({ scope: 'local' }); // auth-js 2.119 drops the local session before its request
      } catch {
        // nothing more to undo here
      }
    },
  };
}

/** How the session was made, for `signup_done`: the started mark, else what the library says. */
export function methodOf(current: SessionLike | null, started: SignInMethod | null): SignInMethod {
  if (started) return started;
  return current?.user?.app_metadata?.provider === 'google' ? 'google' : 'email';
}

let shared: Auth | null = null;

/** The page's one Auth for these settings (one library client per page). */
export function sharedAuth(config: AuthConfig): Auth {
  shared ??= createAuth(config);
  return shared;
}

/** The page's Auth, or null when sign-in is off or its settings cannot be read. */
export async function getAuth(): Promise<Auth | null> {
  const config = await authConfig();
  return config && config.enabled ? sharedAuth(config) : null;
}

export type SessionStatus =
  | { type: 'off' } // no SUPABASE_URL / SUPABASE_ANON_KEY: "sign-in opens soon"
  | { type: 'unreachable' } // the settings could not be read: "try again later"
  | { type: 'signedOut'; auth: Auth; google: boolean }
  | { type: 'signedIn'; auth: Auth; google: boolean; session: SessionLike };

/** What the diary and the account page start from (spec 4.4b §5, §6). */
export async function openSession(readConfig: () => Promise<AuthConfig | null> = authConfig,
  makeAuth: (config: AuthConfig) => Auth = sharedAuth): Promise<SessionStatus> {
  const config = await readConfig();
  if (config === null) return { type: 'unreachable' };
  if (!config.enabled) return { type: 'off' };
  const auth = makeAuth(config);
  const current = await auth.session();
  return current ? { type: 'signedIn', auth, google: config.google, session: current }
    : { type: 'signedOut', auth, google: config.google };
}

/** Tests only: the next call builds a new Auth. */
export function forgetAuth(): void {
  shared = null;
}
```

Create `site/src/lib/supabaseClient.ts`:

```ts
// The only file that imports @supabase/auth-js (the guards test checks it). auth.ts loads it with import(), so
// the library is a chunk of its own that a guest's reading page never downloads (tools/site/check_dist.py).
// Implicit flow: the token comes back in the address (#access_token=…), so the e-mail link can be opened on any
// device (owner decision 14.11.2026); detectSessionInUrl reads it and clears the hash.
import { AuthClient } from '@supabase/auth-js';
import type { AuthClientLike } from './auth';
import type { AuthConfig } from './authConfig';

export const AUTH_STORAGE_KEY = 'ad-auth';

export function createClient(config: AuthConfig): AuthClientLike {
  return new AuthClient({
    url: `${config.supabase_url}/auth/v1`,
    headers: { apikey: config.anon_key },
    storageKey: AUTH_STORAGE_KEY,
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    flowType: 'implicit',
  }) as unknown as AuthClientLike;
}
```

- [ ] **Step 4: Run the tests**

Run: the Vitest command of Step 2, then the same without files, then the type check (Global Constraints).
Expected: PASS — `26 passed` in 4 files; then `223 passed` in 22 files; `- 0 errors`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/authState.ts site/src/lib/authConfig.ts site/src/lib/auth.ts site/src/lib/supabaseClient.ts site/src/lib/testing/auth.ts site/src/lib/authState.test.ts site/src/lib/authConfig.test.ts site/src/lib/auth.test.ts site/src/lib/guards.test.ts
git commit -m "feat(site): stage 4.4b — sign-in state, settings and the lazy auth-js client

ad_signed_in and the started-sign-in mark; GET /api/auth-config once per page; an Auth
wrapper (session, refresh, e-mail link, Google, sign-out) over @supabase/auth-js, which
only supabaseClient.ts imports and auth.ts loads with import() (implicit flow).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Site — the token on every API request of a signed-in person, and the `401` rules

**Files:**
- Create: `site/src/lib/authFetch.ts`, `site/src/lib/siteApi.ts`
- Modify: `site/src/islands/ReadingIsland.tsx`, `site/src/islands/DailyIsland.tsx`, `site/src/components/ui/PlusCard.tsx` (they call `siteApi()` instead of `createApi(browserFetch())`)
- Test: `site/src/lib/authFetch.test.ts`

**Interfaces:**
- Consumes: `isSignedIn`, `StorageLike`, `browserStorage` (Task 9), `Auth`, `getAuth` (Task 9), `reasonOf` (`errors.ts`), `createApi`, `browserFetch`, `FetchFn`, `Api`, `ApiOptions` (`api.ts`).
- Produces:
  - `authFetch(base: FetchFn, source: AuthSource, storage?: StorageLike | null): FetchFn` with `type AuthSource = () => Promise<Pick<Auth, 'token' | 'refresh' | 'signOut'> | null>`. Not signed in (no `ad_signed_in`) or not `/api/*` → `base` as is, the library is never loaded. Signed in → `authorization: Bearer <token>`; `401 {"reason": "auth"}` → `refresh()` once and repeat; still `401 "auth"` or no new token → `signOut()` and repeat once without the header (a guest). `401 "sign_in"`, `401` without JSON (the stage cookie — the existing `'stage'` error shows «Reload»), `503 auth_unavailable` (the existing `'unavailable'` message) go back unchanged.
  - `siteFetch(): FetchFn` = `authFetch(browserFetch(), getAuth)`; `siteApi(options?: ApiOptions): Api` = `createApi(siteFetch(), options)`.

- [ ] **Step 1: Write the failing test**

Create `site/src/lib/authFetch.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { createApi } from './api';
import { authFetch, type AuthSource } from './authFetch';
import { SIGNED_IN_KEY } from './authState';
import { memoryStorage } from './testing/auth';
import { fakeFetch, jsonResponse } from './testing/fakes';

function source(tokens: { token: string | null; refresh?: string | null }) {
  const log: string[] = [];
  let loads = 0;
  const auth = {
    token: async () => { log.push('token'); return tokens.token; },
    refresh: async () => { log.push('refresh'); return tokens.refresh ?? null; },
    signOut: async () => { log.push('signOut'); },
  };
  const get: AuthSource = async () => { loads += 1; return auth; };
  return { get, log, loads: () => loads };
}

const SIGNED = () => memoryStorage({ [SIGNED_IN_KEY]: '1' });

describe('authFetch', () => {
  it('a guest request goes as it is and never loads the sign-in library', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, { limit: 2 }));
    const auth = source({ token: 'tok-1' });
    await authFetch(fetch, auth.get, memoryStorage())('/api/limits');
    expect(calls[0].headers.authorization).toBeUndefined();
    expect(auth.loads()).toBe(0);
  });

  it('a signed-in request carries the token and keeps the other headers', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(201, { id: 'r1' }));
    const api = createApi(authFetch(fetch, source({ token: 'tok-1' }).get, SIGNED()));
    await api.createReading({ lang: 'en', kind: 'one' });
    expect(calls[0].headers).toEqual({ 'content-type': 'application/json', authorization: 'Bearer tok-1' });
  });

  it('only /api/* gets the token', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, []));
    await authFetch(fetch, source({ token: 'tok-1' }).get, SIGNED())('/data/daily-en.json');
    expect(calls[0].headers.authorization).toBeUndefined();
  });

  it('401 "auth": one refresh and the same request again with the new token', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(401, { reason: 'auth' }), jsonResponse(200, { items: [] }));
    const auth = source({ token: 'tok-1', refresh: 'tok-2' });
    const response = await authFetch(fetch, auth.get, SIGNED())('/api/diary', { method: 'GET' });
    expect(response.status).toBe(200);
    expect(calls.map((c) => c.headers.authorization)).toEqual(['Bearer tok-1', 'Bearer tok-2']);
    expect(auth.log).toEqual(['token', 'refresh']);
  });

  it('401 "auth" again after the refresh: sign out here and repeat once as a guest', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(401, { reason: 'auth' }), jsonResponse(401, { reason: 'auth' }),
      jsonResponse(201, { id: 'r1' }));
    const auth = source({ token: 'tok-1', refresh: 'tok-2' });
    const body = JSON.stringify({ lang: 'en', kind: 'one' });
    const response = await authFetch(fetch, auth.get, SIGNED())('/api/readings', { method: 'POST', body });
    expect(response.status).toBe(201);
    expect(calls.map((c) => c.headers.authorization)).toEqual(['Bearer tok-1', 'Bearer tok-2', undefined]);
    expect(calls[2].body).toEqual({ lang: 'en', kind: 'one' }); // the same body
    expect(auth.log).toEqual(['token', 'refresh', 'signOut']);
  });

  it('a failed refresh signs out at once', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(401, { reason: 'auth' }), jsonResponse(200, { limit: 2 }));
    const auth = source({ token: 'tok-1', refresh: null });
    await authFetch(fetch, auth.get, SIGNED())('/api/limits');
    expect(calls).toHaveLength(2);
    expect(auth.log).toEqual(['token', 'refresh', 'signOut']);
  });

  it('401 "sign_in", 401 without JSON and 503 come back unchanged, with no refresh', async () => {
    for (const answer of [jsonResponse(401, { reason: 'sign_in' }), new Response('Unauthorized', { status: 401 }),
      jsonResponse(503, { reason: 'auth_unavailable' })]) {
      const { fetch, calls } = fakeFetch(answer);
      const auth = source({ token: 'tok-1', refresh: 'tok-2' });
      const response = await authFetch(fetch, auth.get, SIGNED())('/api/account');
      expect(response).toBe(answer);
      expect(calls).toHaveLength(1);
      expect(auth.log).toEqual(['token']);
    }
  });

  it('the caller still reads the body of a refusal it gets back', async () => {
    const { fetch } = fakeFetch(jsonResponse(401, { reason: 'sign_in' }));
    const api = createApi(authFetch(fetch, source({ token: 'tok-1' }).get, SIGNED()));
    expect(await api.getReading('r1', undefined)).toMatchObject({ ok: false, status: 401, body: { reason: 'sign_in' } });
  });

  it('a flag without a session (signed out in another tab) is a guest request', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, { limit: 2 }));
    await authFetch(fetch, source({ token: null }).get, SIGNED())('/api/limits');
    expect(calls[0].headers.authorization).toBeUndefined();
  });

  it('sign-in off (no Auth) is a guest request', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, { limit: 2 }));
    await authFetch(fetch, async () => null, SIGNED())('/api/limits');
    expect(calls[0].headers.authorization).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/authFetch.test.ts`
Expected: FAIL — `Failed to resolve import "./authFetch"`.

- [ ] **Step 3: Implement**

Create `site/src/lib/authFetch.ts`:

```ts
// Every /api/* request of a signed-in person carries Authorization: Bearer (spec 4.4b §3, api/README.md
// "Передача в 4.4"): 401 {"reason": "auth"} — refresh the token once and repeat; still 401 — sign out on this
// device and repeat as a guest. Other answers (401 "sign_in", 401 without JSON on the stage, 503) go back to the
// caller unchanged. A guest (no `ad_signed_in`) never loads the sign-in library: the request goes as it is.
import type { FetchFn } from './api';
import { reasonOf } from './errors';
import type { Auth } from './auth';
import { isSignedIn, type StorageLike, browserStorage } from './authState';

export type AuthSource = () => Promise<Pick<Auth, 'token' | 'refresh' | 'signOut'> | null>;

function withBearer(init: RequestInit | undefined, token: string): RequestInit {
  return { ...init, headers: { ...((init?.headers ?? {}) as Record<string, string>), authorization: `Bearer ${token}` } };
}

async function isAuthRefusal(response: Response): Promise<boolean> {
  if (response.status !== 401) return false;
  try {
    return reasonOf(await response.clone().json()) === 'auth';
  } catch {
    return false; // 401 without JSON: the stage cookie, not the token
  }
}

export function authFetch(base: FetchFn, source: AuthSource, storage: StorageLike | null = browserStorage()): FetchFn {
  return async (input, init) => {
    if (!input.startsWith('/api/') || !isSignedIn(storage)) return base(input, init);
    const auth = await source();
    const token = auth ? await auth.token() : null;
    if (!auth || !token) return base(input, init); // the session went: a guest request
    const first = await base(input, withBearer(init, token));
    if (!(await isAuthRefusal(first))) return first;
    const fresh = await auth.refresh();
    if (fresh) {
      const again = await base(input, withBearer(init, fresh));
      if (!(await isAuthRefusal(again))) return again;
    }
    await auth.signOut();
    return base(input, init);
  };
}
```

Create `site/src/lib/siteApi.ts`:

```ts
// The site's API client for islands: the browser's fetch, with the token of a signed-in person on /api/* (spec 4.4b
// §3). For a guest nothing changes and the sign-in library is never loaded.
import { browserFetch, createApi, type Api, type ApiOptions, type FetchFn } from './api';
import { getAuth } from './auth';
import { authFetch } from './authFetch';

export function siteFetch(): FetchFn {
  return authFetch(browserFetch(), getAuth);
}

export function siteApi(options?: ApiOptions): Api {
  return createApi(siteFetch(), options);
}
```

In `site/src/islands/ReadingIsland.tsx` replace `import { browserFetch, createApi } from '../lib/api';` with `import { siteApi } from '../lib/siteApi';` and `const api = useMemo(() => createApi(browserFetch()), []);` with `const api = useMemo(() => siteApi(), []);`.

In `site/src/islands/DailyIsland.tsx` replace `import { browserFetch, createApi } from '../lib/api';` with `import { siteApi } from '../lib/siteApi';` and `dailyNext(await createApi(browserFetch()).getDaily(lang, tz), lang)` with `dailyNext(await siteApi().getDaily(lang, tz), lang)`.

In `site/src/components/ui/PlusCard.tsx` replace `import { browserFetch, createApi } from '../../lib/api';` with `import { siteApi } from '../../lib/siteApi';` and `await createApi(browserFetch()).joinWaitlist(email.trim(), lang)` with `await siteApi().joinWaitlist(email.trim(), lang)`.

- [ ] **Step 4: Run the tests and the build**

Run: the Vitest command of Step 2, then the same without a file, then the type check, then `deploy/build-site.sh && python3 tools/site/check_dist.py`
Expected: `10 passed`; then `233 passed` in 23 files; `- 0 errors`; then `OK: 167 pages`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/authFetch.ts site/src/lib/siteApi.ts site/src/lib/authFetch.test.ts site/src/islands/ReadingIsland.tsx site/src/islands/DailyIsland.tsx site/src/components/ui/PlusCard.tsx
git commit -m "feat(site): stage 4.4b — Bearer token on /api/* for a signed-in person, 401 rules

401 auth: one refresh and a repeat, then sign out here and repeat as a guest; 401
sign_in, 401 without JSON and 503 go back to the screen. A guest never loads auth-js.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Site — the account API client

**Files:**
- Create: `site/src/lib/accountApi.ts`
- Modify: `site/src/lib/api.ts` (export `readingPath`, `jsonBody`; `call` becomes the exported `callJson`)
- Test: `site/src/lib/accountApi.test.ts`

**Interfaces:**
- Consumes: `FetchFn`, `ApiResult<T>`, `withQuery` (`api.ts`), `classifyError`, `ErrorKind` (`errors.ts`), `DrawnCard`, `Kind`, `Lang`, `ReadingView` (`types.ts`).
- Produces:
  - `api.ts`: `readingPath(id: string, tail?: string): string`, `jsonBody(response): Promise<Record<string, unknown> | null>`, `callJson<T>(fetchFn, path, init?, timeoutMs?): Promise<ApiResult<T>>` (the same behaviour as the old inner `call`).
  - `accountApi.ts`: `type Outcome = 'yes' | 'partly' | 'no'`; `interface DiaryItem` (the API's diary item), `interface DiaryPage { items; next_before: string | null; hidden_count: number }`, `interface DiaryEntry extends ReadingView { created_at; question; topic; in_diary; outcome; note }`, `interface EntryPatch { outcome?: Outcome | null; note?: string | null }`, `interface Account { email; created_at; reminders_consent; consent_at; limit; used; remaining; day }`, `type ExportResult = { ok: true; blob: Blob; filename: string } | { ok: false; status: number; error: ErrorKind }`, `interface AccountApi { claimToken(readingId); claim(tokens, device); diary(before?, limit?); entry(id, tz); patchEntry(id, patch); deleteEntry(id); account(tz); setConsent(on); exportFile(); deleteAccount() }`, `exportName(disposition, today): string`, `createAccountApi(fetchFn: FetchFn): AccountApi`.

- [ ] **Step 1: Write the failing test**

Create `site/src/lib/accountApi.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { createAccountApi, exportName } from './accountApi';
import { fakeFetch, jsonResponse } from './testing/fakes';

describe('account API', () => {
  it('asks for a claim token of the reading and claims with the tokens, with or without this device', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(201, { token: 't1', expires_at: 'x' }), jsonResponse(200, { claimed: ['r1'] }),
      jsonResponse(200, { claimed: [] }));
    const api = createAccountApi(fetch);
    expect(await api.claimToken('r 1')).toMatchObject({ ok: true, data: { token: 't1' } });
    expect(await api.claim(['t1'], false)).toMatchObject({ ok: true, data: { claimed: ['r1'] } });
    await api.claim([], true);
    expect(calls.map((c) => [c.method, c.url, c.body])).toEqual([
      ['POST', '/api/readings/r%201/claim-token', undefined], ['POST', '/api/account/claim', { tokens: ['t1'], device: false }],
      ['POST', '/api/account/claim', { tokens: [], device: true }],
    ]);
  });

  it('pages the diary with an encoded next_before', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, { items: [], next_before: null, hidden_count: 0 }));
    await createAccountApi(fetch).diary('2026-11-20T18:00:00+00:00', 10);
    expect(calls[0].url).toBe('/api/diary?before=2026-11-20T18%3A00%3A00%2B00%3A00&limit=10');
  });

  it('patches and deletes an entry, reads the account, sets consent and deletes the account', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, {}), new Response(null, { status: 204 }), jsonResponse(200, {}),
      jsonResponse(200, {}), jsonResponse(200, { deleted: true }));
    const api = createAccountApi(fetch);
    await api.patchEntry('r1', { outcome: null });
    expect(await api.deleteEntry('r1')).toEqual({ ok: true, status: 204, data: null });
    await api.account('America/Mexico_City');
    await api.setConsent(true);
    expect(await api.deleteAccount()).toMatchObject({ ok: true, data: { deleted: true } });
    expect(calls.map((c) => [c.method, c.url, c.body])).toEqual([
      ['PATCH', '/api/diary/r1', { outcome: null }], ['DELETE', '/api/diary/r1', undefined],
      ['GET', '/api/account?tz=America%2FMexico_City', undefined], ['PATCH', '/api/account', { reminders_consent: true }],
      ['DELETE', '/api/account', { confirm: 'DELETE' }],
    ]);
  });

  it('downloads the export as a file with its own name', async () => {
    const file = new Response('{"readings":[]}', { status: 200, headers: {
      'content-type': 'application/json', 'content-disposition': 'attachment; filename="arcana-diary-2026-11-22.json"' } });
    const { fetch } = fakeFetch(file, jsonResponse(401, { reason: 'sign_in' }), new TypeError('offline'));
    const api = createAccountApi(fetch);
    const ok = await api.exportFile();
    expect(ok.ok && ok.filename).toBe('arcana-diary-2026-11-22.json');
    expect(ok.ok && (await ok.blob.text())).toBe('{"readings":[]}');
    expect(await api.exportFile()).toEqual({ ok: false, status: 401, error: 'other' });
    expect(await api.exportFile()).toEqual({ ok: false, status: 0, error: 'network' });
  });

  it('never takes a strange file name from the header', () => {
    expect(exportName('attachment; filename="../../x.sh"', '2026-11-22')).toBe('arcana-diary-2026-11-22.json');
    expect(exportName(null, '2026-11-22')).toBe('arcana-diary-2026-11-22.json');
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/accountApi.test.ts`
Expected: FAIL — `Failed to resolve import "./accountApi"`.

- [ ] **Step 3: Implement**

In `site/src/lib/api.ts` replace

```ts
function readingPath(id: string, tail = ''): string {
  return `/api/readings/${encodeURIComponent(id)}${tail}`;
}

async function jsonBody(response: Response): Promise<Record<string, unknown> | null> {
```

with

```ts
export function readingPath(id: string, tail = ''): string {
  return `/api/readings/${encodeURIComponent(id)}${tail}`;
}

export async function jsonBody(response: Response): Promise<Record<string, unknown> | null> {
```

and replace

```ts
export function createApi(fetchFn: FetchFn, options: ApiOptions = {}): Api {
  const idleMs = options.idleMs ?? STREAM_IDLE_MS;
  const createTimeoutMs = options.createTimeoutMs ?? CREATE_TIMEOUT_MS;

  async function call<T>(path: string, init?: RequestInit, timeoutMs?: number): Promise<ApiResult<T>> {
    let response: Response;
    const controller = timeoutMs ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : undefined;
    try {
      response = await fetchFn(path, controller ? { ...init, signal: controller.signal } : init);
    } catch {
      return { ok: false, status: 0, error: 'network', body: null };
    } finally {
      clearTimeout(timer);
    }
    const body = await jsonBody(response);
    if (response.ok) return { ok: true, status: response.status, data: body as T };
    return { ok: false, status: response.status, error: classifyError(response.status, body), body };
  }
```

with

```ts
/** One JSON request: the answer, its status and, for a refusal, what it means for the screen. */
export async function callJson<T>(fetchFn: FetchFn, path: string, init?: RequestInit, timeoutMs?: number): Promise<ApiResult<T>> {
  let response: Response;
  const controller = timeoutMs ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : undefined;
  try {
    response = await fetchFn(path, controller ? { ...init, signal: controller.signal } : init);
  } catch {
    return { ok: false, status: 0, error: 'network', body: null };
  } finally {
    clearTimeout(timer);
  }
  const body = await jsonBody(response);
  if (response.ok) return { ok: true, status: response.status, data: body as T };
  return { ok: false, status: response.status, error: classifyError(response.status, body), body };
}

export function createApi(fetchFn: FetchFn, options: ApiOptions = {}): Api {
  const idleMs = options.idleMs ?? STREAM_IDLE_MS;
  const createTimeoutMs = options.createTimeoutMs ?? CREATE_TIMEOUT_MS;
  const call = <T>(path: string, init?: RequestInit, timeoutMs?: number) => callJson<T>(fetchFn, path, init, timeoutMs);
```

Create `site/src/lib/accountApi.ts`:

```ts
// The account's requests (spec 2026-11-19 stage 4.3 §4, §6, §8; spec 4.4b §4–§6): claim tokens and the claim, the
// diary list, one entry, its outcome and note, delete; the account, consent, export, delete. Everything that comes
// back is shown as text only.
import { callJson, jsonBody, readingPath, withQuery, type ApiResult, type FetchFn } from './api';
import { classifyError, type ErrorKind } from './errors';
import type { DrawnCard, Kind, Lang, ReadingView } from './types';

export type Outcome = 'yes' | 'partly' | 'no';

export interface DiaryItem {
  id: string;
  created_at: string;
  lang: Lang;
  kind: Kind;
  topic: string | null;
  question: string | null;
  headline: string | null;
  answer_shown: 'model' | 'fallback' | 'crisis' | null;
  cards: DrawnCard[];
  outcome: Outcome | null;
  has_note: boolean;
  followups: number;
}

export interface DiaryPage {
  items: DiaryItem[];
  next_before: string | null;
  hidden_count: number; // spec 4.4b §5: older readings beyond the free 10
}

/** GET /api/readings/{id} for the account that owns it. */
export interface DiaryEntry extends ReadingView {
  created_at: string;
  question: string | null;
  topic: string | null;
  in_diary: boolean;
  outcome: Outcome | null;
  note: string | null;
}

export interface EntryPatch {
  outcome?: Outcome | null;
  note?: string | null;
}

export interface Account {
  email: string | null;
  created_at: string;
  reminders_consent: boolean;
  consent_at: string | null;
  limit: number;
  used: number;
  remaining: number;
  day: string;
}

export type ExportResult = { ok: true; blob: Blob; filename: string } | { ok: false; status: number; error: ErrorKind };

export interface AccountApi {
  claimToken(readingId: string): Promise<ApiResult<{ token: string; expires_at: string }>>;
  /** `device`: also move this device's guest readings (spec 4.4b §4, owner decision 12; API Task 6). */
  claim(tokens: string[], device: boolean): Promise<ApiResult<{ claimed: string[] }>>;
  diary(before?: string, limit?: number): Promise<ApiResult<DiaryPage>>;
  entry(id: string, tz: string | undefined): Promise<ApiResult<DiaryEntry>>;
  patchEntry(id: string, patch: EntryPatch): Promise<ApiResult<{ id: string; outcome: Outcome | null; note: string | null }>>;
  deleteEntry(id: string): Promise<ApiResult<null>>;
  account(tz: string | undefined): Promise<ApiResult<Account>>;
  setConsent(on: boolean): Promise<ApiResult<Pick<Account, 'email' | 'reminders_consent' | 'consent_at'>>>;
  exportFile(): Promise<ExportResult>;
  deleteAccount(): Promise<ApiResult<{ deleted: boolean }>>;
}

const JSON_HEADERS = { 'content-type': 'application/json' };
const json = (method: string, body: unknown): RequestInit => ({ method, headers: JSON_HEADERS, body: JSON.stringify(body) });

/** The file name of Content-Disposition, else today's export name. */
export function exportName(disposition: string | null, today: string): string {
  const name = /filename="([^"]+)"/.exec(disposition ?? '')?.[1];
  return name && /^[\w.-]+$/.test(name) ? name : `arcana-diary-${today}.json`;
}

export function createAccountApi(fetchFn: FetchFn): AccountApi {
  const call = <T>(path: string, init?: RequestInit) => callJson<T>(fetchFn, path, init);
  return {
    claimToken: (readingId) => call(readingPath(readingId, '/claim-token'), { method: 'POST' }),
    claim: (tokens, device) => call('/api/account/claim', json('POST', { tokens, device })),
    diary: (before, limit) => call(withQuery('/api/diary', { before, limit: limit ? String(limit) : undefined })),
    entry: (id, tz) => call(withQuery(readingPath(id), { tz })),
    patchEntry: (id, patch) => call(`/api/diary/${encodeURIComponent(id)}`, json('PATCH', patch)),
    deleteEntry: (id) => call(`/api/diary/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    account: (tz) => call(withQuery('/api/account', { tz })),
    setConsent: (on) => call('/api/account', json('PATCH', { reminders_consent: on })),
    async exportFile() {
      let response: Response;
      try {
        response = await fetchFn('/api/account/export', { method: 'GET' });
      } catch {
        return { ok: false, status: 0, error: 'network' };
      }
      if (!response.ok) return { ok: false, status: response.status, error: classifyError(response.status, await jsonBody(response)) };
      const today = new Date().toISOString().slice(0, 10);
      return { ok: true, blob: await response.blob(), filename: exportName(response.headers.get('content-disposition'), today) };
    },
    deleteAccount: () => call('/api/account', json('DELETE', { confirm: 'DELETE' })),
  };
}
```

- [ ] **Step 4: Run the tests**

Run: the Vitest command of Step 2 with `src/lib/api.test.ts` added, then the same without files, then the type check.
Expected: PASS — `23 passed` in 2 files (`api.test.ts` unchanged at 18); then `238 passed` in 24 files; `- 0 errors`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/api.ts site/src/lib/accountApi.ts site/src/lib/accountApi.test.ts
git commit -m "feat(site): stage 4.4b — account API client (claim, diary, entry, account, export)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Site — the diary addresses, the 4.4b events, and finishing a sign-in (claim once)

**Files:**
- Create: `site/src/lib/claim.ts`
- Modify: `site/src/lib/routes.ts` (`PageKey`, `PAGE_PATHS`, `PRIVATE_PAIRS`, `switchPath`), `site/src/lib/analytics.ts` (`EventName`, `NO_TOOL`, `analyticsEvent` takes `Tool | null`)
- Test: `site/src/lib/claim.test.ts` (new), `site/src/lib/routes.test.ts`, `site/src/lib/analytics.test.ts`

**Interfaces:**
- Consumes: `AccountApi` (`claim`, `setConsent`, Task 11), `signInStarted`, `clearSignInStarted`, `SignInMethod`, `StorageLike` (Task 9), `memoryStorage` (Task 9 fakes).
- Produces:
  - `routes.ts`: `PageKey` gains `'diary' | 'account'`; `pagePath('diary', 'en') === '/diary'`, `'/es/diario'`, `pagePath('account', …)` `'/account'`, `'/es/cuenta'`; `PRIVATE_PAIRS` (the four, both ways) used by `switchPath`; `allPagePaths()` includes the four. (The menu item comes in Task 18, the pages in Tasks 14 and 16.)
  - `analytics.ts`: `EventName` adds `'save_click' | 'signup_done' | 'outcome_answered' | 'remind_click'`; `NO_TOOL = {plus_view, signup_done, outcome_answered}`; `analyticsEvent(name, tool: Tool | null, lang, params?)`.
  - `claim.ts`: `interface ReturnParams { claim: string | null; remind: boolean }`, `returnUrl(origin, lang, params?): string` (`<origin>/diary?claim=…&remind=1`), `readReturnParams(search): ReturnParams` (a token longer than 100 is ignored), `cleanReturnUrl(href): string` (drops `claim`, `remind` and the hash), `interface FinishDeps { api; storage; href; lang; method(started); replaceUrl(url); send(event); now? }`, `type FinishResult = {type:'none'} | {type:'claimed'; claimed: string[]} | {type:'error'; error: ErrorKind}`, `finishSignIn(deps): Promise<FinishResult>` (one run at a time per page; `api.claim(tokens, device)` with `device = true` only when the "sign-in started here" mark is set — owner decision 12; consent and `signup_done` only with the mark or when `claimed` is not empty — review I1; the address is cleaned in both cases), `linkFailed(hash): boolean`.

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/claim.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import type { AnalyticsEvent } from './analytics';
import { STARTED_KEY, markSignInStarted } from './authState';
import { cleanReturnUrl, finishSignIn, linkFailed, readReturnParams, returnUrl, type FinishDeps } from './claim';
import { memoryStorage } from './testing/auth';

describe('the return address', () => {
  it('is the diary of the page language, with the claim token and the reminder', () => {
    expect(returnUrl('https://arcana.test', 'en')).toBe('https://arcana.test/diary');
    expect(returnUrl('https://arcana.test', 'es', { claim: 'a-b_c', remind: true })).toBe('https://arcana.test/es/diario?claim=a-b_c&remind=1');
    expect(returnUrl('https://arcana.test', 'en', { claim: null, remind: true })).toBe('https://arcana.test/diary?remind=1');
  });

  it('is read back, and cleaned of claim and remind only', () => {
    expect(readReturnParams('?claim=tok&remind=1&r=x')).toEqual({ claim: 'tok', remind: true });
    expect(readReturnParams('?claim=' + 'x'.repeat(101))).toEqual({ claim: null, remind: false });
    expect(cleanReturnUrl('https://arcana.test/diary?claim=tok&remind=1&r=abc')).toBe('/diary?r=abc');
    expect(cleanReturnUrl('https://arcana.test/es/diario?claim=tok')).toBe('/es/diario');
    expect(cleanReturnUrl('https://arcana.test/diary?claim=tok#access_token=secret&type=magiclink')).toBe('/diary');
  });
});

function deps(href: string, overrides: Partial<FinishDeps> = {}) {
  const calls: string[] = [];
  const events: AnalyticsEvent[] = [];
  const urls: string[] = [];
  const storage = memoryStorage();
  const d: FinishDeps = {
    api: {
      claim: async (tokens, device) => {
        calls.push(`claim ${JSON.stringify(tokens)} ${device ? 'device' : 'tokens only'}`);
        return { ok: true, status: 200, data: { claimed: tokens.length || device ? ['r1'] : [] } };
      },
      setConsent: async (on) => { calls.push(`consent ${on}`); return { ok: true, status: 200, data: { email: null, reminders_consent: on, consent_at: null } }; },
    },
    storage, href, lang: 'en', now: 1000,
    method: (started) => started ?? 'email',
    replaceUrl: (url) => urls.push(url),
    send: (event) => events.push(event),
    ...overrides,
  };
  return { d, calls, events, urls, storage };
}

describe('finishSignIn', () => {
  it('with only a token in the address (the link opened on another device): claims that reading only, gives consent, counts signup_done and cleans the address', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?claim=tok&remind=1');
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: ['r1'] });
    expect(calls).toEqual(['claim ["tok"] tokens only', 'consent true']); // owner decision 12: not this browser's readings
    expect(events).toEqual([{ name: 'signup_done', tool: null, lang: 'en', params: { method: 'email' } }]);
    expect(urls).toEqual(['/diary']);
  });

  it('with the token and the mark (the link opened on the device that sent it): the token and this device', async () => {
    const { d, calls, storage } = deps('https://arcana.test/diary?claim=tok&remind=1');
    markSignInStarted('email', 900, storage);
    await finishSignIn(d);
    expect(calls).toEqual(['claim ["tok"] device', 'consent true']);
  });

  it('after a sign-in started here: claims this device with no token, with its method', async () => {
    const { d, calls, events, storage } = deps('https://arcana.test/diary');
    markSignInStarted('google', 900, storage);
    expect(await finishSignIn(d)).toMatchObject({ type: 'claimed' });
    expect(calls).toEqual(['claim [] device']);
    expect(events[0].params).toEqual({ method: 'google' });
    expect(storage.data[STARTED_KEY]).toBeUndefined(); // once: the next visit claims nothing
    expect(await finishSignIn(d)).toEqual({ type: 'none' });
    expect(calls).toHaveLength(1);
  });

  it('a token that moves nothing, without the mark (made up, or the same link again after Back): no consent, no signup_done, a clean address (review I1)', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?claim=used&remind=1', {
      api: {
        claim: async (tokens, device) => {
          calls.push(`claim ${JSON.stringify(tokens)} ${device ? 'device' : 'tokens only'}`);
          return { ok: true, status: 200, data: { claimed: [] } };
        },
        setConsent: async () => { throw new Error('must not be called'); },
      },
    });
    expect(await finishSignIn(d)).toEqual({ type: 'claimed', claimed: [] });
    expect(calls).toEqual(['claim ["used"] tokens only']);
    expect(events).toEqual([]);
    expect(urls).toEqual(['/diary']);
  });

  it('an ordinary visit claims nothing (a shared computer keeps its guest readings)', async () => {
    const { d, calls, events, urls } = deps('https://arcana.test/diary?r=abc');
    expect(await finishSignIn(d)).toEqual({ type: 'none' });
    expect(calls).toEqual([]);
    expect(events).toEqual([]);
    expect(urls).toEqual([]);
  });

  it('a failed claim changes nothing, so a reload tries again', async () => {
    const { d, calls, urls, storage } = deps('https://arcana.test/diary?claim=tok', {
      api: { claim: async () => ({ ok: false, status: 503, error: 'unavailable', body: null }), setConsent: async () => { throw new Error('no'); } },
    });
    markSignInStarted('email', 900, storage);
    expect(await finishSignIn(d)).toEqual({ type: 'error', error: 'unavailable' });
    expect(urls).toEqual([]);
    expect(storage.data[STARTED_KEY]).toBeDefined();
    expect(calls).toEqual([]);
  });

  it('runs once when two parts of the page ask at the same time', async () => {
    const { d, calls } = deps('https://arcana.test/diary?claim=tok');
    await Promise.all([finishSignIn(d), finishSignIn(d)]);
    expect(calls).toEqual(['claim ["tok"] tokens only']);
  });
});

describe('linkFailed', () => {
  it('sees the error Supabase puts in the address of an expired link', () => {
    expect(linkFailed('#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid')).toBe(true);
    expect(linkFailed('#access_token=x&type=magiclink')).toBe(false);
    expect(linkFailed('')).toBe(false);
  });
});
```

In `site/src/lib/routes.test.ts`:

- replace `import { NAV_KEYS, allPagePaths, cardPath, distFile, langOf, pagePath, switchPath } from './routes';` with `import { NAV_KEYS, PRIVATE_PAIRS, allPagePaths, cardPath, distFile, langOf, pagePath, switchPath } from './routes';`
- replace

```ts
    expect(paths).toHaveLength(6 + 78 + 5 + 78);
    for (const p of ['/', '/one-card', '/yes-no', '/love', '/daily', '/404', '/es', '/es/si-o-no', '/es/amor',
      '/es/carta-del-dia', '/es/404', '/cards/the-moon', '/es/cartas/la-luna']) {
```

with

```ts
    expect(paths).toHaveLength(8 + 78 + 7 + 78);
    for (const p of ['/', '/one-card', '/yes-no', '/love', '/daily', '/diary', '/account', '/404', '/es', '/es/si-o-no',
      '/es/amor', '/es/carta-del-dia', '/es/diario', '/es/cuenta', '/es/404', '/cards/the-moon', '/es/cartas/la-luna']) {
```

- replace

```ts
    expect(switchPath('/es/404')).toBe('/404');
  });
```

with

```ts
    expect(switchPath('/es/404')).toBe('/404');
    expect([switchPath('/diary'), switchPath('/es/diario'), switchPath('/account'), switchPath('/es/cuenta')])
      .toEqual(['/es/diario', '/diary', '/es/cuenta', '/account']);
  });
```

- replace `      if (!p.endsWith('/404')) expect(Object.keys(pairs)).toContain(p);` with `      if (!p.endsWith('/404') && !(p in PRIVATE_PAIRS)) expect(Object.keys(pairs)).toContain(p);`
- after the test `'has the four menu items of 4.4a in both languages'` add:

```ts
  it('keeps the diary and the account out of hreflang.csv (noindex pages)', () => {
    for (const p of Object.keys(PRIVATE_PAIRS)) expect(Object.keys(pairs)).not.toContain(p);
  });
```

In `site/src/lib/analytics.test.ts`, after the test `'sends plus_view without a tool'` add:

```ts
  it('knows the events of stage 4.4b (spec §8): signup_done and outcome_answered without a tool', () => {
    expect(analyticsEvent('save_click', 'love', 'es')).toEqual({ name: 'save_click', tool: 'love', lang: 'es', params: {} });
    expect(analyticsEvent('remind_click', 'daily', 'en')).toEqual({ name: 'remind_click', tool: 'daily', lang: 'en', params: {} });
    expect(analyticsEvent('signup_done', null, 'en', { method: 'google' })).toEqual({
      name: 'signup_done', tool: null, lang: 'en', params: { method: 'google' },
    });
    expect(analyticsEvent('outcome_answered', 'home', 'es', { after_days: 7, answer: 'partly' }).tool).toBeNull();
    expect(analyticsEvent('plus_view', null, 'en', { place: 'diary' }).params).toEqual({ place: 'diary' });
  });
```

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/claim.test.ts src/lib/routes.test.ts src/lib/analytics.test.ts`
Expected: FAIL — `Failed to resolve import "./claim"`; routes: `expected 167 to have a length of 171`, `PRIVATE_PAIRS` undefined; analytics: `tool: 'home'` instead of `null` for `outcome_answered`.

- [ ] **Step 3: Implement**

In `site/src/lib/routes.ts`:

- replace `export type PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'not_found';` with `export type PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'diary' | 'account' | 'not_found';`
- after the line `const NOT_FOUND_PAIRS: Readonly<Record<string, string>> = { '/404': '/es/404', '/es/404': '/404' };` add:

```ts
/** Spec 4.4b §5, §6: the diary and the account are noindex, outside hreflang.csv; the switch still pairs them. */
export const PRIVATE_PAIRS: Readonly<Record<string, string>> = {
  '/diary': '/es/diario', '/es/diario': '/diary', '/account': '/es/cuenta', '/es/cuenta': '/account',
};
```

- replace `  en: { home: '/', one_card: '/one-card', yes_no: '/yes-no', love: '/love', daily: '/daily', not_found: '/404' },` with

```ts
  en: {
    home: '/', one_card: '/one-card', yes_no: '/yes-no', love: '/love', daily: '/daily', diary: '/diary',
    account: '/account', not_found: '/404',
  },
```

- replace

```ts
    home: '/es', one_card: '/es#una-carta', yes_no: '/es/si-o-no', love: '/es/amor', daily: '/es/carta-del-dia',
    not_found: '/es/404',
```

with

```ts
    home: '/es', one_card: '/es#una-carta', yes_no: '/es/si-o-no', love: '/es/amor', daily: '/es/carta-del-dia',
    diary: '/es/diario', account: '/es/cuenta', not_found: '/es/404',
```

- replace `  const pair = PAIRS[path] ?? NOT_FOUND_PAIRS[path];` with `  const pair = PAIRS[path] ?? NOT_FOUND_PAIRS[path] ?? PRIVATE_PAIRS[path];`
- replace `/** Every page the build must produce, both languages: tools, 78 card pages each, 404. */` with `/** Every page the build must produce, both languages: tools, the diary and the account, 78 card pages each, 404. */`

In `site/src/lib/analytics.ts`:

- replace

```ts
export type EventName = 'tool_view' | 'draw_click' | 'night_open' | 'cards_revealed' | 'reading_shown'
  | 'more_about_cards' | 'plus_view';
```

with

```ts
export type EventName = 'tool_view' | 'draw_click' | 'night_open' | 'cards_revealed' | 'reading_shown'
  | 'more_about_cards' | 'plus_view' | 'save_click' | 'signup_done' | 'outcome_answered' | 'remind_click';

/** The events of docs/design/analytics-events.md that carry no tool. */
export const NO_TOOL: ReadonlySet<EventName> = new Set<EventName>(['plus_view', 'signup_done', 'outcome_answered']);
```

- replace

```ts
/** plus_view carries no tool (its only parameter is `place`); every other 4.4a event names its tool. */
export function analyticsEvent(name: EventName, tool: Tool, lang: Lang, params: Params = {}): AnalyticsEvent {
```

with

```ts
/** plus_view, signup_done and outcome_answered carry no tool; every other event names its tool. */
export function analyticsEvent(name: EventName, tool: Tool | null, lang: Lang, params: Params = {}): AnalyticsEvent {
```

- replace `  return { name, tool: name === 'plus_view' ? null : tool, lang, params: clean };` with `  return { name, tool: NO_TOOL.has(name) ? null : tool, lang, params: clean };`

Create `site/src/lib/claim.ts`:

```ts
// Saving a guest reading through sign-in (spec 4.4b §4; spec 4.3 §4): the e-mail link and Google come back to the
// diary of the page's language, `?claim=<token>` (one-time token of the reading, so it can be saved from any
// device) and `&remind=1` when "Remind me in 7 days" was ticked. After sign-in the diary calls
// POST /api/account/claim once — only after a sign-in started on this device or with a token in the address
// (api/README.md: on a shared computer a claim without tokens takes every guest reading of the device) — then
// removes `claim` and `remind` from the address bar. This device's guest readings move ("device": true) only after
// a sign-in started here: a link opened on another device moves the reading of its token only (owner decision 12).
// The consent and signup_done need that mark or a reading actually moved: the same address opened again (Back after
// the library cleared #access_token, or a made-up token) switches nothing on (Fable plan review I1).
import type { AccountApi } from './accountApi';
import { analyticsEvent, type AnalyticsEvent } from './analytics';
import { clearSignInStarted, signInStarted, type SignInMethod, type StorageLike } from './authState';
import type { ErrorKind } from './errors';
import { pagePath } from './routes';
import type { Lang } from './types';

export interface ReturnParams {
  claim: string | null;
  remind: boolean;
}

/** Where the e-mail link and Google bring the person back. */
export function returnUrl(origin: string, lang: Lang, params: ReturnParams = { claim: null, remind: false }): string {
  const query = new URLSearchParams();
  if (params.claim) query.set('claim', params.claim);
  if (params.remind) query.set('remind', '1');
  const text = query.toString();
  return `${origin}${pagePath('diary', lang)}${text ? `?${text}` : ''}`;
}

export function readReturnParams(search: string): ReturnParams {
  const query = new URLSearchParams(search);
  const claim = query.get('claim');
  return { claim: claim && claim.length <= 100 ? claim : null, remind: query.get('remind') === '1' };
}

/** The same address without `claim` and `remind` (the entry `r` and anything else stay) and without the hash,
 * where the sign-in library may have left #access_token=… (the diary page has no anchors). */
export function cleanReturnUrl(href: string): string {
  const url = new URL(href);
  url.searchParams.delete('claim');
  url.searchParams.delete('remind');
  return `${url.pathname}${url.search}`;
}

export interface FinishDeps {
  api: Pick<AccountApi, 'claim' | 'setConsent'>;
  storage: StorageLike | null;
  href: string;
  lang: Lang;
  method: (started: SignInMethod | null) => SignInMethod;
  replaceUrl: (url: string) => void;
  send: (event: AnalyticsEvent) => void;
  now?: number;
}

export type FinishResult =
  | { type: 'none' } // nothing to finish: an ordinary visit of a signed-in person
  | { type: 'claimed'; claimed: string[] }
  | { type: 'error'; error: ErrorKind }; // nothing changed: the address keeps its token, the mark stays

let running: Promise<FinishResult> | null = null;

/** After sign-in, once per page: the claim, the reminder consent, `signup_done`, a clean address. */
export function finishSignIn(deps: FinishDeps): Promise<FinishResult> {
  running ??= finish(deps).finally(() => { running = null; });
  return running;
}

async function finish(deps: FinishDeps): Promise<FinishResult> {
  const params = readReturnParams(new URL(deps.href).search);
  const started = signInStarted(deps.now ?? Date.now(), deps.storage);
  if (!params.claim && !started) {
    if (params.remind) deps.replaceUrl(cleanReturnUrl(deps.href));
    return { type: 'none' };
  }
  const result = await deps.api.claim(params.claim ? [params.claim] : [], started !== null);
  if (!result.ok) return { type: 'error', error: result.error };
  const claimed = result.data?.claimed ?? [];
  if (started || claimed.length > 0) {
    if (params.remind) await deps.api.setConsent(true); // a failure here leaves the switch on the account page
    deps.send(analyticsEvent('signup_done', null, deps.lang, { method: deps.method(started) }));
  }
  clearSignInStarted(deps.storage);
  deps.replaceUrl(cleanReturnUrl(deps.href));
  return { type: 'claimed', claimed };
}

/** Supabase sends a failed or expired link back with #error=…&error_code=… in the address. */
export function linkFailed(hash: string): boolean {
  return new URLSearchParams(hash.replace(/^#/, '')).has('error');
}
```

- [ ] **Step 4: Run the tests**

Run: the Vitest command of Step 2, then the same without files, then the type check.
Expected: PASS — `26 passed` in 3 files; then `250 passed` in 25 files; `- 0 errors`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/claim.ts site/src/lib/claim.test.ts site/src/lib/routes.ts site/src/lib/routes.test.ts site/src/lib/analytics.ts site/src/lib/analytics.test.ts
git commit -m "feat(site): stage 4.4b — diary addresses, 4.4b events, finishing a sign-in

The claim runs once per page and only after a sign-in started on this device or with a
?claim= token; the device's guest readings only with that mark (owner decision 12); consent
and signup_done only with the mark or a moved reading (review I1); then the address loses
claim, remind and the hash. The diary and account pairs are outside hreflang.csv.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Site — "Save to diary", the save sheet and "Check your e-mail" (screens 3, 3b)

**Files:**
- Create: `site/src/components/ui/SignInBlock.tsx`, `site/src/components/ui/SaveSheet.tsx`, `site/src/components/ui/useSaveToDiary.tsx` (the island's save wiring, review M20), `site/src/lib/sheetHistory.ts` (owner decision 14), `site/src/lib/diary.ts` (entry addresses only; Task 14 adds the rest), `site/src/lib/testing/night.ts` (a shown room for screen tests)
- Modify: `site/src/components/ui/NightRoom.tsx`, `site/src/islands/ReadingIsland.tsx`, `site/src/i18n/en.ts`, `site/src/i18n/es.ts`, `site/src/i18n/i18n.test.ts`, `site/src/styles/global.css`
- Test: `site/src/components/ui/SaveSheet.test.tsx`, `site/src/components/ui/NightRoom.test.tsx`, `site/src/components/ui/useSaveToDiary.test.tsx`, `site/src/lib/diary.test.ts` (new)

**Interfaces:**
- Consumes: `Auth`, `SendError`, `getAuth` (Task 9), `markSignInStarted`, `isSignedIn`, `STARTED_KEY` (Task 9), `authConfig`, `AuthConfig` (Task 9), `AccountApi.claimToken`, `createAccountApi` (Task 11), `siteFetch` (Task 10), `returnUrl` (Task 12), `analyticsEvent('save_click', …)` (Task 12), `pagePath('diary', …)` (Task 12), DOM helpers incl. `cleanup`, `waitFor` (Task 7); the room's own history entry `{ arcanaNight: true }` and its `popstate` handler in `ReadingIsland.tsx` (4.4a, unchanged).
- Produces:
  - `SignInBlock` props `{ lang; auth: Pick<Auth, 'sendLink' | 'google'>; google: boolean; idBase: string; redirectTo: () => Promise<string>; surface: 'night' | 'day' }`; `RESEND_WAIT_S = 60`; its root has the class `signin signin--<surface>` (the day labels' colour, review I6); «Use another e-mail» puts the focus into the e-mail field (review M15). Reused by the diary (Task 14) and the account (Task 16).
  - `SaveSheet` props `{ lang; readingId; auth: Pick<Auth, 'sendLink' | 'google'> | null; google: boolean; accountApi: Pick<AccountApi, 'claimToken'>; origin: string; onClose(): void }` — one claim token per open sheet, asked for at the first send; only a token that was made is kept, a failure is asked again at the next send (review M13).
  - `NightRoom` new optional props `save?: SaveSlot | null`, `sheet?: ComponentChildren`, `onCloseSheet?: () => void`; `export interface SaveSlot { saved: boolean; href: string; onSave(): void }`. «Save to diary» / «Saved ✓» is the **last** item of `.night__actions`, so a late button never moves the others under the finger (review M14); with the sheet open `.night__top` and `.night__body` are `inert` (review M15).
  - `sheetHistory.ts`: `interface HistoryLike { readonly state: unknown; pushState(data, unused); back() }`, `SHEET_STATE = { arcanaNight: true, arcanaSheet: true }`, `class SheetHistory { push(); popped(state): boolean; consume(): number }` — the sheet's own history entry (owner decision 14).
  - `useSaveToDiary(options): SaveToDiary` with `SaveToDiaryOptions { lang; tool; readingId: string | null; signedIn: boolean; readConfig?; loadAuth?; accountApi?; history?; send?; origin? }` and `SaveToDiary { slot: SaveSlot | null; sheet: ComponentChildren; closeSheet: (() => void) | undefined; closeForRoom(): number }`: reads `/api/auth-config` once a reading is created (not when the answer is shown — review M14), sends `save_click`, pushes the sheet's entry when the sheet opens; Back (`popstate`) closes only the sheet; × and Escape take the entry back with one `history.back()`; `closeForRoom()` tells `ReadingIsland` how many entries to step back over when the room closes with the sheet open.
  - `testing/night.ts`: `ONE: ReadingCreated`, `shown(reading, sections): NightState`.
  - `diary.ts`: `entryParam(search: string): string | null` (a UUID only, lower-cased), `entryHref(lang, id): string` (`/diary?r=<id>`).
  - Dictionary keys (EN prototype copy unless listed as drafts): `saveToDiary`, `savedToDiary`, `saveTitle`, `saveLead`, `saveRemind`, `signInEmailLabel`, `signInSend`, `signInOr`, `signInGoogle`, `signInTooOften`, `checkEmailTitle`, `checkEmailLead` (`{email}`), `checkEmailResend`, `checkEmailWait` (`{n}`), `checkEmailOther`, `checkEmailSent`.

- [ ] **Step 1: Write the failing tests**

Create `site/src/components/ui/SaveSheet.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AccountApi } from '../../lib/accountApi';
import type { Auth, SendResult } from '../../lib/auth';
import { STARTED_KEY } from '../../lib/authState';
import { byText, cleanup, click, mount, queryText, submit, typeInto } from '../../lib/testing/dom';
import { SaveSheet } from './SaveSheet';
import { RESEND_WAIT_S } from './SignInBlock';

function fakes(token: string | null = 'tok-1', answers: SendResult[] = []) {
  const sent: Array<{ method: 'email' | 'google'; email?: string; redirectTo: string }> = [];
  const tokens: string[] = [];
  const auth: Pick<Auth, 'sendLink' | 'google'> = {
    sendLink: async (email, redirectTo) => { sent.push({ method: 'email', email, redirectTo }); return answers.shift() ?? { ok: true }; },
    google: async (redirectTo) => { sent.push({ method: 'google', redirectTo }); return { ok: true }; },
  };
  const accountApi: Pick<AccountApi, 'claimToken'> = {
    claimToken: async (id) => {
      tokens.push(id);
      return token ? { ok: true, status: 201, data: { token, expires_at: '2026-11-29T00:00:00Z' } }
        : { ok: false, status: 409, error: 'other', body: { reason: 'in_diary' } };
    },
  };
  return { auth, accountApi, sent, tokens };
}

function sheet(f: ReturnType<typeof fakes>, props: { lang?: 'en' | 'es'; google?: boolean; onClose?: () => void } = {}) {
  return (
    <SaveSheet lang={props.lang ?? 'en'} readingId="r1" auth={f.auth} google={props.google ?? false}
      accountApi={f.accountApi} origin="https://arcana.test" onClose={props.onClose ?? (() => {})} />
  );
}

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.useRealTimers();
});

describe('the save sheet (screens 3, 3b; spec 4.4b §4)', () => {
  it('sends the e-mail link back to the diary with the claim token and the reminder, then shows "Check your e-mail"', async () => {
    const f = fakes();
    const { root } = await mount(sheet(f));
    expect(document.activeElement?.textContent).toBe('Save to your diary');
    const remind = root.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    expect(remind.checked).toBe(false); // off unless ticked (design review В3)
    await click(remind);
    await typeInto(root.querySelector('input[type="email"]')!, ' ana@example.com ');
    await submit(root.querySelector('form')!);
    expect(f.tokens).toEqual(['r1']);
    expect(f.sent).toEqual([{ method: 'email', email: 'ana@example.com', redirectTo: 'https://arcana.test/diary?claim=tok-1&remind=1' }]);
    expect(JSON.parse(localStorage.getItem(STARTED_KEY)!).method).toBe('email');
    expect(document.activeElement?.textContent).toBe('Check your e-mail');
    expect(root.textContent).toContain('We sent a link to ana@example.com.');
    expect(queryText(root, 'Continue with Google')).toBeNull(); // Google is off
  });

  it('without a claim token (already saved, too many) still returns to the diary of the page language', async () => {
    const f = fakes(null);
    const { root } = await mount(sheet(f, { lang: 'es' }));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(f.sent[0].redirectTo).toBe('https://arcana.test/es/diario');
    expect(byText(root, 'Revisa tu correo')).toBeTruthy();
  });

  it('offers Google when it is on and marks the sign-in as started here', async () => {
    const f = fakes();
    const { root } = await mount(sheet(f, { google: true }));
    await click(byText(root, 'Continue with Google', 'button'));
    expect(f.sent).toEqual([{ method: 'google', redirectTo: 'https://arcana.test/diary?claim=tok-1' }]);
    expect(JSON.parse(localStorage.getItem(STARTED_KEY)!).method).toBe('google');
  });

  it('says what went wrong: a wrong e-mail before sending, "too often" from Supabase', async () => {
    const f = fakes('tok-1', [{ ok: false, error: 'tooOften' }]);
    const { root } = await mount(sheet(f));
    const email = root.querySelector('input[type="email"]')!;
    await typeInto(email, 'not-an-email');
    await submit(root.querySelector('form')!);
    expect(root.querySelector('[role="alert"]')?.textContent).toBe('Please check the e-mail address and try again.');
    expect(f.sent).toEqual([]);
    await typeInto(email, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(root.querySelector('[role="alert"]')?.textContent).toBe('Too many tries for now. Please wait a few minutes and try again.');
    expect(root.querySelector('input[type="email"]')).not.toBeNull(); // still the form
  });

  it('lets the link be sent again only after 60 seconds, with the same token', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const f = fakes();
    const { root } = await mount(sheet(f));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(byText<HTMLButtonElement>(root, 'Send it again', 'button').disabled).toBe(true);
    expect(root.textContent).toContain(`You can send it again in ${RESEND_WAIT_S} s.`);
    await act(() => {
      vi.advanceTimersByTime(RESEND_WAIT_S * 1000);
    });
    expect(byText<HTMLButtonElement>(root, 'Send it again', 'button').disabled).toBe(false);
    await click(byText(root, 'Send it again', 'button'));
    expect(f.sent.map((s) => s.redirectTo)).toEqual(['https://arcana.test/diary?claim=tok-1', 'https://arcana.test/diary?claim=tok-1']);
    expect(f.tokens).toEqual(['r1']);
    expect(root.textContent).toContain('Sent again.');
  });

  it('closes with × before anything was sent, and makes no claim token', async () => {
    const onClose = vi.fn();
    const f = fakes();
    const { root } = await mount(sheet(f, { onClose }));
    await click(root.querySelector('button[aria-label="Close"]')!);
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(f.tokens).toEqual([]);
  });

  it('a claim token that could not be made is asked for again at the next send (review M13)', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const f = fakes(null);
    const { root } = await mount(sheet(f));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    await act(() => {
      vi.advanceTimersByTime(RESEND_WAIT_S * 1000);
    });
    await click(byText(root, 'Send it again', 'button'));
    expect(f.tokens).toEqual(['r1', 'r1']); // a failure is not kept for the whole sheet
    expect(f.sent.map((s) => s.redirectTo)).toEqual(['https://arcana.test/diary', 'https://arcana.test/diary']);
  });

  it('"Use another e-mail" goes back to the form with the focus in the e-mail field (review M15)', async () => {
    const f = fakes();
    const { root } = await mount(sheet(f));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    await click(byText(root, 'Use another e-mail', 'button'));
    expect(document.activeElement).toBe(root.querySelector('input[type="email"]'));
  });
});
```

Create `site/src/components/ui/NightRoom.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { NightState } from '../../lib/nightRoom';
import { panelConfig } from '../../lib/panel';
import { byText, cleanup, click, mount, queryText } from '../../lib/testing/dom';
import { ONE, shown } from '../../lib/testing/night';
import { NightRoom, type NightRoomProps } from './NightRoom';

function room(state: NightState, extra: Partial<NightRoomProps> = {}) {
  const noop = () => {};
  return (
    <NightRoom state={state} lang="en" config={panelConfig('one_card', 'en')} threeCards={false} question="Will it work?"
      sourceName={null} onClose={noop} onRetry={noop} onRestore={noop} onRestoreFollowup={noop} onFollowup={noop}
      onConfirmFollowup={noop} onCancelFollowup={noop} onMoreAbout={noop} onAskAnother={noop} {...extra} />
  );
}

afterEach(() => cleanup());

describe('the night room and the diary (spec 4.4b §4)', () => {
  it('a guest gets "Save to diary" under the answer, after the other actions (review M14)', async () => {
    const onSave = vi.fn();
    const { root } = await mount(room(shown(ONE, { headline: 'Slow down.' }), { save: { saved: false, href: '/diary?r=r1', onSave } }));
    expect(root.querySelector('.night__actions')!.lastElementChild?.textContent).toBe('Save to diary');
    await click(byText(root, 'Save to diary', 'button'));
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(queryText(root, 'Saved to your diary ✓')).toBeNull();
  });

  it('a signed-in person sees "Saved to your diary ✓" with the link to the entry', async () => {
    const { root } = await mount(room(shown(ONE, { headline: 'Slow down.' }), { save: { saved: true, href: '/diary?r=r1', onSave: vi.fn() } }));
    expect(byText<HTMLAnchorElement>(root, 'Saved to your diary ✓', 'a').getAttribute('href')).toBe('/diary?r=r1');
    expect(queryText(root, 'Save to diary', 'button')).toBeNull();
  });

  it('shows nothing when sign-in is off; with the sheet open Escape closes the sheet, not the room', async () => {
    const off = await mount(room(shown(ONE, { headline: 'Slow down.' }), { save: null }));
    expect(queryText(off.root, 'Save to diary', 'button')).toBeNull();
    off.unmount();
    const onClose = vi.fn();
    const onCloseSheet = vi.fn();
    await mount(room(shown(ONE, { headline: 'Slow down.' }), {
      onClose, onCloseSheet, save: { saved: false, href: '/diary?r=r1', onSave: vi.fn() },
      sheet: <div class="sheet"><button type="button">Inside</button></div>,
    }));
    expect(document.querySelector('.night__top')!.hasAttribute('inert')).toBe(true); // review M15
    await act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(onCloseSheet).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });
});
```

Create `site/src/lib/testing/night.ts` (the shown room moves here from the test file, so two screen tests share it):

```ts
// The night room with a whole answer on screen, for screen tests (NightRoom.test.tsx, useSaveToDiary.test.tsx).
import { CLOSED, nightReducer, type NightAction, type NightState } from '../nightRoom';
import type { ReadingCreated } from '../types';

export const ONE: ReadingCreated = {
  id: 'r1', lang: 'en', kind: 'one', verdict: null, soft_line: null, remaining: 1,
  cards: [{ card_id: 'major-18-moon', position: 'card', reversed: false, name: 'The Moon' }],
};

/** The room with the whole answer shown (cards turned, stream done). */
export function shown(reading: ReadingCreated, sections: Record<string, string>): NightState {
  const actions: NightAction[] = [
    { type: 'open' }, { type: 'created', reading, reducedMotion: true },
    { type: 'stream', event: { event: 'meta', data: { soft_line: null } } },
    ...Object.entries(sections).flatMap(([name, text]): NightAction[] => [
      { type: 'stream', event: { event: 'section', data: { name } } },
      { type: 'stream', event: { event: 'text', data: { name, text } } },
    ]),
    { type: 'stream', event: { event: 'done', data: { answer_shown: 'model' } } },
    { type: 'counts', counts: { followups_left: 2, followup_attempts_left: 8 } },
  ];
  return actions.reduce(nightReducer, CLOSED);
}
```

Create `site/src/components/ui/useSaveToDiary.test.tsx` (owner decision 14, review M14 and M20: the wiring the island uses, with the real night room; `history.back` is replaced by a spy and the Back press is a `popstate` the test sends, so nothing depends on happy-dom's navigation):

```tsx
// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AccountApi } from '../../lib/accountApi';
import type { AnalyticsEvent } from '../../lib/analytics';
import type { Auth } from '../../lib/auth';
import type { AuthConfig } from '../../lib/authConfig';
import { panelConfig } from '../../lib/panel';
import { SHEET_STATE } from '../../lib/sheetHistory';
import { byText, cleanup, click, mount, queryText, waitFor } from '../../lib/testing/dom';
import { ONE, shown } from '../../lib/testing/night';
import { NightRoom } from './NightRoom';
import { useSaveToDiary, type SaveToDiaryOptions } from './useSaveToDiary';

const ON: AuthConfig = { enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: false };
const STATE = shown(ONE, { headline: 'Slow down.' });
const ROOM = { arcanaNight: true }; // the room's own history entry (ReadingIsland)

function fakes(config: AuthConfig | null = ON) {
  const events: AnalyticsEvent[] = [];
  let reads = 0;
  const auth: Auth = {
    session: async () => null, token: async () => null, refresh: async () => null,
    sendLink: async () => ({ ok: true as const }), google: async () => ({ ok: true as const }), signOut: async () => {},
  };
  const accountApi: Pick<AccountApi, 'claimToken'> = {
    claimToken: async () => ({ ok: true, status: 201, data: { token: 'tok-1', expires_at: '2026-11-29T00:00:00Z' } }),
  };
  const options = (extra: Partial<SaveToDiaryOptions> = {}): SaveToDiaryOptions => ({
    lang: 'en', tool: 'love', readingId: 'r1', signedIn: false, accountApi, origin: 'https://arcana.test',
    readConfig: async () => { reads += 1; return config; }, loadAuth: async () => auth,
    send: (event) => { events.push(event); }, ...extra,
  });
  return { events, reads: () => reads, options };
}

/** What ReadingIsland does with the hook: its slot and its sheet in the real night room. */
function Room({ options, onClose = () => {} }: { options: SaveToDiaryOptions; onClose?: (steps: number) => void }) {
  const saving = useSaveToDiary(options);
  const noop = () => {};
  return (
    <>
      <NightRoom state={STATE} lang="en" config={panelConfig('one_card', 'en')} threeCards={false} question="Will it work?"
        sourceName={null} onClose={noop} onRetry={noop} onRestore={noop} onRestoreFollowup={noop} onFollowup={noop}
        onConfirmFollowup={noop} onCancelFollowup={noop} onMoreAbout={noop} onAskAnother={noop}
        save={saving.slot} sheet={saving.sheet} onCloseSheet={saving.closeSheet} />
      <button type="button" onClick={() => onClose(saving.closeForRoom())}>Close the room</button>
    </>
  );
}

/** The phone's Back: the browser is on the entry below and tells the page. */
async function backTo(state: unknown) {
  history.replaceState(state, '');
  await act(() => {
    window.dispatchEvent(new PopStateEvent('popstate', { state }));
  });
}

beforeEach(() => history.replaceState(ROOM, '', '/love'));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Save to diary in the night room (spec 4.4b §4)', () => {
  it('reads the sign-in settings once the reading exists and counts save_click when the sheet opens', async () => {
    const none = fakes();
    const before = await mount(<Room options={none.options({ readingId: null })} />);
    expect(none.reads()).toBe(0);
    expect(queryText(before.root, 'Save to diary', 'button')).toBeNull();
    before.unmount();
    const f = fakes();
    const { root } = await mount(<Room options={f.options()} />);
    await waitFor(() => byText(root, 'Save to diary', 'button'));
    expect(f.reads()).toBe(1);
    await click(byText(root, 'Save to diary', 'button'));
    expect(f.events).toEqual([{ name: 'save_click', tool: 'love', lang: 'en', params: {} }]);
    expect(root.querySelector('.night .sheet')).not.toBeNull();
  });

  it('signed in: "Saved to your diary ✓" with the entry link; sign-in off: no button at all', async () => {
    const signed = await mount(<Room options={fakes().options({ signedIn: true })} />);
    await waitFor(() => byText(signed.root, 'Saved to your diary ✓', 'a'));
    expect(byText<HTMLAnchorElement>(signed.root, 'Saved to your diary ✓', 'a').getAttribute('href')).toBe('/diary?r=r1');
    signed.unmount();
    const off = fakes({ enabled: false, supabase_url: '', anon_key: '', google: false });
    const { root } = await mount(<Room options={off.options()} />);
    await waitFor(() => off.reads() === 1);
    expect(queryText(root, 'Save to diary', 'button')).toBeNull();
  });

  it("the sheet is a history entry of its own: the phone's Back closes only the sheet (owner decision 14)", async () => {
    const push = vi.spyOn(history, 'pushState');
    const back = vi.spyOn(history, 'back').mockImplementation(() => {});
    const { root } = await mount(<Room options={fakes().options()} />);
    await waitFor(() => byText(root, 'Save to diary', 'button'));
    await click(byText(root, 'Save to diary', 'button'));
    expect(push).toHaveBeenCalledWith(SHEET_STATE, '');
    await backTo(ROOM);
    expect(root.querySelector('.sheet')).toBeNull();
    expect(byText(root, 'Slow down.')).toBeTruthy(); // the room and its answer stay
    expect(back).not.toHaveBeenCalled();
    expect(document.activeElement?.textContent).toBe('Save to diary');
  });

  it('× and Escape take the entry back once; the room closing with the sheet open steps over both', async () => {
    vi.spyOn(history, 'pushState');
    const back = vi.spyOn(history, 'back').mockImplementation(() => {});
    const steps: number[] = [];
    const { root } = await mount(<Room options={fakes().options()} onClose={(n) => steps.push(n)} />);
    await waitFor(() => byText(root, 'Save to diary', 'button'));
    await click(byText(root, 'Save to diary', 'button'));
    await click(root.querySelector('.sheet button[aria-label="Close"]')!);
    expect(back).toHaveBeenCalledTimes(1);
    expect(root.querySelector('.sheet')).toBeNull();
    await backTo(ROOM); // the popstate of that back(): nothing more happens
    expect(back).toHaveBeenCalledTimes(1);
    await click(byText(root, 'Save to diary', 'button'));
    await act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(back).toHaveBeenCalledTimes(2);
    expect(root.querySelector('.sheet')).toBeNull();
    await click(byText(root, 'Save to diary', 'button'));
    await click(byText(root, 'Close the room', 'button'));
    expect(steps).toEqual([1]); // ReadingIsland then steps back over the sheet's entry and the room's in one go
    expect(back).toHaveBeenCalledTimes(2);
    expect(root.querySelector('.sheet')).toBeNull();
  });
});
```

Create `site/src/lib/diary.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { entryHref, entryParam } from './diary';

describe('diary rules', () => {
  it('opens an entry only for a real reading id', () => {
    expect(entryParam('?r=2B3C4D5E-0000-4000-8000-000000000001')).toBe('2b3c4d5e-0000-4000-8000-000000000001');
    expect(entryParam('?r=../account')).toBeNull();
    expect(entryParam('')).toBeNull();
    expect(entryHref('es', 'abc')).toBe('/es/diario?r=abc');
  });
});
```

In `site/src/i18n/i18n.test.ts` replace `expect(keys('en').length).toBe(160);` with `expect(keys('en').length).toBe(176);`, `expect(DRAFTS.en.length).toBe(57);` with `expect(DRAFTS.en.length).toBe(66);` and `expect(DRAFTS.es.length).toBe(116);` with `expect(DRAFTS.es.length).toBe(131);`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/components/ui/SaveSheet.test.tsx src/components/ui/NightRoom.test.tsx src/components/ui/useSaveToDiary.test.tsx src/lib/diary.test.ts src/i18n/i18n.test.ts`
Expected: FAIL — `Failed to resolve import "./SaveSheet"`, `"./SignInBlock"`, `"./useSaveToDiary"`, `"../../lib/sheetHistory"`, `"./diary"`; NightRoom: `no element with the text "Save to diary"`; i18n: `expected 160 to be 176`.

- [ ] **Step 3: Implement**

In `site/src/i18n/en.ts`, after the line `  crisisWeb: 'Open {name}',` add:

```ts
  // stage 4.4b: save to diary and sign-in (screens 3, 3b)
  saveToDiary: 'Save to diary',
  savedToDiary: 'Saved to your diary ✓',
  saveTitle: 'Save to your diary',
  saveLead: 'Your reading stays here — nothing is lost.',
  saveRemind: 'Remind me in 7 days: did it come true?',
  signInEmailLabel: 'Your e-mail',
  signInSend: 'Send me a link',
  signInOr: 'or',
  signInGoogle: 'Continue with Google',
  signInTooOften: 'Too many tries for now. Please wait a few minutes and try again.',
  checkEmailTitle: 'Check your e-mail',
  checkEmailLead: 'We sent a link to {email}. Open it on this or any other device to finish.',
  checkEmailResend: 'Send it again',
  checkEmailWait: 'You can send it again in {n} s.',
  checkEmailOther: 'Use another e-mail',
  checkEmailSent: 'Sent again.',
```

and in `enDrafts`, after the line `  'crisisWeb', 'errDayCap', 'followupReady',` add:

```ts
  'signInEmailLabel', 'signInSend', 'signInOr', 'signInTooOften', 'checkEmailLead', 'checkEmailResend', 'checkEmailWait',
  'checkEmailOther', 'checkEmailSent',
```

In `site/src/i18n/es.ts`, after the line `  crisisWeb: 'Abrir {name}',` add:

```ts
  // etapa 4.4b: guardar en el diario y acceso (pantallas 3, 3b)
  saveToDiary: 'Guardar en el diario',
  savedToDiary: 'Guardada en tu diario ✓',
  saveTitle: 'Guárdala en tu diario',
  saveLead: 'Tu tirada se queda aquí: no se pierde nada.',
  saveRemind: 'Recuérdamelo en 7 días: ¿se cumplió?',
  signInEmailLabel: 'Tu correo',
  signInSend: 'Envíame un enlace',
  signInOr: 'o',
  signInGoogle: 'Continuar con Google',
  signInTooOften: 'Demasiados intentos por ahora. Espera unos minutos y vuelve a intentarlo.',
  checkEmailTitle: 'Revisa tu correo',
  checkEmailLead: 'Enviamos un enlace a {email}. Ábrelo en este u otro dispositivo para terminar.',
  checkEmailResend: 'Enviar de nuevo',
  checkEmailWait: 'Podrás enviarlo de nuevo en {n} s.',
  checkEmailOther: 'Usar otro correo',
  checkEmailSent: 'Enviado de nuevo.',
```

and in `esDrafts`, after the line `  'errDayCap', 'followupReady', 'plusNotNow', 'yesNoCountHint',` add:

```ts
  'savedToDiary', 'saveTitle', 'saveLead', 'saveRemind', 'signInEmailLabel', 'signInSend', 'signInOr', 'signInGoogle',
  'signInTooOften', 'checkEmailTitle', 'checkEmailLead', 'checkEmailResend', 'checkEmailWait', 'checkEmailOther', 'checkEmailSent',
```

Create `site/src/components/ui/SignInBlock.tsx`:

```tsx
// The sign-in block (screens 3, 3b; spec 4.4b §3–§6): an e-mail for a link and, when it is on, "Continue with
// Google"; after the e-mail — "Check your e-mail" with "Send it again" after RESEND_WAIT_S seconds. The same block in
// the save sheet, the diary and the account page. Pressing either button marks this device (authState.ts), so the
// diary moves its guest readings into the account once after sign-in. "Use another e-mail" puts the focus back into
// the e-mail field (review M15).
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t, type DictKey } from '../../i18n';
import type { Auth, SendError } from '../../lib/auth';
import { markSignInStarted } from '../../lib/authState';
import type { Lang } from '../../lib/types';

export const RESEND_WAIT_S = 60;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MESSAGES: Record<SendError | 'invalid', DictKey> = {
  tooOften: 'signInTooOften', badEmail: 'plusEmailError', unavailable: 'errUnavailable', invalid: 'plusEmailError',
};

interface Props {
  lang: Lang;
  auth: Pick<Auth, 'sendLink' | 'google'>;
  google: boolean;
  idBase: string;
  /** Where the link and Google bring the person back (the save sheet adds the reading's claim token). */
  redirectTo: () => Promise<string>;
  /** 'night' inside the night room, 'day' on the diary and account pages. */
  surface: 'night' | 'day';
}

export function SignInBlock({ lang, auth, google, idBase, redirectTo, surface }: Props) {
  const d = t(lang);
  const [email, setEmail] = useState('');
  const [phase, setPhase] = useState<'form' | 'sending' | 'sent'>('form');
  const [error, setError] = useState<SendError | 'invalid' | null>(null);
  const [wait, setWait] = useState(0);
  const [resent, setResent] = useState(false);
  const sentTitle = useRef<HTMLHeadingElement>(null);
  const emailInput = useRef<HTMLInputElement>(null);
  const backToForm = useRef(false); // "Use another e-mail" was pressed
  const counting = wait > 0;

  useEffect(() => {
    if (!counting) return;
    const timer = setInterval(() => setWait((w) => Math.max(w - 1, 0)), 1000);
    return () => clearInterval(timer);
  }, [counting]);

  useEffect(() => { // the pressed button is gone: focus goes to what took its place
    if (phase === 'sent') sentTitle.current?.focus();
    else if (phase === 'form' && backToForm.current) emailInput.current?.focus();
    backToForm.current = false;
  }, [phase]);

  const send = async (again: boolean) => {
    const address = email.trim();
    if (!EMAIL.test(address)) {
      setError('invalid');
      return;
    }
    setError(null);
    setResent(false);
    if (!again) setPhase('sending');
    markSignInStarted('email');
    const result = await auth.sendLink(address, await redirectTo());
    if (!result.ok) {
      setError(result.error);
      if (!again) setPhase('form');
      return;
    }
    setPhase('sent');
    setWait(RESEND_WAIT_S);
    setResent(again);
  };

  const withGoogle = async () => {
    setError(null);
    markSignInStarted('google');
    const result = await auth.google(await redirectTo()); // on success the browser leaves for Google
    if (!result.ok) setError(result.error);
  };

  const message = error ? d[MESSAGES[error]] : null;
  const errorId = `${idBase}-error`;

  if (phase === 'sent') {
    return (
      <div class={`signin signin--${surface}`}>
        <h3 class="signin__title" tabIndex={-1} ref={sentTitle}>{d.checkEmailTitle}</h3>
        <p>{fill(d.checkEmailLead, { email: email.trim() })}</p>
        <button type="button" class="btn btn--outline" disabled={counting} onClick={() => void send(true)}>
          {d.checkEmailResend}
        </button>
        {counting ? <p class="small">{fill(d.checkEmailWait, { n: wait })}</p> : null}
        <p class="small" role="status">{resent ? d.checkEmailSent : ''}</p>
        {message ? <p role="alert">{message}</p> : null}
        <button type="button" class="btn btn--text" onClick={() => { backToForm.current = true; setPhase('form'); setWait(0); setError(null); }}>
          {d.checkEmailOther}
        </button>
      </div>
    );
  }

  return (
    <div class={`signin signin--${surface}`}>
      <form class="field" onSubmit={(event) => { event.preventDefault(); void send(false); }} noValidate>
        <label for={`${idBase}-email`}>{d.signInEmailLabel}</label>
        <input id={`${idBase}-email`} ref={emailInput} class={surface === 'day' ? 'input input--day' : 'input'} type="email"
          autocomplete="email" required maxLength={254} placeholder={d.plusEmailPlaceholder} value={email}
          aria-invalid={error ? 'true' : undefined} aria-describedby={message ? errorId : undefined}
          onInput={(e) => setEmail((e.target as HTMLInputElement).value)} />
        <button type="submit" class={surface === 'day' ? 'btn btn--ink' : 'btn btn--gold'} disabled={phase === 'sending'}>
          {d.signInSend}
        </button>
      </form>
      {google ? (
        <>
          <p class="signin__or">{d.signInOr}</p>
          <button type="button" class="btn btn--outline" onClick={() => void withGoogle()}>{d.signInGoogle}</button>
        </>
      ) : null}
      {message ? <p role="alert" id={errorId}>{message}</p> : null}
    </div>
  );
}
```

Create `site/src/components/ui/SaveSheet.tsx`:

```tsx
// "Save to diary" for a guest (screens 3, 3b; spec 4.4b §4): a sheet at the bottom of the night room with the
// "Remind me in 7 days" box (off) and the sign-in block. The return address carries the reading's one-time claim
// token, so the reading is saved on whatever device the e-mail link is opened. Closing it (×, Escape) keeps the
// answer on screen: the night room stays as it was.
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../../i18n';
import type { AccountApi } from '../../lib/accountApi';
import type { Auth } from '../../lib/auth';
import { returnUrl } from '../../lib/claim';
import type { Lang } from '../../lib/types';
import { CloseIcon } from './icons';
import { SignInBlock } from './SignInBlock';

interface Props {
  lang: Lang;
  readingId: string;
  auth: Pick<Auth, 'sendLink' | 'google'> | null; // null until the page's Auth is ready (the library loads at the first send)
  google: boolean;
  accountApi: Pick<AccountApi, 'claimToken'>;
  origin: string;
  onClose: () => void;
}

export function SaveSheet({ lang, readingId, auth, google, accountApi, origin, onClose }: Props) {
  const d = t(lang);
  const [remind, setRemind] = useState(false);
  const remindNow = useRef(remind);
  remindNow.current = remind;
  const title = useRef<HTMLHeadingElement>(null);
  const token = useRef<Promise<string | null> | null>(null);

  useEffect(() => title.current?.focus(), []);

  // one token per open sheet, asked for at the first send; only a token that was made is kept, so "Send it again"
  // after a failure asks once more (review M13). Without one (409 already saved, 429, offline) the link still saves
  // the reading on this device: the sign-in started here, so the claim moves this device's guest readings
  const redirectTo = async () => {
    token.current ??= accountApi.claimToken(readingId).then((r) => {
      if (r.ok && r.data) return r.data.token;
      token.current = null;
      return null;
    });
    return returnUrl(origin, lang, { claim: await token.current, remind: remindNow.current });
  };

  return (
    <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="save-title">
      <div class="sheet__top">
        <h2 id="save-title" class="sheet__title" tabIndex={-1} ref={title}>{d.saveTitle}</h2>
        <button type="button" class="close-button" aria-label={d.close} onClick={onClose}><CloseIcon /></button>
      </div>
      <p class="small">{d.saveLead}</p>
      <label class="check">
        <input type="checkbox" checked={remind} onChange={(e) => setRemind((e.target as HTMLInputElement).checked)} />
        <span>{d.saveRemind}</span>
      </label>
      {auth ? (
        <SignInBlock lang={lang} auth={auth} google={google} idBase="save" redirectTo={redirectTo} surface="night" />
      ) : (
        <p class="small" role="status" aria-live="polite" />
      )}
    </div>
  );
}
```

Create `site/src/lib/diary.ts`:

```ts
// The diary's rules for the screen (spec 4.4b §5): which entry the address opens and its link.
import { pagePath } from './routes';
import type { Lang } from './types';

const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** `?r=<id>` of the diary page: the entry to open, or null for the list. */
export function entryParam(search: string): string | null {
  const id = new URLSearchParams(search).get('r');
  return id && ID.test(id) ? id.toLowerCase() : null;
}

export function entryHref(lang: Lang, id: string): string {
  return `${pagePath('diary', lang)}?r=${encodeURIComponent(id)}`;
}
```

Create `site/src/lib/sheetHistory.ts`:

```ts
// The save sheet's own entry in the browser history (spec 4.4b §4, owner decision 14). Opening the sheet adds one
// entry above the night room's, so the phone's Back leaves only the sheet; closing it by × or Escape takes that entry
// back exactly once; when the room closes with the sheet open, ReadingIsland steps back over both entries at once.
// The entry keeps `arcanaNight: true`, so the room's own popstate handler (ReadingIsland) still sees a room entry.

export interface HistoryLike {
  readonly state: unknown;
  pushState(data: unknown, unused: string): void;
  back(): void;
}

export const SHEET_STATE = { arcanaNight: true, arcanaSheet: true } as const;

function isSheetEntry(state: unknown): boolean {
  return typeof state === 'object' && state !== null && (state as { arcanaSheet?: unknown }).arcanaSheet === true;
}

export class SheetHistory {
  private readonly history: HistoryLike;
  private onTop = false;

  constructor(history: HistoryLike) {
    this.history = history;
  }

  /** The sheet opened. */
  push(): void {
    if (this.onTop) return;
    this.history.pushState(SHEET_STATE, '');
    this.onTop = true;
  }

  /** popstate: true when Back left the sheet's entry (close the sheet, keep the room). */
  popped(state: unknown): boolean {
    if (!this.onTop || isSheetEntry(state)) return false;
    this.onTop = false;
    return true;
  }

  /** The sheet closes by ×, Escape or with the room: 1 when its entry is still on top (step back over it, once). */
  consume(): number {
    if (!this.onTop) return 0;
    this.onTop = false;
    return 1;
  }
}
```

Create `site/src/components/ui/useSaveToDiary.tsx`:

```tsx
// "Save to diary" in the night room (spec 4.4b §4): the button or "Saved to your diary ✓", the save sheet and its
// own history entry (owner decision 14: the phone's Back closes only the sheet), and save_click. ReadingIsland keeps
// the room and the room's history entry; this hook keeps the sheet's, so the wiring has a test of its own
// (useSaveToDiary.test.tsx, Fable plan review M20). The sign-in settings are read once a reading exists, so the
// button is there by the time the answer shows (review M14); the sign-in library loads only at the first send.
import type { ComponentChildren } from 'preact';
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { createAccountApi, type AccountApi } from '../../lib/accountApi';
import { analyticsEvent, sendEvent, type AnalyticsEvent } from '../../lib/analytics';
import { getAuth, type Auth } from '../../lib/auth';
import { authConfig, type AuthConfig } from '../../lib/authConfig';
import { entryHref } from '../../lib/diary';
import { SheetHistory, type HistoryLike } from '../../lib/sheetHistory';
import { siteFetch } from '../../lib/siteApi';
import type { Lang, Tool } from '../../lib/types';
import type { SaveSlot } from './NightRoom';
import { SaveSheet } from './SaveSheet';

export interface SaveToDiaryOptions {
  lang: Lang;
  tool: Tool;
  /** The reading in the room, once it is created. */
  readingId: string | null;
  /** The create request carried the token: the reading is in the account already. */
  signedIn: boolean;
  /** Tests pass their own; the page uses the real ones. */
  readConfig?: () => Promise<AuthConfig | null>;
  loadAuth?: () => Promise<Auth | null>;
  accountApi?: Pick<AccountApi, 'claimToken'>;
  history?: HistoryLike;
  send?: (event: AnalyticsEvent) => void;
  origin?: string;
}

export interface SaveToDiary {
  /** NightRoom `save`: null where sign-in is off or no reading is made yet. */
  slot: SaveSlot | null;
  /** NightRoom `sheet`. */
  sheet: ComponentChildren;
  /** NightRoom `onCloseSheet` (Escape inside the sheet). */
  closeSheet: (() => void) | undefined;
  /** The room is closing: the sheet goes too, without a step of its own; 1 when the sheet's history entry was still
   * on top (ReadingIsland then steps back over it together with the room's entry), else 0. */
  closeForRoom: () => number;
}

export function useSaveToDiary(options: SaveToDiaryOptions): SaveToDiary {
  const { lang, tool, readingId, signedIn, readConfig = authConfig, loadAuth = getAuth, send = sendEvent } = options;
  const [config, setConfig] = useState<AuthConfig | null>(null); // null: not read yet, or could not be read
  const [open, setOpen] = useState(false);
  const [auth, setAuth] = useState<Auth | null>(null);
  const api = useMemo(() => options.accountApi ?? createAccountApi(siteFetch()), []);
  const entry = useRef<SheetHistory | null>(null);
  const browserHistory = (): HistoryLike => options.history ?? window.history; // not at build time: Astro renders this
  const sheetEntry = () => (entry.current ??= new SheetHistory(browserHistory()));

  useEffect(() => {
    if (readingId && config === null) void readConfig().then(setConfig);
  }, [readingId]);

  useEffect(() => {
    const onPop = () => {
      if (sheetEntry().popped(browserHistory().state)) setOpen(false); // Back left the sheet's entry: the room stays
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const openSheet = () => {
    send(analyticsEvent('save_click', tool, lang));
    sheetEntry().push();
    setOpen(true);
    void loadAuth().then(setAuth); // the page's Auth; the library itself loads at the first send
  };

  const closeSheet = () => {
    if (sheetEntry().consume()) browserHistory().back(); // × and Escape: the sheet's entry goes, exactly once
    setOpen(false);
  };

  const closeForRoom = () => {
    setOpen(false);
    return sheetEntry().consume();
  };

  const slot = config?.enabled && readingId ? { saved: signedIn, href: entryHref(lang, readingId), onSave: openSheet } : null;
  const sheet = open && config && readingId ? (
    <SaveSheet lang={lang} readingId={readingId} auth={auth} google={config.google} accountApi={api}
      origin={options.origin ?? location.origin} onClose={closeSheet} />
  ) : null;
  return { slot, sheet, closeSheet: open ? closeSheet : undefined, closeForRoom };
}
```

In `site/src/components/ui/NightRoom.tsx`:

- replace

```tsx
// §4): under each card its own vote (icon and word), the verdict and "why" large in the text column.
import { useEffect, useRef, useState } from 'preact/hooks';
```

with

```tsx
// §4): under each card its own vote (icon and word), the verdict and "why" large in the text column. Stage 4.4b §4:
// the last of the answer's actions is "Save to diary" (a guest: opens the save sheet inside this dialog; Escape then
// closes the sheet first, and the room behind it is inert) or "Saved to your diary ✓" with the link to the entry.
import type { ComponentChildren } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
```

- replace

```tsx
  onMoreAbout: () => void;
  onAskAnother: () => void;
}
```

with

```tsx
  onMoreAbout: () => void;
  onAskAnother: () => void;
  /** Spec 4.4b §4: null where sign-in is off (no button at all). */
  save?: SaveSlot | null;
  /** The open save sheet, drawn inside the dialog so that focus stays in the room. */
  sheet?: ComponentChildren;
  onCloseSheet?: () => void;
}

export interface SaveSlot {
  saved: boolean; // signed in: the reading is in the account already
  href: string; // the diary entry of this reading
  onSave: () => void;
}
```

- replace

```tsx
  const onClose = useRef(props.onClose);
  onClose.current = props.onClose;
```

with

```tsx
  const onClose = useRef(props.onClose);
  onClose.current = props.onClose;
  const onCloseSheet = useRef(props.onCloseSheet);
  onCloseSheet.current = props.onCloseSheet;
  const saveButton = useRef<HTMLButtonElement>(null);
  const hadSheet = useRef(false);
```

- replace

```tsx
    const onKey = (event: KeyboardEvent) => dialog.current && handleDialogKey(event, dialog.current, () => onClose.current());
```

with

```tsx
    const onKey = (event: KeyboardEvent) => {
      const sheet = dialog.current?.querySelector<HTMLElement>('.sheet');
      if (sheet && onCloseSheet.current) handleDialogKey(event, sheet, () => onCloseSheet.current?.());
      else if (dialog.current) handleDialogKey(event, dialog.current, () => onClose.current());
    };
```

- replace `  const then = (action: () => void) => () => {` with

```tsx
  // the sheet closed: focus goes back to "Save to diary"
  useEffect(() => {
    const open = Boolean(props.sheet);
    if (hadSheet.current && !open) saveButton.current?.focus();
    hadSheet.current = open;
  }, [Boolean(props.sheet)]);

  const then = (action: () => void) => () => {
```

- replace

```tsx
                  <button type="button" class="btn btn--text" onClick={props.onAskAnother}>{d.askAnother}</button>
                </div>
              ) : null}
```

with (last in the row: the settings may arrive after the answer, and a late button must not move the others — review M14)

```tsx
                  <button type="button" class="btn btn--text" onClick={props.onAskAnother}>{d.askAnother}</button>
                  {props.save ? (props.save.saved ? (
                    <p class="saved-mark"><a href={props.save.href}>{d.savedToDiary}</a></p>
                  ) : (
                    <button type="button" class="btn btn--gold" ref={saveButton} onClick={props.save.onSave}>{d.saveToDiary}</button>
                  )) : null}
                </div>
              ) : null}
```

- replace `        <div class="night__top">` with `        <div class="night__top" inert={props.sheet ? true : undefined}>` and `          <div class="night__body">` with `          <div class="night__body" inert={props.sheet ? true : undefined}>` (the sheet is the dialog now; what is behind it takes no focus and no clicks — review M15)

- replace `        {state.phase === 'crisis' && state.crisis ? <CrisisView payload={state.crisis} lang={lang} /> : null}` with

```tsx
        {state.phase === 'crisis' && state.crisis ? <CrisisView payload={state.crisis} lang={lang} /> : null}

        {props.sheet ?? null}
```

In `site/src/islands/ReadingIsland.tsx`:

- replace the header comment line `// closes the room instead of leaving the page; × and Escape step back over that entry.` with

```tsx
// closes the room instead of leaving the page; × and Escape step back over that entry. Stage 4.4b §4: requests carry
// the token of a signed-in person (siteApi.ts); under a shown answer "Save to diary" opens the save sheet
// (useSaveToDiary.tsx). The open sheet has a history entry of its own above the room's (owner decision 14): Back
// closes only the sheet, and the room closing with the sheet open steps back over both entries at once.
```

- replace `import { analyticsEvent, sendEvent } from '../lib/analytics';` with

```tsx
import { analyticsEvent, sendEvent } from '../lib/analytics';
import { isSignedIn } from '../lib/authState';
```

- replace `import { PlusCard } from '../components/ui/PlusCard';` with

```tsx
import { PlusCard } from '../components/ui/PlusCard';
import { useSaveToDiary } from '../components/ui/useSaveToDiary';
```

- replace `    cards: cardsFor(config.kind) as CardCount });` with `    cards: cardsFor(config.kind) as CardCount, signedIn: false });`
- in the function draw, replace `    drawn.current = { at: Date.now(), tz, question: body.question ?? '', id: '', tool: toolFor(config, kind), cards: cardsFor(kind, count) };` with `    drawn.current = { at: Date.now(), tz, question: body.question ?? '', id: '', tool: toolFor(config, kind), cards: cardsFor(kind, count), signedIn: false };` (the ref's type now has `signedIn`; without it here `astro check` reports TS2741 — review I10)
- replace `  const api = useMemo(() => siteApi(), []);` with

```tsx
  const api = useMemo(() => siteApi(), []);
  const saving = useSaveToDiary({ lang, tool: drawn.current.tool, readingId: state.reading?.id ?? null,
    signedIn: drawn.current.signedIn });
```

- replace `        if (action.type === 'created') drawn.current.id = action.reading.id;` with

```tsx
        if (action.type === 'created') {
          drawn.current.id = action.reading.id;
          drawn.current.signedIn = isSignedIn(); // the request carried the token: the reading is in the account
        }
```

- in `closeNow`, replace

```tsx
  function closeNow() {
    run.current += 1;
```

with

```tsx
  function closeNow() {
    run.current += 1;
    saving.closeForRoom(); // the sheet goes with the room; its history entry is handled in stepBack
```

- replace

```tsx
  function stepBack() {
    if (!inHistory.current) return;
    inHistory.current = false;
    history.back();
  }
```

with

```tsx
  function stepBack() {
    const steps = (inHistory.current ? 1 : 0) + saving.closeForRoom(); // the sheet's entry sits above the room's
    inHistory.current = false;
    if (steps === 1) history.back();
    else if (steps > 1) history.go(-steps);
  }
```

- replace

```tsx
          onAskAnother={askAnother}
        />
```

with

```tsx
          onAskAnother={askAnother}
          save={saving.slot}
          sheet={saving.sheet}
          onCloseSheet={saving.closeSheet}
        />
```

The room's own `popstate` handler stays as it is: Back from the sheet's entry lands on the room's entry (`arcanaNight: true`), so it keeps the room open, while the hook closes the sheet. The diary's `history.replaceState` after sign-in (Task 14) is on another page and is not touched.

In `site/src/styles/global.css`, before `/* Simple card page */` add:

```css
/* Stage 4.4b: the save sheet in the night room (screens 3, 3b) */
.sheet {
  position: sticky; bottom: 0; z-index: 1; display: flex; flex-direction: column; gap: var(--space-3);
  margin: var(--space-6) calc(-1 * var(--space-4)) calc(-1 * var(--space-7)); padding: var(--space-5) var(--space-4) var(--space-6);
  border-radius: var(--radius-panel-large) var(--radius-panel-large) 0 0; background: var(--color-night-surface);
  border-top: 1px solid var(--color-night-line);
}
@media (min-width: 900px) { /* the room's side padding is wider there: the sheet still meets its edges (review I9) */
  .sheet { margin-inline: calc(-1 * var(--space-7)); padding-inline: var(--space-7); }
}
.sheet__top { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
.sheet__title { margin: 0; font-family: var(--font-display); font-weight: 500; font-size: var(--font-size-h-2); }
.check { display: flex; align-items: flex-start; gap: var(--space-3); min-height: 44px; cursor: pointer; }
.check input { width: 20px; height: 20px; margin: var(--space-1) 0 0; flex: none; accent-color: var(--color-night-accent); }
.signin { display: flex; flex-direction: column; gap: var(--space-3); }
.signin__title { margin: 0; font-family: var(--font-display); font-weight: 500; font-size: var(--font-size-h-2); }
.signin__or { margin: 0; text-align: center; font-size: var(--font-size-small); }
.signin--day .field label { color: var(--color-day-text-muted); } /* the night label colour is ≈1.8:1 on day (review I6) */
.saved-mark { margin: 0; font-weight: 600; }
.saved-mark a { display: inline-flex; align-items: center; min-height: 44px; color: var(--color-night-accent); } /* M16 */
```

- [ ] **Step 4: Run the tests and the build**

Run: the Vitest command of Step 2, then the same without files, then the type check, then `deploy/build-site.sh && python3 tools/site/check_dist.py`
Expected: PASS — `25 passed` in 5 files; then `266 passed` in 29 files; `- 0 errors`; then `OK: 167 pages`.

- [ ] **Step 5: Commit**

```bash
git add site/src/components/ui/SignInBlock.tsx site/src/components/ui/SaveSheet.tsx site/src/components/ui/useSaveToDiary.tsx site/src/components/ui/NightRoom.tsx site/src/islands/ReadingIsland.tsx site/src/lib/diary.ts site/src/lib/sheetHistory.ts site/src/lib/testing/night.ts site/src/i18n site/src/styles/global.css site/src/components/ui/SaveSheet.test.tsx site/src/components/ui/NightRoom.test.tsx site/src/components/ui/useSaveToDiary.test.tsx site/src/lib/diary.test.ts
git commit -m "feat(site): stage 4.4b — Save to diary, the save sheet and Check your e-mail

A guest's sheet sends the e-mail link (or Google) back to the diary with the reading's
claim token and the 7-day reminder flag; resend after 60 s; Supabase errors as one line.
Signed in: Saved to your diary with the entry link. The answer stays on screen; the
sheet has its own history entry, so the phone's Back closes only the sheet (owner
decision 14).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Site — the diary page and its list (screen 4a), the Plus card in the diary

**Files:**
- Create: `site/src/islands/DiaryIsland.tsx`, `site/src/components/ui/DiaryList.tsx`, `site/src/views/DiaryView.astro`, `site/src/pages/diary.astro`, `site/src/pages/es/diario.astro`
- Modify: `site/src/lib/diary.ts` (whole file), `site/src/components/ui/PlusCard.tsx` (whole file), `site/src/components/ui/icons.tsx` (`NoteIcon`), `site/src/layouts/Base.astro` (`noindex`), `site/src/lib/testing/fakes.ts` (`routeFetch`), `site/src/i18n/en.ts`, `es.ts`, `i18n.test.ts`, `site/src/styles/global.css`
- Test: `site/src/lib/diary.test.ts` (whole file), `site/src/islands/DiaryIsland.test.tsx`

**Interfaces:**
- Consumes: `openSession`, `methodOf`, `SessionStatus` (Task 9), `browserStorage`, `clearSignedIn`, `SIGNED_IN_KEY` (Task 9), `createAccountApi`, `DiaryItem`, `Outcome` (Task 11), `siteFetch` (Task 10), `finishSignIn`, `linkFailed`, `readReturnParams`, `returnUrl` (Task 12), `SignInBlock` (Task 13), `entryHref`, `entryParam` (Task 13), `sendEvent` (analytics), `cardById`, `cardImage` (deck), `forgetAuth`, `forgetAuthConfig` (tests).
- Produces:
  - `diary.ts` adds: `OUTCOME_AFTER_DAYS = 7`, `DAY_MS`, `NOTE_MAX = 1000`, `DIARY_PAGE = 10`, `outcomeOpensOn(createdAt): Date` — **00:00 local time of the day «local date of the reading + 7 days»** (owner decision 13), `outcomeOpen(createdAt, now): boolean` (`now >= outcomeOpensOn(createdAt)`: the "come back" line and the buttons use one rule — review I7), `afterDays(createdAt, now): 7 | 30`, `formatDate(iso | Date, lang, timeZone?): string`, `kindKey(kind, topic): DictKey`, `noteLeft(text): number`, `isCrisis(item): boolean`.
  - `DiaryList` props `{ lang; api: Pick<AccountApi, 'diary'>; onSignedOut(): void }`; `OUTCOME_KEYS: Record<Outcome, DictKey>` (Task 15 uses it). One request (`limit=10`): the free diary is one page, so there is no "Show more" (review M19). Only `401 {"reason": "sign_in"}` calls `onSignedOut`; a `401` without JSON is the stage cookie — `errStage` and a button that reloads the page; any other error — its line, the help link where it belongs, and «Try again» (reviews I2, M18).
  - `DiaryIsland`: re-opens the session after `onSignedOut` once per page; a second time it shows «Try again» instead (review I2: never a loop of requests).
  - `PlusCard` props `{ lang; tool: Tool | null; place?: 'limit' | 'diary'; focusOnShow? }` — `place: 'diary'` renders only the white card and sends `plus_view {place: 'diary'}`; both places show `plusBenefit3` and `plusDiaryNote`.
  - `Base.astro` prop `noindex?: boolean` → `<meta name="robots" content="noindex, nofollow">`.
  - `routeFetch(routes: Record<string, (call: Call) => Response>): { fetch: FetchFn; calls: Call[] }` in `testing/fakes.ts` — answers by `"METHOD /path?query"`, else `"METHOD /path"`, else throws.
  - Pages `/diary`, `/es/diario` (noindex, `current="diary"`); `DiaryIsland` props `{ lang }`.
  - Dictionary keys: `diaryTitle`, `navDiary`, `navDiaryShort`, `diaryWhy`, `diarySignInSoon`, `signInLinkExpired`, `diaryEmpty`, `diaryNoQuestion`, `diaryKindThree`, `diaryHidden` (`{n}`), `diaryNoteMark`, `outcomeYes`, `outcomePartly`, `outcomeNo`, `diaryAccountLink`, `plusDiaryNote`.

- [ ] **Step 1: Write the failing tests**

Replace the whole `site/src/lib/diary.test.ts` with (the day rule is tested with local dates — `new Date(y, m, d, h)` — so it holds in any time zone; review I7, I11):

```ts
import { describe, expect, it } from 'vitest';
import { DAY_MS, afterDays, entryHref, entryParam, formatDate, isCrisis, kindKey, noteLeft, outcomeOpen, outcomeOpensOn } from './diary';

const MADE = new Date(2026, 10, 1, 22, 0).toISOString(); // 1 November 2026, 22:00 on this device's clock
const local = (month: number, day: number, hour = 0, minute = 0) => new Date(2026, month, day, hour, minute);
const at = (days: number) => new Date(new Date(MADE).getTime() + days * DAY_MS);

describe('diary rules', () => {
  it('opens an entry only for a real reading id', () => {
    expect(entryParam('?r=2B3C4D5E-0000-4000-8000-000000000001')).toBe('2b3c4d5e-0000-4000-8000-000000000001');
    expect(entryParam('?r=../account')).toBeNull();
    expect(entryParam('')).toBeNull();
    expect(entryHref('es', 'abc')).toBe('/es/diario?r=abc');
  });

  it('opens "did it come true?" at 00:00 local time of the 7th day after the reading\'s day (owner decision 13)', () => {
    expect(outcomeOpensOn(MADE).getTime()).toBe(local(10, 8).getTime());
    expect(outcomeOpen(MADE, local(10, 7, 23, 59))).toBe(false);
    expect(outcomeOpen(MADE, local(10, 8, 0, 0))).toBe(true);
    expect(outcomeOpen(MADE, local(10, 8, 9, 0))).toBe(true); // less than 7 × 24 h after 22:00, yet the named day
  });

  it('names in the "come back" line the very day the buttons open, also across a month end', () => {
    const late = new Date(2026, 10, 30, 23, 59).toISOString();
    expect(formatDate(outcomeOpensOn(late), 'en')).toBe('7 December 2026');
    expect(outcomeOpen(late, local(11, 6, 23, 59))).toBe(false);
    expect(outcomeOpen(late, local(11, 7))).toBe(true);
  });

  it('counts after_days 7 up to 30 days, then 30', () => {
    expect(afterDays(MADE, at(7))).toBe(7);
    expect(afterDays(MADE, at(29.9))).toBe(7);
    expect(afterDays(MADE, at(30))).toBe(30);
  });

  it('formats a date in each language', () => {
    expect(formatDate('2026-11-01T12:00:00+00:00', 'en', 'UTC')).toBe('1 November 2026');
    expect(formatDate('2026-11-01T12:00:00+00:00', 'es', 'UTC')).toBe('1 de noviembre de 2026');
  });

  it('names an entry by its tool', () => {
    expect(kindKey('three', 'love')).toBe('navLove');
    expect(kindKey('yes_no', null)).toBe('navYesNo');
    expect(kindKey('three', 'work')).toBe('diaryKindThree');
    expect(kindKey('one', null)).toBe('fmtOneCard');
    expect(kindKey('card_page', null)).toBe('fmtOneCard');
  });

  it('counts the note and knows a crisis entry', () => {
    expect(noteLeft('x'.repeat(990))).toBe(10);
    expect(isCrisis({ answer_shown: 'crisis' })).toBe(true);
    expect(isCrisis({ answer_shown: 'model' })).toBe(false);
  });
});
```

Append to `site/src/lib/testing/fakes.ts`:

```ts
/** Answers by "METHOD /path?query" or, failing that, "METHOD /path"; anything else throws (no network). For screens
 * that make several requests at once (the diary: settings, claim, list). */
export function routeFetch(routes: Record<string, (call: Call) => Response>): { fetch: FetchFn; calls: Call[] } {
  const calls: Call[] = [];
  const fetchFn: FetchFn = async (url, init) => {
    const headers = (init?.headers ?? {}) as Record<string, string>;
    const call: Call = { url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : undefined, headers };
    calls.push(call);
    const route = routes[`${call.method} ${url}`] ?? routes[`${call.method} ${url.split('?')[0]}`];
    if (!route) throw new Error(`unexpected call ${call.method} ${url}`);
    return route(call);
  };
  return { fetch: fetchFn, calls };
}
```

Create `site/src/islands/DiaryIsland.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../lib/analytics';
import { forgetAuth } from '../lib/auth';
import { forgetAuthConfig } from '../lib/authConfig';
import { SIGNED_IN_KEY } from '../lib/authState';
import { byText, cleanup, click, mount, settle, waitFor } from '../lib/testing/dom';
import { jsonResponse, routeFetch, type Call } from '../lib/testing/fakes';
import DiaryIsland from './DiaryIsland';

type FakeSession = { access_token: string; user?: { email?: string; app_metadata?: { provider?: string } } };
const h = vi.hoisted(() => ({ session: null as FakeSession | null, sent: [] as unknown[] }));
vi.mock('../lib/supabaseClient', () => ({ // the sign-in library is never loaded in tests
  createClient: () => ({
    getSession: async () => ({ data: { session: h.session }, error: null }),
    refreshSession: async () => ({ data: { session: null }, error: null }),
    signInWithOtp: async (args: unknown) => { h.sent.push(args); return { error: null }; },
    signInWithOAuth: async () => ({ error: null }),
    signOut: async () => { h.session = null; return { error: null }; },
  }),
}));
vi.mock('../lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../lib/analytics')>()), sendEvent: vi.fn(),
}));

const ON = { enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: false };
const ITEM = {
  id: '2b3c4d5e-0000-4000-8000-000000000001', created_at: '2026-11-20T18:00:00+00:00', lang: 'en', kind: 'three',
  topic: 'work', question: 'Will the <b>move</b> go well?', headline: 'Slow and steady.', answer_shown: 'model',
  cards: [{ card_id: 'major-18-moon', position: 'past', reversed: true, name: 'The Moon' }], outcome: 'partly',
  has_note: true, followups: 1,
};
const CRISIS = { ...ITEM, id: '2b3c4d5e-0000-4000-8000-000000000002', question: null, topic: null, headline: null,
  answer_shown: 'crisis', outcome: null, has_note: false };
const page = (items: unknown[], hidden = 0) => () => jsonResponse(200, { items, next_before: null, hidden_count: hidden });

function serve(routes: Record<string, (call: Call) => Response>) {
  const served = routeFetch({ 'GET /api/auth-config': () => jsonResponse(200, ON), ...routes });
  vi.stubGlobal('fetch', served.fetch);
  return served;
}

/** Mounts the page and waits until `ready` passes: the settings, the library (mocked), the claim and the list come
 * one after another (waitFor, not a count of rounds — review I11). */
async function open(ready: (root: HTMLElement) => unknown) {
  const mounted = await mount(<DiaryIsland lang="en" />);
  await waitFor(() => ready(mounted.root));
  return mounted;
}

beforeEach(() => history.replaceState(null, '', '/diary'));
afterEach(() => {
  cleanup();
  localStorage.clear();
  forgetAuthConfig();
  forgetAuth();
  h.session = null;
  h.sent = [];
  vi.unstubAllGlobals();
  vi.mocked(sendEvent).mockClear();
});

describe('the diary page (screen 4a; spec 4.4b §5)', () => {
  it('says that signing in opens soon when sign-in is off', async () => {
    serve({ 'GET /api/auth-config': () => jsonResponse(200, { enabled: false, supabase_url: '', anon_key: '', google: false }) });
    await open((root) => byText(root, 'Signing in opens soon.'));
  });

  it('not signed in: one line why and the sign-in block, and no claim', async () => {
    const served = serve({});
    const { root } = await open((r) => expect(r.querySelector('input[type="email"]')).not.toBeNull());
    expect(root.textContent).toContain('Save your readings here and come back to see what came true.');
    expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/auth-config']);
  });

  it('after the e-mail link on another device: claims only the token once, gives consent, counts signup_done and cleans the address', async () => {
    history.replaceState(null, '', '/diary?claim=tok-1&remind=1');
    h.session = { access_token: 'tok-a', user: { app_metadata: { provider: 'email' } } };
    const served = serve({
      'POST /api/account/claim': () => jsonResponse(200, { claimed: [ITEM.id] }),
      'PATCH /api/account': () => jsonResponse(200, { email: 'ana@example.com', reminders_consent: true, consent_at: null }),
      'GET /api/diary': page([ITEM]),
    });
    await open(() => expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual([
      'GET /api/auth-config', 'POST /api/account/claim', 'PATCH /api/account', 'GET /api/diary?limit=10']));
    expect(served.calls[1].body).toEqual({ tokens: ['tok-1'], device: false }); // no mark here: owner decision 12
    expect(served.calls[1].headers.authorization).toBe('Bearer tok-a');
    expect(served.calls[2].body).toEqual({ reminders_consent: true });
    expect(`${location.pathname}${location.search}`).toBe('/diary');
    expect(vi.mocked(sendEvent)).toHaveBeenCalledWith({ name: 'signup_done', tool: null, lang: 'en', params: { method: 'email' } });
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBe('1');
  });

  it('an ordinary visit claims nothing and lists the entries as text, a crisis entry without text', async () => {
    h.session = { access_token: 'tok-a' };
    const served = serve({ 'GET /api/diary': page([ITEM, CRISIS]) });
    const { root } = await open((r) => expect(r.querySelectorAll('a.diary-item')).toHaveLength(2));
    expect(served.calls.some((c) => c.url === '/api/account/claim')).toBe(false);
    const links = Array.from(root.querySelectorAll<HTMLAnchorElement>('a.diary-item'));
    expect(links.map((a) => a.getAttribute('href'))).toEqual([`/diary?r=${ITEM.id}`, `/diary?r=${CRISIS.id}`]);
    expect(links[0].textContent).toContain('Will the <b>move</b> go well?'); // text, never markup
    expect(root.querySelector('a.diary-item b')).toBeNull();
    expect(links[0].textContent).toContain('20 November 2026 · Three cards');
    expect(links[0].textContent).toContain('Slow and steady.');
    expect(links[0].textContent).toContain('Partly');
    expect(links[0].textContent).toContain('Has a note');
    expect(links[1].querySelector('.diary-item__question')).toBeNull();
    expect(links[1].querySelector('.diary-item__headline')).toBeNull();
  });

  it('more than ten: the hidden line and the Plus card with the whole-diary benefit', async () => {
    h.session = { access_token: 'tok-a' };
    serve({ 'GET /api/diary': page([ITEM], 3) });
    const { root } = await open((r) => byText(r, 'More readings in Plus: 3'));
    expect(byText(root, 'What Plus gives you')).toBeTruthy();
    expect(byText(root, 'Your whole diary, with no limit')).toBeTruthy();
    expect(byText(root, 'Your diary keeps your last 10 readings. Plus keeps all of them.')).toBeTruthy();
    expect(vi.mocked(sendEvent)).toHaveBeenCalledWith({ name: 'plus_view', tool: null, lang: 'en', params: { place: 'diary' } });
  });

  it('an empty diary offers a reading', async () => {
    h.session = { access_token: 'tok-a' };
    serve({ 'GET /api/diary': page([]) });
    const { root } = await open((r) => byText(r, 'Your saved readings will appear here.'));
    expect(byText<HTMLAnchorElement>(root, 'Get a free reading', 'a').getAttribute('href')).toBe('/');
  });

  it('a 401 without JSON (the stage cookie) is the stage line with a reload button — one request, no loop (review I2)', async () => {
    h.session = { access_token: 'tok-a' };
    const served = serve({ 'GET /api/diary': () => new Response('', { status: 401 }) });
    const { root } = await open((r) => byText(r, 'Your session on this preview site has expired. Reload the page to continue.'));
    await settle();
    expect(served.calls.filter((c) => c.url.startsWith('/api/diary'))).toHaveLength(1);
    expect(byText(root, 'Try again', 'button')).toBeTruthy(); // it reloads the page (spec §3)
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBe('1'); // not signed out: the token was never refused
  });

  it('a list that could not be read says so and "Try again" asks once more (review M18)', async () => {
    h.session = { access_token: 'tok-a' };
    let lists = 0;
    serve({ 'GET /api/diary': () => (lists++ === 0 ? jsonResponse(503, { reason: 'db' }) : page([ITEM])()) });
    const { root } = await open((r) => byText(r, 'The service is unavailable right now. Please try again in a few minutes.'));
    await click(byText(root, 'Try again', 'button'));
    await waitFor(() => expect(root.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(lists).toBe(2);
  });
});
```

In `site/src/i18n/i18n.test.ts` replace `.toBe(176);` with `.toBe(192);`, `expect(DRAFTS.en.length).toBe(66);` with `expect(DRAFTS.en.length).toBe(76);` and `expect(DRAFTS.es.length).toBe(131);` with `expect(DRAFTS.es.length).toBe(146);`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/diary.test.ts src/islands/DiaryIsland.test.tsx src/i18n/i18n.test.ts`
Expected: FAIL — `outcomeOpen is not a function` (and the other new diary exports), `Failed to resolve import "./DiaryIsland"`, `expected 176 to be 192`.

- [ ] **Step 3: Implement**

In `site/src/i18n/en.ts`, after the line `  checkEmailSent: 'Sent again.',` add:

```ts
  // stage 4.4b: the diary (screen 4a, menu 11c, desktop header 13a)
  diaryTitle: 'Your diary — Arcana Diary',
  navDiary: 'Your diary',
  navDiaryShort: 'Diary',
  diaryWhy: 'Save your readings here and come back to see what came true.',
  diarySignInSoon: 'Signing in opens soon.',
  signInLinkExpired: 'This link has expired or was already used. Send yourself a new one below.',
  diaryEmpty: 'Your saved readings will appear here.',
  diaryNoQuestion: 'No question',
  diaryKindThree: 'Three cards',
  diaryHidden: 'More readings in Plus: {n}',
  diaryNoteMark: 'Has a note',
  outcomeYes: 'Came true',
  outcomePartly: 'Partly',
  outcomeNo: 'No',
  diaryAccountLink: 'Account',
  plusDiaryNote: 'Your diary keeps your last 10 readings. Plus keeps all of them.',
```

and in `enDrafts`, after the line `  'checkEmailOther', 'checkEmailSent',` add:

```ts
  'diaryTitle', 'diaryWhy', 'diarySignInSoon', 'signInLinkExpired', 'diaryEmpty', 'diaryNoQuestion', 'diaryKindThree',
  'diaryHidden', 'diaryNoteMark', 'diaryAccountLink',
```

In `site/src/i18n/es.ts`, after the line `  checkEmailSent: 'Enviado de nuevo.',` add:

```ts
  // etapa 4.4b: el diario (pantalla 4a, menú 11d)
  diaryTitle: 'Tu diario — Arcana Diary',
  navDiary: 'Tu diario',
  navDiaryShort: 'Diario',
  diaryWhy: 'Guarda aquí tus tiradas y vuelve a ver qué se cumplió.',
  diarySignInSoon: 'El acceso abrirá pronto.',
  signInLinkExpired: 'Este enlace caducó o ya se usó. Envíate uno nuevo aquí abajo.',
  diaryEmpty: 'Aquí aparecerán tus tiradas guardadas.',
  diaryNoQuestion: 'Sin pregunta',
  diaryKindThree: 'Tres cartas',
  diaryHidden: 'Más tiradas en Plus: {n}',
  diaryNoteMark: 'Tiene una nota',
  outcomeYes: 'Se cumplió',
  outcomePartly: 'En parte',
  outcomeNo: 'No',
  diaryAccountLink: 'Cuenta',
  plusDiaryNote: 'Tu diario guarda tus últimas 10 tiradas. Plus las guarda todas.',
```

and in `esDrafts`, after the line `  'signInTooOften', 'checkEmailTitle', 'checkEmailLead', 'checkEmailResend', 'checkEmailWait', 'checkEmailOther', 'checkEmailSent',` add:

```ts
  'diaryTitle', 'navDiaryShort', 'diaryWhy', 'diarySignInSoon', 'signInLinkExpired', 'diaryEmpty', 'diaryNoQuestion',
  'diaryKindThree', 'diaryHidden', 'diaryNoteMark', 'outcomeYes', 'outcomePartly', 'outcomeNo', 'diaryAccountLink',
  'plusDiaryNote',
```

Replace the whole `site/src/lib/diary.ts` with:

```ts
// The diary's rules for the screen (spec 4.4b §5): which entry the address opens, how an entry is named, when
// "Came true / Partly / No" opens (00:00 local time of the 7th day after the reading's day — owner decision 13), the
// note's length, the outcome event's `after_days`.
import type { DictKey } from '../i18n';
import type { DiaryItem } from './accountApi';
import { pagePath } from './routes';
import type { Kind, Lang } from './types';

export const OUTCOME_AFTER_DAYS = 7; // owner decision 6
export const DAY_MS = 24 * 60 * 60 * 1000;
export const NOTE_MAX = 1000; // spec 4.3 §6
export const DIARY_PAGE = 10; // the free diary shows 10 (spec 4.4b §5): one request holds them all, no "Show more"

const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** `?r=<id>` of the diary page: the entry to open, or null for the list. */
export function entryParam(search: string): string | null {
  const id = new URLSearchParams(search).get('r');
  return id && ID.test(id) ? id.toLowerCase() : null;
}

export function entryHref(lang: Lang, id: string): string {
  return `${pagePath('diary', lang)}?r=${encodeURIComponent(id)}`;
}

/** The moment "did it come true?" opens (owner decision 13): 00:00 local time of the day «the reading's local date + 7
 * days». The "Come back on {date}" line names this day, so the line and the buttons always agree (review I7). */
export function outcomeOpensOn(createdAt: string): Date {
  const made = new Date(createdAt);
  return new Date(made.getFullYear(), made.getMonth(), made.getDate() + OUTCOME_AFTER_DAYS);
}

export function outcomeOpen(createdAt: string, now: Date): boolean {
  return now.getTime() >= outcomeOpensOn(createdAt).getTime();
}

/** `after_days` of `outcome_answered` (docs/design/analytics-events.md): 7 up to 30 days after, then 30. */
export function afterDays(createdAt: string, now: Date): 7 | 30 {
  return now.getTime() - new Date(createdAt).getTime() < 30 * DAY_MS ? 7 : 30;
}

/** "20 November 2026" / "20 de noviembre de 2026", in the person's own time zone. */
export function formatDate(iso: string | Date, lang: Lang, timeZone?: string): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-GB' : 'es-MX', { day: 'numeric', month: 'long', year: 'numeric', timeZone }).format(date);
}

/** How a diary entry is named: by the tool it came from. */
export function kindKey(kind: Kind, topic: string | null): DictKey {
  if (topic === 'love') return 'navLove';
  if (kind === 'yes_no') return 'navYesNo';
  if (kind === 'three') return 'diaryKindThree';
  return 'fmtOneCard';
}

export function noteLeft(text: string): number {
  return NOTE_MAX - text.length;
}

/** A crisis entry is listed without any text (the API sends none); everything else may show its question. */
export function isCrisis(item: Pick<DiaryItem, 'answer_shown'>): boolean {
  return item.answer_shown === 'crisis';
}
```

Append to `site/src/components/ui/icons.tsx`:

```tsx
/** A note in a diary entry (spec 4.4b §5). */
export function NoteIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <path d="M3 2.5h7l3 3v8H3z" />
      <path d="M5.5 8h5M5.5 10.5h5" />
    </svg>
  );
}
```

Replace the whole `site/src/components/ui/PlusCard.tsx` with (Task 10's `siteApi` import kept; the callers `PlusCard lang={lang} tool={…} focusOnShow` in `ReadingIsland.tsx` and `NightRoom.tsx` stay as they are):

```tsx
// Today's free readings are used (screen 11a, spec 4.4a §4): a day page block — the title, the lead, the help link,
// a white card with a gold rule ("What Plus gives you", the benefits, "tell me when it opens" by e-mail through
// POST /api/plus/waitlist, "Not now"), then the free Card of the Day. No price on the closed stage (owner,
// 19.11.2026); never inside the answer text. Stage 4.4b §5, §8: the third benefit (the whole diary) and the line about
// the free diary's 10 readings; in the diary (`place: 'diary'`) only the white card, without the "today's readings"
// title and the Card of the Day links.
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import { errorMessageKey, type ErrorKind } from '../../lib/errors';
import { pagePath } from '../../lib/routes';
import { siteApi } from '../../lib/siteApi';
import type { Lang, Tool } from '../../lib/types';
import { HelpLine } from './HelpLine';

interface Props {
  lang: Lang;
  tool: Tool | null; // null in the diary: plus_view carries no tool anyway
  place?: 'limit' | 'diary';
  focusOnShow?: boolean;
}

export function PlusCard({ lang, tool, place = 'limit', focusOnShow = false }: Props) {
  const d = t(lang);
  const heading = useRef<HTMLHeadingElement>(null);
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'done' | 'invalid' | ErrorKind>('idle');
  const id = `plus-${tool ?? place}`;

  useEffect(() => {
    sendEvent(analyticsEvent('plus_view', tool, lang, { place }));
    if (focusOnShow) heading.current?.focus();
  }, []);

  const submit = async (event: Event) => {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { // the API still validates; this keeps the browser's own bubble away
      setStatus('invalid');
      return;
    }
    setStatus('sending');
    const result = await siteApi().joinWaitlist(email.trim(), lang);
    if (result.ok) setStatus('done');
    else setStatus(result.status === 422 ? 'invalid' : result.error);
  };

  const error = status === 'invalid' ? d.plusEmailError
    : status !== 'idle' && status !== 'sending' && status !== 'done' ? d[errorMessageKey(status)] : null;
  const daily = pagePath('daily', lang);

  const card = (
    <section class="plus__card" aria-labelledby={`${id}-title`}>
      <h3 id={`${id}-title`}>{d.plusGives}</h3>
      <ul>
        <li>{d.plusBenefit1}</li>
        <li>{d.plusBenefit2}</li>
        <li>{d.plusBenefit3}</li>
      </ul>
      <p class="small">{d.plusDiaryNote}</p>
      {status === 'done' ? (
        <p role="status">{d.plusDone}</p>
      ) : (
        <form class="field" onSubmit={submit} noValidate>
          <label for={`${id}-email`}>{d.plusEmailLabel}</label>
          <input
            id={`${id}-email`}
            class="input input--day"
            type="email"
            autocomplete="email"
            required
            aria-invalid={error ? 'true' : undefined}
            aria-describedby={error ? `${id}-error` : undefined}
            maxLength={254}
            placeholder={d.plusEmailPlaceholder}
            value={email}
            onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
          />
          <div class="plus__row">
            <button type="submit" class="btn btn--ink" disabled={status === 'sending'}>{d.plusNotify}</button>
            {place === 'limit' ? <a href={daily}>{d.plusNotNow}</a> : null}
          </div>
          {error ? <p role="alert" id={`${id}-error`}>{error}</p> : null}
        </form>
      )}
    </section>
  );

  if (place === 'diary') return card;
  return (
    <div class="plus">
      <h2 class="display" tabIndex={-1} ref={heading}>{d.plusTitle}</h2>
      <p class="lead">{d.plusLead}</p>
      <HelpLine lang={lang} />
      {card}
      <a class="plus__daily" href={daily}>{d.plusDaily}</a>
    </div>
  );
}
```

Create `site/src/components/ui/DiaryList.tsx`:

```tsx
// The diary list (screen 4a; spec 4.4b §5): the newest readings first — date, kind, question (or "no question"),
// small cards, the answer's headline, the "did it come true?" mark and a note mark; a crisis entry shows no text.
// More than the free 10: a line and the Plus card (plus_view, place: diary). Every text from the API is a text node.
// One request: the free diary is one page. Only 401 "sign_in" means the session went (review I2); a 401 without JSON
// is the stage cookie — reload the page (spec §3); any other error — its line and "Try again" (review M18).
import { useEffect, useState } from 'preact/hooks';
import { fill, t, type DictKey } from '../../i18n';
import type { AccountApi, DiaryItem, Outcome } from '../../lib/accountApi';
import { cardById, cardImage } from '../../lib/deck';
import { DIARY_PAGE, entryHref, formatDate, isCrisis, kindKey } from '../../lib/diary';
import { errorMessageKey, needsHelpLink, reasonOf, type ErrorKind } from '../../lib/errors';
import { pagePath } from '../../lib/routes';
import type { Lang } from '../../lib/types';
import { HelpLine } from './HelpLine';
import { NoteIcon } from './icons';
import { PlusCard } from './PlusCard';

export const OUTCOME_KEYS: Record<Outcome, DictKey> = { yes: 'outcomeYes', partly: 'outcomePartly', no: 'outcomeNo' };

interface Props {
  lang: Lang;
  api: Pick<AccountApi, 'diary'>;
  onSignedOut: () => void; // 401 "sign_in": the session went
}

function Row({ item, lang }: { item: DiaryItem; lang: Lang }) {
  const d = t(lang);
  const crisis = isCrisis(item);
  return (
    <a class="diary-item" href={entryHref(lang, item.id)}>
      <span class="diary-item__meta">{formatDate(item.created_at, lang)} · {d[kindKey(item.kind, item.topic)]}</span>
      {crisis ? null : <span class="diary-item__question">{item.question ?? d.diaryNoQuestion}</span>}
      <span class="diary-item__cards" aria-hidden="true">
        {item.cards.map((c) => {
          const card = cardById(c.card_id);
          return card ? <img src={cardImage(card, 160)} alt="" width={32} height={55} class={c.reversed ? 'is-reversed' : undefined} /> : null;
        })}
      </span>
      {!crisis && item.headline ? <span class="diary-item__headline">{item.headline}</span> : null}
      <span class="diary-item__marks">
        {item.outcome ? <span class="diary-item__outcome">{d[OUTCOME_KEYS[item.outcome]]}</span> : null}
        {item.has_note ? <span class="diary-item__note"><NoteIcon /><span class="visually-hidden">{d.diaryNoteMark}</span></span> : null}
      </span>
    </a>
  );
}

export function DiaryList({ lang, api, onSignedOut }: Props) {
  const d = t(lang);
  const [items, setItems] = useState<DiaryItem[]>([]);
  const [hidden, setHidden] = useState(0);
  const [status, setStatus] = useState<'loading' | 'ready' | ErrorKind>('loading');

  const load = async () => {
    setStatus('loading');
    const result = await api.diary(undefined, DIARY_PAGE);
    if (!result.ok) {
      if (result.status === 401 && reasonOf(result.body) === 'sign_in') onSignedOut();
      else setStatus(result.error); // 'stage' for a 401 without JSON
      return;
    }
    setItems(result.data.items);
    setHidden(result.data.hidden_count);
    setStatus('ready');
  };

  useEffect(() => { void load(); }, []);

  return (
    <section class="diary__list" aria-busy={status === 'loading'}>
      {status === 'ready' && items.length === 0 ? (
        <div class="diary__empty">
          <p>{d.diaryEmpty}</p>
          <a class="btn btn--ink" href={pagePath('home', lang)}>{d.notFoundReading}</a>
        </div>
      ) : null}
      {items.length > 0 ? (
        <ul class="diary-list">
          {items.map((item) => <li key={item.id}><Row item={item} lang={lang} /></li>)}
        </ul>
      ) : null}
      {status !== 'loading' && status !== 'ready' ? (
        <div class="diary__error">
          <p role="alert">{d[errorMessageKey(status)]}</p>
          {needsHelpLink(status) ? <HelpLine lang={lang} /> : null}
          <button type="button" class="btn btn--outline" onClick={() => (status === 'stage' ? location.reload() : void load())}>
            {d.retry}
          </button>
        </div>
      ) : null}
      {hidden > 0 ? (
        <>
          <p class="diary__hidden">{fill(d.diaryHidden, { n: hidden })}</p>
          <PlusCard lang={lang} tool={null} place="diary" />
        </>
      ) : null}
    </section>
  );
}
```

Create `site/src/islands/DiaryIsland.tsx`:

```tsx
// The diary page (screens 4a, 4b; spec 4.4b §5) on /diary and /es/diario. Static HTML, drawn here after load:
// sign-in off — "signing in opens soon"; not signed in — a line and the sign-in block (the person who comes back
// signs in right here, owner decision 3); signed in — once, the claim after sign-in (claim.ts), then the list. Nothing
// here runs at build time.
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { t } from '../i18n';
import { createAccountApi } from '../lib/accountApi';
import { sendEvent } from '../lib/analytics';
import { methodOf, openSession, type SessionStatus } from '../lib/auth';
import { browserStorage, clearSignedIn } from '../lib/authState';
import { finishSignIn, linkFailed, readReturnParams, returnUrl } from '../lib/claim';
import { errorMessageKey, type ErrorKind } from '../lib/errors';
import { pagePath } from '../lib/routes';
import { siteFetch } from '../lib/siteApi';
import type { Lang } from '../lib/types';
import { DiaryList } from '../components/ui/DiaryList';
import { HelpLine } from '../components/ui/HelpLine';
import { SignInBlock } from '../components/ui/SignInBlock';

type View =
  | { type: 'loading' }
  | { type: 'status'; status: Exclude<SessionStatus, { type: 'signedIn' }>; expired: boolean }
  | { type: 'failed'; error: ErrorKind } // the claim after sign-in did not go through
  | { type: 'ready' };

export default function DiaryIsland({ lang }: { lang: Lang }) {
  const d = t(lang);
  const [view, setView] = useState<View>({ type: 'loading' });
  const api = useMemo(() => createAccountApi(siteFetch()), []);
  const reopened = useRef(false);

  const open = async () => {
    setView({ type: 'loading' });
    const status = await openSession();
    if (status.type !== 'signedIn') {
      setView({ type: 'status', status, expired: linkFailed(location.hash) });
      return;
    }
    const finished = await finishSignIn({
      api, storage: browserStorage(), href: location.href, lang,
      method: (started) => methodOf(status.session, started),
      replaceUrl: (url) => history.replaceState(history.state, '', url),
      send: sendEvent,
    });
    if (finished.type === 'error') setView({ type: 'failed', error: finished.error });
    else setView({ type: 'ready' });
  };

  useEffect(() => { void open(); }, []);

  const signedOut = async () => { // a 401 "sign_in" in the middle: the session went on this device
    clearSignedIn();
    if (reopened.current) { // once per page: a second one shows "Try again", never a loop of requests (review I2)
      setView({ type: 'failed', error: 'other' });
      return;
    }
    reopened.current = true;
    await open();
  };

  if (view.type === 'loading') return <div class="diary" aria-busy="true" />; // no empty status line (review M18)
  if (view.type === 'failed') {
    return (
      <div class="diary">
        <p role="alert">{d[errorMessageKey(view.error)]}</p>
        <HelpLine lang={lang} />
        <button type="button" class="btn btn--outline" onClick={() => void open()}>{d.retry}</button>
      </div>
    );
  }
  if (view.type === 'status') {
    const { status } = view;
    if (status.type === 'off') return <p class="lead">{d.diarySignInSoon}</p>;
    if (status.type === 'unreachable') {
      return (
        <div class="diary">
          <p role="alert">{d.errUnavailable}</p>
          <HelpLine lang={lang} />
          <button type="button" class="btn btn--outline" onClick={() => void open()}>{d.retry}</button>
        </div>
      );
    }
    // a link from the e-mail (or Google) brings back ?claim / ?remind: signing in here keeps them
    const keep = readReturnParams(location.search);
    return (
      <div class="diary diary--signin">
        <p class="lead">{d.diaryWhy}</p>
        {view.expired ? <p role="alert">{d.signInLinkExpired}</p> : null}
        <SignInBlock lang={lang} auth={status.auth} google={status.google} idBase="diary" surface="day"
          redirectTo={async () => returnUrl(location.origin, lang, keep)} />
      </div>
    );
  }
  return (
    <div class="diary">
      <DiaryList lang={lang} api={api} onSignedOut={() => void signedOut()} />
      <p><a class="diary__account" href={pagePath('account', lang)}>{d.diaryAccountLink}</a></p>
    </div>
  );
}
```

In `site/src/layouts/Base.astro`:

- replace `// header with the menu and the language switch, the footer. The stage is closed by Caddy (password, X-Robots-Tag).` with

```
// header with the menu and the language switch, the footer. The stage is closed by Caddy (password, X-Robots-Tag).
// `noindex`: the diary and the account (spec 4.4b §5, §6) — never indexed, also after the launch.
```

- replace

```
  current?: PageKey;
}

const { lang, title, path, current } = Astro.props;
```

with

```
  current?: PageKey;
  noindex?: boolean;
}

const { lang, title, path, current, noindex = false } = Astro.props;
```

- replace `    <title>{title}</title>` with

```
    <title>{title}</title>
    {noindex ? <meta name="robots" content="noindex, nofollow" /> : null}
```

Create `site/src/views/DiaryView.astro`:

```astro
---
// The diary (screens 4a, 4b; spec 4.4b §5): a static page, noindex and outside hreflang; DiaryIsland draws the list,
// an entry (?r=<id>) or the sign-in block after load.
import Base from '../layouts/Base.astro';
import DiaryIsland from '../islands/DiaryIsland';
import { t } from '../i18n';
import { pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
---
<Base lang={lang} title={d.diaryTitle} path={pagePath('diary', lang)} current="diary" noindex>
  <section class="page-hero">
    <h1 class="display">{d.navDiary}</h1>
  </section>
  <DiaryIsland client:load lang={lang} />
</Base>
```

Create `site/src/pages/diary.astro`:

```astro
---
import DiaryView from '../views/DiaryView.astro';
---
<DiaryView lang="en" />
```

Create `site/src/pages/es/diario.astro`:

```astro
---
import DiaryView from '../../views/DiaryView.astro';
---
<DiaryView lang="es" />
```

In `site/src/styles/global.css`, before `/* Simple card page */` add (the entry's rules come with Task 15, the account's with Task 16 — review M19):

```css
/* Stage 4.4b: the diary (screen 4a) */
.diary { display: flex; flex-direction: column; gap: var(--space-4); padding-top: var(--space-5); max-width: 720px; }
.diary__list, .diary__error { display: flex; flex-direction: column; gap: var(--space-4); }
.diary-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-3); }
.diary-item {
  display: grid; gap: var(--space-1); padding: var(--space-4); border-radius: var(--radius-panel); text-decoration: none;
  background: var(--color-day-surface); color: var(--color-day-text); border: 1px solid var(--color-day-line);
}
.diary-item__meta { font-size: var(--font-size-small); color: var(--color-day-text-muted); }
.diary-item__question { font-weight: 600; }
.diary-item__cards { display: flex; gap: var(--space-1); }
.diary-item__cards img { width: 32px; height: auto; aspect-ratio: var(--card-ratio); border-radius: var(--radius-card); }
.diary-item__cards img.is-reversed { transform: rotate(180deg); }
.diary-item__headline { color: var(--color-day-text-muted); }
.diary-item__marks { display: flex; gap: var(--space-3); align-items: center; font-size: var(--font-size-small); }
.diary-item__outcome { font-weight: 600; color: var(--color-day-text); }
.diary__hidden { margin: 0; font-weight: 600; }
.diary__account { display: inline-flex; align-items: center; min-height: 44px; } /* a touch target (review M16) */
.diary :focus-visible { outline-color: var(--color-day-text); }
```

- [ ] **Step 4: Run the tests and the build**

Run: the Vitest command of Step 2, then the same without files, then the type check, then `deploy/build-site.sh && python3 tools/site/check_dist.py && grep -c 'name="robots"' site/dist/diary.html site/dist/es/diario.html site/dist/index.html`
Expected: PASS — `24 passed` in 3 files; then `280 passed` in 30 files; `- 0 errors`; the build writes `169 page(s)`, `OK: 167 pages` (check_dist learns the new pages in Task 21), and the grep prints `site/dist/diary.html:1`, `site/dist/es/diario.html:1`, `site/dist/index.html:0`.

- [ ] **Step 5: Commit**

```bash
git add site/src/islands/DiaryIsland.tsx site/src/islands/DiaryIsland.test.tsx site/src/components/ui/DiaryList.tsx site/src/components/ui/PlusCard.tsx site/src/components/ui/icons.tsx site/src/lib/diary.ts site/src/lib/diary.test.ts site/src/lib/testing/fakes.ts site/src/layouts/Base.astro site/src/views/DiaryView.astro site/src/pages/diary.astro site/src/pages/es/diario.astro site/src/i18n site/src/styles/global.css
git commit -m "feat(site): stage 4.4b — the diary page and its list, Plus in the diary

/diary and /es/diario (noindex): sign-in off, sign-in block, the claim once after sign-in,
the 10 newest readings as text (a crisis entry without text), the hidden count and the
Plus card with the whole-diary benefit (plus_view place diary). Only 401 sign_in signs
out; the stage cookie's 401 reloads; errors have Try again (review I2, M18).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Site — one diary entry (screen 4b): outcome from the named day, the note, delete

**Files:**
- Create: `site/src/components/ui/DiaryEntry.tsx`, `site/src/lib/timeZone.ts`
- Modify: `site/src/islands/DiaryIsland.tsx` (the `?r=<id>` branch; the sign-in block keeps `r`), `site/src/i18n/en.ts`, `es.ts`, `i18n.test.ts`, `site/src/styles/global.css` (the entry's rules, moved here from Task 14 — review M19)
- Test: `site/src/components/ui/DiaryEntry.test.tsx`, `site/src/islands/DiaryIsland.test.tsx` (two more tests)

**Interfaces:**
- Consumes: `AccountApi.entry`, `patchEntry`, `deleteEntry`, `DiaryEntry` type, `Outcome` (Task 11); `outcomeOpen`, `outcomeOpensOn`, `afterDays`, `formatDate`, `kindKey`, `noteLeft`, `NOTE_MAX`, `entryParam` (Tasks 13–14); `OUTCOME_KEYS` (Task 14); `answerFromView`, `answerBlocks` (`answer.ts`); `analyticsEvent`, `sendEvent`; `CardFace`, `HelpLine`, `VerdictIcon`.
- Produces: `DiaryEntry` props `{ lang; id; api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'>; onSignedOut(): void; now?: () => Date; tz?: string; navigate?: (url: string) => void; send?: (event: AnalyticsEvent) => void }`. A reading that is not in the account (`in_diary: false`) or `404` shows `errGone`. «Came true / Partly / No» from `outcomeOpensOn` (00:00 local of the named day, owner decision 13), the same day the «Come back on {date}» line names. In every handler (load, mark, note, delete) only `401 {"reason": "sign_in"}` calls `onSignedOut`; a `401` without JSON shows `errStage` with a reload button; other errors their line (review I4). The outcome buttons are disabled while their PATCH runs; `outcome_answered` is sent for an answer given on an empty mark, not again for a change (yes → no) (review M21); the reading's and the follow-ups' `soft_line` are shown (review M21). Signing in from `/diary?r=<id>` comes back to the same entry (`r` kept in the return address; `cleanReturnUrl` keeps it). Dictionary keys: `diaryBack`, `entryOutcomeQuestion`, `entryOutcomeLater` (`{date}`), `entryOutcomeClear`, `noteLabel`, `noteLeft` (`{n}`), `noteSave`, `noteSaved`, `entryDelete`, `entryDeleteConfirm`, `entryDeleteYes`, `cancel` (all drafts).

- [ ] **Step 1: Write the failing test**

Create `site/src/components/ui/DiaryEntry.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AccountApi, DiaryEntry as Entry } from '../../lib/accountApi';
import { DAY_MS } from '../../lib/diary';
import { byText, cleanup, click, mount, queryText, settle, submit, typeInto } from '../../lib/testing/dom';
import { DiaryEntry } from './DiaryEntry';

const MADE = new Date(2026, 10, 1, 22, 0).toISOString(); // 1 November 2026, 22:00 on this device's clock (any zone)
const at = (days: number) => () => new Date(new Date(MADE).getTime() + days * DAY_MS);
const ENTRY: Entry = {
  id: 'e1', kind: 'three', topic: 'work', question: 'Will <i>the move</i> go well?', created_at: MADE,
  cards: [{ card_id: 'major-18-moon', position: 'past', reversed: false, name: 'The Moon' },
    { card_id: 'major-19-sun', position: 'present', reversed: false, name: 'The Sun' },
    { card_id: 'major-17-star', position: 'path', reversed: true, name: 'The Star' }],
  verdict: null, soft_line: 'Take it gently.', answer_shown: 'model', status: 'done', retries_left: 0,
  answer: { headline: 'Slow and steady.', card1: 'The Moon asks for patience.', synthesis: 'Step by step.', step: 'Write one list.' },
  followups: [{ n: 1, question: 'And then?', answer: 'Then rest.', soft_line: 'One day at a time.' }],
  followups_left: 1, followup_attempts_left: 7, in_diary: true, outcome: null, note: null,
};

function fakeApi(entry: Entry | null, status = 404) {
  const calls: Array<[string, unknown]> = [];
  const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
    entry: async (id) => {
      calls.push(['entry', id]);
      return entry ? { ok: true, status: 200, data: entry } : { ok: false, status, error: status === 404 ? 'gone' : 'other', body: null };
    },
    patchEntry: async (id, patch) => {
      calls.push(['patch', patch]);
      return { ok: true, status: 200, data: { id, outcome: patch.outcome ?? null, note: patch.note ?? null } };
    },
    deleteEntry: async (id) => {
      calls.push(['delete', id]);
      return { ok: true, status: 204, data: null };
    },
  };
  return { api, calls };
}

function entry(f: ReturnType<typeof fakeApi>, now: () => Date, extra: { navigate?: (url: string) => void; send?: () => void } = {}) {
  return <DiaryEntry lang="en" id="e1" api={f.api} onSignedOut={vi.fn()} now={now} navigate={extra.navigate} send={extra.send ?? vi.fn()} />;
}

afterEach(() => cleanup());

describe('a diary entry (screen 4b; spec 4.4b §5)', () => {
  it('shows the cards, the answer by sections and the follow-ups, all as text', async () => {
    const { root } = await mount(entry(fakeApi(ENTRY), at(3)));
    expect(root.querySelector('h2')?.textContent).toBe('Will <i>the move</i> go well?');
    expect(root.querySelector('h2 i')).toBeNull();
    expect(root.textContent).toContain('1 November 2026 · Three cards');
    for (const text of ['Slow and steady.', 'Take it gently.', 'The Moon asks for patience.', 'Step by step.', 'Write one list.',
      'Then rest.', 'One day at a time.']) { // the soft lines too (review M21)
      expect(root.textContent).toContain(text);
    }
    expect(root.querySelectorAll('.entry__cards .card-frame')).toHaveLength(3);
  });

  it('before 7 days: the day to come back, no outcome buttons (owner decision 6)', async () => {
    const { root } = await mount(entry(fakeApi(ENTRY), at(3)));
    expect(byText(root, 'Come back on 8 November 2026 to mark whether it came true.')).toBeTruthy();
    expect(queryText(root, 'Came true', 'button')).toBeNull();
  });

  it('opens on the named day from 00:00 local time, before 7 × 24 hours (owner decision 13, review I7)', async () => {
    const eve = await mount(entry(fakeApi(ENTRY), () => new Date(2026, 10, 7, 23, 59)));
    expect(byText(eve.root, 'Come back on 8 November 2026 to mark whether it came true.')).toBeTruthy();
    eve.unmount();
    const { root } = await mount(entry(fakeApi(ENTRY), () => new Date(2026, 10, 8, 9, 0))); // 8 November, 09:00
    expect(byText(root, 'Came true', 'button')).toBeTruthy();
    expect(queryText(root, 'Come back on 8 November 2026 to mark whether it came true.')).toBeNull();
  });

  it('from 7 days: Came true / Partly / No, change and clear; outcome_answered once, for the first answer', async () => {
    const f = fakeApi(ENTRY);
    const send = vi.fn();
    const { root, unmount } = await mount(entry(f, at(8), { send }));
    await click(byText(root, 'Partly', 'button'));
    expect(byText(root, 'Partly', 'button').getAttribute('aria-pressed')).toBe('true');
    await click(byText(root, 'No', 'button')); // a change, not a new answer (review M21)
    await click(byText(root, 'Clear', 'button'));
    expect(f.calls.filter(([name]) => name === 'patch')).toEqual([['patch', { outcome: 'partly' }], ['patch', { outcome: 'no' }],
      ['patch', { outcome: null }]]);
    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith({ name: 'outcome_answered', tool: null, lang: 'en', params: { after_days: 7, answer: 'partly' } });
    unmount();
    const late = vi.fn();
    const again = await mount(entry(fakeApi(ENTRY), at(40), { send: late }));
    await click(byText(again.root, 'No', 'button'));
    expect(late).toHaveBeenCalledWith({ name: 'outcome_answered', tool: null, lang: 'en', params: { after_days: 30, answer: 'no' } });
  });

  it('the note: 1000 characters at most, a counter, "Save note"', async () => {
    const f = fakeApi(ENTRY);
    const { root } = await mount(entry(f, at(3)));
    const note = root.querySelector<HTMLTextAreaElement>('textarea')!;
    expect(note.maxLength).toBe(1000);
    await typeInto(note, 'Talked to her on Friday.');
    expect(root.textContent).toContain('976 characters left');
    await submit(note.closest('form')!);
    expect(f.calls.at(-1)).toEqual(['patch', { note: 'Talked to her on Friday.' }]);
    expect(byText(root, 'Note saved.')).toBeTruthy();
  });

  it('delete asks first; Cancel keeps it, Delete removes it and goes back to the diary', async () => {
    const f = fakeApi(ENTRY);
    const navigate = vi.fn();
    const { root } = await mount(entry(f, at(3), { navigate }));
    await click(byText(root, 'Delete this entry', 'button'));
    expect(byText(root, 'Delete this reading from your diary? This cannot be undone.')).toBeTruthy();
    await click(byText(root, 'Cancel', 'button'));
    expect(document.activeElement?.textContent).toBe('Delete this entry');
    await click(byText(root, 'Delete this entry', 'button'));
    await click(byText(root, 'Delete', 'button'));
    expect(f.calls.at(-1)).toEqual(['delete', 'e1']);
    expect(navigate).toHaveBeenCalledWith('/diary');
  });

  it('a missing entry is "no longer available"; a crisis entry shows only its date and the help line', async () => {
    const gone = await mount(entry(fakeApi(null), at(3)));
    expect(byText(gone.root, 'This reading is no longer available.')).toBeTruthy();
    gone.unmount();
    const crisis = { ...ENTRY, answer_shown: 'crisis' as const, question: null, answer: null, followups: [] };
    const { root } = await mount(entry(fakeApi(crisis), at(8)));
    expect(root.querySelector('h2')?.textContent).toBe('1 November 2026');
    expect(byText(root, 'Free, confidential help lines', 'a')).toBeTruthy();
    expect(root.querySelector('textarea')).toBeNull();
    expect(queryText(root, 'Came true', 'button')).toBeNull();
  });

  it('a refused change: 401 "sign_in" signs out here, a 401 without JSON is the stage line (review I4)', async () => {
    const onSignedOut = vi.fn();
    const answers = [{ ok: false as const, status: 401, error: 'other' as const, body: { reason: 'sign_in' } },
      { ok: false as const, status: 401, error: 'stage' as const, body: null }];
    const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
      ...fakeApi(ENTRY).api, patchEntry: async () => answers.shift()!,
    };
    const { root } = await mount(<DiaryEntry lang="en" id="e1" api={api} onSignedOut={onSignedOut} now={at(8)} send={vi.fn()} />);
    await click(byText(root, 'Partly', 'button'));
    expect(onSignedOut).toHaveBeenCalledTimes(1);
    await click(byText(root, 'Partly', 'button'));
    expect(onSignedOut).toHaveBeenCalledTimes(1);
    expect(byText(root, 'Your session on this preview site has expired. Reload the page to continue.')).toBeTruthy();
    expect(byText(root, 'Try again', 'button')).toBeTruthy(); // it reloads the page
    expect(queryText(root, 'Something went wrong. Please try again.')).toBeNull();
  });

  it('the outcome buttons wait while their change is saved (review M21)', async () => {
    const pending: { resolve?: () => void } = {};
    const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
      ...fakeApi(ENTRY).api,
      patchEntry: (id, patch) => new Promise((resolve) => {
        pending.resolve = () => resolve({ ok: true, status: 200, data: { id, outcome: patch.outcome ?? null, note: null } });
      }),
    };
    const { root } = await mount(<DiaryEntry lang="en" id="e1" api={api} onSignedOut={vi.fn()} now={at(8)} send={vi.fn()} />);
    await click(byText(root, 'Came true', 'button'));
    expect(byText<HTMLButtonElement>(root, 'No', 'button').disabled).toBe(true);
    await act(() => {
      pending.resolve?.();
    });
    await settle();
    expect(byText<HTMLButtonElement>(root, 'No', 'button').disabled).toBe(false);
    expect(byText(root, 'Came true', 'button').getAttribute('aria-pressed')).toBe('true');
  });
});
```

In `site/src/islands/DiaryIsland.test.tsx` (Task 14), inside `describe(…)`, after the last test add:

```tsx
  it('?r=<id> opens that entry of the account (screen 4b)', async () => {
    history.replaceState(null, '', `/diary?r=${ITEM.id}`);
    h.session = { access_token: 'tok-a' };
    serve({ [`GET /api/readings/${ITEM.id}`]: () => jsonResponse(200, {
      id: ITEM.id, kind: 'three', topic: 'work', question: 'Will the move go well?', created_at: ITEM.created_at,
      cards: ITEM.cards, verdict: null, soft_line: null, answer_shown: 'model', status: 'done', retries_left: 0,
      answer: { headline: 'Slow and steady.' }, followups: [], followups_left: 2, followup_attempts_left: 8,
      in_diary: true, outcome: null, note: null,
    }) });
    const { root } = await open((r) => expect(r.querySelector('h2')?.textContent).toBe('Will the move go well?'));
    expect(byText<HTMLAnchorElement>(root, '← Your diary', 'a').getAttribute('href')).toBe('/diary');
  });

  it('signing in from an entry\'s address comes back to that entry (review M21)', async () => {
    history.replaceState(null, '', `/diary?r=${ITEM.id}`);
    serve({});
    const { root } = await open((r) => expect(r.querySelector('input[type="email"]')).not.toBeNull());
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    await waitFor(() => expect(h.sent).toHaveLength(1));
    expect(h.sent[0]).toMatchObject({ options: { emailRedirectTo: `https://arcana.test/diary?r=${ITEM.id}` } });
  });
```

and replace `import { byText, cleanup, click, mount, settle, waitFor } from '../lib/testing/dom';` with `import { byText, cleanup, click, mount, settle, submit, typeInto, waitFor } from '../lib/testing/dom';`.

In `site/src/i18n/i18n.test.ts` replace `.toBe(192);` with `.toBe(204);`, `expect(DRAFTS.en.length).toBe(76);` with `expect(DRAFTS.en.length).toBe(88);` and `expect(DRAFTS.es.length).toBe(146);` with `expect(DRAFTS.es.length).toBe(158);`.

- [ ] **Step 2: Run it to see it fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/components/ui/DiaryEntry.test.tsx src/islands/DiaryIsland.test.tsx src/i18n/i18n.test.ts`
Expected: FAIL — `Failed to resolve import "./DiaryEntry"`; DiaryIsland: the two new tests (the list instead of the entry; the return address without `r`); `expected 192 to be 204`.

- [ ] **Step 3: Implement**

In `site/src/i18n/en.ts`, after the line `  plusDiaryNote: 'Your diary keeps your last 10 readings. Plus keeps all of them.',` add:

```ts
  // stage 4.4b: a diary entry (screen 4b)
  diaryBack: '← Your diary',
  entryOutcomeQuestion: 'Did it come true?',
  entryOutcomeLater: 'Come back on {date} to mark whether it came true.',
  entryOutcomeClear: 'Clear',
  noteLabel: 'Your note — only you see it',
  noteLeft: '{n} characters left',
  noteSave: 'Save note',
  noteSaved: 'Note saved.',
  entryDelete: 'Delete this entry',
  entryDeleteConfirm: 'Delete this reading from your diary? This cannot be undone.',
  entryDeleteYes: 'Delete',
  cancel: 'Cancel',
```

and in `enDrafts`, after the line `  'diaryHidden', 'diaryNoteMark', 'diaryAccountLink',` add:

```ts
  'diaryBack', 'entryOutcomeQuestion', 'entryOutcomeLater', 'entryOutcomeClear', 'noteLabel', 'noteLeft', 'noteSave',
  'noteSaved', 'entryDelete', 'entryDeleteConfirm', 'entryDeleteYes', 'cancel',
```

In `site/src/i18n/es.ts`, after the line `  plusDiaryNote: 'Tu diario guarda tus últimas 10 tiradas. Plus las guarda todas.',` add:

```ts
  // etapa 4.4b: una entrada del diario (pantalla 4b)
  diaryBack: '← Tu diario',
  entryOutcomeQuestion: '¿Se cumplió?',
  entryOutcomeLater: 'Vuelve el {date} para marcar si se cumplió.',
  entryOutcomeClear: 'Quitar',
  noteLabel: 'Tu nota — solo tú la ves',
  noteLeft: 'Quedan {n} caracteres',
  noteSave: 'Guardar nota',
  noteSaved: 'Nota guardada.',
  entryDelete: 'Borrar esta entrada',
  entryDeleteConfirm: '¿Borrar esta tirada de tu diario? No se puede deshacer.',
  entryDeleteYes: 'Borrar',
  cancel: 'Cancelar',
```

and in `esDrafts`, after the line `  'plusDiaryNote',` add:

```ts
  'diaryBack', 'entryOutcomeQuestion', 'entryOutcomeLater', 'entryOutcomeClear', 'noteLabel', 'noteLeft', 'noteSave',
  'noteSaved', 'entryDelete', 'entryDeleteConfirm', 'entryDeleteYes', 'cancel',
```

Create `site/src/components/ui/DiaryEntry.tsx`:

```tsx
// One diary entry (screen 4b; spec 4.4b §5) — /diary?r=<id>, GET /api/readings/{id}: the cards, the answer by
// sections, the follow-ups; "Came true / Partly / No" from 7 days after the reading (change or clear it), before
// that the day to come back; a private note (1000 characters, counter, "Save note"); delete with a confirmation.
// A crisis entry shows only its date, the help line and "delete". Every text from the API is a text node. Only
// 401 "sign_in" means the session went (review I4): a 401 without JSON is the stage cookie — reload the page.
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t } from '../../i18n';
import type { AccountApi, DiaryEntry as Entry, Outcome } from '../../lib/accountApi';
import { analyticsEvent, sendEvent, type AnalyticsEvent } from '../../lib/analytics';
import { answerBlocks, answerFromView } from '../../lib/answer';
import { NOTE_MAX, afterDays, formatDate, kindKey, noteLeft, outcomeOpen, outcomeOpensOn } from '../../lib/diary';
import type { ApiResult } from '../../lib/api';
import { errorMessageKey, reasonOf, type ErrorKind } from '../../lib/errors';
import { pagePath } from '../../lib/routes';
import type { Lang } from '../../lib/types';
import { CardFace } from './CardFace';
import { OUTCOME_KEYS } from './DiaryList';
import { HelpLine } from './HelpLine';
import { VerdictIcon } from './icons';

const OUTCOMES: readonly Outcome[] = ['yes', 'partly', 'no'];

type Refusal = Extract<ApiResult<unknown>, { ok: false }>;

/** 401 {"reason": "sign_in"}: the session went on this device (spec 4.4b §3). */
function sessionGone(result: Refusal): boolean {
  return result.status === 401 && reasonOf(result.body) === 'sign_in';
}

interface Props {
  lang: Lang;
  id: string;
  api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'>;
  onSignedOut: () => void;
  now?: () => Date;
  tz?: string;
  navigate?: (url: string) => void;
  send?: (event: AnalyticsEvent) => void;
}

export function DiaryEntry({ lang, id, api, onSignedOut, now = () => new Date(), tz, navigate = (url) => location.assign(url),
  send = sendEvent }: Props) {
  const d = t(lang);
  const [entry, setEntry] = useState<Entry | null>(null);
  const [error, setError] = useState<ErrorKind | null>(null); // the entry could not be read
  const [failed, setFailed] = useState<ErrorKind | null>(null); // a change could not be saved
  const [note, setNote] = useState('');
  const [noteState, setNoteState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false); // an outcome is being saved: its buttons wait (review M21)
  const deleteButton = useRef<HTMLButtonElement>(null);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const wasConfirming = useRef(false);
  const diary = pagePath('diary', lang);

  useEffect(() => {
    void (async () => {
      const result = await api.entry(id, tz);
      if (result.ok && result.data.in_diary) {
        setEntry(result.data);
        setNote(result.data.note ?? '');
      } else if (!result.ok && sessionGone(result)) onSignedOut();
      else setError(result.ok ? 'gone' : result.error); // a reading of this device that is not in the account
    })();
  }, [id]);

  useEffect(() => { // the pressed button disappears: focus goes to the one that took its place
    if (confirming) confirmButton.current?.focus();
    else if (wasConfirming.current) deleteButton.current?.focus();
    wasConfirming.current = confirming;
  }, [confirming]);

  if (error) {
    return (
      <div class="entry">
        <a class="entry__back" href={diary}>{d.diaryBack}</a>
        <p role="alert">{d[errorMessageKey(error)]}</p>
        {error === 'stage' ? <button type="button" class="btn btn--outline" onClick={() => location.reload()}>{d.retry}</button> : null}
      </div>
    );
  }
  if (!entry) return <p class="small" role="status" aria-live="polite" />;

  const crisis = entry.answer_shown === 'crisis';
  const answer = answerFromView(entry);
  const headline = answer.sections.headline?.trim();

  const refused = (result: Refusal) => {
    if (sessionGone(result)) onSignedOut();
    else setFailed(result.error); // 'stage' for a 401 without JSON: the line and a reload button
  };

  const mark = async (outcome: Outcome | null) => {
    setBusy(true);
    const result = await api.patchEntry(id, { outcome });
    setBusy(false);
    if (!result.ok) return refused(result);
    setFailed(null);
    const first = entry.outcome === null; // an answer on an empty mark; a change (yes → no) is not counted again
    setEntry({ ...entry, outcome: result.data.outcome });
    if (outcome && first) {
      send(analyticsEvent('outcome_answered', null, lang, { after_days: afterDays(entry.created_at, now()), answer: outcome }));
    }
  };

  const saveNote = async (event: Event) => {
    event.preventDefault();
    setNoteState('saving');
    const result = await api.patchEntry(id, { note: note.trim() ? note : null });
    if (!result.ok) {
      setNoteState('idle');
      return refused(result);
    }
    setFailed(null);
    setNoteState('saved');
  };

  const remove = async () => {
    const result = await api.deleteEntry(id);
    if (!result.ok) return refused(result);
    navigate(diary);
  };

  return (
    <article class="entry" aria-labelledby="entry-title">
      <a class="entry__back" href={diary}>{d.diaryBack}</a>
      <p class="eyebrow">{formatDate(entry.created_at, lang)} · {d[kindKey(entry.kind, entry.topic)]}</p>
      <h2 id="entry-title" class="h2">{crisis ? formatDate(entry.created_at, lang) : entry.question ?? d.diaryNoQuestion}</h2>
      {crisis ? <HelpLine lang={lang} /> : (
        <>
          <div class="entry__cards">
            {entry.cards.map((card) => (
              <CardFace cardId={card.card_id} name={card.name} reversed={card.reversed} lang={lang} sizes="120px" />
            ))}
          </div>
          {headline ? <p class="entry__headline">{headline}</p> : null}
          {entry.soft_line ? <p class="answer__soft">{entry.soft_line}</p> : null}
          {entry.verdict ? (
            <p class="entry__verdict"><VerdictIcon value={entry.verdict.value} size={28} />{entry.verdict.label}</p>
          ) : null}
          {answerBlocks(answer, entry.cards).map((block, i) => {
            if (block.kind === 'headline') return null;
            const label = block.kind === 'card' ? block.card.name : block.kind === 'step' ? d.stepLabel : block.kind === 'why' ? d.whyPrefix : null;
            return (
              <div key={i}>
                {label ? <span class="answer__label">{label}</span> : null}
                <p class="answer__text">{block.text}</p>
              </div>
            );
          })}
          {entry.followups.map((f) => (
            <div key={f.n}>
              <p class="followup__q">{d.followupYouAsked}: {f.question}</p>
              {f.soft_line ? <p class="answer__soft">{f.soft_line}</p> : null}
              <p class="answer__text">{f.answer}</p>
            </div>
          ))}
          <section class="entry__outcome" aria-labelledby="outcome-title">
            <h3 id="outcome-title">{d.entryOutcomeQuestion}</h3>
            {outcomeOpen(entry.created_at, now()) ? (
              <div class="chips" role="group" aria-labelledby="outcome-title">
                {OUTCOMES.map((value) => (
                  <button type="button" class="chip chip--day" aria-pressed={entry.outcome === value} disabled={busy}
                    onClick={() => void mark(value)}>
                    {d[OUTCOME_KEYS[value]]}
                  </button>
                ))}
                {entry.outcome ? (
                  <button type="button" class="btn btn--text" disabled={busy} onClick={() => void mark(null)}>{d.entryOutcomeClear}</button>
                ) : null}
              </div>
            ) : (
              <p class="small">{fill(d.entryOutcomeLater, { date: formatDate(outcomeOpensOn(entry.created_at), lang) })}</p>
            )}
          </section>
          <form class="field entry__note" onSubmit={saveNote}>
            <label for="entry-note">{d.noteLabel}</label>
            <textarea id="entry-note" class="input input--day" rows={4} maxLength={NOTE_MAX} value={note}
              onInput={(e) => { setNote((e.target as HTMLTextAreaElement).value); setNoteState('idle'); }} />
            <p class="small" aria-live="polite">{fill(d.noteLeft, { n: noteLeft(note) })}</p>
            <button type="submit" class="btn btn--ink" disabled={noteState === 'saving'}>{d.noteSave}</button>
            {noteState === 'saved' ? <p class="small" role="status">{d.noteSaved}</p> : null}
          </form>
        </>
      )}
      {failed ? <p role="alert">{d[errorMessageKey(failed)]}</p> : null}
      {failed === 'stage' ? <button type="button" class="btn btn--outline" onClick={() => location.reload()}>{d.retry}</button> : null}
      {confirming ? (
        <div class="notice notice--day" role="alert">
          <p>{d.entryDeleteConfirm}</p>
          <div class="plus__row">
            <button type="button" class="btn btn--ink" ref={confirmButton} onClick={() => void remove()}>{d.entryDeleteYes}</button>
            <button type="button" class="btn btn--text" onClick={() => setConfirming(false)}>{d.cancel}</button>
          </div>
        </div>
      ) : (
        <button type="button" class="btn btn--text" ref={deleteButton} onClick={() => setConfirming(true)}>{d.entryDelete}</button>
      )}
    </article>
  );
}
```

Create `site/src/lib/timeZone.ts` (one helper for the diary and the account pages, not a third and fourth copy of the 4.4a islands' private one — review M22):

```ts
// The device's time zone for the API's `tz` (the local day of the limits and of the account page).
export function deviceTimeZone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}
```

In `site/src/islands/DiaryIsland.tsx`:

- replace the header comment's last two lines

```tsx
// signs in right here, owner decision 3); signed in — once, the claim after sign-in (claim.ts), then the list. Nothing
// here runs at build time.
```

with

```tsx
// signs in right here, owner decision 3); signed in — once, the claim after sign-in (claim.ts), then the list or,
// with ?r=<id>, one entry. Nothing here runs at build time.
```

- after `import { finishSignIn, linkFailed, readReturnParams, returnUrl } from '../lib/claim';` add `import { entryParam } from '../lib/diary';`
- after `import type { Lang } from '../lib/types';` add `import { DiaryEntry } from '../components/ui/DiaryEntry';`
- replace `  | { type: 'ready' };` with `  | { type: 'ready'; entry: string | null };`
- after `import { entryParam } from '../lib/diary';` add `import { deviceTimeZone } from '../lib/timeZone';`

- replace `    else setView({ type: 'ready' });` with `    else setView({ type: 'ready', entry: entryParam(location.search) });`
- replace `          redirectTo={async () => returnUrl(location.origin, lang, keep)} />` with

```tsx
          redirectTo={async () => {
            const back = new URL(returnUrl(location.origin, lang, keep)); // an entry's address comes back to it (M21)
            const entry = entryParam(location.search);
            if (entry) back.searchParams.set('r', entry);
            return back.toString();
          }} />
```

- replace `      <DiaryList lang={lang} api={api} onSignedOut={() => void signedOut()} />` with

```tsx
      {view.entry ? (
        <DiaryEntry lang={lang} id={view.entry} api={api} tz={deviceTimeZone()} onSignedOut={() => void signedOut()} />
      ) : (
        <DiaryList lang={lang} api={api} onSignedOut={() => void signedOut()} />
      )}
```

In `site/src/styles/global.css`, before `/* Simple card page */` add:

```css
/* Stage 4.4b: a diary entry (screen 4b) */
.entry { display: flex; flex-direction: column; gap: var(--space-4); padding-top: var(--space-5); max-width: 720px; }
.entry__back { min-height: 44px; display: inline-flex; align-items: center; }
.entry__cards { display: flex; flex-wrap: wrap; gap: var(--space-3); }
.entry__cards .card-frame { width: 120px; }
.entry__headline { margin: 0; font-family: var(--font-display); font-size: var(--font-size-h-2); }
.entry__verdict { display: flex; align-items: center; gap: var(--space-3); margin: 0; font-weight: 600; }
.entry .answer__label { color: var(--color-day-accent); }
.entry .answer__soft, .entry .followup__q { color: var(--color-day-text-muted); }
.entry__outcome h3 { margin: 0 0 var(--space-2); font-size: var(--font-size-h-3); }
.chip--day { border-color: var(--color-day-control-border); background: transparent; color: var(--color-day-text); }
.chip--day[aria-pressed='true'] { background: var(--color-brand-ink-button); color: var(--color-day-on-accent); }
.entry .field label { color: var(--color-day-text-muted); } /* the night label colour is ≈1.8:1 on day (review I6) */
.entry__note textarea { resize: vertical; min-height: 120px; padding: var(--space-3) var(--space-4); font: inherit; }
.entry :focus-visible { outline-color: var(--color-day-text); }
```

- [ ] **Step 4: Run the tests and the build**

Run: the Vitest command of Step 2, then the same without files, then the type check, then `deploy/build-site.sh && python3 tools/site/check_dist.py`
Expected: PASS — `28 passed` in 3 files; then `291 passed` in 31 files; `- 0 errors`; `OK: 167 pages`.

- [ ] **Step 5: Commit**

```bash
git add site/src/components/ui/DiaryEntry.tsx site/src/components/ui/DiaryEntry.test.tsx site/src/lib/timeZone.ts site/src/islands/DiaryIsland.tsx site/src/islands/DiaryIsland.test.tsx site/src/i18n site/src/styles/global.css
git commit -m "feat(site): stage 4.4b — a diary entry: outcome after 7 days, the note, delete

?r=<id> opens the reading of the account: cards, answer, follow-ups as text; Came true /
Partly / No from 00:00 local of the named day (owner decision 13; outcome_answered once,
after_days 7 or 30), else that day to come back; the note with its counter; delete with a
confirmation. 401 sign_in signs out, the stage 401 reloads (review I4).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: Site — the account page, "Delete forever?", the home page notice

**Files:**
- Create: `site/src/islands/AccountIsland.tsx`, `site/src/components/ui/DeleteAccountDialog.tsx`, `site/src/islands/HomeNotice.tsx`, `site/src/lib/notice.ts`, `site/src/lib/download.ts`, `site/src/views/AccountView.astro`, `site/src/pages/account.astro`, `site/src/pages/es/cuenta.astro`
- Modify: `site/src/views/HomeView.astro` (the notice island), `site/src/i18n/en.ts`, `es.ts`, `i18n.test.ts`, `site/src/styles/global.css` (the account's and the dialog's rules, moved here from Task 14 — review M19)
- Test: `site/src/lib/notice.test.ts`, `site/src/lib/download.test.ts`, `site/src/islands/AccountIsland.test.tsx`, `site/src/islands/HomeNotice.test.tsx`

**Interfaces:**
- Consumes: `openSession`, `Auth`, `SessionStatus` (Task 9), `createAccountApi`, `Account`, `AccountApi` (Task 11), `siteFetch` (Task 10), `returnUrl` (Task 12), `SignInBlock` (Task 13), `handleDialogKey` (`focus.ts`), `pagePath('account' | 'diary' | 'home')`, `noindex` of `Base.astro` (Task 14), `navDiary`, `diarySignInSoon` (Task 14).
- Produces:
  - `download.ts`: `type SaveFile = (blob: Blob, filename: string) => void`, `REVOKE_AFTER_MS = 60_000`, `saveFile` (Task 17 uses it for the calendar file). The object URL is freed a minute after the click, not a second: iOS Safari asks before it saves a blob and may read the URL late (review I8).
  - `notice.ts`: `type Notice = 'accountDeleted'`, `NOTICE_PARAM = 'account'`, `NOTICE_KEY = 'ad_notice'`, `noticeHref(home): string` (`<home>?account=deleted`), `noticeOf(search): Notice | null`, `markNotice(notice, storage?)` (sessionStorage), `takeNotice(search, storage?): Notice | null` (the address's notice only when this browser left the mark; the mark goes — a shared link alone shows nothing, review M22), `withoutNotice(href): string`.
  - `AccountIsland` props `{ lang; api?: AccountApi; save?: SaveFile; navigate?: (url) => void; session?: () => Promise<SessionStatus>; signOutWaitMs?: number }` (the page passes only `lang`); `SIGN_OUT_WAIT_MS = 3000` — a sign-out that hangs never holds the person on the page (auth-js 2.119 drops the local session before its network call, and `Auth.signOut` clears the flags first — Task 9, review M6). Only `401 {"reason": "sign_in"}` shows the sign-in block; a `401` without JSON is `errStage` with a reload button.
  - `DeleteAccountDialog` props `{ lang; busy; error: string | null; onDownload(); onDelete(); onCancel() }` (`role="alertdialog"`, Escape = Cancel). A failed deletion or download says so **inside** the dialog (review I5); while `busy`, Escape does nothing and the three buttons are disabled (review M22).
  - `HomeNotice` props `{ lang }`.
  - Pages `/account`, `/es/cuenta` (noindex). Dictionary keys `accountTitle`, `accountH1`, `accountEmail` (`{email}`), `accountLeft` (`{n}`, `{limit}`), `accountSignOut`, `accountConsent`, `accountConsentNote`, `accountExport`, `accountDelete`, `deleteTitle`, `deleteBody`, `deleteDownload`, `deleteForever`, `accountDeleted` (all drafts). `deviceTimeZone()` (Task 15) for `GET /api/account?tz=`.

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/notice.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { NOTICE_KEY, markNotice, noticeHref, noticeOf, takeNotice, withoutNotice } from './notice';
import { memoryStorage } from './testing/auth';

describe('the home page notice', () => {
  it('says "account deleted" once and leaves a clean address', () => {
    expect(noticeHref('/es')).toBe('/es?account=deleted');
    expect(noticeOf('?account=deleted')).toBe('accountDeleted');
    expect(noticeOf('?account=other')).toBeNull();
    expect(withoutNotice('https://arcana.test/es?account=deleted&utm_source=x')).toBe('/es?utm_source=x');
  });

  it("shows the line only after this browser's own deletion, and only once (review M22)", () => {
    const storage = memoryStorage();
    expect(takeNotice('?account=deleted', storage)).toBeNull(); // a shared link alone
    markNotice('accountDeleted', storage);
    expect(storage.data[NOTICE_KEY]).toBe('accountDeleted');
    expect(takeNotice('', storage)).toBeNull(); // the mark goes with any visit of the home page
    markNotice('accountDeleted', storage);
    expect(takeNotice('?account=deleted', storage)).toBe('accountDeleted');
    expect(takeNotice('?account=deleted', storage)).toBeNull(); // once
  });
});
```

Create `site/src/lib/download.test.ts`:

```ts
// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { REVOKE_AFTER_MS, saveFile } from './download';

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('saveFile (the export of spec 4.3 §8, the calendar file of spec 4.4b §7)', () => {
  it('clicks a download link with the name, removes it, and frees the address only after a minute (review I8)', () => {
    vi.useFakeTimers({ toFake: ['setTimeout'] });
    const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:https://arcana.test/1');
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const clicked: Array<[string, string]> = [];
    const onClick = (event: MouseEvent) => {
      const link = event.target as HTMLAnchorElement;
      clicked.push([link.getAttribute('href') ?? '', link.download]);
      event.preventDefault(); // no navigation in the test
    };
    document.addEventListener('click', onClick);
    const blob = new Blob(['x'], { type: 'text/calendar;charset=utf-8' });
    saveFile(blob, 'arcana-diary-card-of-the-day.ics');
    document.removeEventListener('click', onClick);
    expect(create).toHaveBeenCalledWith(blob);
    expect(clicked).toEqual([['blob:https://arcana.test/1', 'arcana-diary-card-of-the-day.ics']]);
    expect(document.querySelector('a[download]')).toBeNull();
    vi.advanceTimersByTime(REVOKE_AFTER_MS - 1);
    expect(revoke).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(revoke).toHaveBeenCalledWith('blob:https://arcana.test/1');
  });
});
```

Create `site/src/islands/AccountIsland.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Account, AccountApi } from '../lib/accountApi';
import type { Auth, SessionStatus } from '../lib/auth';
import { NOTICE_KEY } from '../lib/notice';
import { byText, cleanup, click, mount, waitFor } from '../lib/testing/dom';
import AccountIsland from './AccountIsland';

const ACCOUNT: Account = { email: 'ana@example.com', created_at: '2026-11-20T18:00:00+00:00', reminders_consent: false,
  consent_at: null, limit: 3, used: 1, remaining: 2, day: '2026-11-22' };

function fakes(over: { deleteAccount?: AccountApi['deleteAccount']; signOut?: () => Promise<void> } = {}) {
  const calls: string[] = [];
  const saved: Array<[Blob, string]> = [];
  const navigate = vi.fn();
  const auth = {
    session: async () => null, token: async () => 'tok', refresh: async () => null,
    sendLink: async () => ({ ok: true as const }), google: async () => ({ ok: true as const }),
    signOut: vi.fn(over.signOut ?? (async () => { calls.push('signOut'); })),
  } satisfies Auth;
  const api = {
    account: async () => { calls.push('account'); return { ok: true, status: 200, data: ACCOUNT }; },
    setConsent: async (on: boolean) => {
      calls.push(`consent ${on}`);
      return { ok: true, status: 200, data: { email: ACCOUNT.email, reminders_consent: on, consent_at: null } };
    },
    exportFile: async () => {
      calls.push('export');
      return { ok: true, blob: new Blob(['{"readings":[]}'], { type: 'application/json' }), filename: 'arcana-diary-2026-11-22.json' };
    },
    deleteAccount: over.deleteAccount
      ?? (async () => { calls.push('delete'); return { ok: true, status: 200, data: { deleted: true } }; }),
  } as unknown as AccountApi;
  const signedIn = async (): Promise<SessionStatus> => ({ type: 'signedIn', auth, google: false, session: { access_token: 'tok' } });
  const props = { api, navigate, save: (blob: Blob, name: string) => { saved.push([blob, name]); }, session: signedIn,
    signOutWaitMs: 20 };
  return { calls, saved, navigate, auth, props };
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

describe('the account page (spec 4.4b §6)', () => {
  it('shows the e-mail, the readings left today and the way back to the diary', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    expect(byText(root, 'Signed in as ana@example.com')).toBeTruthy();
    expect(byText(root, 'Readings left today: 2 of 3')).toBeTruthy();
    expect(byText<HTMLAnchorElement>(root, 'Your diary', 'a').getAttribute('href')).toBe('/diary');
  });

  it('the consent switch says the e-mails start later and saves the choice', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    const box = root.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    expect(box.checked).toBe(false);
    expect(root.textContent).toContain('These e-mails start later. You can turn them off here at any time.');
    await click(box);
    expect(f.calls).toContain('consent true');
    expect(root.querySelector<HTMLInputElement>('input[type="checkbox"]')!.checked).toBe(true);
  });

  it('downloads all readings as a file', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Download my readings', 'button'));
    expect(f.saved.map(([, name]) => name)).toEqual(['arcana-diary-2026-11-22.json']);
    expect(await f.saved[0][0].text()).toBe('{"readings":[]}');
  });

  it('"Delete account" opens "Delete forever?" with Download and Cancel; Cancel gives focus back', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    const dialog = root.querySelector('[role="alertdialog"]')!;
    expect(document.activeElement?.textContent).toBe('Delete forever?');
    expect(dialog.textContent).toContain('This cannot be undone.');
    await click(byText(dialog, 'Download', 'button'));
    expect(f.calls).toContain('export');
    await click(byText(dialog, 'Cancel', 'button'));
    expect(root.querySelector('[role="alertdialog"]')).toBeNull();
    expect(document.activeElement?.textContent).toBe('Delete account');
    expect(f.calls).not.toContain('delete');
  });

  it('"Delete forever" deletes, signs out on this device at once and goes home with the notice', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="es" {...f.props} />);
    await click(byText(root, 'Eliminar cuenta', 'button'));
    await click(byText(root, 'Eliminar para siempre', 'button'));
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/es?account=deleted'));
    expect(f.calls.slice(-2)).toEqual(['delete', 'signOut']);
    expect(sessionStorage.getItem(NOTICE_KEY)).toBe('accountDeleted'); // the home page says it once (review M22)
  });

  it('"Sign out" goes home; not signed in shows the sign-in block', async () => {
    const f = fakes();
    const { root, unmount } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Sign out', 'button'));
    expect(f.calls).toContain('signOut');
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/'));
    unmount();
    const out = await mount(<AccountIsland lang="en" {...f.props}
      session={async () => ({ type: 'signedOut', auth: f.auth, google: false })} />);
    expect(out.root.querySelector('input[type="email"]')).not.toBeNull();
  });

  it('a deletion that fails says so inside the dialog; nothing is signed out (review I5)', async () => {
    const f = fakes({ deleteAccount: async () => ({ ok: false, status: 503, error: 'unavailable', body: { reason: 'db' } }) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    await click(byText(root, 'Delete forever', 'button'));
    const dialog = root.querySelector('[role="alertdialog"]')!;
    expect(dialog.querySelector('[role="alert"]')?.textContent)
      .toBe('The service is unavailable right now. Please try again in a few minutes.');
    expect(f.auth.signOut).not.toHaveBeenCalled();
    expect(f.navigate).not.toHaveBeenCalled();
    expect(byText<HTMLButtonElement>(dialog, 'Delete forever', 'button').disabled).toBe(false);
  });

  it('a sign-out that hangs does not hold the person here: home after a short wait (review M6)', async () => {
    const f = fakes({ signOut: () => new Promise<void>(() => {}) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Sign out', 'button'));
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/'));
  });

  it('while the account is being deleted, Escape and Cancel do nothing (review M22)', async () => {
    const pending: { finish?: () => void } = {};
    const f = fakes({ deleteAccount: () => new Promise((resolve) => {
      pending.finish = () => resolve({ ok: true, status: 200, data: { deleted: true } });
    }) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    await click(byText(root, 'Delete forever', 'button'));
    await act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(root.querySelector('[role="alertdialog"]')).not.toBeNull();
    expect(byText<HTMLButtonElement>(root, 'Cancel', 'button').disabled).toBe(true);
    await act(() => {
      pending.finish?.();
    });
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/?account=deleted'));
  });
});
```

Create `site/src/islands/HomeNotice.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest';
import { NOTICE_KEY } from '../lib/notice';
import { byText, cleanup, mount } from '../lib/testing/dom';
import HomeNotice from './HomeNotice';

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

describe('the home page notice (spec 4.4b §6)', () => {
  it('says once that the account was deleted and cleans the address', async () => {
    sessionStorage.setItem(NOTICE_KEY, 'accountDeleted'); // left by the account page right before it came here
    history.replaceState(null, '', '/es?account=deleted&utm_source=x');
    const { root } = await mount(<HomeNotice lang="es" />);
    expect(byText(root, 'Tu cuenta se eliminó.').getAttribute('role')).toBe('status');
    expect(`${location.pathname}${location.search}`).toBe('/es?utm_source=x');
    expect(sessionStorage.getItem(NOTICE_KEY)).toBeNull();
  });

  it('a link with ?account=deleted alone says nothing, and the address is cleaned (review M22)', async () => {
    history.replaceState(null, '', '/?account=deleted');
    const { root } = await mount(<HomeNotice lang="en" />);
    expect(root.textContent).toBe('');
    expect(`${location.pathname}${location.search}`).toBe('/');
  });
});
```

In `site/src/i18n/i18n.test.ts` replace `.toBe(204);` with `.toBe(218);`, `expect(DRAFTS.en.length).toBe(88);` with `expect(DRAFTS.en.length).toBe(102);` and `expect(DRAFTS.es.length).toBe(158);` with `expect(DRAFTS.es.length).toBe(172);`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/notice.test.ts src/lib/download.test.ts src/islands/AccountIsland.test.tsx src/islands/HomeNotice.test.tsx src/i18n/i18n.test.ts`
Expected: FAIL — `Failed to resolve import "./notice"`, `"./download"`, `"./AccountIsland"`, `"./HomeNotice"`; `expected 204 to be 218`.

- [ ] **Step 3: Implement**

In `site/src/i18n/en.ts`, after the line `  cancel: 'Cancel',` add:

```ts
  // stage 4.4b: the account page
  accountTitle: 'Your account — Arcana Diary',
  accountH1: 'Your account',
  accountEmail: 'Signed in as {email}',
  accountLeft: 'Readings left today: {n} of {limit}',
  accountSignOut: 'Sign out',
  accountConsent: 'E-mail me 7 and 30 days after a reading: did it come true?',
  accountConsentNote: 'These e-mails start later. You can turn them off here at any time.',
  accountExport: 'Download my readings',
  accountDelete: 'Delete account',
  deleteTitle: 'Delete forever?',
  deleteBody: 'Your account and every reading, note and "did it come true?" answer are deleted at once. This cannot be undone. You can download your readings first.',
  deleteDownload: 'Download',
  deleteForever: 'Delete forever',
  accountDeleted: 'Your account has been deleted.',
```

and in `enDrafts`, after the line `  'noteSaved', 'entryDelete', 'entryDeleteConfirm', 'entryDeleteYes', 'cancel',` add:

```ts
  'accountTitle', 'accountH1', 'accountEmail', 'accountLeft', 'accountSignOut', 'accountConsent', 'accountConsentNote',
  'accountExport', 'accountDelete', 'deleteTitle', 'deleteBody', 'deleteDownload', 'deleteForever', 'accountDeleted',
```

In `site/src/i18n/es.ts`, after the line `  cancel: 'Cancelar',` add:

```ts
  // etapa 4.4b: la cuenta
  accountTitle: 'Tu cuenta — Arcana Diary',
  accountH1: 'Tu cuenta',
  accountEmail: 'Sesión iniciada como {email}',
  accountLeft: 'Tiradas que te quedan hoy: {n} de {limit}',
  accountSignOut: 'Cerrar sesión',
  accountConsent: 'Escríbeme 7 y 30 días después de una tirada: ¿se cumplió?',
  accountConsentNote: 'Estos correos empezarán más adelante. Puedes desactivarlos aquí cuando quieras.',
  accountExport: 'Descargar mis tiradas',
  accountDelete: 'Eliminar cuenta',
  deleteTitle: '¿Eliminar para siempre?',
  deleteBody: 'Tu cuenta y cada tirada, nota y respuesta a «¿se cumplió?» se eliminan de inmediato. No se puede deshacer. Puedes descargar tus tiradas antes.',
  deleteDownload: 'Descargar',
  deleteForever: 'Eliminar para siempre',
  accountDeleted: 'Tu cuenta se eliminó.',
```

and in `esDrafts`, after the line `  'noteSaved', 'entryDelete', 'entryDeleteConfirm', 'entryDeleteYes', 'cancel',` add:

```ts
  'accountTitle', 'accountH1', 'accountEmail', 'accountLeft', 'accountSignOut', 'accountConsent', 'accountConsentNote',
  'accountExport', 'accountDelete', 'deleteTitle', 'deleteBody', 'deleteDownload', 'deleteForever', 'accountDeleted',
```

Create `site/src/lib/notice.ts`:

```ts
// A one-time line on the home page after an action that left another page (spec 4.4b §6: "account deleted"). The
// address names the line; a mark in sessionStorage, left by the account page right before it goes, says that this
// browser really did it — a shared link with ?account=deleted alone shows nothing (review M22).
import type { StorageLike } from './authState';

export type Notice = 'accountDeleted';

export const NOTICE_PARAM = 'account';
export const NOTICE_KEY = 'ad_notice';

function sessionStore(): StorageLike | null {
  try {
    return typeof sessionStorage === 'undefined' ? null : sessionStorage;
  } catch {
    return null;
  }
}

export function noticeHref(home: string): string {
  return `${home}?${NOTICE_PARAM}=deleted`;
}

export function noticeOf(search: string): Notice | null {
  return new URLSearchParams(search).get(NOTICE_PARAM) === 'deleted' ? 'accountDeleted' : null;
}

export function markNotice(notice: Notice, storage: StorageLike | null = sessionStore()): void {
  try {
    storage?.setItem(NOTICE_KEY, notice);
  } catch {
    // without a storage the home page simply shows no line
  }
}

/** The address's notice, once, only when this browser left the mark; the mark goes in any case. */
export function takeNotice(search: string, storage: StorageLike | null = sessionStore()): Notice | null {
  const asked = noticeOf(search);
  try {
    const mine = storage?.getItem(NOTICE_KEY) ?? null;
    storage?.removeItem(NOTICE_KEY);
    return asked !== null && mine === asked ? asked : null;
  } catch {
    return null;
  }
}

/** The same address without the notice, for history.replaceState. */
export function withoutNotice(href: string): string {
  const url = new URL(href);
  url.searchParams.delete(NOTICE_PARAM);
  return `${url.pathname}${url.search}${url.hash}`;
}
```

Create `site/src/lib/download.ts`:

```ts
// A file saved from the browser (the export of spec 4.3 §8, the calendar file of spec 4.4b §7): an object URL and a
// download link, removed right after. The URL is freed only after a minute: iOS Safari asks before it saves a blob
// and may read the URL late (Fable plan review I8).
export type SaveFile = (blob: Blob, filename: string) => void;

export const REVOKE_AFTER_MS = 60_000;

export const saveFile: SaveFile = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), REVOKE_AFTER_MS);
};
```

Create `site/src/components/ui/DeleteAccountDialog.tsx`:

```tsx
// "Delete forever?" (owner decision 4, spec 4.4b §6): what goes and that it cannot be undone; "Download", "Delete
// forever", "Cancel" — no word to type. A modal dialog: focus inside, Escape and "Cancel" close it — not while the
// account is being deleted (review M22). A failed deletion or download is said here, above the buttons (review I5).
import { useEffect, useRef } from 'preact/hooks';
import { t } from '../../i18n';
import { handleDialogKey } from '../../lib/focus';
import type { Lang } from '../../lib/types';

interface Props {
  lang: Lang;
  busy: boolean;
  error: string | null; // the line of a failed deletion or download, shown inside the dialog
  onDownload: () => void;
  onDelete: () => void;
  onCancel: () => void;
}

export function DeleteAccountDialog({ lang, busy, error, onDownload, onDelete, onCancel }: Props) {
  const d = t(lang);
  const box = useRef<HTMLDivElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const cancel = useRef(onCancel);
  cancel.current = busy ? () => {} : onCancel; // Escape waits for the deletion too

  useEffect(() => {
    title.current?.focus();
    const onKey = (event: KeyboardEvent) => box.current && handleDialogKey(event, box.current, () => cancel.current());
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div class="dialog-layer">
      <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title" aria-describedby="delete-body" ref={box}>
        <h2 id="delete-title" class="h2" tabIndex={-1} ref={title}>{d.deleteTitle}</h2>
        <p id="delete-body">{d.deleteBody}</p>
        {error ? <p role="alert">{error}</p> : null}
        <div class="dialog__actions">
          <button type="button" class="btn btn--outline" disabled={busy} onClick={onDownload}>{d.deleteDownload}</button>
          <button type="button" class="btn btn--ink" disabled={busy} onClick={onDelete}>{d.deleteForever}</button>
          <button type="button" class="btn btn--text" disabled={busy} onClick={onCancel}>{d.cancel}</button>
        </div>
      </div>
    </div>
  );
}
```

Create `site/src/islands/AccountIsland.tsx`:

```tsx
// The account page (spec 4.4b §6) on /account and /es/cuenta: not signed in — the sign-in block; signed in — the
// e-mail, readings left today, "Sign out"; the consent to "did it come true?" e-mails (they start later); "Download
// my readings"; "Delete account" with the "Delete forever?" dialog. After the deletion this device signs out at once
// (api/README.md "Передача в 4.4") and goes to the home page, which says the account is deleted — once, by a mark
// this page leaves in sessionStorage (review M22). A sign-out that hangs never holds the person here: after
// SIGN_OUT_WAIT_MS the page goes on (auth-js drops the local session before its request — review M6).
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { fill, t } from '../i18n';
import { createAccountApi, type Account, type AccountApi } from '../lib/accountApi';
import { openSession, type Auth, type SessionStatus } from '../lib/auth';
import { returnUrl } from '../lib/claim';
import { saveFile, type SaveFile } from '../lib/download';
import { errorMessageKey, reasonOf, type ErrorKind } from '../lib/errors';
import { markNotice, noticeHref } from '../lib/notice';
import { pagePath } from '../lib/routes';
import { siteFetch } from '../lib/siteApi';
import { deviceTimeZone } from '../lib/timeZone';
import type { Lang } from '../lib/types';
import { DeleteAccountDialog } from '../components/ui/DeleteAccountDialog';
import { HelpLine } from '../components/ui/HelpLine';
import { SignInBlock } from '../components/ui/SignInBlock';

export const SIGN_OUT_WAIT_MS = 3000;

interface Props {
  lang: Lang;
  /** Tests pass their own; the page uses the real ones. */
  api?: AccountApi;
  save?: SaveFile;
  navigate?: (url: string) => void;
  session?: () => Promise<SessionStatus>;
  signOutWaitMs?: number;
}

export default function AccountIsland({ lang, api: given, save = saveFile, navigate = (url) => location.assign(url),
  session = openSession, signOutWaitMs = SIGN_OUT_WAIT_MS }: Props) {
  const d = t(lang);
  const api = useMemo(() => given ?? createAccountApi(siteFetch()), []);
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState<ErrorKind | null>(null);
  const [dialog, setDialog] = useState(false);
  const [busy, setBusy] = useState(false);
  const deleteButton = useRef<HTMLButtonElement>(null);
  const hadDialog = useRef(false);

  const load = async () => {
    const opened = await session();
    setStatus(opened);
    if (opened.type !== 'signedIn') return;
    const result = await api.account(deviceTimeZone());
    if (result.ok) setAccount(result.data);
    else if (result.status === 401 && reasonOf(result.body) === 'sign_in') {
      setStatus({ type: 'signedOut', auth: opened.auth, google: opened.google });
    } else setError(result.error); // 'stage' for a 401 without JSON: the line and a reload button
  };

  useEffect(() => { void load(); }, []);
  useEffect(() => {
    if (hadDialog.current && !dialog) deleteButton.current?.focus();
    hadDialog.current = dialog;
  }, [dialog]);

  if (!status || (status.type === 'signedIn' && !account && !error)) return <p class="small" role="status" aria-live="polite" />;
  if (status.type === 'off') return <p class="lead">{d.diarySignInSoon}</p>;
  if (status.type === 'unreachable') {
    return <div class="account"><p role="alert">{d.errUnavailable}</p><HelpLine lang={lang} /></div>;
  }
  if (status.type === 'signedOut') {
    return (
      <div class="account">
        <SignInBlock lang={lang} auth={status.auth} google={status.google} idBase="account" surface="day"
          redirectTo={async () => returnUrl(location.origin, lang)} />
      </div>
    );
  }

  const auth: Auth = status.auth;
  const home = pagePath('home', lang);

  const toggle = async (on: boolean) => {
    const result = await api.setConsent(on);
    if (result.ok && account) setAccount({ ...account, reminders_consent: result.data.reminders_consent });
    else if (!result.ok) setError(result.error);
  };

  const download = async () => {
    const file = await api.exportFile();
    if (file.ok) save(file.blob, file.filename);
    else setError(file.error);
  };

  const leave = async (url: string) => { // sign out on this device at once, then go; a hung sign-out waits at most
    await Promise.race([auth.signOut(), new Promise<void>((resolve) => setTimeout(resolve, signOutWaitMs))]);
    navigate(url);
  };

  const signOut = () => leave(home);

  const remove = async () => {
    setBusy(true);
    setError(null);
    const result = await api.deleteAccount();
    if (!result.ok) {
      setBusy(false);
      setError(result.error); // said inside the dialog (review I5)
      return;
    }
    markNotice('accountDeleted');
    await leave(noticeHref(home)); // at once: the token still lives until it expires
  };

  return (
    <div class="account">
      {account ? (
        <>
          <p>{fill(d.accountEmail, { email: account.email ?? '' })}</p>
          <p>{fill(d.accountLeft, { n: account.remaining, limit: account.limit })}</p>
          <label class="check check--day">
            <input type="checkbox" checked={account.reminders_consent}
              onChange={(e) => void toggle((e.target as HTMLInputElement).checked)} />
            <span>{d.accountConsent}</span>
          </label>
          <p class="small muted">{d.accountConsentNote}</p>
        </>
      ) : null}
      {error && !dialog ? <p role="alert">{d[errorMessageKey(error)]}</p> : null}
      {error === 'stage' && !dialog ? (
        <button type="button" class="btn btn--outline" onClick={() => location.reload()}>{d.retry}</button>
      ) : null}
      <div class="account__actions">
        <button type="button" class="btn btn--outline" onClick={() => void download()}>{d.accountExport}</button>
        <a class="btn btn--outline" href={pagePath('diary', lang)}>{d.navDiary}</a>
        <button type="button" class="btn btn--ink" onClick={() => void signOut()}>{d.accountSignOut}</button>
        <button type="button" class="btn btn--text" ref={deleteButton} onClick={() => setDialog(true)}>{d.accountDelete}</button>
      </div>
      {dialog ? (
        <DeleteAccountDialog lang={lang} busy={busy} error={error ? d[errorMessageKey(error)] : null}
          onDownload={() => void download()} onDelete={() => void remove()}
          onCancel={() => { setDialog(false); setError(null); }} />
      ) : null}
    </div>
  );
}
```

Create `site/src/islands/HomeNotice.tsx`:

```tsx
// A one-time line on the home page (spec 4.4b §6): "Your account has been deleted." after the account page sent
// the person here — only with the mark that page left in sessionStorage (review M22); the address loses its
// ?account=deleted at once in any case.
import { useEffect, useState } from 'preact/hooks';
import { t } from '../i18n';
import { noticeOf, takeNotice, withoutNotice } from '../lib/notice';
import type { Lang } from '../lib/types';

export default function HomeNotice({ lang }: { lang: Lang }) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!noticeOf(location.search)) return;
    setShown(takeNotice(location.search) !== null);
    history.replaceState(history.state, '', withoutNotice(location.href));
  }, []);
  return shown ? <p class="notice notice--day" role="status">{t(lang).accountDeleted}</p> : null;
}
```

Create `site/src/views/AccountView.astro`:

```astro
---
// The account (spec 4.4b §6): a static page, noindex and outside hreflang; AccountIsland draws it after load.
import Base from '../layouts/Base.astro';
import AccountIsland from '../islands/AccountIsland';
import { t } from '../i18n';
import { pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
---
<Base lang={lang} title={d.accountTitle} path={pagePath('account', lang)} noindex>
  <section class="page-hero">
    <h1 class="display">{d.accountH1}</h1>
  </section>
  <AccountIsland client:load lang={lang} />
</Base>
```

Create `site/src/pages/account.astro`:

```astro
---
import AccountView from '../views/AccountView.astro';
---
<AccountView lang="en" />
```

Create `site/src/pages/es/cuenta.astro`:

```astro
---
import AccountView from '../../views/AccountView.astro';
---
<AccountView lang="es" />
```

In `site/src/views/HomeView.astro`:

- replace `// and is the one-card page at #una-carta. Hub links and diary steps wait for stages 6 and 4.4b.` with

```
// and is the one-card page at #una-carta. Hub links wait for stage 6. Stage 4.4b: step 3 is about the diary; a line
// after the account was deleted (HomeNotice).
```

- replace `import ReadingIsland from '../islands/ReadingIsland';` with

```
import HomeNotice from '../islands/HomeNotice';
import ReadingIsland from '../islands/ReadingIsland';
```

- replace

```
<Base lang={lang} title={d.homeTitle} path={pagePath('home', lang)} current="home">
  <div class="tool-layout">
```

with

```
<Base lang={lang} title={d.homeTitle} path={pagePath('home', lang)} current="home">
  <HomeNotice client:load lang={lang} />
  <div class="tool-layout">
```

In `site/src/styles/global.css`, before `/* Simple card page */` add:

```css
/* Stage 4.4b: the account page and "Delete forever?" */
.account { display: flex; flex-direction: column; gap: var(--space-4); padding-top: var(--space-5); max-width: 720px; }
.account__actions { display: flex; flex-wrap: wrap; gap: var(--space-3); }
.check--day input { accent-color: var(--color-day-accent); }
.dialog-layer {
  position: fixed; inset: 0; z-index: 30; display: flex; align-items: center; justify-content: center; padding: var(--space-4);
  background: color-mix(in srgb, var(--color-day-text) 40%, transparent);
}
.dialog {
  width: 100%; max-width: 480px; display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-5);
  border-radius: var(--radius-panel); background: var(--color-day-surface); color: var(--color-day-text);
}
.dialog p { margin: 0; }
.dialog__actions { display: flex; flex-wrap: wrap; gap: var(--space-3); }
.dialog :focus-visible, .account :focus-visible { outline-color: var(--color-day-text); }
```

- [ ] **Step 4: Run the tests and the build**

Run: the Vitest command of Step 2, then the same without files, then the type check, then `deploy/build-site.sh && python3 tools/site/check_dist.py && grep -c 'name="robots"' site/dist/account.html site/dist/es/cuenta.html`
Expected: PASS — `23 passed` in 5 files; then `305 passed` in 35 files; `- 0 errors`; the build writes `171 page(s)`, `OK: 167 pages`, the grep prints `:1` for both pages.

- [ ] **Step 5: Commit**

```bash
git add site/src/islands/AccountIsland.tsx site/src/islands/AccountIsland.test.tsx site/src/islands/HomeNotice.tsx site/src/islands/HomeNotice.test.tsx site/src/components/ui/DeleteAccountDialog.tsx site/src/lib/notice.ts site/src/lib/notice.test.ts site/src/lib/download.ts site/src/lib/download.test.ts site/src/views/AccountView.astro site/src/views/HomeView.astro site/src/pages/account.astro site/src/pages/es/cuenta.astro site/src/i18n site/src/styles/global.css
git commit -m "feat(site): stage 4.4b — the account page and Delete forever?

/account and /es/cuenta (noindex): e-mail, readings left today, sign-out, consent to the
did-it-come-true e-mails (they start later), download, delete with Download / Delete
forever / Cancel; after deleting, sign-out here at once (never held by a hung sign-out) and
the home page says so once. Errors show inside the dialog (review I5, M6, M22).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: Site — "Remind me tomorrow" under the Card of the Day (a calendar file)

**Files:**
- Create: `site/src/lib/ics.ts`
- Modify: `site/src/islands/DailyIsland.tsx`, `site/src/i18n/en.ts`, `es.ts`, `i18n.test.ts`, `site/src/styles/global.css` (the outline button on the night surface of the card, review M12)
- Test: `site/src/lib/ics.test.ts`, `site/src/islands/DailyIsland.test.tsx`

**Interfaces:**
- Consumes: `saveFile`, `SaveFile` (Task 16), `analyticsEvent('remind_click', 'daily', lang)` (Task 12; the API accepts it from Task 4), `pagePath('daily', lang)`, `routeFetch` (Task 14).
- Produces: `ics.ts`: `ICS_FILENAME = 'arcana-diary-card-of-the-day.ics'`, `ICS_TYPE = 'text/calendar;charset=utf-8'` (without the charset some Android and Outlook readers break «—» and «í», review M11), `tomorrowAtNine(now: Date): Date` (local), `icsTime(date, utc): string`, `icsText(text): string` (RFC 5545: `\\`, `\;`, `\,`, `\n` — review M10), `dailyReminderIcs({ now, lang, origin }): string` (CRLF lines, no `METHOD`, one `VEVENT` with `UID:daily-<YYYYMMDD of the event>@arcanadiary.com` — two presses the same day give one event, review M11 —, `DTSTART` floating local 09:00 tomorrow, `DURATION:PT15M`, `SUMMARY` per language, `URL` and `DESCRIPTION` = the Card of the Day page, and a `VALARM` with `ACTION:DISPLAY`, `TRIGGER:PT0M`, `DESCRIPTION` = the title — owner decision 11). `DailyIsland` props `{ lang; save?: SaveFile }`. Dictionary keys `remindTomorrow` (prototype 7b in EN), `remindDone` (draft).
- Known risk (review I8): the page cannot tell whether the phone saved or opened the file. iOS Safari asks before it saves a blob (hence `REVOKE_AFTER_MS`, Task 16); the in-app browsers of Instagram, Facebook and TikTok often ignore blob downloads while the page still says «Open the file to add it to your calendar.». The walk-through (item 11) checks a real iPhone Safari and Android Chrome; an in-app browser is a known limit of the closed stage (`navigator.share` with the file is not added: it needs a second, different flow per platform).

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/ics.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { dailyReminderIcs, icsText, icsTime, tomorrowAtNine } from './ics';

// the device's own clock: 22 November 2026, 23:40 local time
const NOW = new Date(2026, 10, 22, 23, 40, 5);
const ORIGIN = 'https://arcana.test';

describe('the Card of the Day reminder', () => {
  it('is tomorrow at 9:00 local time, also late at night and at the end of a month', () => {
    expect(icsTime(tomorrowAtNine(NOW), false)).toBe('20261123T090000');
    expect(icsTime(tomorrowAtNine(new Date(2026, 11, 31, 8, 0)), false)).toBe('20270101T090000');
  });

  it('is one 15-minute event with the title and link of the page language', () => {
    const text = dailyReminderIcs({ now: NOW, lang: 'es', origin: ORIGIN });
    const lines = text.split('\r\n');
    expect(text.endsWith('\r\n')).toBe(true);
    expect(lines.filter((l) => l === 'BEGIN:VEVENT')).toHaveLength(1);
    expect(lines).toContain('DTSTART:20261123T090000');
    expect(lines).toContain('DURATION:PT15M');
    expect(lines).toContain('SUMMARY:Carta del día — Arcana Diary');
    expect(lines).toContain('URL:https://arcana.test/es/carta-del-dia');
    expect(lines).toContain('UID:daily-20261123@arcanadiary.com');
    expect(lines.some((l) => l.startsWith('METHOD:'))).toBe(false); // a file to add, not an invitation (review M11)
    expect(lines.find((l) => l.startsWith('DTSTAMP:'))).toMatch(/^DTSTAMP:\d{8}T\d{6}Z$/);
    for (const line of lines) expect(new TextEncoder().encode(line).length).toBeLessThanOrEqual(75);
  });

  it('rings at the start: a display alarm at 9:00 (owner decision 11)', () => {
    const lines = dailyReminderIcs({ now: NOW, lang: 'en', origin: ORIGIN }).split('\r\n');
    const alarm = lines.slice(lines.indexOf('BEGIN:VALARM'), lines.indexOf('END:VALARM') + 1);
    expect(alarm).toEqual(['BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:Card of the Day — Arcana Diary', 'TRIGGER:PT0M',
      'END:VALARM']);
    expect(lines.indexOf('BEGIN:VALARM')).toBeGreaterThan(lines.indexOf('BEGIN:VEVENT'));
    expect(lines.indexOf('END:VALARM')).toBeLessThan(lines.indexOf('END:VEVENT'));
  });

  it('pressed twice the same day it is the same event; the next day another (review M11)', () => {
    const uid = (now: Date) => dailyReminderIcs({ now, lang: 'en', origin: ORIGIN }).split('\r\n').find((l) => l.startsWith('UID:'));
    expect(uid(new Date(2026, 10, 22, 8, 0))).toBe(uid(NOW));
    expect(uid(new Date(2026, 10, 23, 8, 0))).toBe('UID:daily-20261124@arcanadiary.com');
  });

  it('in English links /daily', () => {
    const text = dailyReminderIcs({ now: NOW, lang: 'en', origin: ORIGIN });
    expect(text).toContain('SUMMARY:Card of the Day — Arcana Diary\r\n');
    expect(text).toContain('URL:https://arcana.test/daily\r\n');
  });

  it('escapes calendar text (RFC 5545 §3.3.11; review M10)', () => {
    expect(icsText('a, b; c\\d\ne')).toBe('a\\, b\\; c\\\\d\\ne');
  });
});
```

Create `site/src/islands/DailyIsland.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../lib/analytics';
import { ICS_FILENAME, ICS_TYPE } from '../lib/ics';
import { byText, cleanup, click, mount } from '../lib/testing/dom';
import { jsonResponse, routeFetch } from '../lib/testing/fakes';
import DailyIsland from './DailyIsland';

vi.mock('../lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../lib/analytics')>()), sendEvent: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('the Card of the Day reminder (screen 7b; spec 4.4b §7)', () => {
  it('saves a calendar file for tomorrow 9:00 with the link, and counts remind_click', async () => {
    const served = routeFetch({ 'GET /api/daily': () => jsonResponse(200, {
      day: '2026-11-22', card: { card_id: 'major-18-moon', name: 'The Moon', reversed: false }, text: 'Rest tonight.', source: 'cache',
    }) });
    vi.stubGlobal('fetch', served.fetch);
    const saved: Array<[Blob, string]> = [];
    const { root } = await mount(<DailyIsland lang="en" save={(blob, name) => { saved.push([blob, name]); }} />);
    await click(byText(root, 'Tap to turn your card', 'span').closest('button')!);
    await click(byText(root, 'Remind me tomorrow', 'button'));
    expect(saved.map(([blob, name]) => [blob.type, name])).toEqual([[ICS_TYPE, ICS_FILENAME]]);
    const text = await saved[0][0].text();
    expect(text).toContain('SUMMARY:Card of the Day — Arcana Diary\r\n');
    expect(text).toContain('BEGIN:VALARM\r\n');
    expect(text).toContain('URL:https://arcana.test/daily\r\n');
    expect(text).toContain('DURATION:PT15M\r\n');
    expect(vi.mocked(sendEvent)).toHaveBeenCalledWith({ name: 'remind_click', tool: 'daily', lang: 'en', params: {} });
    expect(byText(root, 'Open the file to add it to your calendar.')).toBeTruthy();
    expect(served.calls.map((c) => c.url.split('?')[0])).toEqual(['/api/daily']); // no server for the reminder
  });
});
```

In `site/src/i18n/i18n.test.ts` replace `.toBe(218);` with `.toBe(220);`, `expect(DRAFTS.en.length).toBe(102);` with `expect(DRAFTS.en.length).toBe(103);` and `expect(DRAFTS.es.length).toBe(172);` with `expect(DRAFTS.es.length).toBe(174);`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/ics.test.ts src/islands/DailyIsland.test.tsx src/i18n/i18n.test.ts`
Expected: FAIL — `Failed to resolve import "./ics"` (both files); `expected 218 to be 220`.

- [ ] **Step 3: Implement**

In `site/src/i18n/en.ts`, after the line `  accountDeleted: 'Your account has been deleted.',` add:

```ts
  // stage 4.4b: the Card of the Day (screen 7b)
  remindTomorrow: 'Remind me tomorrow',
  remindDone: 'Open the file to add it to your calendar.',
```

and in `enDrafts`, after the line `  'accountExport', 'accountDelete', 'deleteTitle', 'deleteBody', 'deleteDownload', 'deleteForever', 'accountDeleted',` add:

```ts
  'remindDone',
```

In `site/src/i18n/es.ts`, after the line `  accountDeleted: 'Tu cuenta se eliminó.',` add:

```ts
  // etapa 4.4b: la carta del día (pantalla 7b)
  remindTomorrow: 'Recuérdamelo mañana',
  remindDone: 'Abre el archivo para añadirlo a tu calendario.',
```

and in `esDrafts`, after the line `  'accountExport', 'accountDelete', 'deleteTitle', 'deleteBody', 'deleteDownload', 'deleteForever', 'accountDeleted',` add:

```ts
  'remindTomorrow', 'remindDone',
```

Create `site/src/lib/ics.ts`:

```ts
// "Remind me tomorrow" under the Card of the Day (spec 4.4b §7): a calendar file made in the browser — one event
// tomorrow at 9:00 local time (a floating time, so the calendar keeps 9:00 wherever the person is), 15 minutes,
// with the link to the Card of the Day and an alarm at its start (owner decision 11: on an iPhone an event without
// one passes silently). No server, no personal data. The UID names the day: two presses give one event (M11).
import { pagePath } from './routes';
import type { Lang } from './types';

export const ICS_FILENAME = 'arcana-diary-card-of-the-day.ics';
export const ICS_TYPE = 'text/calendar;charset=utf-8';
const TITLES: Record<Lang, string> = { en: 'Card of the Day — Arcana Diary', es: 'Carta del día — Arcana Diary' };

const two = (n: number) => String(n).padStart(2, '0');

/** Tomorrow, 9:00 in the device's time zone. */
export function tomorrowAtNine(now: Date): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9, 0, 0);
}

/** 20261123T090000 (local, floating) or 20261122T103000Z (UTC). */
export function icsTime(date: Date, utc: boolean): string {
  if (utc) {
    return `${date.getUTCFullYear()}${two(date.getUTCMonth() + 1)}${two(date.getUTCDate())}T${two(date.getUTCHours())}${two(date.getUTCMinutes())}${two(date.getUTCSeconds())}Z`;
  }
  return `${date.getFullYear()}${two(date.getMonth() + 1)}${two(date.getDate())}T${two(date.getHours())}${two(date.getMinutes())}${two(date.getSeconds())}`;
}

/** RFC 5545 text: backslash, semicolon, comma and new lines escaped. */
export function icsText(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
}

export function dailyReminderIcs(input: { now: Date; lang: Lang; origin: string }): string {
  const start = tomorrowAtNine(input.now);
  const link = `${input.origin}${pagePath('daily', input.lang)}`;
  const title = icsText(TITLES[input.lang]);
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Arcana Diary//Card of the Day//EN',
    'CALSCALE:GREGORIAN',
    'BEGIN:VEVENT',
    `UID:daily-${icsTime(start, false).slice(0, 8)}@arcanadiary.com`,
    `DTSTAMP:${icsTime(input.now, true)}`,
    `DTSTART:${icsTime(start, false)}`,
    'DURATION:PT15M',
    `SUMMARY:${title}`,
    `DESCRIPTION:${icsText(link)}`,
    `URL:${link}`,
    'BEGIN:VALARM',
    'ACTION:DISPLAY',
    `DESCRIPTION:${title}`,
    'TRIGGER:PT0M',
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ];
  return `${lines.join('\r\n')}\r\n`;
}
```

In `site/src/islands/DailyIsland.tsx`:

- replace `// the card comes from the card base (src/lib/daily.ts). "Remind me tomorrow" and "Save to diary" are stage 4.4b.` with

```tsx
// the card comes from the card base (src/lib/daily.ts). Under the card "Remind me tomorrow" (spec 4.4b §7): a calendar
// file made here, no server. The card of the day is not a reading: it is not saved to the diary (spec 4.4b §2.10).
```

- after `import { CARD_BACK } from '../lib/deck';` add `import { saveFile, type SaveFile } from '../lib/download';`
- replace `import { cardPath } from '../lib/routes';` with

```tsx
import { ICS_FILENAME, ICS_TYPE, dailyReminderIcs } from '../lib/ics';
import { cardPath } from '../lib/routes';
```

- replace

```tsx
export default function DailyIsland({ lang }: { lang: Lang }) {
  const d = t(lang);
  const [view, setView] = useState<View>({ type: 'back' });
```

with

```tsx
export default function DailyIsland({ lang, save = saveFile }: { lang: Lang; save?: SaveFile }) {
  const d = t(lang);
  const [view, setView] = useState<View>({ type: 'back' });
  const [reminded, setReminded] = useState(false);
```

- replace

```tsx
  if (view.type === 'shown') {
    const { shown } = view;
```

with

```tsx
  const remind = () => {
    sendEvent(analyticsEvent('remind_click', 'daily', lang));
    const text = dailyReminderIcs({ now: new Date(), lang, origin: location.origin });
    save(new Blob([text], { type: ICS_TYPE }), ICS_FILENAME);
    setReminded(true);
  };

  if (view.type === 'shown') {
    const { shown } = view;
```

- replace

```tsx
          {fill(d.fullMeaning, { name: shown.name })}
        </a>
      </section>
```

with

```tsx
          {fill(d.fullMeaning, { name: shown.name })}
        </a>
        <button type="button" class="btn btn--outline" onClick={remind}>{d.remindTomorrow}</button>
        <p class="small" role="status">{reminded ? d.remindDone : ''}</p>
      </section>
```

In `site/src/styles/global.css` replace `.night .btn--outline, .night-panel .btn--outline { border-color: var(--color-night-control-border); }` with `.night .btn--outline, .night-panel .btn--outline, .daily .btn--outline { border-color: var(--color-night-control-border); }` (the card of the day is a night surface: the day border would not show — `00-design.md:85`, review M12).

- [ ] **Step 4: Run the tests and the build**

Run: the Vitest command of Step 2, then the same without files, then the type check, then `deploy/build-site.sh && python3 tools/site/check_dist.py`
Expected: PASS — `16 passed` in 3 files; then `312 passed` in 37 files; `- 0 errors`; `OK: 167 pages`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/ics.ts site/src/lib/ics.test.ts site/src/islands/DailyIsland.tsx site/src/islands/DailyIsland.test.tsx site/src/i18n site/src/styles/global.css
git commit -m "feat(site): stage 4.4b — Remind me tomorrow: a calendar file for the Card of the Day

One event tomorrow 9:00 local time, 15 minutes, with the page link and an alarm at its
start (owner decision 11); one UID per day, UTF-8, proper escaping (review M10, M11);
made in the browser, no server, no personal data; remind_click.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 18: Site — the diary in the menu and the header, the deferred 4.4a copy

**Files:**
- Modify: `site/src/lib/routes.ts` (`NAV_KEYS`), `site/src/lib/routes.test.ts`, `site/src/components/Header.astro`, `site/src/islands/ReadingIsland.tsx` (`freeSaveAfter`), `site/src/i18n/en.ts`, `es.ts`, `i18n.test.ts`

**Interfaces:**
- Consumes: `navDiary`, `navDiaryShort` (Task 14), `pagePath('diary', …)` (Task 12).
- Produces: `NAV_KEYS = ['home', 'yes_no', 'love', 'daily', 'diary']`; the phone menu says «Your diary» / «Tu diario», the desktop header «Diary» / «Diario» (screens 11c, 11d, 13a). The key `freeNoSignup` is renamed `freeSaveAfter` («Free · save it to your diary after» / «Gratis · guárdala en tu diario después», prototypes 1, 12a, 13a); `howStep3` becomes «Save it, and check later what came true.» (prototype 1; the Spanish text stays a draft). `plusBenefit3` and `plusDiaryNote` are shown since Task 14.

- [ ] **Step 1: Write the failing tests**

In `site/src/lib/routes.test.ts` replace

```ts
  it('has the four menu items of 4.4a in both languages', () => {
    expect(NAV_KEYS).toEqual(['home', 'yes_no', 'love', 'daily']);
    expect(NAV_KEYS.map((k) => pagePath(k, 'es'))).toEqual(['/es', '/es/si-o-no', '/es/amor', '/es/carta-del-dia']);
  });
```

with

```ts
  it('has the menu items of 4.4b in both languages', () => {
    expect(NAV_KEYS).toEqual(['home', 'yes_no', 'love', 'daily', 'diary']);
    expect(NAV_KEYS.map((k) => pagePath(k, 'es'))).toEqual(['/es', '/es/si-o-no', '/es/amor', '/es/carta-del-dia', '/es/diario']);
  });
```

In `site/src/i18n/i18n.test.ts` replace `expect(DRAFTS.en.length).toBe(103);` with `expect(DRAFTS.en.length).toBe(101);` and `expect(DRAFTS.es.length).toBe(174);` with `expect(DRAFTS.es.length).toBe(173);` (the key count stays 220), and before `  it('name the votes with the card base labels (content/cards/yes-no-rules.json)', () => {` add:

```ts
  it('keep the 4.4b copy of the prototypes and the spec (spec 4.4b §8)', () => {
    expect([t('en').freeSaveAfter, t('es').freeSaveAfter]).toEqual(['Free · save it to your diary after',
      'Gratis · guárdala en tu diario después']);
    expect(t('en').howStep3).toBe('Save it, and check later what came true.');
    expect([t('en').navDiary, t('es').navDiary, t('en').navDiaryShort, t('es').navDiaryShort]).toEqual([
      'Your diary', 'Tu diario', 'Diary', 'Diario']);
    expect([t('en').plusBenefit3, t('es').plusBenefit3]).toEqual(['Your whole diary, with no limit', 'Todo tu diario, sin límite']);
    expect([t('en').plusDiaryNote, t('es').plusDiaryNote]).toEqual(['Your diary keeps your last 10 readings. Plus keeps all of them.',
      'Tu diario guarda tus últimas 10 tiradas. Plus las guarda todas.']);
    expect([t('en').saveToDiary, t('es').saveToDiary, t('en').savedToDiary]).toEqual(['Save to diary', 'Guardar en el diario',
      'Saved to your diary ✓']);
    expect(DRAFTS.en).not.toContain('howStep3');
    expect(DRAFTS.es).toContain('howStep3');
    expect(DRAFTS.es).toContain('plusDiaryNote');
  });

```

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/routes.test.ts src/i18n/i18n.test.ts`
Expected: FAIL — the menu (`expected [ …4 items ] to deeply equal [ …5 items ]`), the drafts counts (`expected 103 to be 101`), the copy (`expected [ undefined, undefined ] to deeply equal …`).

- [ ] **Step 3: Implement**

In `site/src/lib/routes.ts` replace

```ts
/** The menu (stage 2 structure, design screens 11c/11d). "Card Meanings" and the diary arrive with stages 6 and
 * 4.4b; until then the menu has these four items. */
export const NAV_KEYS: readonly PageKey[] = ['home', 'yes_no', 'love', 'daily'];
```

with

```ts
/** The menu (stage 2 structure, design screens 11c/11d, 13a): the diary since 4.4b; "Card Meanings" arrives with
 * stage 6. */
export const NAV_KEYS: readonly PageKey[] = ['home', 'yes_no', 'love', 'daily', 'diary'];
```

In `site/src/components/Header.astro`:

- replace `// on a desktop the menu items and EN | ES sit in the header (screen 13a).` with

```
// on a desktop the menu items and EN | ES sit in the header (screen 13a). The diary: "Your diary" in the menu,
// "Diary" in the desktop header (spec 4.4b §8).
```

- replace

```
const LABELS: Record<string, DictKey> = { home: 'navHome', yes_no: 'navYesNo', love: 'navLove', daily: 'navDaily' };
const items = NAV_KEYS.map((key) => ({ key, href: pagePath(key, lang), label: d[LABELS[key]] }));
```

with

```
const LABELS: Record<string, DictKey> = {
  home: 'navHome', yes_no: 'navYesNo', love: 'navLove', daily: 'navDaily', diary: 'navDiary',
};
const SHORT: Record<string, DictKey> = { diary: 'navDiaryShort' };
const items = NAV_KEYS.map((key) => ({
  key, href: pagePath(key, lang), label: d[LABELS[key]], short: d[SHORT[key] ?? LABELS[key]],
}));
```

- in the desktop `<nav>` (inside `<div class="site-header__desktop">`) replace `{item.label}</a></li>` with `{item.short}</a></li>` (the phone menu `#site-menu` keeps `{item.label}`).

In `site/src/i18n/en.ts` replace `  freeNoSignup: 'Free · no sign-up',` with `  freeSaveAfter: 'Free · save it to your diary after',` and `  howStep3: 'Ask up to two follow-up questions, free.',` with `  howStep3: 'Save it, and check later what came true.',`; in `enDrafts` replace

```ts
  'skipToContent', 'langLabel', 'helpLead', 'helpLink', 'freeNoSignup', 'homeTitle', 'dailyTileText', 'learnLead',
  'howStep3', 'oneCardTitle',
```

with

```ts
  'skipToContent', 'langLabel', 'helpLead', 'helpLink', 'homeTitle', 'dailyTileText', 'learnLead',
  'oneCardTitle',
```

(only those two keys leave the list; the rest of the second line stays).

In `site/src/i18n/es.ts` replace `  freeNoSignup: 'Gratis · sin registro',` with `  freeSaveAfter: 'Gratis · guárdala en tu diario después',` and `  howStep3: 'Haz hasta dos preguntas de seguimiento, gratis.',` with `  howStep3: 'Guárdala y revisa después qué se cumplió.',`; in `esDrafts` replace `  'skipToContent', 'langLabel', 'footerLabel', 'footerOneCard', 'helpLead', 'helpLink', 'freeNoSignup',` with `  'skipToContent', 'langLabel', 'footerLabel', 'footerOneCard', 'helpLead', 'helpLink',`.

In `site/src/islands/ReadingIsland.tsx` replace `<p class="panel-hint">{d.freeNoSignup}</p>` with `<p class="panel-hint">{d.freeSaveAfter}</p>`.

- [ ] **Step 4: Run the tests and the build**

Run: the Vitest command of Step 2, then the same without files, then the type check, then `deploy/build-site.sh && grep -o '>Diary<' site/dist/index.html | head -1 && grep -c '>Your diary<' site/dist/index.html && grep -c 'Free · save it to your diary after' site/dist/index.html`
Expected: PASS — `19 passed` in 2 files; then `313 passed` in 37 files; `- 0 errors`; `>Diary<`, `1`, `1` (`grep -rn freeNoSignup site/src` prints nothing).

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/routes.ts site/src/lib/routes.test.ts site/src/components/Header.astro site/src/islands/ReadingIsland.tsx site/src/i18n
git commit -m "feat(site): stage 4.4b — Your diary in the menu, Diary in the header, deferred copy

Free · save it to your diary after; step 3 about the diary (4.4a spec §11 return list).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 19: Site — "Try again" on a follow-up lost more than an hour ago only reads back (GET)

**Files:**
- Modify: `site/src/lib/readingFlow.ts` (`FlowDeps.now`, `LOST_REPOST_MAX_MS`, `restoreFollowup`, `retryFollowup`), `site/src/lib/nightRoom.ts` (`followupLost` keeps the first loss time), `site/src/lib/followups.ts` (`Followup.lost.at`), `site/src/islands/ReadingIsland.tsx` (`now` in `deps()`)
- Test: `site/src/lib/readingFlow.test.ts`

**Interfaces:**
- Consumes: the 4.5 "Try again" flow (`retryFollowup(deps, id, tz, lost)` re-POSTs the lost body with the same `request_id`).
- Produces: `FlowDeps.now?: () => number` (ms, `Date.now` by default); `LOST_REPOST_MAX_MS = 3_600_000`; `NightAction` `followupLost` carries `at?: number`; `Followup.lost.at?: number` — the time of the **first** loss (kept when "Try again" loses it again). `retryFollowup` sends no POST when `now() − lost.at > LOST_REPOST_MAX_MS`: only the GET read-back (`restoreFollowup`). Why (4.5 final review, Minor 2): after the hourly cleanup a day-old crisis tombstone is gone and a repeat with the same number would be a fresh, possibly paid, ask.

- [ ] **Step 1: Write the failing tests**

In `site/src/lib/readingFlow.test.ts` replace `  DEFAULT_COUNTS, REPEAT_WAIT_MS, RESTORE_TRIES, askFollowup,` with `  DEFAULT_COUNTS, LOST_REPOST_MAX_MS, REPEAT_WAIT_MS, RESTORE_TRIES, askFollowup,`, and before `  it('Try again answered 402 plus leaves followupPlus, 429 attempts leaves the refusal state', async () => {` add:

```ts
  it('Try again more than an hour after the loss only reads back with GET, never re-POSTs (spec 4.4b §9)', async () => {
    const { h, lost } = await lostHarness(...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [] })),
      jsonResponse(200, VIEW));
    expect(lost.lost?.at).toEqual(expect.any(Number));
    h.deps.now = () => lost.lost!.at! + LOST_REPOST_MAX_MS + 1;
    const before = h.calls.length;
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    expect(posts(h)).toHaveLength(2); // the ask and its one A1 re-POST, nothing now
    expect(h.calls.slice(before).every((c) => c.method === 'GET')).toBe(true);
    expect(h.state().followups[0]).toMatchObject({ status: 'failed', lost: { n: 2, answeredBefore: 1 } });
  });

  it('Try again within the hour still re-POSTs the same body', async () => {
    const { h, lost } = await lostHarness(
      sseResponse(sseText([['meta', { followup: 2, replay: true }], ['text', { name: 'followup', text: 'A2' }],
        ['done', { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true }]])));
    h.deps.now = () => lost.lost!.at! + LOST_REPOST_MAX_MS - 1;
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    expect(posts(h)).toHaveLength(3);
    expect(h.state().followups[0]).toMatchObject({ text: 'A2', status: 'done' });
  });

  it('keeps the time of the first loss when Try again loses it again', async () => {
    const { h, lost } = await lostHarness(new TypeError('offline'),
      ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, { ...VIEW, followups: [] })), jsonResponse(200, VIEW));
    const first = lost.lost!.at!;
    expect(first).toEqual(expect.any(Number));
    h.deps.now = () => first + 5000;
    await retryFollowup(h.deps, 'r1', undefined, lost.lost!);
    expect(h.state().followups[0].lost?.at).toBe(first);
  });

```

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/readingFlow.test.ts`
Expected: FAIL — `2 failed` (`expected undefined to equal Any<Number>`: no loss time yet); `Try again within the hour …` passes already — it pins the 4.5 behaviour that must stay.

- [ ] **Step 3: Implement**

In `site/src/lib/readingFlow.ts`:

- replace

```ts
  newId: () => string; // a request number (requestId.ts)
}
```

with

```ts
  newId: () => string; // a request number (requestId.ts)
  now?: () => number; // ms; Date.now by default (the time a follow-up was lost)
}
```

- replace `/** What a new reading allows` with

```ts
/** Spec 4.4b §9: "Try again" on a follow-up lost longer ago than this only reads back (GET): after the hourly
 * cleanup a crisis tombstone may be gone, and a re-POST would then be a fresh (for a paid body: charged) ask. */
export const LOST_REPOST_MAX_MS = 60 * 60 * 1000;
/** What a new reading allows
```

- in `restoreFollowup` replace

```ts
  if (repost && !gone) {
    deps.dispatch({ type: 'followupLost', n, answeredBefore, body }); // clears the partial text, then shows it as streaming again
```

with

```ts
  const at = (deps.now ?? Date.now)();
  if (repost && !gone) {
    deps.dispatch({ type: 'followupLost', n, answeredBefore, body, at }); // clears the partial text, then shows it as streaming again
```

  and replace

```ts
  deps.dispatch({ type: 'followupLost', n, answeredBefore, body });
  await loadCounts(deps, id, tz);
```

  with

```ts
  deps.dispatch({ type: 'followupLost', n, answeredBefore, body, at });
  await loadCounts(deps, id, tz);
```

- replace the comment and the head of `retryFollowup`

```ts
 * read-back, with the same `n` and `answeredBefore`. A follow-up without a number: the GET read-back only. */
export async function retryFollowup(deps: FlowDeps, id: string, tz: string | undefined,
  lost: { n?: number; answeredBefore: number; body?: FollowupBody }): Promise<void> {
  deps.dispatch({ type: 'followupRetrying' });
  const body = lost.body;
  let n = lost.n;
  if (body?.request_id) {
```

  with

```ts
 * read-back, with the same `n` and `answeredBefore`. A follow-up without a number, or one lost more than
 * LOST_REPOST_MAX_MS ago (spec 4.4b §9): the GET read-back only. */
export async function retryFollowup(deps: FlowDeps, id: string, tz: string | undefined,
  lost: { n?: number; answeredBefore: number; body?: FollowupBody; at?: number }): Promise<void> {
  deps.dispatch({ type: 'followupRetrying' });
  const body = lost.body;
  let n = lost.n;
  const stale = lost.at !== undefined && (deps.now ?? Date.now)() - lost.at > LOST_REPOST_MAX_MS;
  if (body?.request_id && !stale) {
```

In `site/src/lib/nightRoom.ts` replace `  | { type: 'followupLost'; n?: number; answeredBefore: number; body?: FollowupBody }` with `  | { type: 'followupLost'; n?: number; answeredBefore: number; body?: FollowupBody; at?: number }` and

```ts
        ? { ...f, status: 'failed', text: '', lost: { n: action.n, answeredBefore: action.answeredBefore, body: action.body } } : f));
```

with

```ts
        ? { ...f, status: 'failed', text: '', lost: {
          n: action.n, answeredBefore: action.answeredBefore, body: action.body, at: f.lost?.at ?? action.at, // the first loss
        } } : f));
```

In `site/src/lib/followups.ts` replace `  lost?: { n?: number; answeredBefore: number; body?: FollowupBody };` with `  lost?: { n?: number; answeredBefore: number; body?: FollowupBody; at?: number }; // at: ms of the first loss`.

In `site/src/islands/ReadingIsland.tsx`, in `deps()`, replace `      newId: () => newRequestId(),` with

```tsx
      newId: () => newRequestId(),
      now: () => Date.now(),
```

- [ ] **Step 4: Run the tests**

Run: the Vitest command of Step 2 with `src/lib/nightRoom.test.ts src/lib/followups.test.ts` added, then the same without files, then the type check.
Expected: PASS — `92 passed` in 3 files; then `316 passed` in 37 files; `- 0 errors`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/readingFlow.ts site/src/lib/readingFlow.test.ts site/src/lib/nightRoom.ts site/src/lib/followups.ts site/src/islands/ReadingIsland.tsx
git commit -m "fix(site): stage 4.4b — Try again on a follow-up lost over an hour ago only reads back

After the hourly cleanup a crisis tombstone may be gone; a re-POST with the same number
would then be a fresh, possibly paid, ask (4.5 final review, Minor 2).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 20: Site — a DOM test of the three yes/no votes (and the 360 px check)

**Files:**
- Test: `site/src/components/ui/NightRoom.test.tsx` (one more test)

**Interfaces:**
- Consumes: `NightRoom`, `room()` of the same test file and `shown()` of `site/src/lib/testing/night.ts` (Task 13), the 4.5 vote rendering (`cardVotes`, `.spread__vote`, `VerdictIcon`).
- Produces: nothing new in code. This closes the 4.5 review's "no DOM test" note for the votes (spec §9); the 360 px layout is checked by eye in the walk-through (item 12 below) — happy-dom does no layout.

- [ ] **Step 1: Write the test**

In `site/src/components/ui/NightRoom.test.tsx` replace `import { ONE, shown } from '../../lib/testing/night';` with

```tsx
import { ONE, shown } from '../../lib/testing/night';
import type { ReadingCreated } from '../../lib/types';
```

and inside `describe(…)`, after the last test add:

```tsx
  it('shows each of three yes/no cards with its own vote, icon and word, and the verdict (spec 4.5 §4)', async () => {
    const yesNo: ReadingCreated = {
      id: 'r3', lang: 'en', kind: 'yes_no', soft_line: null, remaining: 1, verdict: { value: 'yes', label: 'Yes' },
      cards: [
        { card_id: 'major-19-sun', position: 'card', reversed: false, name: 'The Sun', vote: 'yes' },
        { card_id: 'major-16-tower', position: 'card', reversed: false, name: 'The Tower', vote: 'no' },
        { card_id: 'major-17-star', position: 'card', reversed: true, name: 'The Star', vote: 'unclear' },
      ],
    };
    const state = shown(yesNo, { headline: 'Leaning yes.', card1: 'Warm.', card2: 'A jolt.', card3: 'Wait.', why: 'Two decide.' });
    const { root } = await mount(room(state, { threeCards: true, config: panelConfig('yes_no', 'en') }));
    const votes = Array.from(root.querySelectorAll('.spread__vote'));
    expect(votes.map((v) => v.textContent)).toEqual(['Yes', 'No', 'Not clear yet']);
    expect(votes.every((v) => v.querySelector('svg[aria-hidden="true"]') !== null)).toBe(true);
    expect(root.querySelector('.verdict__word')?.textContent).toBe('Yes');
    expect(root.textContent).toContain('Why: Two decide.');
    expect(root.querySelectorAll('.spread__pos')).toHaveLength(0); // no past · present · path on yes/no
  });
```

- [ ] **Step 2: Run it**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 npx vitest run src/components/ui/NightRoom.test.tsx`
Expected: PASS — `4 passed` (the behaviour exists since 4.5; this pins it). If it fails, the votes regressed in this stage: stop and report.

- [ ] **Step 3: Run everything**

Run: the same command without a file, then the type check.
Expected: `317 passed` in 37 files; `- 0 errors`.

- [ ] **Step 4: Commit**

```bash
git add site/src/components/ui/NightRoom.test.tsx
git commit -m "test(site): stage 4.4b — DOM test of the three yes/no votes under their cards

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 21: Build and server checks — the four private pages, noindex, no sign-in library on reading pages

**Files:**
- Modify: `tools/site/check_dist.py` (whole file), `tools/site/test_sync_site_data.py` (171 pages), `deploy/Caddyfile` (`@private` header), `deploy/test-site-routes.sh` (new checks), `deploy/check-indexing.sh` (new checks; edited, not run)
- Test: `tools/site/test_check_dist.py` (new)

**Interfaces:**
- Consumes: `site/src/data/pairs.json`; the build of Tasks 14 and 16 (the four pages with `<meta name="robots" content="noindex, nofollow">`); `site/src/lib/supabaseClient.ts` built as its own chunk (Task 9).
- Produces:
  - `check_dist.py`: `PRIVATE`, `READING_PAGES`, `AUTH_MARKERS`, `expected_pages()` (171), `robots_problems(dist)`, `static_chunks(dist, html) -> set[Path]` (islands, renderers and scripts of a page and their static imports; `import("…")` is not followed), `auth_problems(dist)`, `main(dist=None) -> int` printing `OK: 171 pages`.
  - Caddy: `/diary`, `/es/diario`, `/account`, `/es/cuenta` answer with `X-Robots-Tag: noindex, nofollow` also when `LAUNCHED=true`, and with `Referrer-Policy: same-origin` (`/diary?claim=<token>` must not leave the site in a `Referer` — the page loads Google Fonts; modern browsers send only the origin anyway, the header covers old ones; review M8); the strict-address and 404 rules already cover them (`try_files {path} {path}.html`, `/es/…` → Spanish 404).

- [ ] **Step 1: Write the failing tests**

Create `tools/site/test_check_dist.py`:

```python
"""tools/site/check_dist.py on small hand-made builds (spec 4.4b §5, §6, §11): the private pages are noindex and the
sign-in library is never loaded at start by a reading page."""
import check_dist
from check_dist import PRIVATE, READING_PAGES, auth_problems, dist_file, expected_pages, robots_problems, static_chunks

ISLAND = '<astro-island component-url="/_astro/ReadingIsland.a1.js" renderer-url="/_astro/client.b2.js"></astro-island>'
NOINDEX = '<meta name="robots" content="noindex, nofollow">'


def write(dist, name, text):
    file = dist / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def site(tmp_path, reading_island: str):
    dist = tmp_path / "dist"
    for path in expected_pages():
        write(dist, dist_file(path), (NOINDEX if path in PRIVATE else "") + ISLAND)
    write(dist, "_astro/client.b2.js", 'import{h}from"./preact.c3.js";')
    write(dist, "_astro/preact.c3.js", "export const h=1;")
    write(dist, "_astro/ReadingIsland.a1.js", reading_island)
    write(dist, "_astro/api.d4.js", 'const l=()=>import("./supabaseClient.e5.js");export{l};')
    write(dist, "_astro/supabaseClient.e5.js", 'class GoTrueClient{};export{GoTrueClient as A};')
    return dist


def test_the_private_pages_are_expected():
    assert {"/diary", "/es/diario", "/account", "/es/cuenta"} <= set(expected_pages())
    assert len(expected_pages()) == 171


def test_only_the_private_pages_say_noindex(tmp_path):
    dist = site(tmp_path, 'import{x}from"./api.d4.js";')
    assert robots_problems(dist) == []
    write(dist, "diary.html", ISLAND)
    write(dist, "yes-no.html", NOINDEX + ISLAND)
    assert robots_problems(dist) == ["no noindex meta: site/dist/diary.html", "unexpected noindex meta: site/dist/yes-no.html"]


def test_a_dynamic_import_of_the_library_is_fine(tmp_path):
    dist = site(tmp_path, 'import{x}from"./api.d4.js";')
    names = {f.name for f in static_chunks(dist, ISLAND)}
    assert names == {"ReadingIsland.a1.js", "client.b2.js", "preact.c3.js", "api.d4.js"}
    assert auth_problems(dist) == []


def test_a_static_import_of_the_library_is_reported(tmp_path):
    dist = site(tmp_path, 'import{A as G}from"./supabaseClient.e5.js";')
    assert auth_problems(dist) == [f"{path} loads the sign-in library at start" for path in READING_PAGES]


def test_a_build_without_the_library_chunk_is_reported(tmp_path):
    dist = site(tmp_path, "")
    (dist / "_astro/supabaseClient.e5.js").unlink()
    assert auth_problems(dist) == ["no chunk of the sign-in library in site/dist/_astro (src/lib/supabaseClient.ts not built?)"]


def test_main_reports_every_problem_and_passes_a_good_build(tmp_path, capsys):
    assert check_dist.main(tmp_path / "nothing") == 1
    assert "missing: site/dist/diary.html" in capsys.readouterr().out
    dist = site(tmp_path, 'import{x}from"./api.d4.js";')
    for name in check_dist.DATA_FILES:
        write(dist, name, "[]")
    assert check_dist.main(dist) == 0
    assert capsys.readouterr().out == "OK: 171 pages\n"
```

In `tools/site/test_sync_site_data.py` replace

```python
def test_the_build_check_expects_167_pages_with_their_files():
    pages = expected_pages()
    assert len(pages) == 167
    assert {"/", "/es", "/404", "/es/404", "/one-card", "/es/cartas/la-luna"} <= set(pages)
```

with

```python
def test_the_build_check_expects_171_pages_with_their_files():
    pages = expected_pages()
    assert len(pages) == 171  # stage 4.4b: + /diary, /es/diario, /account, /es/cuenta
    assert {"/", "/es", "/404", "/es/404", "/one-card", "/es/cartas/la-luna", "/diary", "/es/cuenta"} <= set(pages)
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary && api/.venv/bin/pytest -q tools/site`
Expected: FAIL — `ImportError: cannot import name 'PRIVATE' from 'check_dist'`, and `assert 167 == 171`.

- [ ] **Step 3: Implement**

Replace the whole `tools/site/check_dist.py` with:

```python
"""After the site build: every page of spec 2026-11-19 stage 4.4a §3 and of spec 2026-11-22 stage 4.4b §5–§6 exists in
site/dist for EN and ES; only the diary and the account pages say noindex; no page that draws a reading loads the
sign-in library at start (spec 4.4b §3: it is a chunk of its own, fetched only when needed).

The pages are the language pairs of site/src/data/pairs.json (tools, 78 cards per language), the two 404 pages and
the four private pages; Astro writes one file per page (build.format "file"): / → index.html, /es → es.html,
/cards/x → cards/x.html.

  python3 tools/site/check_dist.py   — prints "OK: 171 pages" or the problems (exit 1)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
EXTRA = ("/404", "/es/404")
PRIVATE = ("/diary", "/es/diario", "/account", "/es/cuenta")  # noindex, outside hreflang.csv
DATA_FILES = ("data/daily-en.json", "data/daily-es.json")
# the pages with a night room or the Card of the Day: a guest there never downloads the sign-in library
READING_PAGES = ("/", "/one-card", "/yes-no", "/love", "/daily", "/cards/the-moon", "/es", "/es/si-o-no", "/es/amor",
                 "/es/carta-del-dia", "/es/cartas/la-luna")
AUTH_MARKERS = ("GoTrueClient", "supabase.auth.token")  # strings found only in @supabase/auth-js
ROBOTS = re.compile(r'<meta name="robots" content="noindex, nofollow"\s*/?>')
ENTRY = re.compile(r'(?:component-url|renderer-url|src)="(/_astro/[^"]+\.js)"')
# static imports and re-exports only: import("…") (a chunk loaded later) is not followed
STATIC_IMPORT = re.compile(r'\b(?:import|export)\s*(?:[\w$*\s{},]*?\bfrom\s*)?["\'](\.{1,2}/[^"\']+|/_astro/[^"\']+)["\']')


def expected_pages() -> list[str]:
    pairs = json.loads((SITE / "src/data/pairs.json").read_text(encoding="utf-8"))
    return sorted(set(pairs) | set(EXTRA) | set(PRIVATE))


def dist_file(path: str) -> str:
    return "index.html" if path == "/" else f"{path[1:]}.html"


def missing(dist: Path) -> list[str]:
    files = [dist_file(p) for p in expected_pages()] + list(DATA_FILES)
    return [f for f in files if not (dist / f).is_file()]


def robots_problems(dist: Path) -> list[str]:
    """The four private pages carry the noindex meta; no other page does."""
    problems = []
    for path in expected_pages():
        file = dist / dist_file(path)
        if not file.is_file():
            continue  # missing() reports it
        noindex = bool(ROBOTS.search(file.read_text(encoding="utf-8")))
        if noindex != (path in PRIVATE):
            problems.append(f"{'no' if path in PRIVATE else 'unexpected'} noindex meta: site/dist/{dist_file(path)}")
    return problems


def static_chunks(dist: Path, html: str) -> set[Path]:
    """Every script a page loads at start: its islands, their renderers and scripts, and their static imports."""
    seen: set[Path] = set()
    todo = [dist / url.lstrip("/") for url in ENTRY.findall(html)]
    while todo:
        file = todo.pop().resolve()
        if file in seen or not file.is_file():
            continue
        seen.add(file)
        for ref in STATIC_IMPORT.findall(file.read_text(encoding="utf-8")):
            todo.append(dist / ref.lstrip("/") if ref.startswith("/") else file.parent / ref)
    return seen


def auth_problems(dist: Path) -> list[str]:
    library = {c.resolve() for c in (dist / "_astro").glob("*.js")
               if any(marker in c.read_text(encoding="utf-8") for marker in AUTH_MARKERS)}
    if not library:
        return ["no chunk of the sign-in library in site/dist/_astro (src/lib/supabaseClient.ts not built?)"]
    problems = []
    for path in READING_PAGES:
        file = dist / dist_file(path)
        if file.is_file() and static_chunks(dist, file.read_text(encoding="utf-8")) & library:
            problems.append(f"{path} loads the sign-in library at start")
    return problems


def main(dist: Path | None = None) -> int:
    dist = dist or SITE / "dist"
    problems = [f"missing: site/dist/{name}" for name in missing(dist)] + robots_problems(dist) + auth_problems(dist)
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"OK: {len(expected_pages())} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

In `deploy/Caddyfile`, after the line `	import /etc/caddy/parts/auth-{$LAUNCHED}.caddy` (tab-indented, like the file) add:

```
	# stage 4.4b: the diary and the account are never indexed, also after the launch (the pages carry the meta too);
	# their address (?claim=<token>) never leaves the site in a Referer (Fable plan review M8)
	@private path /diary /es/diario /account /es/cuenta
	header @private X-Robots-Tag "noindex, nofollow"
	header @private Referrer-Policy "same-origin"
```

In `deploy/test-site-routes.sh`:

- replace

```bash
for path in / /one-card /yes-no /love /daily /cards/the-moon /cards/ace-of-cups /es /es/si-o-no /es/amor \
  /es/carta-del-dia /es/cartas/la-luna /data/daily-en.json /data/daily-es.json /cards/back.svg; do
```

with

```bash
for path in / /one-card /yes-no /love /daily /cards/the-moon /cards/ace-of-cups /es /es/si-o-no /es/amor \
  /es/carta-del-dia /es/cartas/la-luna /data/daily-en.json /data/daily-es.json /cards/back.svg \
  /diary /es/diario /account /es/cuenta; do
```

- after the line `` location() { "${CURL[@]}" -o /dev/null -D - "$URL$1" | tr -d '\r' | awk 'tolower($0) ~ /^location:/ { print }'; } `` add:

```bash
robots() { "${CURL[@]}" -o /dev/null -D - "$URL$1" | tr -d '\r' | awk 'tolower($0) ~ /^x-robots-tag:/ { sub(/^[^:]*: */, ""); print }'; }
referrer() { "${CURL[@]}" -o /dev/null -D - "$URL$1" | tr -d '\r' | awk 'tolower($0) ~ /^referrer-policy:/ { sub(/^[^:]*: */, ""); print }'; }
```

- before the line `# /api/* идёт к API раньше этих правил, 404 API проходит без изменений` add:

```bash
# stage 4.4b: дневник и аккаунт — noindex и в заголовке, и в HTML; строгие адреса и 404 по языку, как у остальных
for path in /diary /es/diario /account /es/cuenta; do
  expect "$path — X-Robots-Tag" "$(robots "$path")" "noindex, nofollow"
  expect "$path — Referrer-Policy" "$(referrer "$path")" "same-origin"
  expect "$path — meta robots" "$("${CURL[@]}" "$URL$path" | grep -c 'name="robots" content="noindex, nofollow"')" 1
done
expect "/ — без X-Robots-Tag (LAUNCHED=true)" "$(robots /)" ""
expect "/es/diario — страница ES" "$(html_lang /es/diario)" '<html lang="es"'
expect "/diary?claim=…&remind=1" "$(status '/diary?claim=abc_DEF-1&remind=1')" 200
expect "/diary/ → /diary" "$(moved_to /diary/)" "308 $URL/diary"
expect "/es/cuenta.html → /es/cuenta" "$(moved_to /es/cuenta.html)" "308 $URL/es/cuenta"
expect "/diary/?claim=x → /diary?claim=x" "$(moved_to '/diary/?claim=x')" "308 $URL/diary?claim=x"
expect "/es/diario/nada" "$(status /es/diario/nada)" 404
expect "/es/diario/nada — страница 404 ES" "$(html_lang /es/diario/nada)" '<html lang="es"'
```

In `deploy/check-indexing.sh` (the owner runs it after the deploy; here it is only edited):

- after the line `  expect "сайт с паролем" "$(status "${AUTH[@]}" "https://$D/")" 200` add:

```bash
  expect "/diary с паролем" "$(status "${AUTH[@]}" "https://$D/diary")" 200
```

- after the line `  expect "нет noindex в HTML" "$(has_noindex "$("${CURL[@]}" "https://$D/")")" no` add:

```bash
  for p in /diary /es/diario /account /es/cuenta; do  # stage 4.4b: never indexed
    expect "$p noindex в заголовке" "$(has_noindex "$(header X-Robots-Tag "https://$D$p")")" yes
    expect "$p noindex в HTML" "$(has_noindex "$("${CURL[@]}" "https://$D$p")")" yes
  done
```

- [ ] **Step 4: Run the tool tests, the build check and the route check**

Run:

```bash
cd ~/arcana-diary && api/.venv/bin/pytest -q tools/site tools/cards
deploy/build-site.sh && python3 tools/site/check_dist.py
grep -l GoTrueClient site/dist/_astro/*.js | wc -l
deploy/test-site-routes.sh | tail -3
bash -n deploy/check-indexing.sh && echo syntax-ok
```

Expected: `86 passed` (`tools/site` 13, `tools/cards` 73 — the latter unchanged); `OK: 171 pages` (no `noindex` or sign-in-library problem); `1` — exactly one chunk carries the library's marker, so `auth_problems` really looks at it (review M23: the markers are literals in auth-js 2.119.0 and survive minification; with none found the check fails loudly with «no chunk…»); the route script ends with `OK: адреса страниц и 404`; `syntax-ok`. (Measured while amending the plan on a scratch build of Tasks 7–20: `86 passed`, `OK: 171 pages`, `1`; the route script was not run there.) `test-site-routes.sh` starts only its own `arcana-routetest-<pid>` containers and removes them.

- [ ] **Step 5: Commit**

```bash
git add tools/site/check_dist.py tools/site/test_check_dist.py tools/site/test_sync_site_data.py deploy/Caddyfile deploy/test-site-routes.sh deploy/check-indexing.sh
git commit -m "build: stage 4.4b — diary and account pages noindex, sign-in library off reading pages

check_dist expects 171 pages, the noindex meta only on the four private pages, and no
reading page that loads the auth-js chunk at start. Caddy adds X-Robots-Tag to them also
after the launch; the route test covers their addresses.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 22: Final verification of the branch

**Files:** none (a fix found here goes back to its task's files, with its own commit).

- [ ] **Step 1: The API**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q`
Expected: `1531 passed` (see the note on `test_two_followups_at_once_make_one` in Global Constraints; the new account race of Task 1 is timing-based in the same way).

- [ ] **Step 2: The tools**

Run: `cd ~/arcana-diary && api/.venv/bin/pytest -q tools/site tools/cards && python3 tools/cards/validate_cards.py && python3 tools/site/sync_site_data.py --check`
Expected: `86 passed`; `OK`; the sync check prints nothing and exits 0.

- [ ] **Step 3: The site tests and the type check**

Run: the Vitest command (no files), then the `astro check` command
Expected: `317 passed` in 37 files; `- 0 errors`.

- [ ] **Step 4: The build and its checks**

Run: `deploy/build-site.sh && python3 tools/site/check_dist.py && deploy/test-site-routes.sh | tail -1`
Expected: `171 page(s) built`; `OK: 171 pages`; `OK: адреса страниц и 404`.

- [ ] **Step 5: The security greps**

Run:

```bash
grep -rnE "innerHTML|dangerouslySetInnerHTML|set:html|insertAdjacentHTML" site/src --include=*.ts --include=*.tsx --include=*.astro | grep -v "\.test\.ts" ; echo "sinks: $?"
grep -rln "@supabase/auth-js" site/src | grep -v "\.test\." ; echo
grep -rn "account/claim" site/src --include=*.ts --include=*.tsx | grep -v "\.test\."
```

Expected: `sinks: 1` (nothing found); only `site/src/lib/supabaseClient.ts` and the comment in `site/src/lib/auth.ts`; the claim request only in `site/src/lib/accountApi.ts` (called only from `site/src/lib/claim.ts`, with `device` true only after a sign-in started on this device).

- [ ] **Step 6: Report**

No commit. Report the numbers above, any `astro check` fix beyond the nine of Task 8 and the package sizes of Task 7 to the controller; the branch then goes to the Fable 5.2 final review (spec §11), not to `main`.

---
## After the tasks: the owner's steps and the stage walk-through (not a coding task)

From spec §10–§12. Nothing here is done by an implementer or a subagent.

**Owner (spec §10):**

1. «Да» на установку пакетов — before Task 7, with the table «Packages» above (versions, dates, sizes; five rows since the plan check — `@emnapi/runtime` 1.11.3 is new, the other four are unchanged).
2. Google: OAuth client in Google Cloud and the provider in Supabase — `api/README.md` «Вход через Supabase», step 1.
3. Supabase → Authentication → URL Configuration: Redirect URLs `https://arcanadiary.com/diary` and `https://arcanadiary.com/es/diario` (step 2; the `?claim=…&remind=1` addresses match them); the settings of step 5 (anonymous sign-in off, «Confirm email» on, JWT expiry 3600 s).
4. In `deploy/.env`, by the owner (values never pasted into the chat): `SUPABASE_URL` (already there since 4.3), `SUPABASE_ANON_KEY` (Project Settings → API Keys → the public anon / publishable key), `GOOGLE_SIGNIN=true` once step 2 is done.
5. The merge and the deploy (`deploy/deploy.sh`, which also applies migration 007; then `deploy/check-indexing.sh`); after the deploy — the stage password in Chrome for the walk-through.
6. Before the launch (does not block 4.4b): a mail service for the sign-in e-mails (Supabase's built-in mail sends only a few an hour), the Plus price, a new stage password.

**Checks before the walk-through (controller):** the API log shows `migration applied: 007_remind_click`; `GET /api/auth-config` (with the stage cookie) answers `enabled: true`; the Fable 5.2 final review of the branch says "ready to merge" (spec §11).

**Walk-through on the stage, EN and ES, phone and desktop (spec §11, paths П6 and П7; mind the few e-mails an hour of the built-in Supabase mail):**

1. Guest, `/love`: draw, wait for the answer → «Save to diary» under it → the sheet: the reminder box is off, «Continue with Google» only with `GOOGLE_SIGNIN=true`; tick the box, send to your e-mail → «Check your e-mail»; «Send it again» is disabled for 60 s; close the sheet — the answer is still there. Open the sheet again and press the phone's Back (Android Chrome, iPhone Safari swipe back): only the sheet closes, the answer stays; Back once more closes the room (owner decision 14). Network tab: `GET /api/auth-config` when the reading is made, `POST /api/readings/{id}/claim-token` once; no `@supabase` chunk was loaded before the first send. On a desktop (≥ 900 px) the sheet meets the room's left and right edges (review I9, screen 13d).
2. Open the e-mail link **on another device** that has guest readings of its own (implicit flow): `/diary?claim=…&remind=1` → the address becomes `/diary`, the reading from step 1 is in the list and **none of that device's guest readings** (`POST /api/account/claim` once, body `{"tokens": […], "device": false}` — owner decision 12), `PATCH /api/account` consent on (check on `/account`), `signup_done` (`method: email`) in `events`. Then press Back until the address with `?claim=` shows again: no second consent, no second `signup_done` (review I1).
3. Reload the diary: no second `POST /api/account/claim`.
4. Google (when on): `/es/diario` → «Continuar con Google» → back on `/es/diario`, signed in; `signup_done` with `method: google`.
5. Signed in, draw on `/yes-no`: no «Save to diary» button but «Saved to your diary ✓» linking to the entry; the request carries `Authorization: Bearer`.
6. Diary list: date, kind, question or «No question», small cards (a reversed one turned), headline, outcome mark, note mark. With more than 10 readings (insert old ones in SQL if needed): «More readings in Plus: N» and the Plus card with «Your whole diary, with no limit»; an old hidden entry still opens by its `?r=` link; the export has all of them; deleting a listed entry brings the next older one in.
7. Entry: a reading younger than 7 days shows «Come back on <date>…» — the day of the reading's local date + 7; set `created_at` back in SQL to the evening 7 days ago and the buttons are there from 00:00 of that named day (owner decision 13); an older one shows Came true / Partly / No — change it, clear it; `outcome_answered` with `after_days` 7 (and 30 for one older than 30 days). Note: 1000 characters, the counter, «Save note», reload — it stays. Delete with the confirmation.
8. Account: e-mail, «Readings left today: N of 3», the consent switch with the note that e-mails start later, «Download my readings» saves a JSON file; «Delete account» → «Delete forever?» → «Download», «Cancel» (focus back on the button), then «Delete forever» → the home page says «Your account has been deleted.»; the old session cannot write (a draw is a guest draw).
9. Sign-out from the account: back on the home page as a guest; `ad_signed_in` gone from localStorage.
10. Limits: a guest gets 2 readings a day, then only the Plus card (no sign-in offer there, decision 5); signed in — 3 per account on every device.
11. Card of the Day, on a real iPhone (Safari) and a real Android phone (Chrome), not only the desktop device toolbar (review I8): «Remind me tomorrow» saves or offers `arcana-diary-card-of-the-day.ics`; opening it adds one event tomorrow 9:00 local time, 15 minutes, «Card of the Day — Arcana Diary» / «Carta del día — Arcana Diary», with the `/daily` / `/es/carta-del-dia` link and an alert at 9:00 (owner decision 11); pressing twice the same day adds no second event; `remind_click` in `events`. Note how an in-app browser (Instagram) behaves — a known limit, not a blocker.
12. Phone 360 px (Chrome device toolbar): the three yes/no votes under their cards fit, wrap inside their column, no horizontal scroll; the save sheet (also with the on-screen keyboard open on the e-mail field) and the delete dialog fit; every button and link ≥ 44 px («Saved to your diary ✓», «Account» in the diary); the labels of the sign-in block on the diary and account pages and of the note are dark grey on the light surface (review I6).
13. Menu: «Your diary» / «Tu diario» on the phone, «Diary» / «Diario» in the desktop header; EN | ES on `/diary` goes to `/es/diario`, on `/account` to `/es/cuenta`.
14. Sign-in off (temporarily remove `SUPABASE_ANON_KEY` on a test deploy, or check before setting it): no «Save to diary» button, the diary says «Signing in opens soon.»; readings work as in 4.4a.
15. Expired link: open an e-mail link a second time → the diary says the link expired and offers the sign-in block.
16. Lost follow-up (4.5 item 14, now with the 4.4b rule): lose a follow-up, wait more than an hour with the tab open, press «Try again» — the Network tab shows only `GET /api/readings/{id}`, no POST.

---

## Self-review

**Spec coverage:**

| Spec section | Tasks |
|---|---|
| §1 goal and scope | 1–22 (out of scope untouched: reminder e-mails, payment, daily card in the diary, Apple, legal texts) |
| §2 decisions 1–14 | 1 (7, 8), 2 (9), 13 (2, 14), 14 (3, 9), 15 (6, 13), 14 (13: the rule), 16 (4), 17 (1, 10, 11), 6 + 12 (12); decision 5 — no change (the limit screen stays the Plus card) |
| §3 sign-in in the browser | 3 (`/api/auth-config`; a secret key and `GOOGLE_SIGNIN` never stop the API), 7 (auth-js), 9 (state, settings, lazy client, implicit flow), 10 (Bearer, `401`, `503`), 14–16 (`401` rules on the screens), 16 (sign-out), 21 (no library on reading pages) |
| §4 Save to diary | 6 (`"device": false`), 12 (return address, claim once, device only with the mark, consent and `signup_done` only with the mark or a moved reading, `replaceState`), 13 (button, sheet, 3b, 60 s, errors, «Saved ✓», answer kept, Back closes only the sheet) |
| §5 diary | 2 (cap 10, `hidden_count`, `created_at`), 14 (pages, list, hidden + Plus, the local-day rule), 15 (entry, outcome from the named day, note, delete), 21 (noindex) |
| §6 account | 16 |
| §7 Remind me tomorrow | 4 (`remind_click`, migration 007), 17 (with its alarm) |
| §8 small changes | 1 (limits), 4 (events), 6 (claim), 14 (Plus line, third benefit), 18 (menu, header, copy), 12 + 18 (language pairs), 21 (Caddy, route test, check_dist) |
| §9 debts | 7 (DOM library), 13–17, 20 (DOM tests), 19 (Try again GET-only), 5 (stream logs), 8 (`astro check`), walk-through 12 (360 px) |
| §10 owner | «After the tasks» |
| §11 checks | 1–6 (API), 9–20 (Vitest; `astro check` from Task 8 on), 21–22 (build, check_dist), walk-through |
| §12 done when | 22 + walk-through |

**Found while planning — spec vs code, and open questions (each with the resolution used in this plan):**

1. **`remind_click` needs a migration.** The spec puts the new event in `api/app/events.py` only, but `events.name` has a database `CHECK` (migration 004), so the insert fails with `CheckViolation`. Task 4 adds migration 007 (only the constraint; safe on the live table) and the README line that checks the constraint's name on the live database before the deploy (review M2). Recommendation: accept; the owner's deploy applies it.
2. **The entry has no date in the API.** «Сбылось» opens on the named local day (decision 13), but `GET /api/readings/{id}` did not return `created_at`. Task 2 adds it to the owner's view only. Recommendation: accept.
3. **Prototype copy of screens 3, 3b, 4a, 4b and of the account is not in the repository** (the prototypes are a claude.ai artifact, which this planning did not open). English strings that exist in the repo (stage 3 plan, `docs/design/review-fable.md`, 4.4a spec §11, this spec) are used as prototype copy; every other string is a draft in `enDrafts`, every new Spanish string in `esDrafts`. The controller **must** compare the drafts with the prototype artifact before the walk-through (Fable plan check: «обязательна») and replace them in `en.ts` / `es.ts` (no code change).
4. **«Ещё N раскладов — в Plus» in English.** A literal «{n} more readings — in Plus» reads wrong for 1; the plan uses «More readings in Plus: {n}» / «Más tiradas en Plus: {n}» (drafts). Recommendation: the owner may reword at stage 5.
5. **Copy that mentions the diary is static.** «Free · save it to your diary after» and step 3 show also while sign-in is off (no `SUPABASE_ANON_KEY`), although §12 says the site then works as in 4.4a. Recommendation: accept for the closed stage (the owner sets the key before the walk-through); the alternative — switching the panel hint by `/api/auth-config` — adds a request to every page and a text flicker.
6. **«401 без JSON — перезагрузить страницу».** The plan keeps 4.4a's behaviour: the screen shows «Your session on this preview site has expired…» with a «Try again» button that reloads (`errStage`), not an automatic reload, which could loop on a stale stage cookie. The Fable check agreed but found the rule missing in the diary and the entry (I2, I4): now the list (Task 14), the entry's load and every change (Task 15) and the account (Task 16) call `onSignedOut` only on `401 {"reason": "sign_in"}` and show `errStage` with the reload button otherwise; the diary re-opens the session once per page at most. Recommendation: accept.
7. **«Три обработчика потоков».** The 4.5 review named three line numbers that have moved; the code has three stream generators (`_reading_events`, `_followup_events`, `replay_followup`) with five `except DatabaseUnavailable` blocks. Task 5 logs all five. Recommendation: accept.
8. **TypeScript version.** The registry's latest is 7.0.2, but `@astrojs/check` 0.9.12 accepts only `^5 || ^6`; 6.0.3 would fit it, yet Astro 5.18.2's own dependencies (`tsconfck` 3.1.6, `zod-to-ts` 1.2.0) declare TypeScript `^5`. The plan pins 5.9.3. Recommendation: accept 5.9.3.
9. **Sign-in from the account page returns to the diary.** The spec's Supabase return addresses are only `/diary` and `/es/diario` (owner step 3), so signing in on `/account` lands on the diary. Recommendation: accept (one more Redirect URL would be needed otherwise).
10. **No sitemap exists yet.** «Вне карты сайта» holds trivially; `tools/site/check_dist.py` `PRIVATE` is the list stage 7 must keep out of the sitemap and hreflang. Recommendation: note for stage 7.
11. **The claim token is made at the first send, not when the sheet opens** (fewer of the 5 live tokens per reading; a token that cannot be made still saves the reading from this device, where the sign-in was started). Only a token that was made is kept for the open sheet — a failure is asked again at the next send (review M13). The diary's sign-in block keeps a `?claim=` that came back with an expired link, and an entry's `?r=` (review M21). `?claim=` / `?remind=1` in the address alone switch nothing on: consent and `signup_done` need the "started here" mark or a reading that really moved (review I1), and this device's guest readings move only with the mark (owner decision 12). Recommendation: accept.
12. **«Saved to your diary ✓» comes from `ad_signed_in` at the moment the reading was created** (the request carried the token). A person who signs in in another tab after drawing still sees «Save to diary»; the sheet then saves it through the device claim. Recommendation: accept.
13. **DOM tests now ran before the plan went to the implementer.** The first version could not run them (happy-dom comes with Task 7); the Fable check asked for the harness to pin its assumptions first (I11). While amending the plan, Tasks 7–21 were applied to a scratch copy with the five packages installed there (`--no-save`), and every `.test.tsx` ran with happy-dom 21.0.4: all pass, the counts in Global Constraints are measured, and three plan defects were found that way and fixed in the text — `astro check` cannot load without the `@emnapi/runtime` peer (Task 7), `setup(null)` in `auth.test.ts` (TS2345, Task 9), and an anchor with «…» in it (Task 12). The smoke test of Task 7 pins the four happy-dom properties the screens rely on (checkbox `click()` → `change`, focus on `tabIndex=-1`, `pushState`/`replaceState`, `Response`); `cleanup()` and `waitFor()` replace `document.body.replaceChildren()` and counted `settle` rounds. If a test still fails for a harness reason, fix the test helper, never weaken the component or the assertion; report it.
14. **Supabase error codes** (`over_email_send_rate_limit`, `email_address_invalid`, `validation_failed`, status 429/400/422) follow auth-js 2.x; the walk-through (built-in mail, a few e-mails an hour) will show «too often» for real. Recommendation: check in walk-through item 1.
15. **360 px for the yes/no votes** cannot be tested in happy-dom (no layout): Task 20 pins the markup, walk-through item 12 checks the layout. If it breaks, the fix is a CSS rule in `global.css` (tokens only).
16. **Known risk: the calendar file on phones (review I8).** The page cannot tell whether a phone saved or opened the `.ics`: iOS Safari asks first (the object URL now lives 60 s), the in-app browsers of Instagram, Facebook and TikTok often ignore blob downloads, and «Open the file to add it to your calendar.» is shown in every case. Walk-through item 11 checks a real iPhone Safari and a real Android Chrome. `navigator.share({ files })` (the review's optional idea) is not added: it is a second flow with its own wording per platform. Recommendation: accept for the closed stage; revisit if the walk-through shows a phone that does nothing.
17. **Known limit of the implicit flow (review M9).** After sign-in auth-js clears `#access_token=…` with `location.hash = ''`, which is a new history entry: Back shows the address with `?claim=…&remind=1` (and briefly the token entry) again. After I1 this has no effect — the token is used, there is no mark any more, so nothing is claimed, consented or counted twice — and the token in that entry expires with the session. Recommendation: accept; PKCE would need the same device (decision 14.11.2026).
18. **A fifth package.** `@emnapi/runtime` 1.11.3 (peer of `@napi-rs/wasm-runtime`, which `@astrojs/check`'s language server loads) is needed because `legacy-peer-deps=true` skips peers; without it `astro check` cannot run (measured). The owner's yes of Task 7 has to cover it; the other four versions are unchanged.
19. **A secret key is dropped, not refused (review I3, with I12's reasoning).** The review proposed refusing such a key; a refusal at start would turn into the same restart loop as I12. Task 3 drops it (sign-in stays off, «Signing in opens soon.»), logs an `ERROR` without the key, and never publishes it. Recommendation: accept.

**Review triage (Fable plan check, `.superpowers/sdd/s44b-plan-fable-review.md`, 22.11.2026; numbers are the new task numbers):**

| ID | Status | How |
|---|---|---|
| I1 | fixed | Task 12: consent and `signup_done` only with the "started here" mark or a non-empty `claimed`; the address is cleaned either way; a negative test (`claimed: []`, no mark). The device side is owner decision 12: Task 6 (server `"device"`), Tasks 11–12 (site sends `device` only with the mark). |
| I2 | fixed | Task 14: `onSignedOut` only on `401 {"reason": "sign_in"}`; a `401` without JSON is `errStage` + reload button; one automatic re-open per page; DOM test: one list request, the stage line. |
| I3 | fixed (differently) | Task 3: `sb_secret_…`, a JWT whose role is not `anon`, or an undecodable dotted value is dropped (sign-in off) with an `ERROR` log that does not print the key — not a refusal at start, which would be the I12 restart loop; five test cases; `.env.example` and README say «never service_role / sb_secret_». |
| I4 | fixed | Task 15: the same rule in the entry's load, outcome, note and delete; stage line with reload; DOM test. |
| I5 | fixed | Task 16: the error is shown inside `.dialog`; DOM test (`deleteAccount` → 503: the line in the dialog, no sign-out, no navigation). |
| I6 | fixed | Task 13 `.signin--day .field label` (the sign-in block on the diary and account pages carries its surface), Task 15 `.entry .field label` and the textarea padding — day muted colour. |
| I7 | fixed | Owner decision 13: `outcomeOpensOn` = 00:00 local of «local date + 7 days», `outcomeOpen` uses it (Task 14); tests with local dates (any zone) and `TZ=UTC` in `vitest.config.ts` (Task 7); the entry opens at 00:00 of the named day (Task 15 test). |
| I8 | fixed | Task 16: the object URL lives 60 s (`REVOKE_AFTER_MS`, DOM test); walk-through item 11 on a real iPhone Safari and Android Chrome; known risk in item 16 above. The optional `navigator.share` is declined (item 16). |
| I9 | fixed | Task 13 CSS: from 900 px the sheet takes `--space-7` side margins and padding; walk-through items 1 (desktop) and 12 (360 px with the keyboard). |
| I10 | fixed | `astro check` is Task 8, right after the packages, with the nine measured errors and their exact fixes; every site task 9–20 runs it (`- 0 errors`, measured in the scratch copy after each). The `signedIn` of `draw()` (TS2741) is in Task 13; running the check also found `setup(null)` in Task 9's test (fixed). |
| I11 | fixed | Task 7: the smoke test pins the four happy-dom properties (six tests, measured), `mount` remembers its roots and `cleanup()` unmounts them (every DOM test calls it), `waitFor()` replaces counted `settle(30)`, `TZ=UTC`. |
| I12 | fixed | Task 3: only exactly `true` switches Google on; anything else is off with a `WARNING`; never an error at import; test. |
| M1 | fixed | Task 5 uses `-k is_logged` (4 tests). |
| M2 | fixed | Task 4: README line to check `events_name_check` on the live database before the deploy; «миграции 004, 007». |
| M3 | fixed | Task 2: the `before` beyond the 10th entry case; the two-query race on `hidden_count` is accepted as the review says (noted in Step 4). |
| M4 | fixed | Task 1: `docs/design/00-design.md` decision row 3 gets the 4.4b note. |
| M5 | fixed | Task 1: `test_paid_followups_of_an_account_at_once_cannot_overspend_the_day` keeps the three-way race with the account's three. |
| M6 | fixed | Task 9: `signOut` clears the flags first; tests for a library error and a throw. Task 16: a hung sign-out waits `SIGN_OUT_WAIT_MS` at most; test. |
| M7 | fixed | Task 9: a failed library load is not cached; test. |
| M8 | fixed | Task 21: `Referrer-Policy: same-origin` on the four private pages; route check. |
| M9 | fixed (documented) | Item 17 above: no effect after I1. |
| M10 | fixed | Task 17: `'\\;'` and the corrected expectation. |
| M11 | fixed | Task 17: `text/calendar;charset=utf-8`, no `METHOD`, `UID:daily-<YYYYMMDD>@arcanadiary.com`; tests. |
| M12 | fixed | Task 17: `.daily .btn--outline` takes the night control border. |
| M13 | fixed | Task 13: only a made token is kept; test. |
| M14 | fixed | Task 13: the settings are read when the reading is created (`useSaveToDiary`), and the button is the last of the actions; tests. |
| M15 | fixed | Task 13: «Use another e-mail» focuses the e-mail field; `.night__top` and `.night__body` are `inert` while the sheet is open; tests. |
| M16 | fixed | Tasks 13–14: `.saved-mark a` and the diary's «Account» link are 44 px targets. |
| M17 | fixed | Task 14: the list is `.diary__list`, no `.diary` inside `.diary`. |
| M18 | fixed | Task 14: «Try again» on list errors and on «unreachable»; no empty `role="status"` while loading; test. |
| M19 | fixed | Task 14: no «Show more», no `next`, no `diaryMore` (dictionary counts follow: 220 keys, 101 / 173 drafts at the end); the entry's CSS moves to Task 15, the account's and the dialog's (with `.check--day`) to Task 16; the «library is loaded now» comments say «at the first send». |
| M20 | fixed (differently) | Task 13: the island's wiring is the hook `useSaveToDiary` with its own DOM test in the real night room (a lib function could not hold the sheet, its history entry and `save_click` together). |
| M21 | fixed | Task 15: the reading's and the follow-ups' `soft_line` are shown; `outcome_answered` only for an answer on an empty mark; outcome buttons disabled during the PATCH; `?r=` kept through sign-in; two DiaryIsland tests (`?r=` opens the entry, the return address keeps `r`). |
| M22 | fixed (one part declined) | Task 16: a sessionStorage mark makes the home notice one-time and link-proof; Escape and the buttons wait while deleting; `download.test.ts`. Task 15 adds one `deviceTimeZone()` for the new pages. Declined: replacing the two 4.4a copies in `ReadingIsland.tsx` / `DailyIsland.tsx` — no behaviour change, and it would touch tested 4.4a islands for nothing. |
| M23 | fixed | Task 21 Step 4: `grep -l GoTrueClient site/dist/_astro/*.js` piped to `wc -l` → `1` (measured on the scratch build). |
| M24 | fixed | Global Constraints: the trailer names the implementer's own model; the steps keep `Claude Opus 5.5` (this stage's model). |

Self-review items where the check disagreed: 1 (M2 added), 3 (the drafts check is now a must), 6 (I2, I4 implemented), 11 (M13, I1), 13 (I11 harness, DOM tests now measured) — all resolved above. The check's four questions to the owner are answered by decisions 11–14 (spec §2).
