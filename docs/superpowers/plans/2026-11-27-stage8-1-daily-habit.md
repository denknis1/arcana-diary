# Stage 8.1: Card of the Day as a Habit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Card of the Day a daily habit without a single new model call: one card per account on every device,
a streak without punishment, a month calendar in the diary with each day's card, text, evening mark and one-line note,
and an opt-in morning browser reminder (Web Push) that never names the card — for EN and ES, on the live site, ready for
the owner's deploy.

**Architecture:** Migration `009_daily_journal` gives `daily_draws` two kinds of owner (a guest cookie or an account,
never both, rollback-safe) plus the mark and note columns, adds `push_subscriptions` and four event names. Pure helpers
in `api/app/journal.py` (streaks, months, most frequent card) feed `GET /api/daily` (now by account), the new
`GET /api/daily/calendar` and `PUT /api/daily/{day}`; sign-in claim, export, deletion and the hourly cleanup learn the
new rows. Web Push is our own code in `api/app/webpush.py` (RFC 8291 encryption + RFC 8292 VAPID on the already pinned
`cryptography` and PyJWT, checked against the RFC example) with a subscription API (`routes/push.py`) and a 10-minute
sender job (`app/push.py`) inside the existing background work. The site gets `src/lib/journal.ts` and
`src/lib/push.ts`, three components (`EveningMark`, `DailyCalendar`, `PushOffer`/`PushSwitch`), a service worker built
from the dictionaries (`src/pages/sw.js.ts` → `/sw.js`), a standalone manifest, and the new texts.

**Tech Stack:** Python 3.12, FastAPI, psycopg 3, PostgreSQL 16 (tests in a throwaway `postgres:16.10-alpine`),
`cryptography` 50.0.2, PyJWT 2.15.1, httpx 0.28.1 (all already pinned); Astro 5 (static), Preact islands, vitest 5 +
happy-dom, all in Docker `node:22`; Caddy 2.8.4 (route test only); Bash for the key script.

**Spec:** `docs/superpowers/specs/2026-11-27-stage8-1-daily-habit-design.md` (owner decisions 51–53). Its exact texts
are binding: «Day 4 in a row · Your month in cards» / «Día 4 seguido · Tu mes en cartas»; «Did today's card show up in
your day?» / «¿Apareció la carta de hoy en tu día?» with «Yes / Partly / No» («Sí / En parte / No»), a one-line note of
up to 280 characters; «Sign in to keep your cards»; «Remind me each morning», 8:00 local by default; «Your card for
today is waiting» / «Tu carta de hoy te espera»; the tab «Card of the Day» / «Carta del día»; FAQ «Is my daily card
saved?»; free calendar = this and the previous month; guests 7 days, cards kept 60 days, guest subscriptions 90 days
without activity.

**How this plan was checked:** every code step below was run on a copy of `main` (an export, not a branch): the API suite
(`1750 passed`), the site suite (533 tests, 0 failures), `astro check` (0 errors), the build, `check_dist --launched`
(`OK: 187 pages`), `check_links`, `check_tool_pages` on the edited texts and `deploy/test-gen-vapid.sh`; the plan's own
edits were then applied in order to a fresh export and compared with that copy file by file.

## Global Constraints

Every task's requirements include this section.

- **Working directory:** every command runs from the repository root `~/arcana-diary`, on the branch
  `stage8-daily-habit` (Task 1 creates it from `main`).
- **Node only via Docker `node:22`; never `npm install` on the host.** Site commands:
  - all site tests and the build: `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npm run build'`
  - one test file: the same with `'npx vitest run <files>'`; types: the same with `'npx astro check'` (`0 errors`)
  - then `python3 tools/site/sync_site_data.py --check`; `python3 tools/site/check_dist.py --launched`;
    `python3 tools/site/check_links.py`; `python3 tools/cards/check_tool_pages.py`
- **API tests:** `cd api && .venv/bin/pytest -q` (Docker runs a temporary Postgres; never a Supabase database).
- **The site is LIVE** (`LAUNCHED=true`, behind Cloudflare, `TRUST_CLOUDFLARE=true`): every deploy is visible to
  visitors and search engines. **No deploy, merge to main, push, or container restart inside tasks** — those happen only
  on the owner's word (see «Operator steps»). `deploy/test-site-routes.sh` and `deploy/test-gen-vapid.sh` use their own
  temporary containers / files and are allowed.
- **New dependency only with the owner's yes.** `pywebpush` (and whatever it pulls) may be installed only after the
  owner says yes; Task 6 has an explicit STOP step that reports the choice before anything is installed or fetched. The
  plan's choice is **no new package** (decision 1); nothing is added to `api/requirements.txt` or `site/package.json`.
- **Secrets:** never read, print or commit `deploy/.env` or `deploy/caddy/stage_auth.caddy*`. VAPID keys are created by
  `deploy/gen-vapid.sh`, which appends them to `deploy/.env` without printing them; running it and deploying is an
  owner-approved operator step outside the tasks.
- **No paid model calls anywhere in this stage.** The new code never imports the reader or a provider; the daily job is
  unchanged. Notes and marks never go to a model or into analytics events (tests check both).
- **Texts:** EN and Mexican Spanish (tú, no gendered forms about the reader); UI strings only in `site/src/i18n/{en,es}.ts`
  (same keys in both; the key count in `i18n.test.ts` moves 266 → 277 → 289 → 302); page texts in `content/pages` within
  `tools/cards/check_tool_pages.py`'s limits; JSON edited in place (exact string replacement), never re-serialised.
  Privacy texts must match what the code stores (guest daily cards 60 days, guest push subscriptions 90 days without
  activity). Every new key is new interface copy: the owner reads it at the final checkpoint.
- **Design tokens only** in CSS (`var(--…)`; `guards.test.ts` forbids colour literals and HTML sinks); 44 px controls;
  real `<button>`, `<a>`, `<table>` with `<th scope>`; one `<h1>` per page.
- **Islands never load the sign-in library at start on reading pages** (`check_dist` READING_PAGES): the new code uses
  `siteFetch()` as the existing islands do.
- **Commits:** one commit per task on `stage8-daily-habit`; every message ends with a blank line and
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit commands below pass it as a second `-m`).
- **Reviews:** after each task a review on **Sonnet** (spec compliance, then code quality); after Task 12 a whole-branch
  review on **Fable** (personal notes storage and notifications).

## Decisions taken in this plan (spec gaps)

1. **Web Push without `pywebpush`.** The API already pins `cryptography` (ECDH, HKDF, AES-GCM) and PyJWT (ES256) for the
   stage 4.3 sign-in, and `httpx` for the POST; RFC 8291 + RFC 8292 are ~150 lines (`app/webpush.py`) and the RFC 8291 §5
   example is a byte-exact test. `pywebpush` would add `py-vapid`, `http-ece` and an HTTP client stack (`aiohttp` or
   `requests`) to the image for the same three calls. Task 6 stops for the owner's word before going on.
2. **Account rows keep no device.** An account's card row has `user_id` and `guest_id = NULL`; a guest's has `guest_id`
   only (`daily_draws_one_owner`). The old primary key `(guest_id, day)` becomes a unique index on the same columns, so
   the stage 4.2 insert still works after 009 (rollback-safe insert); `(user_id, day)` is unique too, plus the spec's
   index `(user_id, day DESC)`.
3. **Claim on a day the account already has:** the account's card stays and the device's card of that day is deleted
   (spec §4 "остаётся карта аккаунта"); the device's other days move. The claim answer stays `{"claimed": [...]}`.
4. **Streaks:** current = the run ending today, or yesterday while today has no card yet; best = the longest run kept.
   A new guest (no cookie) gets 1/1 and nothing is stored, as before. The line «Day N in a row» shows from N = 2;
   on day 1 only «Your month in cards» (confirmed by the controller, 28.11).
5. **Most frequent card of the month:** by card (either orientation), shown only from 2 times; a tie goes to the card
   that came last.
6. **Calendar API shape:** one month per request with each day's text (`daily_cache` while it lasts, then the card base —
   cached 62 days since owner decision 54, so the two free months show the text read that morning; the card base only
   for a day whose text was never cached); months before the previous one answer `locked: true` with no days (kept, for Plus); the site offers only
   the two free months. A guest gets the last 7 days whatever `month` says, without `felt`/`note`.
7. **The mark API** follows the diary's PATCH rules: only sent fields change, an empty note is no note, `noted_at` is
   cleared when both are empty; a card is never drawn after the fact (404 for a day without one). Marks for "any day with
   a card" are allowed by the API; the site shows the question under today's card from 17:00 and in the calendar for past
   days (today from 17:00). A guest after 17:00 sees the same question with inactive answers, no note field and the line
   «Sign in to mark your days and keep your cards» (owner decision 56); nothing is sent.
8. **Events carry no mark:** `daily_felt` has only `place` (daily, calendar) and is sent on the first mark of a day;
   `daily_calendar_view` has `signed_in`; `push_enabled` (tool daily) and `push_click` have none. No `daily_open`: the
   Card of the Day opening is the existing `tool_view {tool: daily}` (controller decision, 28.11; the spec is corrected).
9. **Push safety:** only https endpoints of the known push services are stored (`fcm.googleapis.com`,
   `updates.push.services.mozilla.com`, `web.push.apple.com`, `*.push.apple.com`, `*.notify.windows.com`) — the server
   never POSTs to an address a visitor chose. At most 10 browsers per owner and 10 subscribe calls per address a minute.
   `DELETE` by endpoint alone (knowing it means being that browser), always 204.
10. **Sending:** the job runs every 10 minutes (spec) and sends inside a 2-hour window from the chosen local hour;
    `last_sent_day` is set before sending (at most one a day, also when two runs overlap), and also on a day skipped
    because the card is already open. 404/410 delete at once (the browser dropped it); 401/403 (our VAPID key refused)
    are logged and not counted, so a key mistake cannot wipe every subscription; other failures count, 3 in a row
    delete (spec). The message carries only `{"lang"}`; the service worker shows the fixed text and opens a fixed address.
11. **Subscription owner and activity:** signed in → the account; otherwise the guest cookie. A guest's
    `active_at` is renewed on every Card of the Day visit (`GET /api/daily`), which is the "activity" of the 90-day rule
    (added to the spec's column list, confirmed 28.11). Signing in moves the cookie's subscriptions too; a subscription
    made while signed in stays with the account after a sign-out until it is turned off (under the card or on the account
    page), and deleting the account removes it.
12. **Export** lists the push service host only, not the endpoint or its keys (anyone holding them could send to the
    browser); both card names (`name_en`, `name_es`) are exported, as the rows have no language.
13. **The service worker is built, not hand-written:** `src/pages/sw.js.ts` writes `/sw.js` at build time from the
    dictionaries (the spec names `site/public/sw.js`; the served address is the same, and the two texts stay in
    `src/i18n`). It has no `fetch` handler (nothing cached) and is registered only when the person turns reminders on.
    Caddy serves it with `Cache-Control: no-cache`.
14. **iPhone:** an iPhone/iPad (iPadOS reports "Macintosh" with touch) outside the Home Screen app gets the hint instead
    of the button; inside it (`display-mode: standalone`, `display: standalone` in the manifest) the normal offer.
15. **«Not now»** hides the offer for 30 days on that device (local storage); «Remind me tomorrow» (the .ics file) stays.
16. **Calendar tab address:** `/diary?tab=daily` (`/es/diario?tab=daily`); the tabs are two real links in a `<nav>`
    drawn by the island (the diary is noindex; `check_dist` does not see island links). The sign-in from the tab comes
    back to it.

## File map

Created:

| File | Responsibility |
|---|---|
| `api/migrations/009_daily_journal.sql` | owners, mark and note on `daily_draws`; `push_subscriptions`; four event names |
| `api/app/journal.py` | streaks, months, the month's most frequent card (pure) |
| `api/app/webpush.py` | RFC 8291 encryption, RFC 8292 VAPID, endpoint allowlist, key checks |
| `api/app/push.py` | the morning reminder job (due subscriptions, sending, failures) |
| `api/app/routes/push.py` | `GET /api/push/key`, `POST`/`DELETE /api/push/subscription` |
| `api/tests/test_journal.py`, `test_api_daily_calendar.py`, `test_webpush.py`, `test_api_push.py`, `test_push_job.py` | tests |
| `deploy/gen-vapid.sh`, `deploy/test-gen-vapid.sh` | VAPID keys into `deploy/.env` without printing; its test on a temp file |
| `site/src/lib/journal.ts` (+ test) | calendar address, evening hour, calendar/mark requests, month grid |
| `site/src/lib/push.ts` (+ test), `site/src/lib/testing/push.ts` | browser support, on/off/refresh; a fake browser for tests |
| `site/src/lib/sw.ts` (+ test), `site/src/pages/sw.js.ts` | the service worker source and its build endpoint |
| `site/src/components/ui/EveningMark.tsx` | the evening question, Yes/Partly/No and the one-line note |
| `site/src/components/ui/DailyCalendar.tsx` (+ test) | the month grid / guest week, streaks, the day's detail |
| `site/src/components/ui/PushOffer.tsx` (+ test), `PushSwitch.tsx` (+ test) | the offer under the card; the account line |

Modified: `api/app/{db,repo,account_repo,daily,config,context,main,events,housekeeping}.py`,
`api/app/routes/{daily,claim,account}.py`, `api/tests/{test_db,test_api_daily,test_api_claim,test_api_account,
test_housekeeping,test_api_events,test_config}.py`, `api/README.md`, `deploy/{docker-compose.yml,.env.example,Caddyfile,
test-site-routes.sh}`, `docs/design/analytics-events.md`, `site/src/lib/{types,daily,analytics}.ts` (+ analytics test),
`site/src/islands/{DailyIsland,DiaryIsland,AccountIsland}.tsx` (+ Daily/Diary tests), `site/src/i18n/{en,es}.ts`
(+ test), `site/src/styles/global.css`, `site/public/site.webmanifest`, `tools/site/check_dist.py` (+ test),
`content/pages/{en/daily,es/carta-del-dia,en/privacy,es/privacidad}.json`, `site/src/data/pages/**` (generated).
Not modified: `api/app/draw.py` (the seed already takes any id), the terms pages, `api/requirements.txt`,
`site/package.json`.

---
### Task 1: Branch and migration 009 (`009_daily_journal`)

**Files:**
- Create: `api/migrations/009_daily_journal.sql`
- Modify: `api/app/db.py` (`APP_TABLES`); first, in its own commit, `deploy/test-site-routes.sh` (three stale checks)
- Test: `api/tests/test_db.py`, `deploy/test-site-routes.sh`

**Interfaces:**
- Consumes: migrations 001–008; `app.db.migrate`, `split_sql`, `APP_TABLES`; `repo.record_daily_draw` (unchanged).
- Produces (every later task relies on these):
  - `daily_draws(guest_id uuid NULL, user_id uuid NULL, day date, card_id text, reversed boolean, felt text NULL
    CHECK IN ('yes','partly','no'), note text NULL CHECK char_length <= 280, noted_at timestamptz NULL)`; constraint
    `daily_draws_one_owner` = exactly one of `guest_id` / `user_id`; unique indexes `daily_draws_guest_day_key (guest_id,
    day)` and `daily_draws_user_day_key (user_id, day)`; index `daily_draws_user_day_idx (user_id, day DESC)`.
  - `push_subscriptions(id uuid PK default gen_random_uuid(), user_id uuid NULL, guest_id uuid NULL, endpoint text UNIQUE
    <= 1024, p256dh text <= 200, auth text <= 50, lang 'en'|'es', tz text <= 64, hour smallint 0–23, fails smallint >= 0
    default 0, last_sent_day date NULL, created_at timestamptz, active_at timestamptz)`, exactly one owner, RLS on.
  - `events.name` also accepts `daily_felt`, `daily_calendar_view`, `push_enabled`, `push_click`.
  - `APP_TABLES` ends with `"push_subscriptions"` (migrate() revokes the browser roles on it).

- [ ] **Step 1: Create the branch**

```bash
git switch -c stage8-daily-habit
git status --short
```

Expected: `Switched to a new branch 'stage8-daily-habit'` and an empty status.

- [ ] **Step 2: Fix the three stale checks of the route test (own commit, before the stage's work)**

Since the launch (24.11.2026) every service page is open, but `deploy/test-site-routes.sh` still expects `/about` and `/es/privacidad` to be hidden and the sitemap to leave them out; these three lines fail on `main` (controller decision on open question 13).

In `deploy/test-site-routes.sh`, replace:

```bash
# stage 6, часть 4: служебные страницы; с метками оператора — noindex и вне sitemap.xml
```

with:

```bash
# stage 6, часть 4: служебные страницы; с запуска (24.11.2026, данные оператора заполнены) открыты все — без noindex
# и в sitemap.xml
```

In `deploy/test-site-routes.sh`, replace:

```bash
expect "/about — скрыта (meta robots)" "$("${CURL[@]}" "$URL/about" | grep -c 'name="robots" content="noindex, nofollow"')" 1
expect "/es/privacidad — скрыта (meta robots)" "$("${CURL[@]}" "$URL/es/privacidad" | grep -c 'name="robots" content="noindex, nofollow"')" 1
```

with:

```bash
expect "/about — открыта (без meta robots)" "$("${CURL[@]}" "$URL/about" | grep -c 'name="robots" content="noindex, nofollow"')" 0
expect "/es/privacidad — открыта" "$(canonical /es/privacidad)" "https://arcanadiary.com/es/privacidad"
```

In `deploy/test-site-routes.sh`, replace:

```bash
expect "sitemap.xml без скрытых" "$("${CURL[@]}" "$URL/sitemap.xml" | grep -c '/about<\|/privacy<\|/es/terminos<')" 0
```

with:

```bash
expect "sitemap.xml со служебными страницами" "$("${CURL[@]}" "$URL/sitemap.xml" | grep -c '/about<\|/privacy<\|/es/terminos<')" 3
```

Run:

```bash
deploy/test-site-routes.sh 2>&1 | grep -c '^FAIL'
deploy/test-site-routes.sh 2>&1 | grep -E 'открыта|служебными'
```

Expected: `0`; `PASS /about — открыта (без meta robots) (0)`, `PASS /es/privacidad — открыта (...)`, `PASS sitemap.xml со служебными страницами (3)` (it reads the current `site/dist`; temporary containers only).

```bash
git add deploy/test-site-routes.sh
git commit -m "test(deploy): route test follows the launch — the service pages are open and in the sitemap" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 3: Write the failing tests**

Replace all 7 occurrences in `api/tests/test_db.py` (every migration list that ends with 008):

```bash
sed -i 's/"008_person_verdict"\]/"008_person_verdict", "009_daily_journal"]/' api/tests/test_db.py
grep -c '"009_daily_journal"\]' api/tests/test_db.py   # prints 7
```

Append to the end of `api/tests/test_db.py`:

```python
# --- stage 8.1: migration 009 (spec 2026-11-27 §4) ---

BEFORE_009 = ("001_init", "002_accounts", "003_guard_source", "004_events", "005_request_ids", "006_rewrite_purpose",
              "007_remind_click", "008_person_verdict")


def test_009_applies_over_008_keeps_the_guest_draws_and_the_old_insert(fresh_db):
    """The live database before stage 8.1: its guest draws stay, and the stage 4.2 insert (ON CONFLICT (guest_id,
    day)) still works after 009, so going back to the old code is safe."""
    apply_up_to(fresh_db, *BEFORE_009)
    guest = uuid.uuid4()
    with fresh_db.connect() as conn:
        repo.record_daily_draw(conn, guest, T0.date(), "major-18-moon", False)
    assert migrate(fresh_db, MIGRATIONS) == ["009_daily_journal"]
    with fresh_db.connect() as conn:
        repo.record_daily_draw(conn, guest, T0.date(), "cups-02-two", True)  # the same day again: nothing
        rows = conn.execute("SELECT guest_id, user_id, day, card_id, felt, note, noted_at FROM daily_draws").fetchall()
    assert rows == [{"guest_id": guest, "user_id": None, "day": T0.date(), "card_id": "major-18-moon", "felt": None,
                     "note": None, "noted_at": None}]


def test_009_runs_again_without_harm(fresh_db):
    """IF EXISTS / IF NOT EXISTS: the file applied a second time (a half-applied run retried by hand) changes nothing."""
    migrate(fresh_db, MIGRATIONS)
    with fresh_db.connect() as conn:
        for statement in split_sql((MIGRATIONS / "009_daily_journal.sql").read_text(encoding="utf-8")):
            conn.execute(statement)


def test_009_one_card_per_owner_and_day_and_exactly_one_owner(db):
    user, guest, day = uuid.uuid4(), uuid.uuid4(), T0.date()
    insert = "INSERT INTO daily_draws (guest_id, user_id, day, card_id, reversed) VALUES (%s, %s, %s, 'major-18-moon', false)"
    with db.connect() as conn:
        conn.execute(insert, (None, user, day))
        conn.execute(insert, (guest, None, day))  # a guest row and an account row on the same day
        for args in ((None, user, day), (guest, None, day), (None, None, day), (guest, user, day + timedelta(days=1))):
            with pytest.raises((psycopg.errors.UniqueViolation, psycopg.errors.CheckViolation)):
                with conn.transaction():
                    conn.execute(insert, args)


@pytest.mark.parametrize("sql", [
    "UPDATE daily_draws SET felt = 'maybe'",
    "UPDATE daily_draws SET note = repeat('x', 281)",
])
def test_009_mark_and_note_checks(db, sql):
    with db.connect() as conn:
        repo.record_daily_draw(conn, uuid.uuid4(), T0.date(), "major-18-moon", False)
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.connect() as conn:
            conn.execute(sql)


def test_009_push_subscriptions_checks(db):
    row = {"user_id": None, "guest_id": uuid.uuid4(), "endpoint": "https://fcm.googleapis.com/fcm/send/x",
           "p256dh": "k", "auth": "a", "lang": "en", "tz": "UTC", "hour": 8, "now": T0}
    insert = ("INSERT INTO push_subscriptions (user_id, guest_id, endpoint, p256dh, auth, lang, tz, hour, created_at,"
              " active_at) VALUES (%(user_id)s, %(guest_id)s, %(endpoint)s, %(p256dh)s, %(auth)s, %(lang)s, %(tz)s,"
              " %(hour)s, %(now)s, %(now)s)")
    with db.connect() as conn:
        conn.execute(insert, row)
        for bad in ({"endpoint": row["endpoint"]}, {"endpoint": "https://e/2", "hour": 24},
                    {"endpoint": "https://e/3", "guest_id": None}, {"endpoint": "https://e/4", "user_id": uuid.uuid4()},
                    {"endpoint": "https://e/5", "lang": "fr"}):
            with pytest.raises((psycopg.errors.UniqueViolation, psycopg.errors.CheckViolation)):
                with conn.transaction():
                    conn.execute(insert, {**row, **bad})


def test_009_events_take_the_four_new_names(db):
    with db.connect() as conn:
        for name in ("daily_felt", "daily_calendar_view", "push_enabled", "push_click"):
            conn.execute("INSERT INTO events (day, name, tool, lang, params, created_at) VALUES (%s, %s, NULL, 'en',"
                         " '{}', %s)", (T0.date(), name, T0))
        assert conn.execute("SELECT count(*) AS n FROM events").fetchone()["n"] == 4


def test_009_push_subscriptions_are_closed_to_the_browser_roles(fresh_db):
    with psycopg.connect(fresh_db.url, autocommit=True) as conn:
        for role in ("anon", "authenticated"):
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                conn.execute(f"CREATE ROLE {role}")
            conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {role}")
    migrate(fresh_db, MIGRATIONS)
    with fresh_db.connect() as conn:
        row = conn.execute("SELECT has_table_privilege('anon', 'public.push_subscriptions', 'SELECT') AS a,"
                           " has_table_privilege('authenticated', 'public.push_subscriptions', 'INSERT') AS b,"
                           " (SELECT relrowsecurity FROM pg_class WHERE relname = 'push_subscriptions') AS rls"
                           ).fetchone()
    assert row == {"a": False, "b": False, "rls": True}
```

- [ ] **Step 4: Run the tests to see them fail**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_db.py)
```

Expected: FAIL — the seven migration-list tests (`assert [...'008_person_verdict'] == [..., '009_daily_journal']`) and the eight 009 tests (`FileNotFoundError: ... 009_daily_journal.sql`, `UndefinedColumn: column "user_id"`, `DatabaseUnavailable: relation "push_subscriptions" does not exist`, `CheckViolation` on `daily_felt`).

- [ ] **Step 5: Implement**

Create `api/migrations/009_daily_journal.sql`:

```sql
-- 009_daily_journal: stage 8.1 (spec 2026-11-27, owner decisions 51-53): the Card of the Day as a habit.
-- 1. daily_draws gets an owner of two kinds: a guest row has guest_id (the device cookie) and no user_id, as before,
--    an account row has user_id and no guest_id (one card per account and day on every device). The primary key
--    (guest_id, day) becomes a unique index on the same columns (NULLs never conflict), so the code of stage 4.2
--    keeps working on this table (its ON CONFLICT (guest_id, day) still finds the index: a rollback stays safe).
--    felt / note / noted_at: the evening mark "Did today's card show up in your day?" and a one-line note of at
--    most 280 characters (never sent to a model, never in an event).
-- 2. push_subscriptions: browser reminders (Web Push). One row per browser endpoint; the owner is an account or a
--    guest cookie, never both. Row level security on, no policies; migrate() revokes the browser roles (APP_TABLES).
-- 3. events: four more event names (spec §4 "События").
-- Every statement can run again (IF EXISTS / IF NOT EXISTS), as the review of 008 asked; migrate() runs the whole
-- file in one transaction, so the API never sees half of it. Until it has run, the new code meets a missing column
-- or table and answers 503 (db.py), never 500. daily_draws is small (7 days of guest rows before this stage).
ALTER TABLE daily_draws ADD COLUMN IF NOT EXISTS user_id uuid;
ALTER TABLE daily_draws ADD COLUMN IF NOT EXISTS felt text CHECK (felt IN ('yes', 'partly', 'no'));
ALTER TABLE daily_draws ADD COLUMN IF NOT EXISTS note text CHECK (char_length(note) <= 280);
ALTER TABLE daily_draws ADD COLUMN IF NOT EXISTS noted_at timestamptz;
ALTER TABLE daily_draws DROP CONSTRAINT IF EXISTS daily_draws_pkey;
ALTER TABLE daily_draws ALTER COLUMN guest_id DROP NOT NULL;
ALTER TABLE daily_draws DROP CONSTRAINT IF EXISTS daily_draws_one_owner;
ALTER TABLE daily_draws ADD CONSTRAINT daily_draws_one_owner CHECK ((guest_id IS NULL) <> (user_id IS NULL));
CREATE UNIQUE INDEX IF NOT EXISTS daily_draws_guest_day_key ON daily_draws (guest_id, day);
CREATE UNIQUE INDEX IF NOT EXISTS daily_draws_user_day_key ON daily_draws (user_id, day);
CREATE INDEX IF NOT EXISTS daily_draws_user_day_idx ON daily_draws (user_id, day DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS daily_draws_day_idx ON daily_draws (day);

-- endpoint: the push service address the browser gave (https, an allowed push host: app/webpush.py).
-- p256dh, auth: the browser's keys for the message encryption (RFC 8291), base64url.
-- tz: an IANA zone name as resolved by the API. hour: the local hour of the reminder.
-- fails: failed deliveries in a row (3 delete the row). last_sent_day: the local day of the last reminder, or of
-- the day it was skipped because the card was already open, so there is at most one a day.
-- active_at: the guest's last Card of the Day visit (guest rows without one for 90 days are deleted).
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid,
    guest_id      uuid,
    endpoint      text NOT NULL UNIQUE CHECK (char_length(endpoint) <= 1024),
    p256dh        text NOT NULL CHECK (char_length(p256dh) <= 200),
    auth          text NOT NULL CHECK (char_length(auth) <= 50),
    lang          text NOT NULL CHECK (lang IN ('en', 'es')),
    tz            text NOT NULL CHECK (char_length(tz) <= 64),
    hour          smallint NOT NULL CHECK (hour BETWEEN 0 AND 23),
    fails         smallint NOT NULL DEFAULT 0 CHECK (fails >= 0),
    last_sent_day date,
    created_at    timestamptz NOT NULL,
    active_at     timestamptz NOT NULL,
    CONSTRAINT push_subscriptions_one_owner CHECK ((guest_id IS NULL) <> (user_id IS NULL))
);
CREATE INDEX IF NOT EXISTS push_subscriptions_user_idx ON push_subscriptions (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS push_subscriptions_guest_idx ON push_subscriptions (guest_id) WHERE guest_id IS NOT NULL;
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;

ALTER TABLE events DROP CONSTRAINT IF EXISTS events_name_check;
ALTER TABLE events ADD CONSTRAINT events_name_check
    CHECK (name IN ('tool_view', 'draw_click', 'night_open', 'cards_revealed', 'reading_shown', 'save_click',
                    'signup_done', 'more_about_cards', 'outcome_answered', 'plus_view', 'remind_click',
                    'daily_felt', 'daily_calendar_view', 'push_enabled', 'push_click'));
```

Comments in a migration never end a line with `;` (`split_sql` cuts statements at `;` + newline).

In `api/app/db.py`, replace:

```python
              "claim_tokens", "profiles", "plus_waitlist", "deleted_accounts", "events")
```

with:

```python
              "claim_tokens", "profiles", "plus_waitlist", "deleted_accounts", "events", "push_subscriptions")
```

- [ ] **Step 6: Run the tests**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_db.py)
```

Expected: `54 passed`.

Run:

```bash
(cd api && .venv/bin/pytest -q )
```

Expected: `1649 passed` (1641 on main + 8).

- [ ] **Step 7: Commit**

```bash
git add api/migrations/009_daily_journal.sql api/app/db.py api/tests/test_db.py
git commit -m "feat(api): migration 009 — cards of the day by account, evening mark and note, browser reminders, four events (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: The card by account and the streaks in GET /api/daily

**Files:**
- Create: `api/app/journal.py` (streaks; Task 3 adds the months)
- Modify: `api/app/repo.py`, `api/app/routes/daily.py`
- Test: `api/tests/test_journal.py` (new), `api/tests/test_api_daily.py`
- Not modified: `api/app/draw.py` — `daily_draw(guest_id: str, …)` already takes any string; the account's seed is
  `daily_draw(str(user.id), day, order)` (an account id and a cookie id are both random UUIDs).

**Interfaces:**
- Consumes: Task 1 schema; `account_repo.lock_account`, `account_repo.refuse_deleted`; `routes.common.viewer`
  (`Viewer.user`, `.guest_id`, `.new_guest`); `limits.local_day`, `limits.resolve_tz`; `daily.daily_text`.
- Produces:
  - `journal.streaks(days: Iterable[date], today: date) -> tuple[int, int]` — `(current, best)`; current is the run
    ending today, or yesterday while today has no card; 0 otherwise.
  - `repo.DAILY_FIELDS = "day, card_id, reversed, felt, note, noted_at"`
  - `repo._daily_owner(user_id, guest_id) -> tuple[str, tuple]`
  - `repo.account_daily_draw(conn, user_id, day, card_id, reversed_) -> dict` (the row with `DAILY_FIELDS`)
  - `repo.draw_days(conn, user_id, guest_id) -> list[date]` (oldest first)
  - `repo.touch_guest_push(conn, guest_id, now) -> None`
  - `GET /api/daily` 200 adds `"streak": int, "best_streak": int, "mark": {"felt", "note"} | null` (null for a guest);
    signed in, the card is the account's; a deleted account's token → 401; before 009 → 503 `{"reason": "db"}`.

- [ ] **Step 1: Write the failing tests**

Create `api/tests/test_journal.py`:

```python
from datetime import date, timedelta

from app.journal import streaks

D = date(2026, 11, 27)


def days(*offsets: int) -> list[date]:
    return [D - timedelta(days=n) for n in offsets]


def test_a_streak_counts_the_days_in_a_row_up_to_today():
    assert streaks(days(0, 1, 2, 3), D) == (4, 4)


def test_today_without_a_card_keeps_yesterdays_run_alive():
    assert streaks(days(1, 2, 3), D) == (3, 3)


def test_a_missed_day_starts_again_and_the_best_run_stays():
    assert streaks(days(0, 2, 3, 4, 5, 6), D) == (1, 5)
    assert streaks(days(2, 3), D) == (0, 2)


def test_no_cards_no_streak():
    assert streaks([], D) == (0, 0)


def test_repeated_days_count_once():
    assert streaks(days(0, 0, 1), D) == (2, 2)
```

Append to the end of `api/tests/test_api_daily.py`:

```python
# --- stage 8.1: the card by account, streaks, the mark (spec 2026-11-27 §2, §3) ---

import psycopg  # noqa: E402
import pytest  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.db import Database, split_sql  # noqa: E402
from conftest import make_api  # noqa: E402
from helpers import bearer  # noqa: E402

ANA = uuid.UUID("8a1b2c3d-0000-4000-8000-000000000001")


def signed_in(api, user, client=None, lang="en"):
    response = (client or api.new_client()).get("/api/daily", params={"lang": lang, "tz": MX}, headers=bearer(user))
    assert response.status_code == 200, response.text
    return response.json()


def test_signed_in_the_card_is_the_accounts_on_every_device(api):
    phone, laptop = signed_in(api, ANA), signed_in(api, ANA)  # two clients: two guest cookies
    expected = daily_draw(str(ANA), date(2026, 11, 20), api.ctx.cards.order)
    assert (phone["card"]["card_id"], phone["card"]["reversed"]) == expected
    assert phone["card"] == laptop["card"] and phone["mark"] == {"felt": None, "note": None}
    with api.db.connect() as conn:
        rows = conn.execute("SELECT guest_id, user_id FROM daily_draws").fetchall()
    assert rows == [{"guest_id": None, "user_id": ANA}]  # an account row keeps no device


def test_a_guest_streak_counts_days_in_a_row_and_a_missed_day_starts_again(api):
    guest = uuid.uuid4()
    seen = []
    for step in (0, 1, 1, 2, 1):  # the 20th, 21st, 22nd, a missed 23rd, the 24th, 25th
        api.clock.advance(days=step)
        seen.append((daily(api, guest)["streak"], daily(api, guest)["best_streak"]))
    assert seen == [(1, 1), (2, 2), (3, 3), (1, 3), (2, 3)]


def test_a_new_guest_gets_day_one_and_no_mark(api):
    body = api.client.get("/api/daily", params={"lang": "en", "tz": MX}).json()
    assert (body["streak"], body["best_streak"], body["mark"]) == (1, 1, None)


def test_a_returning_guest_has_no_mark(api):
    assert daily(api, uuid.uuid4())["mark"] is None


def test_the_account_streak_spans_devices(api):
    signed_in(api, ANA)
    api.clock.advance(days=1)
    assert signed_in(api, ANA)["streak"] == 2


def test_a_deleted_account_gets_no_card(api):
    assert api.client.request("DELETE", "/api/account", json={"confirm": "DELETE"}, headers=bearer(ANA)).status_code == 200
    response = api.new_client().get("/api/daily", params={"lang": "en", "tz": MX}, headers=bearer(ANA))
    assert response.status_code == 401
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM daily_draws").fetchone()["n"] == 0


@pytest.fixture
def db_before_009(pg_url):
    """The live database before stage 8.1: migrations 001-008 only."""
    name = f"pre009_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(pg_url, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {name}")
    database = Database(pg_url.rsplit("/", 1)[0] + "/" + name)
    migrations = load_settings({}).migrations_dir
    with database.connect() as conn:
        for path in sorted(migrations.glob("00[1-8]_*.sql")):
            for statement in split_sql(path.read_text(encoding="utf-8")):
                conn.execute(statement)
    yield database
    with psycopg.connect(pg_url, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE {name} WITH (FORCE)")


def test_before_009_the_card_answers_503_not_500(db_before_009):
    """The review of 008: new code on a database whose migration has not run yet answers 503 (the site then shows
    the card from the card base), never 500."""
    api = make_api(db_before_009)
    guest = api.new_client().get("/api/daily", params={"lang": "en", "tz": MX}, headers=guest_headers(uuid.uuid4()))
    account = api.new_client().get("/api/daily", params={"lang": "en", "tz": MX}, headers=bearer(ANA))
    assert (guest.status_code, guest.json()) == (503, {"reason": "db"})
    assert (account.status_code, account.json()) == (503, {"reason": "db"})
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_journal.py tests/test_api_daily.py)
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.journal'`; in test_api_daily the new tests fail with `KeyError: 'streak'` and the account card equal to the cookie's draw.

- [ ] **Step 3: Implement**

Create `api/app/journal.py`:

```python
"""The Card of the Day as a habit (spec 2026-11-27 stage 8.1): streaks, months of the calendar, the month's most
frequent card. Pure functions over dates and rows; no database, no model. A note or a mark never passes here."""
from datetime import date, timedelta
from typing import Iterable


def streaks(days: Iterable[date], today: date) -> tuple[int, int]:
    """(current, best). current: the run of days in a row that ends today, or yesterday while today has no card
    yet (the run is not over until the day is); 0 otherwise. A missed day simply starts a new run (spec §2.6)."""
    run_at: dict[date, int] = {}
    best = 0
    previous: date | None = None
    for day in sorted(set(days)):
        run = run_at[previous] + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        run_at[day] = run
        best = max(best, run)
        previous = day
    current = run_at.get(today) or run_at.get(today - timedelta(days=1)) or 0
    return current, best
```

In `api/app/repo.py`, replace:

```python
def record_daily_draw(conn, guest_id, day, card_id: str, reversed_: bool) -> None:
    conn.execute("INSERT INTO daily_draws (guest_id, day, card_id, reversed) VALUES (%s, %s, %s, %s)"
                 " ON CONFLICT (guest_id, day) DO NOTHING", (guest_id, day, card_id, reversed_))
```

with:

```python
def record_daily_draw(conn, guest_id, day, card_id: str, reversed_: bool) -> None:
    conn.execute("INSERT INTO daily_draws (guest_id, day, card_id, reversed) VALUES (%s, %s, %s, %s)"
                 " ON CONFLICT (guest_id, day) DO NOTHING", (guest_id, day, card_id, reversed_))


DAILY_FIELDS = "day, card_id, reversed, felt, note, noted_at"


def _daily_owner(user_id, guest_id) -> tuple[str, tuple]:
    """Migration 009: a row belongs to an account (user_id) or to a guest cookie (guest_id), never both."""
    return ("user_id = %s", (user_id,)) if user_id is not None else ("guest_id = %s", (guest_id,))


def account_daily_draw(conn, user_id, day, card_id: str, reversed_: bool) -> dict:
    """Stage 8.1 §3: one card per account and day on every device. The first request of the day stores `card_id`;
    every later one (and a card claimed from this device's guest cookie) wins over it."""
    conn.execute("INSERT INTO daily_draws (user_id, day, card_id, reversed) VALUES (%s, %s, %s, %s)"
                 " ON CONFLICT (user_id, day) DO NOTHING", (user_id, day, card_id, reversed_))
    return conn.execute(f"SELECT {DAILY_FIELDS} FROM daily_draws WHERE user_id = %s AND day = %s",
                        (user_id, day)).fetchone()


def draw_days(conn, user_id, guest_id) -> list:
    """Every day with a card of this owner, oldest first (the streaks)."""
    where, args = _daily_owner(user_id, guest_id)
    return [r["day"] for r in conn.execute(f"SELECT day FROM daily_draws WHERE {where} ORDER BY day", args)]


def touch_guest_push(conn, guest_id, now) -> None:
    """A guest's reminder lives 90 days from the last Card of the Day visit (housekeeping)."""
    conn.execute("UPDATE push_subscriptions SET active_at = %s WHERE guest_id = %s", (now, guest_id))
```

Replace the whole of `api/app/routes/daily.py`:

```python
"""GET /api/daily (§2.6, §8.8; stage 8.1 §3): the card of the day and its text written ahead by the daily job. Signed
in, the card is the account's (one per local day on every device); otherwise this guest cookie's, as before. The
answer carries the streak and, for an account, today's evening mark. Never waits for the model; not counted in the
daily limit; rate-limited per address."""
from typing import Literal

from fastapi import APIRouter, Request

from app import account_repo, journal, limits, repo
from app.context import get_ctx
from app.daily import daily_text
from app.draw import daily_draw
from app.routes.common import respond, viewer

router = APIRouter(prefix="/api")


@router.get("/daily")
def daily(request: Request, lang: Literal["en", "es"], tz: str | None = None):
    ctx = get_ctx(request)
    now = ctx.clock()
    who = viewer(ctx, request)
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    if ctx.daily_burst.hit(ip_hash, now) > limits.DAILY_RATE_LIMIT:
        return respond(429, {"reason": "rate"}, who.new_guest)
    day = limits.local_day(limits.resolve_tz(tz), now)
    mark = None
    if who.user is not None:
        card_id, reversed_ = daily_draw(str(who.user.id), day, ctx.cards.order)
        with ctx.db.connect() as conn:
            account_repo.lock_account(conn, who.user.id)  # takes turns with delete_account
            account_repo.refuse_deleted(conn, who.user.id)
            row = repo.account_daily_draw(conn, who.user.id, day, card_id, reversed_)
            days = repo.draw_days(conn, who.user.id, None)
        card_id, reversed_ = row["card_id"], row["reversed"]
        mark = {"felt": row["felt"], "note": row["note"]}
    else:
        card_id, reversed_ = daily_draw(str(who.guest_id), day, ctx.cards.order)
        days = [day]
        if who.new_guest is None:  # a request without the cookie is not a returning guest: nothing to remember
            with ctx.db.connect() as conn:
                repo.record_daily_draw(conn, who.guest_id, day, card_id, reversed_)
                repo.touch_guest_push(conn, who.guest_id, now)
                days = repo.draw_days(conn, None, who.guest_id)
    streak, best = journal.streaks(days, day)
    payload = {"day": day.isoformat(),
               "card": {"card_id": card_id, "name": ctx.cards.name(card_id, lang), "reversed": reversed_},
               **daily_text(ctx, card_id, reversed_, lang, day),
               "streak": streak, "best_streak": best, "mark": mark}
    return respond(200, payload, who.new_guest)
```

- [ ] **Step 4: Run the tests**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_journal.py tests/test_api_daily.py)
```

Expected: `19 passed`.

Run:

```bash
(cd api && .venv/bin/pytest -q )
```

Expected: `1661 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/journal.py api/app/repo.py api/app/routes/daily.py api/tests/test_journal.py api/tests/test_api_daily.py
git commit -m "feat(api): the card of the day by account on every device, streaks in GET /api/daily (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: The calendar (GET /api/daily/calendar) and the mark (PUT /api/daily/{day})

**Files:**
- Modify: `api/app/journal.py`, `api/app/config.py`, `api/app/repo.py`, `api/app/daily.py`, `api/app/routes/daily.py`
- Test: `api/tests/test_journal.py`, `api/tests/test_api_daily_calendar.py` (new)

**Interfaces:**
- Consumes: Task 2 (`journal.streaks`, `repo._daily_owner`, `repo.DAILY_FIELDS`, `repo.draw_days`); `daily._excerpt`,
  `fallback.daily_fallback`; `routes.readings.reject_nul`; `routes.common.not_found`, `sign_in_required`.
- Produces:
  - `config.DAILY_NOTE_MAX_CHARS = 280`, `config.CALENDAR_GUEST_DAYS = 7`
  - `journal.parse_month(text) -> date | None`, `next_month(first) -> date`, `previous_month(first) -> date`,
    `month_key(first) -> str`, `free_months(today) -> tuple[date, date]`, `top_card(rows) -> tuple[str, int] | None`,
    `journal.TOP_CARD_MIN = 2`
  - `repo.calendar_rows(conn, user_id, guest_id, start, end, lang) -> list[dict]` (`DAILY_FIELDS` + `cached_text`)
  - `repo.set_daily_mark(conn, user_id, day, fields: dict, now) -> dict | None`
  - `daily.past_text(ctx, card_id, reversed_, lang, cached_text) -> {"text", "source"}`
  - `GET /api/daily/calendar?lang=en|es&month=YYYY-MM&tz=` → 200 `{"guest", "today", "month", "months", "locked",
    "streak", "best_streak", "top_card": {"card_id", "name", "count"} | null, "days": [{"day", "card": {"card_id",
    "name", "reversed"}, "text", "source", "felt"?, "note"?}]}`; a bad month → 422 `["month"]`.
  - `PUT /api/daily/{day}` `{"felt"?: "yes"|"partly"|"no"|null, "note"?: str<=280|null}` → 200 `{"day", "felt", "note",
    "noted_at"}`; guest → 401 `sign_in`; no card that day → 404; extra field / bad value / NUL → 422.

- [ ] **Step 1: Write the failing tests**

In `api/tests/test_journal.py`, replace:

```python
from app.journal import streaks
```

with:

```python
from app.journal import free_months, month_key, next_month, parse_month, previous_month, streaks, top_card
```

Append to the end of `api/tests/test_journal.py`:

```python
def test_months():
    assert parse_month("2026-11") == date(2026, 11, 1)
    for bad in ("2026-13", "2026-1", "26-11", "2026-11-01", "", "2026-00"):
        assert parse_month(bad) is None
    assert next_month(date(2026, 12, 1)) == date(2027, 1, 1)
    assert previous_month(date(2026, 1, 1)) == date(2025, 12, 1)
    assert month_key(date(2026, 3, 1)) == "2026-03"
    assert free_months(date(2026, 1, 15)) == (date(2025, 12, 1), date(2026, 1, 1))


def test_top_card_needs_two_and_a_tie_goes_to_the_latest():
    rows = [{"card_id": "a", "day": D - timedelta(days=5)}, {"card_id": "b", "day": D - timedelta(days=4)},
            {"card_id": "a", "day": D - timedelta(days=3)}, {"card_id": "b", "day": D - timedelta(days=1)}]
    assert top_card(rows) == ("b", 2)
    assert top_card(rows[:2]) is None
    assert top_card([]) is None
```

Create `api/tests/test_api_daily_calendar.py`:

```python
"""Stage 8.1 (spec 2026-11-27 §2.2-§2.4, §3, §4): the calendar of the Card of the Day and the evening mark."""
import uuid
from datetime import date, datetime, timezone

import pytest

from app import repo
from app.daily import fill_daily_cache
from app.draw import daily_draw
from app.reader import fallback
from helpers import bearer, dump_tables, guest_headers

MX = "America/Mexico_City"
ANA = uuid.UUID("8a1b2c3d-0000-4000-8000-000000000011")
BEN = uuid.UUID("8a1b2c3d-0000-4000-8000-000000000012")


def open_card(api, user=None, guest=None, lang="en"):
    headers = bearer(user) if user else guest_headers(guest)
    response = api.new_client().get("/api/daily", params={"lang": lang, "tz": MX}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def calendar(api, user=None, guest=None, **params):
    headers = bearer(user) if user else (guest_headers(guest) if guest else {})
    return api.new_client().get("/api/daily/calendar", params={"lang": "en", "tz": MX, **params}, headers=headers)


def mark(api, user, day, body):
    return api.new_client().put(f"/api/daily/{day}", json=body, headers=bearer(user) if user else {})


def days_in_a_row(api, n, **who):
    for i in range(n):
        if i:
            api.clock.advance(days=1)
        open_card(api, **who)


def test_the_month_has_each_day_with_its_card_text_mark_and_note(api):
    days_in_a_row(api, 3, user=ANA)  # the 20th, 21st, 22nd of November in Mexico City
    assert mark(api, ANA, "2026-11-21", {"felt": "partly", "note": "Kept the word: patience."}).status_code == 200
    body = calendar(api, user=ANA, month="2026-11").json()
    assert (body["guest"], body["month"], body["months"], body["locked"]) == (False, "2026-11", ["2026-10", "2026-11"],
                                                                            False)
    assert (body["today"], body["streak"], body["best_streak"]) == ("2026-11-22", 3, 3)
    assert [d["day"] for d in body["days"]] == ["2026-11-20", "2026-11-21", "2026-11-22"]
    second = body["days"][1]
    card_id, reversed_ = daily_draw(str(ANA), date(2026, 11, 21), api.ctx.cards.order)
    assert second["card"] == {"card_id": card_id, "name": api.ctx.cards.name(card_id, "en"), "reversed": reversed_}
    assert (second["felt"], second["note"]) == ("partly", "Kept the word: patience.")
    assert body["days"][0]["felt"] is None and body["days"][0]["note"] is None


def test_a_days_text_is_the_cached_one_then_the_card_base(api):
    open_card(api, user=ANA)
    card_id, reversed_ = daily_draw(str(ANA), date(2026, 11, 20), api.ctx.cards.order)
    [first] = calendar(api, user=ANA).json()["days"]
    [ex] = api.ctx.cards.excerpts([{"card_id": card_id, "position": "card", "reversed": reversed_}], "en", None)
    assert (first["source"], first["text"]) == ("fallback", fallback.daily_fallback(ex))
    fill_daily_cache(api.ctx, date(2026, 11, 20), [card_id])
    [cached] = calendar(api, user=ANA).json()["days"]
    assert cached["source"] == "cache" and cached["text"] != first["text"]


def test_the_month_defaults_to_this_one_and_the_free_calendar_is_two_months(api):
    open_card(api, user=ANA)
    assert calendar(api, user=ANA).json()["month"] == "2026-11"
    october = calendar(api, user=ANA, month="2026-10").json()
    assert (october["locked"], october["days"]) == (False, [])
    september = calendar(api, user=ANA, month="2026-09").json()
    assert (september["locked"], september["days"], september["streak"]) == (True, [], 1)  # kept, for Plus


def test_an_old_month_is_kept_but_locked(api):
    api.clock.now = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)
    open_card(api, user=ANA)
    api.clock.now = datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)
    assert calendar(api, user=ANA, month="2026-08").json()["locked"] is True
    with api.db.connect() as conn:
        assert repo.draw_days(conn, ANA, None) == [date(2026, 8, 10)]


@pytest.mark.parametrize("month", ["2026-13", "11-2026", "2026-1", "x"])
def test_a_bad_month_is_422(api, month):
    response = calendar(api, user=ANA, month=month)
    assert response.status_code == 422 and response.json()["fields"] == ["month"]


def test_the_most_frequent_card_needs_two(api):
    open_card(api, user=ANA)
    assert calendar(api, user=ANA).json()["top_card"] is None
    card_id, reversed_ = daily_draw(str(ANA), date(2026, 11, 20), api.ctx.cards.order)
    with api.db.connect() as conn:
        conn.execute("INSERT INTO daily_draws (user_id, day, card_id, reversed) VALUES (%s, %s, %s, %s)",
                     (ANA, date(2026, 11, 3), card_id, not reversed_))
    top = calendar(api, user=ANA).json()["top_card"]
    assert top == {"card_id": card_id, "name": api.ctx.cards.name(card_id, "en"), "count": 2}


def test_a_guest_sees_the_last_seven_days_without_marks(api):
    guest = uuid.uuid4()
    days_in_a_row(api, 9, guest=guest)  # the 20th to the 28th
    body = calendar(api, guest=guest, month="2026-10").json()  # the month is ignored for a guest
    assert (body["guest"], body["today"], body["streak"], body["best_streak"]) == (True, "2026-11-28", 9, 9)
    assert [d["day"] for d in body["days"]] == [f"2026-11-{n}" for n in range(22, 29)]
    assert all(set(d) == {"day", "card", "text", "source"} for d in body["days"])


def test_a_new_guest_has_an_empty_calendar_and_gets_the_cookie(api):
    response = calendar(api)
    assert response.status_code == 200 and response.json()["days"] == [] and "ad_guest=" in response.headers["set-cookie"]


def test_the_mark_sets_changes_and_clears(api):
    open_card(api, user=ANA)
    first = mark(api, ANA, "2026-11-20", {"felt": "yes"}).json()
    assert (first["felt"], first["note"]) == ("yes", None) and first["noted_at"]
    both = mark(api, ANA, "2026-11-20", {"note": "  The talk went well.  "}).json()
    assert (both["felt"], both["note"]) == ("yes", "  The talk went well.  ")  # stored exactly as sent
    cleared = mark(api, ANA, "2026-11-20", {"felt": None, "note": "   "}).json()
    assert (cleared["felt"], cleared["note"], cleared["noted_at"]) == (None, None, None)
    unchanged = mark(api, ANA, "2026-11-20", {}).json()
    assert (unchanged["felt"], unchanged["note"]) == (None, None)


def test_the_mark_needs_an_account_and_a_card_that_day(api):
    guest = uuid.uuid4()
    open_card(api, guest=guest)
    assert mark(api, None, "2026-11-20", {"felt": "yes"}).json() == {"reason": "sign_in"}
    open_card(api, user=ANA)
    assert mark(api, ANA, "2026-11-19", {"felt": "yes"}).status_code == 404  # no card that day
    assert mark(api, BEN, "2026-11-20", {"felt": "yes"}).status_code == 404  # another account's day
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM daily_draws WHERE user_id = %s", (BEN,)).fetchone()["n"] == 0


@pytest.mark.parametrize("body, field", [
    ({"felt": "maybe"}, "felt"),
    ({"note": "x" * 281}, "note"),
    ({"note": "a\x00b"}, "note"),
    ({"felt": "yes", "mood": "fine"}, "mood"),
])
def test_a_bad_mark_is_422(api, body, field):
    open_card(api, user=ANA)
    response = mark(api, ANA, "2026-11-20", body)
    assert response.status_code == 422 and response.json()["fields"] == [field]


def test_a_note_of_280_characters_fits_and_is_never_in_an_event_or_a_model_call(api):
    open_card(api, user=ANA)
    note = "é" * 280
    assert mark(api, ANA, "2026-11-20", {"note": note}).status_code == 200
    with api.db.connect() as conn:
        events = conn.execute("SELECT count(*) AS n FROM events").fetchone()["n"]
    assert events == 0 and api.reader.stream_calls() == []
    assert note in dump_tables(api.db)  # only in daily_draws
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_journal.py tests/test_api_daily_calendar.py)
```

Expected: FAIL — `ImportError: cannot import name 'free_months' from 'app.journal'`; the calendar tests get 404 (`/api/daily/calendar` and `PUT /api/daily/{day}` do not exist yet).

- [ ] **Step 3: Implement**

In `api/app/journal.py`, replace:

```python
from datetime import date, timedelta
from typing import Iterable
```

with:

```python
import re
from collections import Counter
from datetime import date, timedelta
from typing import Iterable

MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
TOP_CARD_MIN = 2  # a card that came once is not "the most frequent": below this the line is not shown
```

Append to the end of `api/app/journal.py`:

```python
def parse_month(text: str) -> date | None:
    """"2026-11" → date(2026, 11, 1); anything else → None."""
    match = MONTH.fullmatch(text)
    return date(int(match.group(1)), int(match.group(2)), 1) if match else None


def next_month(first: date) -> date:
    return date(first.year + (first.month == 12), first.month % 12 + 1, 1)


def previous_month(first: date) -> date:
    return date(first.year - (first.month == 1), (first.month - 2) % 12 + 1, 1)


def month_key(first: date) -> str:
    return f"{first.year:04d}-{first.month:02d}"


def free_months(today: date) -> tuple[date, date]:
    """Spec §2: the free calendar shows the current and the previous month (first days); older ones are kept."""
    current = today.replace(day=1)
    return previous_month(current), current


def top_card(rows: list[dict]) -> tuple[str, int] | None:
    """The card (by id, either orientation) that came most often among `rows`, with its count; a tie goes to the card
    that came last. None when no card came at least TOP_CARD_MIN times."""
    counts = Counter(row["card_id"] for row in rows)
    if not counts:
        return None
    last = {row["card_id"]: row["day"] for row in rows}
    card_id = max(counts, key=lambda c: (counts[c], last[c]))
    return (card_id, counts[card_id]) if counts[card_id] >= TOP_CARD_MIN else None
```

In `api/app/config.py`, replace:

```python
FREE_DIARY_VISIBLE = 10        # stage 4.4b §5 (decision 9): the diary lists the newest 10; older ones are hidden, kept
```

with:

```python
FREE_DIARY_VISIBLE = 10        # stage 4.4b §5 (decision 9): the diary lists the newest 10; older ones are hidden, kept
DAILY_NOTE_MAX_CHARS = 280     # stage 8.1 §2.3: the one-line note under the Card of the Day (never sent to a model)
CALENDAR_GUEST_DAYS = 7        # stage 8.1 §2.4: a guest's calendar shows this device's last 7 days, without marks
```

In `api/app/repo.py`, replace:

```python
def touch_guest_push(conn, guest_id, now) -> None:
```

with:

```python
def calendar_rows(conn, user_id, guest_id, start, end, lang: str) -> list[dict]:
    """The owner's cards from `start` to before `end`, oldest first, each with the text the daily job cached for
    it in `lang` (cached_text, None once the cache is gone: the caller then uses the card base)."""
    where, args = _daily_owner(user_id, guest_id)
    return conn.execute(
        f"SELECT d.day, d.card_id, d.reversed, d.felt, d.note, d.noted_at, c.text AS cached_text FROM daily_draws d"
        " LEFT JOIN daily_cache c ON c.card_id = d.card_id AND c.reversed = d.reversed AND c.day = d.day"
        f" AND c.lang = %s WHERE d.{where} AND d.day >= %s AND d.day < %s ORDER BY d.day",
        (lang, *args, start, end)).fetchall()


def set_daily_mark(conn, user_id, day, fields: dict, now) -> dict | None:
    """Stage 8.1 §3: only the fields present in `fields` ("felt", "note") change; noted_at is `now`, or NULL once
    both are empty. None when the account has no card that day (a card is never drawn after the fact)."""
    row = conn.execute("SELECT felt, note FROM daily_draws WHERE user_id = %s AND day = %s FOR UPDATE",
                       (user_id, day)).fetchone()
    if row is None:
        return None
    if not fields:
        return conn.execute(f"SELECT {DAILY_FIELDS} FROM daily_draws WHERE user_id = %s AND day = %s",
                            (user_id, day)).fetchone()
    felt = fields["felt"] if "felt" in fields else row["felt"]
    note = fields["note"] if "note" in fields else row["note"]
    noted_at = None if felt is None and note is None else now
    return conn.execute(f"UPDATE daily_draws SET felt = %s, note = %s, noted_at = %s WHERE user_id = %s AND day = %s"
                        f" RETURNING {DAILY_FIELDS}", (felt, note, noted_at, user_id, day)).fetchone()


def touch_guest_push(conn, guest_id, now) -> None:
```

In `api/app/daily.py`, replace:

```python
def daily_text(ctx, card_id: str, reversed_: bool, lang: str, day: date) -> dict:
```

with:

```python
def past_text(ctx, card_id: str, reversed_: bool, lang: str, cached_text: str | None) -> dict:
    """Stage 8.1 §4: a calendar day's text — the cached one while the cache keeps it, then the card base."""
    if cached_text:
        return {"text": cached_text, "source": "cache"}
    return {"text": fallback.daily_fallback(_excerpt(ctx, card_id, reversed_, lang)), "source": "fallback"}


def daily_text(ctx, card_id: str, reversed_: bool, lang: str, day: date) -> dict:
```

In `api/app/routes/daily.py`, the module docstring and the imports, replace:

```python
"""GET /api/daily (§2.6, §8.8; stage 8.1 §3): the card of the day and its text written ahead by the daily job. Signed
in, the card is the account's (one per local day on every device); otherwise this guest cookie's, as before. The
answer carries the streak and, for an account, today's evening mark. Never waits for the model; not counted in the
daily limit; rate-limited per address."""
from typing import Literal

from fastapi import APIRouter, Request

from app import account_repo, journal, limits, repo
from app.context import get_ctx
from app.daily import daily_text
from app.draw import daily_draw
from app.routes.common import respond, viewer
```

with:

```python
"""The Card of the Day (§2.6, §8.8; stage 8.1 §2-§4).

- GET /api/daily: the card and its text written ahead by the daily job. Signed in, the card is the account's (one
  per local day on every device); otherwise this guest cookie's, as before. The answer carries the streak and, for
  an account, today's evening mark. Never waits for the model; not counted in the daily limit; rate-limited per
  address.
- GET /api/daily/calendar?month=YYYY-MM: the account's cards of a month with their texts, marks and notes, the
  streaks and the month's most frequent card; the free calendar opens the current and the previous month, older
  months answer "locked" (kept, for Plus). A guest gets this device's last CALENDAR_GUEST_DAYS days, without marks
  or notes, whatever the month.
- PUT /api/daily/{day} {"felt", "note"} (signed in): the evening mark and the one-line note of a day that has a
  card; a day without one is 404 (a card is never drawn after the fact).

The note and the mark are stored exactly as sent, returned only as JSON and shown as text; no model and no event
ever gets them.
"""
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import account_repo, journal, limits, repo
from app.config import CALENDAR_GUEST_DAYS, DAILY_NOTE_MAX_CHARS
from app.context import get_ctx
from app.daily import daily_text, past_text
from app.draw import daily_draw
from app.routes.common import not_found, respond, sign_in_required, viewer
from app.routes.readings import reject_nul
```

Append to the end of `api/app/routes/daily.py`:

```python
class DailyMark(BaseModel):
    model_config = ConfigDict(extra="forbid")
    felt: Literal["yes", "partly", "no"] | None = None
    note: str | None = Field(default=None, max_length=DAILY_NOTE_MAX_CHARS)

    _no_nul = field_validator("note", mode="after")(reject_nul)


def calendar_day(ctx, row: dict, lang: str, with_mark: bool) -> dict:
    item = {"day": row["day"].isoformat(),
            "card": {"card_id": row["card_id"], "name": ctx.cards.name(row["card_id"], lang),
                     "reversed": row["reversed"]},
            **past_text(ctx, row["card_id"], row["reversed"], lang, row["cached_text"])}
    if with_mark:
        item.update(felt=row["felt"], note=row["note"])
    return item


@router.get("/daily/calendar")
def calendar(request: Request, lang: Literal["en", "es"], month: str | None = Query(default=None, max_length=7),
             tz: str | None = None):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    today = limits.local_day(limits.resolve_tz(tz), ctx.clock())
    if who.user is None:
        rows, days = [], []
        if who.new_guest is None:
            with ctx.db.connect() as conn:
                rows = repo.calendar_rows(conn, None, who.guest_id, today - timedelta(days=CALENDAR_GUEST_DAYS - 1),
                                          today + timedelta(days=1), lang)
                days = repo.draw_days(conn, None, who.guest_id)
        streak, best = journal.streaks(days, today)
        return respond(200, {"guest": True, "today": today.isoformat(), "month": None, "months": [], "locked": False,
                             "streak": streak, "best_streak": best, "top_card": None,
                             "days": [calendar_day(ctx, r, lang, with_mark=False) for r in rows]}, who.new_guest)
    first = journal.parse_month(month) if month else today.replace(day=1)
    if first is None:
        return respond(422, {"reason": "invalid", "fields": ["month"]})
    oldest, current = journal.free_months(today)
    locked = first < oldest
    with ctx.db.connect() as conn:
        days = repo.draw_days(conn, who.user.id, None)
        rows = [] if locked else repo.calendar_rows(conn, who.user.id, None, first, journal.next_month(first), lang)
    streak, best = journal.streaks(days, today)
    top = journal.top_card(rows)
    return respond(200, {
        "guest": False, "today": today.isoformat(), "month": journal.month_key(first),
        "months": [journal.month_key(oldest), journal.month_key(current)], "locked": locked,
        "streak": streak, "best_streak": best,
        "top_card": {"card_id": top[0], "name": ctx.cards.name(top[0], lang), "count": top[1]} if top else None,
        "days": [calendar_day(ctx, r, lang, with_mark=True) for r in rows]}, who.new_guest)


@router.put("/daily/{day}")
def mark_day(day: date, body: DailyMark, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()  # spec §2.4: marks and notes only after sign-in
    fields = body.model_dump(include=body.model_fields_set)
    if fields.get("note") is not None and not fields["note"].strip():
        fields["note"] = None  # an empty note is no note
    with ctx.db.connect() as conn:
        row = repo.set_daily_mark(conn, who.user.id, day, fields, ctx.clock())
    if row is None:
        return not_found()
    return respond(200, {"day": row["day"].isoformat(), "felt": row["felt"], "note": row["note"],
                         "noted_at": row["noted_at"]})
```

- [ ] **Step 4: Run the tests**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_journal.py tests/test_api_daily.py tests/test_api_daily_calendar.py)
```

Expected: `39 passed`.

Run:

```bash
(cd api && .venv/bin/pytest -q )
```

Expected: `1681 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/journal.py api/app/config.py api/app/repo.py api/app/daily.py api/app/routes/daily.py api/tests/test_journal.py api/tests/test_api_daily_calendar.py
git commit -m "feat(api): Card of the Day calendar and the evening mark and note (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: Sign-in claim, export, account deletion and retention

**Files:**
- Modify: `api/app/account_repo.py`, `api/app/routes/claim.py`, `api/app/routes/account.py`, `api/app/housekeeping.py`
- Test: `api/tests/test_api_claim.py`, `api/tests/test_api_account.py`, `api/tests/test_housekeeping.py`

**Interfaces:**
- Consumes: Tasks 1–3 (`daily_draws` owners, `push_subscriptions`, `repo.account_daily_draw`, `repo.draw_days`,
  `PUT /api/daily/{day}`); `account_repo.ensure_profile` (takes the account lock).
- Produces:
  - `account_repo.claim_daily(conn, user_id, guest_id) -> int` (moved rows; a day the account has keeps the account's
    card, the device's card of that day is deleted), `account_repo.claim_push(conn, user_id, guest_id) -> int`
  - `account_repo.export_daily(conn, user_id) -> list[dict]`, `account_repo.export_push(conn, user_id) -> list[dict]`
  - `account_repo.delete_account` counts gain `"daily_draws"` and `"push_subscriptions"`
  - `POST /api/account/claim` with `device` true (or left out) moves this cookie's cards and reminders; the answer stays
    `{"claimed": [...]}` (16 existing tests compare it exactly).
  - `GET /api/account/export` adds `"daily_cards": [{"day", "card_id", "name_en", "name_es", "reversed", "felt", "note",
    "noted_at"}]` and `"push_subscriptions": [{"service", "hour", "tz", "lang", "created_at", "last_sent_day"}]` (the
    push host only: no endpoint, no keys).
  - `housekeeping.KEEP_DAILY_CACHE_DAYS = 62` (was 2; owner decision 54 — about 312 × 62 ≈ 19 400 rows, no model
    call: the daily job still writes only yesterday..tomorrow)
  - `housekeeping.KEEP_GUEST_DAILY_DRAWS_DAYS = 60`, `KEEP_GUEST_PUSH_DAYS = 90` (replace `KEEP_DAILY_DRAWS_DAYS`);
    `delete_expired` counts gain `"push_subscriptions"`.

- [ ] **Step 1: Write the failing tests**

Append to the end of `api/tests/test_api_claim.py`:

```python
# --- stage 8.1 §3: the cards of the day and the reminders of this device move with the sign-in ---
from datetime import date  # noqa: E402

from app.draw import daily_draw  # noqa: E402


def guest_card(api, client, lang="en"):
    response = client.get("/api/daily", params={"lang": lang, "tz": MX})
    assert response.status_code == 200, response.text
    return response.json()


def test_signing_in_moves_this_devices_cards_of_the_day(api):
    client = api.new_client()
    guest_card(api, client)  # the first request sets the cookie and stores nothing
    first = guest_card(api, client)
    api.clock.advance(days=1)
    guest_card(api, client)
    assert claim(client, ANA).json() == {"claimed": []}
    with api.db.connect() as conn:
        rows = conn.execute("SELECT guest_id, user_id, day, card_id FROM daily_draws ORDER BY day").fetchall()
    assert [(r["guest_id"], r["user_id"], r["day"]) for r in rows] == [(None, ANA, date(2026, 11, 20)),
                                                                       (None, ANA, date(2026, 11, 21))]
    assert rows[0]["card_id"] == first["card"]["card_id"]
    signed = client.get("/api/daily", params={"lang": "en", "tz": MX}, headers=bearer(ANA)).json()
    assert signed["streak"] == 2  # the device's days count for the account now


def test_a_day_the_account_already_has_keeps_the_accounts_card(api):
    phone = api.new_client()
    assert phone.get("/api/daily", params={"lang": "en", "tz": MX}, headers=bearer(ANA)).status_code == 200
    laptop = api.new_client()
    guest_card(api, laptop)
    guest_card(api, laptop)
    claim(laptop, ANA)
    with api.db.connect() as conn:
        rows = conn.execute("SELECT guest_id, user_id, card_id, reversed FROM daily_draws").fetchall()
    expected = daily_draw(str(ANA), date(2026, 11, 20), api.ctx.cards.order)
    assert [(r["guest_id"], r["user_id"], (r["card_id"], r["reversed"])) for r in rows] == [(None, ANA, expected)]


def test_device_false_leaves_this_devices_cards_and_reminders(api):
    client = api.new_client()
    guest_card(api, client)
    guest_card(api, client)
    guest = uuid.UUID(client.cookies["ad_guest"])
    with api.db.connect() as conn:
        conn.execute("INSERT INTO push_subscriptions (guest_id, endpoint, p256dh, auth, lang, tz, hour, created_at,"
                     " active_at) VALUES (%s, 'https://fcm.googleapis.com/fcm/send/x', 'k', 'a', 'en', 'UTC', 8, now(),"
                     " now())", (guest,))
    response = client.post("/api/account/claim", headers=bearer(ANA), json={"device": False})
    assert response.json() == {"claimed": []}
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM daily_draws WHERE guest_id = %s", (guest,)).fetchone()["n"] == 1
        assert conn.execute("SELECT user_id FROM push_subscriptions").fetchone()["user_id"] is None


def test_signing_in_moves_this_devices_reminders(api):
    client = api.new_client()
    guest_card(api, client)
    guest = uuid.UUID(client.cookies["ad_guest"])
    with api.db.connect() as conn:
        conn.execute("INSERT INTO push_subscriptions (guest_id, endpoint, p256dh, auth, lang, tz, hour, created_at,"
                     " active_at) VALUES (%s, 'https://fcm.googleapis.com/fcm/send/x', 'k', 'a', 'en', 'UTC', 8, now(),"
                     " now())", (guest,))
    claim(client, ANA)
    with api.db.connect() as conn:
        row = conn.execute("SELECT user_id, guest_id FROM push_subscriptions").fetchone()
    assert row == {"user_id": ANA, "guest_id": None}
```

Append to the end of `api/tests/test_api_account.py`:

```python
# --- stage 8.1 §3: the export has the cards of the day and the reminders; deleting the account takes them ---
from datetime import date  # noqa: E402

from app.draw import daily_draw  # noqa: E402


def card_today(api, user):
    response = api.new_client().get("/api/daily", params={"lang": "en", "tz": MX}, headers=bearer(user))
    assert response.status_code == 200, response.text


def add_reminder(api, user, endpoint="https://fcm.googleapis.com/fcm/send/abc"):
    with api.db.connect() as conn:
        conn.execute("INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, lang, tz, hour, created_at,"
                     " active_at) VALUES (%s, %s, 'k', 'secret-auth', 'en', 'America/Mexico_City', 8, %s, %s)",
                     (user, endpoint, api.clock(), api.clock()))


def test_the_export_has_the_cards_of_the_day_and_the_reminders_without_their_keys(api):
    card_today(api, ANA)
    api.client.put("/api/daily/2026-11-20", json={"felt": "yes", "note": "It did."}, headers=bearer(ANA))
    add_reminder(api, ANA)
    response = api.client.get("/api/account/export", headers=bearer(ANA))
    body = response.json()
    card_id, reversed_ = daily_draw(str(ANA), date(2026, 11, 20), api.ctx.cards.order)
    [card] = body["daily_cards"]
    assert (card["day"], card["card_id"], card["reversed"], card["felt"], card["note"]) == (
        "2026-11-20", card_id, reversed_, "yes", "It did.")
    assert card["name_en"] == api.ctx.cards.name(card_id, "en") and card["name_es"] == api.ctx.cards.name(card_id, "es")
    [sub] = body["push_subscriptions"]
    assert (sub["service"], sub["hour"], sub["tz"], sub["lang"]) == ("fcm.googleapis.com", 8, MX, "en")
    assert "secret-auth" not in response.text and "/fcm/send/abc" not in response.text


def test_deleting_the_account_takes_its_cards_marks_and_reminders(api):
    card_today(api, ANA)
    card_today(api, BEN)
    api.client.put("/api/daily/2026-11-20", json={"note": "Private line."}, headers=bearer(ANA))
    add_reminder(api, ANA)
    add_reminder(api, BEN, endpoint="https://fcm.googleapis.com/fcm/send/ben")
    assert delete_account(api, confirm="DELETE").status_code == 200
    assert count(api, "SELECT count(*) AS n FROM daily_draws WHERE user_id = %s", ANA) == 0
    assert count(api, "SELECT count(*) AS n FROM push_subscriptions WHERE user_id = %s", ANA) == 0
    assert count(api, "SELECT count(*) AS n FROM daily_draws WHERE user_id = %s", BEN) == 1
    assert count(api, "SELECT count(*) AS n FROM push_subscriptions WHERE user_id = %s", BEN) == 1
    assert "Private line." not in dump_tables(api.db)
```

In `api/tests/test_housekeeping.py`, in `test_delete_stale_counters_caches_and_old_logs`, replace:

```python
        for day in (today, today - timedelta(days=3)):
            conn.execute("INSERT INTO usage (subject, day, count) VALUES ('ip:x', %s, 1)", (day,))
            repo.put_daily_cache(conn, {"card_id": "major-18-moon", "reversed": False, "lang": "en", "day": day,
                                        "text": "T.", "model": "m", "prompt_version": "daily.en.v1"})
```

with:

```python
        for day in (today, today - timedelta(days=3)):
            conn.execute("INSERT INTO usage (subject, day, count) VALUES ('ip:x', %s, 1)", (day,))
        for day in (today - timedelta(days=61), today - timedelta(days=63)):  # stage 8.1: the cache keeps 62 days
            repo.put_daily_cache(conn, {"card_id": "major-18-moon", "reversed": False, "lang": "en", "day": day,
                                        "text": "T.", "model": "m", "prompt_version": "daily.en.v1"})
```

In `api/tests/test_housekeeping.py`, replace:

```python
        repo.record_daily_draw(conn, uuid.uuid4(), today - timedelta(days=8), "major-18-moon", False)
        repo.record_daily_draw(conn, uuid.uuid4(), today, "major-18-moon", False)
```

with:

```python
        repo.record_daily_draw(conn, uuid.uuid4(), today - timedelta(days=61), "major-18-moon", False)
        repo.record_daily_draw(conn, uuid.uuid4(), today - timedelta(days=59), "major-18-moon", False)
```

In `api/tests/test_housekeeping.py`, replace:

```python
    assert delete_expired(db, T0) == {"readings": 0, "usage": 1, "daily_cache": 1, "daily_draws": 1,
                                      "llm_calls": 1, "guard_events": 1, "events": 0, "plus_waitlist": 0, "claim_tokens": 0, "deleted_accounts": 0,
                                      "followup_tombstones": 0}
```

with:

```python
    assert delete_expired(db, T0) == {"readings": 0, "usage": 1, "daily_cache": 1, "daily_draws": 1,
                                      "push_subscriptions": 0, "llm_calls": 1, "guard_events": 1, "events": 0,
                                      "plus_waitlist": 0, "claim_tokens": 0, "deleted_accounts": 0,
                                      "followup_tombstones": 0}
```

Append to the end of `api/tests/test_housekeeping.py`:

```python
# --- stage 8.1: retention of the cards of the day and of browser reminders (spec 2026-11-27 §4) ---

def push_row(conn, *, user_id=None, guest_id=None, active_at=T0, endpoint=None) -> None:
    conn.execute("INSERT INTO push_subscriptions (user_id, guest_id, endpoint, p256dh, auth, lang, tz, hour,"
                 " created_at, active_at) VALUES (%s, %s, %s, 'k', 'a', 'en', 'UTC', 8, %s, %s)",
                 (user_id, guest_id, endpoint or f"https://fcm.googleapis.com/fcm/send/{uuid.uuid4()}", active_at,
                  active_at))


def test_guest_cards_of_the_day_go_after_60_days_an_accounts_stay(db):
    today, user = T0.date(), uuid.uuid4()
    with db.connect() as conn:
        repo.record_daily_draw(conn, uuid.uuid4(), today - timedelta(days=61), "major-18-moon", False)
        repo.account_daily_draw(conn, user, today - timedelta(days=400), "major-18-moon", False)
    assert delete_expired(db, T0)["daily_draws"] == 1
    with db.connect() as conn:
        assert repo.draw_days(conn, user, None) == [today - timedelta(days=400)]


def test_guest_reminders_go_90_days_after_the_last_visit_an_accounts_stay(db):
    with db.connect() as conn:
        push_row(conn, guest_id=uuid.uuid4(), active_at=T0 - timedelta(days=91))
        push_row(conn, guest_id=uuid.uuid4(), active_at=T0 - timedelta(days=89))
        push_row(conn, user_id=uuid.uuid4(), active_at=T0 - timedelta(days=400))
    assert delete_expired(db, T0)["push_subscriptions"] == 1
    assert count(db, "push_subscriptions") == 2
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_api_claim.py tests/test_api_account.py tests/test_housekeeping.py)
```

Expected: FAIL — the claimed cards stay with `guest_id` (`assert [(UUID(...), None, ...)] == [(None, ANA, ...)]`), `KeyError: 'daily_cards'` in the export, the deleted account's rows remain, and `delete_expired` removes the 59-day guest card and the 61-day cached text and has no `push_subscriptions` key.

- [ ] **Step 3: Implement**

In `api/app/account_repo.py`, replace:

```python
def ensure_profile(conn, user_id, now) -> dict:
```

with:

```python
def claim_daily(conn, user_id, guest_id) -> int:
    """Stage 8.1 §3: signing in moves this cookie's cards of the day into the account; on a day the account already
    has a card, the account's card stays and the device's card of that day goes. Returns the number moved."""
    conn.execute("DELETE FROM daily_draws g WHERE g.guest_id = %s"
                 " AND EXISTS (SELECT 1 FROM daily_draws a WHERE a.user_id = %s AND a.day = g.day)", (guest_id, user_id))
    return conn.execute("UPDATE daily_draws SET user_id = %s, guest_id = NULL WHERE guest_id = %s",
                        (user_id, guest_id)).rowcount


def claim_push(conn, user_id, guest_id) -> int:
    """This cookie's browser reminders follow the cards into the account (the "card already open" check then looks
    at the account's card)."""
    return conn.execute("UPDATE push_subscriptions SET user_id = %s, guest_id = NULL WHERE guest_id = %s",
                        (user_id, guest_id)).rowcount


def ensure_profile(conn, user_id, now) -> dict:
```

In `api/app/account_repo.py`, replace:

```python
def waitlist_entry(conn, user_id, email: str | None) -> dict | None:
```

with:

```python
def export_daily(conn, user_id) -> list[dict]:
    """Stage 8.1 §3: every card of the day of the account, oldest first, with its mark and note."""
    return conn.execute("SELECT day, card_id, reversed, felt, note, noted_at FROM daily_draws WHERE user_id = %s"
                        " ORDER BY day", (user_id,)).fetchall()


def export_push(conn, user_id) -> list[dict]:
    """The account's browser reminders; the export names the push service, not the endpoint or its keys."""
    return conn.execute("SELECT endpoint, hour, tz, lang, created_at, last_sent_day FROM push_subscriptions"
                        " WHERE user_id = %s ORDER BY created_at", (user_id,)).fetchall()


def waitlist_entry(conn, user_id, email: str | None) -> dict | None:
```

In `api/app/account_repo.py`, replace:

```python
    """§8: everything of the account at once — its readings (their follow-ups and claim tokens go with them), the
    profile, the Plus waitlist entry and,
```

with:

```python
    """§8: everything of the account at once — its readings (their follow-ups and claim tokens go with them), the
    profile, its cards of the day with their marks and notes and its browser reminders (stage 8.1), the Plus
    waitlist entry and,
```

In `api/app/account_repo.py`, replace:

```python
        "profiles": conn.execute("DELETE FROM profiles WHERE user_id = %s", (user_id,)).rowcount,
```

with:

```python
        "profiles": conn.execute("DELETE FROM profiles WHERE user_id = %s", (user_id,)).rowcount,
        "daily_draws": conn.execute("DELETE FROM daily_draws WHERE user_id = %s", (user_id,)).rowcount,
        "push_subscriptions": conn.execute("DELETE FROM push_subscriptions WHERE user_id = %s", (user_id,)).rowcount,
```

In `api/app/routes/claim.py`, replace:

```python
  readings stay there); left out, it is true, as in 4.3.
"""
```

with:

```python
  readings stay there); left out, it is true, as in 4.3.
- Stage 8.1 §3: with "device" true the same call also moves this cookie's cards of the day (a day the account
  already has keeps the account's card) and its browser reminders. The answer stays {"claimed": [...]}.
"""
```

In `api/app/routes/claim.py`, replace:

```python
        moved = account_repo.claim_device(conn, who.user.id, who.guest_id, now) \
            if device and who.new_guest is None else []
        moved += [i for i in account_repo.claim_by_tokens(conn, who.user.id, hashes, now) if i not in moved]
```

with:

```python
        this_device = device and who.new_guest is None
        moved = account_repo.claim_device(conn, who.user.id, who.guest_id, now) if this_device else []
        moved += [i for i in account_repo.claim_by_tokens(conn, who.user.id, hashes, now) if i not in moved]
        if this_device:
            account_repo.claim_daily(conn, who.user.id, who.guest_id)
            account_repo.claim_push(conn, who.user.id, who.guest_id)
```

In `api/app/routes/account.py`, replace:

```python
from typing import Literal
```

with:

```python
from typing import Literal
from urllib.parse import urlsplit
```

In `api/app/routes/account.py`, replace:

```python
@router.get("/account/export")
```

with:

```python
def export_daily_card(ctx, row: dict) -> dict:
    return {"day": row["day"], "card_id": row["card_id"], "name_en": ctx.cards.name(row["card_id"], "en"),
            "name_es": ctx.cards.name(row["card_id"], "es"), "reversed": row["reversed"], "felt": row["felt"],
            "note": row["note"], "noted_at": row["noted_at"]}


def export_subscription(row: dict) -> dict:
    """The push service by name only: the endpoint and its keys let anyone holding the file send to the browser."""
    return {"service": urlsplit(row["endpoint"]).hostname, "hour": row["hour"], "tz": row["tz"], "lang": row["lang"],
            "created_at": row["created_at"], "last_sent_day": row["last_sent_day"]}


@router.get("/account/export")
```

In `api/app/routes/account.py`, replace:

```python
        waitlist = account_repo.waitlist_entry(conn, who.user.id, who.user.email)
    payload = {"exported_at": now, "account": account_view(who.user, profile),
               "readings": [export_reading(ctx, reading, followups) for reading, followups in entries],
               "plus_waitlist": waitlist}
```

with:

```python
        waitlist = account_repo.waitlist_entry(conn, who.user.id, who.user.email)
        daily_cards = account_repo.export_daily(conn, who.user.id)
        subscriptions = account_repo.export_push(conn, who.user.id)
    payload = {"exported_at": now, "account": account_view(who.user, profile),
               "readings": [export_reading(ctx, reading, followups) for reading, followups in entries],
               "daily_cards": [export_daily_card(ctx, row) for row in daily_cards],
               "push_subscriptions": [export_subscription(row) for row in subscriptions],
               "plus_waitlist": waitlist}
```

In `api/app/housekeeping.py`, replace:

```python
- the hourly cleanup (CLEANUP_INTERVAL_S): expired guest readings with their follow-ups, expired claim tokens,
  old deleted-account marks, follow-up crisis tombstones older than a day, stale counters and caches, old logs, events older than 13 months, Plus waitlist requests older than 12;
```

with:

```python
- the hourly cleanup (CLEANUP_INTERVAL_S): expired guest readings with their follow-ups, expired claim tokens,
  old deleted-account marks, follow-up crisis tombstones older than a day, stale counters and caches, old logs, events older than 13 months, Plus waitlist requests older than 12;
  stage 8.1: guest cards of the day after 60 days, guest browser reminders 90 days after the last visit (an
  account's cards and reminders stay until the account is deleted);
```

In `api/app/housekeeping.py`, replace:

```python
KEEP_DAILY_CACHE_DAYS = 2
```

with:

```python
KEEP_DAILY_CACHE_DAYS = 62  # stage 8.1 (owner decision 54): the calendar shows the text read that morning, two months
```

In `api/app/housekeeping.py`, replace:

```python
KEEP_DAILY_DRAWS_DAYS = 7
```

with:

```python
KEEP_GUEST_DAILY_DRAWS_DAYS = 60  # stage 8.1: a guest's cards of the day (an account keeps its own until deletion)
KEEP_GUEST_PUSH_DAYS = 90         # stage 8.1: a guest's browser reminder without a Card of the Day visit
```

In `api/app/housekeeping.py`, replace:

```python
            "daily_draws": conn.execute("DELETE FROM daily_draws WHERE day < %s",
                                        (before(KEEP_DAILY_DRAWS_DAYS),)).rowcount,
```

with:

```python
            "daily_draws": conn.execute("DELETE FROM daily_draws WHERE user_id IS NULL AND day < %s",
                                        (before(KEEP_GUEST_DAILY_DRAWS_DAYS),)).rowcount,
            "push_subscriptions": conn.execute("DELETE FROM push_subscriptions WHERE user_id IS NULL AND active_at < %s",
                                               (now - timedelta(days=KEEP_GUEST_PUSH_DAYS),)).rowcount,
```

`grep -rn KEEP_DAILY_DRAWS_DAYS api` must print nothing afterwards.

- [ ] **Step 4: Run the tests**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_api_claim.py tests/test_api_account.py tests/test_housekeeping.py)
```

Expected: `61 passed`.

Run:

```bash
(cd api && .venv/bin/pytest -q )
```

Expected: `1689 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/account_repo.py api/app/routes/claim.py api/app/routes/account.py api/app/housekeeping.py api/tests/test_api_claim.py api/tests/test_api_account.py api/tests/test_housekeeping.py
git commit -m "feat(api): cards of the day move with the sign-in, are exported and deleted with the account; guest retention 60/90 days, texts 62 days (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: Analytics events of the stage (API whitelist, site types, events doc)

**Files:**
- Modify: `api/app/events.py`, `site/src/lib/analytics.ts`, `docs/design/analytics-events.md`
- Test: `api/tests/test_api_events.py`, `site/src/lib/analytics.test.ts`

**Interfaces:**
- Consumes: migration 009's `events_name_check` (Task 1).
- Produces:
  - API whitelist: `daily_felt` (no tool, `{"place": "daily"|"calendar"}`), `daily_calendar_view` (no tool,
    `{"signed_in": bool}`), `push_enabled` (tool `daily` only, `{}`), `push_click` (no tool, `{}`). The mark, the
    answer and the note can never be a parameter.
  - Site: `EventName` gains the four names; `NoToolEvent` gains `daily_felt`, `daily_calendar_view`, `push_click`;
    `ToolFor<'push_enabled'>` is `'daily'`.
  - `daily_open` of the spec is the existing `tool_view` with `tool: "daily"` (sent by DailyIsland on load); no new
    name (open question 1).

- [ ] **Step 1: Write the failing tests**

In `api/tests/test_api_events.py`, the list `VALID`, replace:

```python
    {"name": "save_click", "tool": "yes_no", "lang": "es", "params": {}},
]
```

with:

```python
    {"name": "save_click", "tool": "yes_no", "lang": "es", "params": {}},
    # stage 8.1 §4
    {"name": "daily_felt", "lang": "en", "params": {"place": "daily"}},
    {"name": "daily_felt", "lang": "es", "params": {"place": "calendar"}},
    {"name": "daily_calendar_view", "lang": "en", "params": {"signed_in": False}},
    {"name": "daily_calendar_view", "lang": "es", "params": {"signed_in": True}},
    {"name": "push_enabled", "tool": "daily", "lang": "en", "params": {}},
    {"name": "push_click", "lang": "es", "params": {}},
]
```

In `api/tests/test_api_events.py`, the list `INVALID`, replace:

```python
    ({"name": "signup_done", "lang": "en", "params": {}}, "params.method"),
]
```

with:

```python
    ({"name": "signup_done", "lang": "en", "params": {}}, "params.method"),
    # stage 8.1: the mark and the note never reach the counter
    ({"name": "daily_felt", "lang": "en", "params": {"place": "daily", "answer": "yes"}}, "params.answer"),
    ({"name": "daily_felt", "lang": "en", "params": {"place": "daily", "note": "It did."}}, "params.note"),
    ({"name": "daily_felt", "lang": "en", "params": {"place": "home"}}, "params.place"),
    ({"name": "daily_felt", "tool": "daily", "lang": "en", "params": {"place": "daily"}}, "tool"),
    ({"name": "daily_calendar_view", "lang": "en", "params": {"signed_in": 1}}, "params.signed_in"),
    ({"name": "push_enabled", "lang": "en"}, "tool"),
    ({"name": "push_enabled", "tool": "love", "lang": "en"}, "tool"),
    ({"name": "push_click", "lang": "en", "params": {"card": "major-18-moon"}}, "params.card"),
]
```

In `site/src/lib/analytics.test.ts`, replace:

```ts
    expect(analyticsEvent('outcome_answered', null, 'en').tool).toBeNull();
  });
});
```

with:

```ts
    expect(analyticsEvent('outcome_answered', null, 'en').tool).toBeNull();
    // @ts-expect-error push_enabled is the daily card's only
    expect(analyticsEvent('push_enabled', 'home', 'en').tool).toBe('home');
  });

  it('knows the events of stage 8.1: the mark and the calendar without a tool and without the mark itself', () => {
    expect(analyticsEvent('daily_felt', null, 'es', { place: 'calendar' })).toEqual({
      name: 'daily_felt', tool: null, lang: 'es', params: { place: 'calendar' },
    });
    expect(analyticsEvent('daily_calendar_view', 'daily', 'en', { signed_in: false }).tool).toBeNull();
    expect(analyticsEvent('push_enabled', 'daily', 'en')).toEqual({ name: 'push_enabled', tool: 'daily', lang: 'en', params: {} });
    expect(analyticsEvent('push_click', null, 'es').tool).toBeNull();
  });
});
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_api_events.py)
```

Expected: FAIL — the six new valid events get `422 {"fields": ["name"]}`.

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/analytics.test.ts'
```

Expected: FAIL — `analyticsEvent('daily_calendar_view', 'daily', …).tool` is `'daily'`, not null.

- [ ] **Step 3: Implement**

In `api/app/events.py`, replace:

```python
    "remind_click": (True, {}),  # stage 4.4b §7: "Remind me tomorrow" under the Card of the Day
}
# events that belong to one tool only
ONLY_TOOL = {"remind_click": "daily"}
```

with:

```python
    "remind_click": (True, {}),  # stage 4.4b §7: "Remind me tomorrow" under the Card of the Day
    # stage 8.1 §4 (migration 009): never the mark itself or the note — only that a mark was set, and where
    "daily_felt": (False, {"place": _one_of("daily", "calendar")}),
    "daily_calendar_view": (False, {"signed_in": _one_of(True, False)}),
    "push_enabled": (True, {}),  # "Remind me each morning" under the Card of the Day went through
    "push_click": (False, {}),   # the morning reminder was opened (sent by the service worker)
}
# events that belong to one tool only
ONLY_TOOL = {"remind_click": "daily", "push_enabled": "daily"}
```

In `site/src/lib/analytics.ts`, replace:

```ts
export type EventName = 'tool_view' | 'draw_click' | 'night_open' | 'cards_revealed' | 'reading_shown'
  | 'more_about_cards' | 'plus_view' | 'save_click' | 'signup_done' | 'outcome_answered' | 'remind_click';

/** The events of docs/design/analytics-events.md that carry no tool. */
export type NoToolEvent = 'plus_view' | 'signup_done' | 'outcome_answered';
export const NO_TOOL: ReadonlySet<EventName> = new Set<NoToolEvent>(['plus_view', 'signup_done', 'outcome_answered']);

/** The tool an event may be built with: any (it is dropped) for the no-tool events, only `daily` for remind_click
 * (the card of the day's "Remind me tomorrow"), a Tool — never null — for every other event. Not distributive, so a
 * name typed as a wider union (e.g. EventName) needs what every member of it accepts (review Minor 1). */
export type ToolFor<N extends EventName> = [N] extends [NoToolEvent] ? Tool | null
  : [N] extends [Exclude<EventName, 'remind_click'>] ? Tool
  : 'daily';
```

with:

```ts
export type EventName = 'tool_view' | 'draw_click' | 'night_open' | 'cards_revealed' | 'reading_shown'
  | 'more_about_cards' | 'plus_view' | 'save_click' | 'signup_done' | 'outcome_answered' | 'remind_click'
  | 'daily_felt' | 'daily_calendar_view' | 'push_enabled' | 'push_click';

/** The events of docs/design/analytics-events.md that carry no tool. Stage 8.1: daily_felt carries only where the
 * mark was set (never the mark or the note), daily_calendar_view only whether the person was signed in. */
export type NoToolEvent = 'plus_view' | 'signup_done' | 'outcome_answered' | 'daily_felt' | 'daily_calendar_view'
  | 'push_click';
export const NO_TOOL: ReadonlySet<EventName> = new Set<NoToolEvent>(['plus_view', 'signup_done', 'outcome_answered',
  'daily_felt', 'daily_calendar_view', 'push_click']);

/** The events that come only from the Card of the Day: "Remind me tomorrow" and "Remind me each morning". */
type DailyOnly = 'remind_click' | 'push_enabled';

/** The tool an event may be built with: any (it is dropped) for the no-tool events, only `daily` for the DailyOnly
 * events, a Tool — never null — for every other event. Not distributive, so a name typed as a wider union (e.g.
 * EventName) needs what every member of it accepts (review Minor 1). */
export type ToolFor<N extends EventName> = [N] extends [NoToolEvent] ? Tool | null
  : [N] extends [Exclude<EventName, DailyOnly>] ? Tool
  : 'daily';
```

In `docs/design/analytics-events.md`, the table «События», replace:

```markdown
| `remind_click` | «Remind me tomorrow» под картой дня (этап 4.4б) | `tool` (только daily), `lang` | нужна ли карта дня назавтра |
```

with:

```markdown
| `remind_click` | «Remind me tomorrow» под картой дня (этап 4.4б) | `tool` (только daily), `lang` | нужна ли карта дня назавтра |
| `daily_felt` | впервые поставлена вечерняя отметка «Did today's card show up in your day?» (этап 8.1) | `place` (daily, calendar), `lang`; ни ответа, ни заметки | доля отметок |
| `daily_calendar_view` | открыт календарь карты дня в дневнике (этап 8.1) | `signed_in` (true, false), `lang` | смотрят ли календарь; доля гостей календаря, которые вошли |
| `push_enabled` | включено «Remind me each morning» (этап 8.1) | `tool` (только daily), `lang` | доля включивших напоминания |
| `push_click` | нажато утреннее напоминание (шлёт service worker, этап 8.1) | `lang` | доля нажатий на напоминания |
```

- [ ] **Step 4: Run the tests**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_api_events.py)
```

Expected: `56 passed`.

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/analytics.test.ts'
```

Expected: `Tests  9 passed (9)`.

Run:

```bash
(cd api && .venv/bin/pytest -q )
```

Expected: `1703 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/events.py api/tests/test_api_events.py site/src/lib/analytics.ts site/src/lib/analytics.test.ts docs/design/analytics-events.md
git commit -m "feat: events daily_felt, daily_calendar_view, push_enabled, push_click — never the mark or the note (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: Web Push encryption and VAPID by hand (with the STOP for the dependency)

**Files:**
- Create: `api/app/webpush.py`
- Modify: `api/app/config.py` (Settings), `api/app/context.py`
- Test: `api/tests/test_webpush.py` (new), `api/tests/test_config.py`

**Interfaces:**
- Consumes: `cryptography`, `PyJWT`, `httpx` (already pinned); `app.config.load_settings`.
- Produces:
  - `webpush.b64url(data: bytes) -> str`, `webpush.b64url_decode(text: str) -> bytes` (strict, ValueError)
  - `webpush.VapidKeys(private_key: EllipticCurvePrivateKey, public_key: str)`
  - `webpush.generate_vapid() -> tuple[str, str]` (private, public; for `deploy/gen-vapid.sh`)
  - `webpush.load_vapid(private_b64: str, public_b64: str) -> VapidKeys | None` (None + a log line when missing,
    malformed or not a pair; never logs the key)
  - `webpush.valid_endpoint(url: str) -> bool` — https, port 443, no user info, host in `PUSH_HOSTS`
    (`fcm.googleapis.com`, `updates.push.services.mozilla.com`, `web.push.apple.com`) or ending with
    `.notify.windows.com` / `.push.apple.com`; at most `ENDPOINT_MAX = 1024`
  - `webpush.valid_keys(p256dh: str, auth: str) -> bool` (a P-256 point, 16 bytes of auth)
  - `webpush.encrypt(plaintext, p256dh, auth, *, sender=None, salt=None) -> bytes` (RFC 8291, one aes128gcm record)
  - `webpush.vapid_authorization(endpoint, keys, subject, now: float) -> str` (`vapid t=<jwt>, k=<public>`)
  - `webpush.push_request(endpoint, p256dh, auth, payload: dict, keys, subject, now) -> tuple[dict, bytes]` — headers
    `TTL: 14400`, `Urgency: normal`, `Topic: daily`, `Content-Encoding: aes128gcm`, `Authorization`
  - `Settings.vapid_private_key`, `.vapid_public_key` (env `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, default ""),
    `.vapid_subject` (`VAPID_SUBJECT`, default `https://arcanadiary.com`), `.push_job_interval_s` (`PUSH_JOB_INTERVAL_S`,
    default 600)
  - `AppContext.vapid: VapidKeys | None`, `AppContext.push_burst: BurstCounter`

- [ ] **Step 1: STOP: the dependency decision**

**STOP — the owner decides the dependency before anything is installed or fetched.** Report to the owner, in
one message, and wait for the answer:

1. The plan's choice: **no new package.** Web Push needs three things, and the API already pins all of them in
   `api/requirements.txt` for the stage 4.3 sign-in: the message encryption of RFC 8291 (ECDH P-256, HKDF-SHA256,
   AES-128-GCM — `cryptography==50.0.2`), the VAPID token of RFC 8292 (ES256 JWT — `PyJWT==2.15.1`) and one HTTPS POST
   (`httpx==0.28.1`). `app/webpush.py` is about 150 lines, and the RFC 8291 §5 example is a byte-for-byte test, so the
   encryption is checked against the standard itself, not against our own reading of it.
2. Print the versions that are used (installed already, nothing is fetched):

   ```bash
   api/.venv/bin/pip show cryptography PyJWT httpx | grep -E '^(Name|Version):'
   ```

   Expected: `cryptography 50.0.2`, `PyJWT 2.15.1`, `httpx 0.28.1` — the same pins as `api/requirements.txt`.
3. The alternative the spec names, `pywebpush`, is **not** installed and nothing about it is fetched in this step. If
   the owner prefers it, the next step — only after the owner's yes to *looking* — is
   `api/.venv/bin/pip index versions pywebpush` and `api/.venv/bin/pip install --dry-run --report /tmp/pywebpush-report.json pywebpush`
   (the dry run asks the package index for metadata and may download wheels to resolve them: that is why it waits for
   the owner); the report lists every package it would pull (pywebpush pulls at least `py-vapid`, `http-ece`, `aiohttp`
   or `requests` and their own dependencies) with versions and download sizes, and the owner then says yes or no to
   installing. In that case this task changes: `push_request` calls `pywebpush.webpush`, the RFC test stays.

Go on only after the owner's answer. With "no new package" (the plan's default), continue with Step 2; nothing is
added to `api/requirements.txt`.

- [ ] **Step 2: Write the failing tests**

Create `api/tests/test_webpush.py`:

```python
"""Web Push by hand (stage 8.1, plan decision 1): RFC 8291 encryption against the RFC's own example, a browser-side
decryption of our messages, VAPID tokens, the push-host allowlist and the keys of a subscription."""
import json
import os
import struct

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app import webpush
from app.webpush import b64url, b64url_decode

# RFC 8291 §5 (Push Message Encryption Example)
RFC = {
    "plaintext": b"When I grow up, I want to be a watermelon",
    "as_private": "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw",
    "ua_public": "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
    "auth": "BTBZMqHH6r4Tts7J_aSIgg",
    "salt": "DGv6ra1nlYgDCS1FRnbzlw",
    "body": "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3"
            "jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN",
}
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"


def browser():
    """A browser's subscription keys: its private key (to read the message) and what it gives the site."""
    key = ec.generate_private_key(ec.SECP256R1())
    auth = os.urandom(16)
    return key, b64url(webpush._point(key.public_key())), b64url(auth)


def decrypt(body: bytes, key: ec.EllipticCurvePrivateKey, auth: str) -> bytes:
    """What the browser does (RFC 8291 §3.4, from the receiving side)."""
    salt, rs, idlen = body[:16], *struct.unpack("!IB", body[16:21])
    as_public = body[21:21 + idlen]
    shared = key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public))
    ua_public = webpush._point(key.public_key())
    ikm = webpush._hkdf(b64url_decode(auth), shared, b"WebPush: info\x00" + ua_public + as_public, 32)
    cek = webpush._hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = webpush._hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    padded = AESGCM(cek).decrypt(nonce, body[21 + idlen:], None)
    assert rs == webpush.RECORD_SIZE and padded.endswith(b"\x02")
    return padded[:-1]


def test_encryption_matches_the_example_of_rfc_8291():
    sender = ec.derive_private_key(int.from_bytes(b64url_decode(RFC["as_private"]), "big"), ec.SECP256R1())
    body = webpush.encrypt(RFC["plaintext"], RFC["ua_public"], RFC["auth"], sender=sender,
                           salt=b64url_decode(RFC["salt"]))
    assert b64url(body) == RFC["body"]


def test_a_browser_reads_our_message_and_every_message_differs():
    key, p256dh, auth = browser()
    first = webpush.encrypt(b'{"lang":"es"}', p256dh, auth)
    second = webpush.encrypt(b'{"lang":"es"}', p256dh, auth)
    assert decrypt(first, key, auth) == decrypt(second, key, auth) == b'{"lang":"es"}'
    assert first != second  # a fresh sender key and salt each time


def test_generated_keys_load_and_sign_a_vapid_token():
    private, public = webpush.generate_vapid()
    keys = webpush.load_vapid(private, public)
    assert keys is not None and keys.public_key == public and len(b64url_decode(public)) == 65
    header = webpush.vapid_authorization(ENDPOINT, keys, "https://arcanadiary.com", now=1_800_000_000)
    token = header.split("t=", 1)[1].split(",", 1)[0]
    assert header.endswith(f", k={public}")
    claims = jwt.decode(token, keys.private_key.public_key(), algorithms=["ES256"], audience="https://fcm.googleapis.com",
                        options={"verify_exp": False})
    assert claims == {"aud": "https://fcm.googleapis.com", "exp": 1_800_000_000 + 12 * 3600,
                      "sub": "https://arcanadiary.com"}


def test_missing_or_mismatched_keys_leave_reminders_off(caplog):
    private, public = webpush.generate_vapid()
    other_private, _ = webpush.generate_vapid()
    assert webpush.load_vapid("", "") is None
    with caplog.at_level("WARNING", logger="arcana.webpush"):
        assert webpush.load_vapid(other_private, public) is None
        assert webpush.load_vapid("not-a-key!", public) is None
        assert webpush.load_vapid(private, "") is None
    assert "does not belong" in caplog.text and "is not a P-256 key" in caplog.text
    assert private not in caplog.text  # never the key itself


@pytest.mark.parametrize("url, ok", [
    (ENDPOINT, True),
    ("https://updates.push.services.mozilla.com/wpush/v2/gAAAA", True),
    ("https://web.push.apple.com/QGuQyavXutnMH", True),
    ("https://wns2-db5p.notify.windows.com/w/?token=x", True),
    ("http://fcm.googleapis.com/fcm/send/abc", False),
    ("https://fcm.googleapis.com:8443/fcm/send/abc", False),
    ("https://user:pw@fcm.googleapis.com/fcm/send/abc", False),
    ("https://fcm.googleapis.com.evil.example/x", False),
    ("https://evilnotify.windows.com/x", False),
    ("https://169.254.169.254/latest/meta-data", False),
    ("https://localhost/x", False),
    ("https://fcm.googleapis.com", False),
    ("https://fcm.googleapis.com/" + "a" * 1100, False),
    ("https://[::1/x", False),
])
def test_only_known_push_services_are_accepted(url, ok):
    assert webpush.valid_endpoint(url) is ok


def test_subscription_keys_are_checked():
    _, p256dh, auth = browser()
    assert webpush.valid_keys(p256dh, auth)
    assert not webpush.valid_keys(p256dh, b64url(os.urandom(15)))
    assert not webpush.valid_keys(b64url(b"\x04" + bytes(64)), auth)  # not a point on the curve
    assert not webpush.valid_keys(p256dh[:-4], auth)
    assert not webpush.valid_keys("abc+/", auth)


def test_a_push_request_carries_the_vapid_header_and_a_readable_body():
    key, p256dh, auth = browser()
    keys = webpush.load_vapid(*webpush.generate_vapid())
    headers, body = webpush.push_request(ENDPOINT, p256dh, auth, {"lang": "en"}, keys, "https://arcanadiary.com",
                                         now=1_800_000_000)
    assert headers["Content-Encoding"] == "aes128gcm" and headers["TTL"] == "14400" and headers["Topic"] == "daily"
    assert headers["Authorization"].startswith("vapid t=")
    assert json.loads(decrypt(body, key, auth)) == {"lang": "en"}
```

Append to the end of `api/tests/test_config.py`:

```python
def test_browser_reminders_are_off_by_default_and_run_every_ten_minutes():
    s = load_settings({})
    assert (s.vapid_private_key, s.vapid_public_key) == ("", "")
    assert s.vapid_subject == "https://arcanadiary.com" and s.push_job_interval_s == 600.0
    s = load_settings({"VAPID_PRIVATE_KEY": "p", "VAPID_PUBLIC_KEY": "q", "VAPID_SUBJECT": "mailto:x@example.com",
                       "PUSH_JOB_INTERVAL_S": "0"})
    assert (s.vapid_private_key, s.vapid_public_key, s.vapid_subject, s.push_job_interval_s) == (
        "p", "q", "mailto:x@example.com", 0.0)
```

- [ ] **Step 3: Run the tests to see them fail**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_webpush.py tests/test_config.py)
```

Expected: FAIL — `ImportError: cannot import name 'webpush' from 'app'`; `AttributeError: 'Settings' object has no attribute 'vapid_private_key'`.

- [ ] **Step 4: Implement**

Create `api/app/webpush.py`:

```python
"""Web Push without a new package (stage 8.1 §4, plan decision 1): the message encryption of RFC 8291
(aes128gcm content coding, RFC 8188) and VAPID (RFC 8292), built on `cryptography` and PyJWT, which the API already
pins for sign-in (ES256 tokens). The test vector of RFC 8291 §5 checks the encryption byte for byte.

- VapidKeys: the server's P-256 key from VAPID_PRIVATE_KEY (32 bytes, base64url) and VAPID_PUBLIC_KEY (the
  65-byte uncompressed point, base64url; the browser takes it as applicationServerKey). Missing, malformed or not a
  pair: None, a line in the log, and browser reminders stay off — the API itself keeps working.
- valid_endpoint: only https addresses of the known push services, so a stored subscription can never make the
  server send requests anywhere else (SSRF).
- push_request: the headers and the encrypted body of one message; the caller sends it.
"""
import base64
import binascii
import json
import logging
import os
import re
import struct
from dataclasses import dataclass
from urllib.parse import urlsplit

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

log = logging.getLogger("arcana.webpush")

RECORD_SIZE = 4096
VAPID_TTL_S = 12 * 3600       # RFC 8292: at most 24 hours
PUSH_TTL_S = 4 * 3600         # a phone that is off for longer gets no stale "your card is waiting"
ENDPOINT_MAX = 1024
PUSH_HOSTS = frozenset({"fcm.googleapis.com", "updates.push.services.mozilla.com", "web.push.apple.com"})
PUSH_HOST_SUFFIXES = (".notify.windows.com", ".push.apple.com")
_B64URL = re.compile(r"[A-Za-z0-9_-]+={0,2}")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    """Strict base64url (the alphabet of RFC 4648 §5, padding optional); ValueError otherwise."""
    if not isinstance(text, str) or not _B64URL.fullmatch(text):
        raise ValueError("not base64url")
    try:
        return base64.urlsafe_b64decode(text.rstrip("=") + "=" * (-len(text.rstrip("=")) % 4))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("not base64url") from exc


def _point(public_key: ec.EllipticCurvePublicKey) -> bytes:
    return public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


@dataclass(frozen=True)
class VapidKeys:
    private_key: ec.EllipticCurvePrivateKey
    public_key: str


def generate_vapid() -> tuple[str, str]:
    """A new key pair (private, public) as deploy/gen-vapid.sh writes them into deploy/.env."""
    key = ec.generate_private_key(ec.SECP256R1())
    return b64url(key.private_numbers().private_value.to_bytes(32, "big")), b64url(_point(key.public_key()))


def load_vapid(private_b64: str, public_b64: str) -> VapidKeys | None:
    private_b64, public_b64 = private_b64.strip(), public_b64.strip()
    if not private_b64 and not public_b64:
        return None
    try:
        raw = b64url_decode(private_b64)
        if len(raw) != 32:
            raise ValueError("length")
        key = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
    except ValueError:
        log.warning("VAPID_PRIVATE_KEY is not a P-256 key: browser reminders stay off")
        return None
    public = b64url(_point(key.public_key()))
    if public != public_b64.rstrip("="):
        log.warning("VAPID_PUBLIC_KEY does not belong to VAPID_PRIVATE_KEY: browser reminders stay off")
        return None
    return VapidKeys(key, public)


def valid_endpoint(url: str) -> bool:
    if not isinstance(url, str) or len(url) > ENDPOINT_MAX:
        return False
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or port not in (None, 443) or parts.username or parts.password or not parts.path:
        return False
    return host in PUSH_HOSTS or any(host.endswith(suffix) for suffix in PUSH_HOST_SUFFIXES)


def _browser_key(p256dh: str) -> bytes:
    raw = b64url_decode(p256dh)
    if len(raw) != 65 or raw[0] != 4:
        raise ValueError("p256dh")
    ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)  # ValueError when not on the curve
    return raw


def valid_keys(p256dh: str, auth: str) -> bool:
    try:
        _browser_key(p256dh)
        return len(b64url_decode(auth)) == 16
    except ValueError:
        return False


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def encrypt(plaintext: bytes, p256dh: str, auth: str, *, sender: ec.EllipticCurvePrivateKey | None = None,
            salt: bytes | None = None) -> bytes:
    """RFC 8291 §3: one aes128gcm record. `sender` and `salt` are fresh for every message; tests pass the RFC's."""
    ua_public = _browser_key(p256dh)
    sender = sender or ec.generate_private_key(ec.SECP256R1())
    salt = salt if salt is not None else os.urandom(16)
    as_public = _point(sender.public_key())
    shared = sender.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    ikm = _hkdf(b64url_decode(auth), shared, b"WebPush: info\x00" + ua_public + as_public, 32)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    record = AESGCM(cek).encrypt(nonce, plaintext + b"\x02", None)  # \x02: the last (and only) record
    return salt + struct.pack("!IB", RECORD_SIZE, len(as_public)) + as_public + record


def vapid_authorization(endpoint: str, keys: VapidKeys, subject: str, now: float) -> str:
    parts = urlsplit(endpoint)
    token = jwt.encode({"aud": f"{parts.scheme}://{parts.netloc}", "exp": int(now) + VAPID_TTL_S, "sub": subject},
                       keys.private_key, algorithm="ES256")
    return f"vapid t={token}, k={keys.public_key}"


def push_request(endpoint: str, p256dh: str, auth: str, payload: dict, keys: VapidKeys, subject: str,
                 now: float) -> tuple[dict[str, str], bytes]:
    body = encrypt(json.dumps(payload, separators=(",", ":")).encode(), p256dh, auth)
    headers = {"TTL": str(PUSH_TTL_S), "Urgency": "normal", "Topic": "daily", "Content-Encoding": "aes128gcm",
               "Content-Type": "application/octet-stream",
               "Authorization": vapid_authorization(endpoint, keys, subject, now)}
    return headers, body
```

In `api/app/config.py`, replace:

```python
    google_signin: bool  # stage 4.4b §3: GOOGLE_SIGNIN=true shows "Continue with Google"
```

with:

```python
    google_signin: bool  # stage 4.4b §3: GOOGLE_SIGNIN=true shows "Continue with Google"
    vapid_private_key: str  # stage 8.1: browser reminders (Web Push); "" — off. Secret: only in deploy/.env
    vapid_public_key: str   # stage 8.1: its public half, given to the browser
    vapid_subject: str      # stage 8.1: who sends (RFC 8292 "sub"), an https address or mailto:
    push_job_interval_s: float  # stage 8.1: how often the reminder job looks for due subscriptions; 0 — off
```

In `api/app/config.py`, replace:

```python
        google_signin=_flag("GOOGLE_SIGNIN", env.get("GOOGLE_SIGNIN") or ""),
    )
```

with:

```python
        google_signin=_flag("GOOGLE_SIGNIN", env.get("GOOGLE_SIGNIN") or ""),
        vapid_private_key=env.get("VAPID_PRIVATE_KEY") or "",
        vapid_public_key=env.get("VAPID_PUBLIC_KEY") or "",
        vapid_subject=env.get("VAPID_SUBJECT") or "https://arcanadiary.com",
        push_job_interval_s=float(env.get("PUSH_JOB_INTERVAL_S") or 600),
    )
```

In `api/app/context.py`, replace:

```python
from app.turnstile import TurnstileVerifier
```

with:

```python
from app.turnstile import TurnstileVerifier
from app.webpush import VapidKeys, load_vapid
```

In `api/app/context.py`, replace:

```python
    events_burst: BurstCounter  # POST /api/events per address (stage 4.4a)
    clock: Callable[[], datetime]
```

with:

```python
    events_burst: BurstCounter  # POST /api/events per address (stage 4.4a)
    push_burst: BurstCounter    # POST /api/push/subscription per address (stage 8.1)
    vapid: VapidKeys | None     # None: browser reminders are off (no or broken VAPID_* keys, stage 8.1)
    clock: Callable[[], datetime]
```

In `api/app/context.py`, replace:

```python
        salt=DailySalt(), burst=BurstCounter(), daily_burst=BurstCounter(), events_burst=BurstCounter(),
        clock=clock or utc_now,
```

with:

```python
        salt=DailySalt(), burst=BurstCounter(), daily_burst=BurstCounter(), events_burst=BurstCounter(),
        push_burst=BurstCounter(), vapid=load_vapid(settings.vapid_private_key, settings.vapid_public_key),
        clock=clock or utc_now,
```

- [ ] **Step 5: Run the tests**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_webpush.py tests/test_config.py)
```

Expected: `53 passed`.

Run:

```bash
(cd api && .venv/bin/pytest -q )
```

Expected: `1724 passed`.

- [ ] **Step 6: Commit**

```bash
git add api/app/webpush.py api/app/config.py api/app/context.py api/tests/test_webpush.py api/tests/test_config.py
git commit -m "feat(api): Web Push encryption (RFC 8291) and VAPID (RFC 8292) on the pinned cryptography and PyJWT, no new package (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 7: Subscription API: GET /api/push/key, POST and DELETE /api/push/subscription

**Files:**
- Create: `api/app/routes/push.py`
- Modify: `api/app/config.py`, `api/app/repo.py`, `api/app/main.py`
- Test: `api/tests/test_api_push.py` (new)

**Interfaces:**
- Consumes: Task 6 (`ctx.vapid`, `ctx.push_burst`, `webpush.valid_endpoint`, `valid_keys`, `ENDPOINT_MAX`); Task 2
  (`repo._daily_owner`); `account_repo.lock_account` / `refuse_deleted`; `limits.resolve_tz`, `client_ip`.
- Produces:
  - `config.PUSH_PER_MINUTE = 10`, `config.PUSH_SUBSCRIPTIONS_PER_OWNER = 10`
  - `repo.upsert_push(conn, sub: dict) -> None` (keys: user_id, guest_id, endpoint, p256dh, auth, lang, tz, hour, now)
  - `repo.count_push(conn, user_id, guest_id, endpoint) -> int`, `repo.delete_push(conn, endpoint) -> bool`
  - `GET /api/push/key` → `{"enabled": bool, "public_key": str}`
  - `POST /api/push/subscription` `{"endpoint", "keys": {"p256dh", "auth"}, "hour": 0..23, "tz"?, "lang"}` → 201
    `{"hour", "tz"}`; 503 `push_off`; 429 `rate` / `subscriptions`; 422 `endpoint` / `keys` / a field
  - `DELETE /api/push/subscription` `{"endpoint"}` → 204 always

- [ ] **Step 1: Write the failing tests**

Create `api/tests/test_api_push.py`:

```python
"""Stage 8.1 (spec 2026-11-27 §2.5, §3): the browser's reminder subscription — key, subscribe, unsubscribe."""
import os
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import webpush
from app.config import PUSH_PER_MINUTE, PUSH_SUBSCRIPTIONS_PER_OWNER
from helpers import bearer, from_ip, guest_headers

ANA = uuid.UUID("8a1b2c3d-0000-4000-8000-000000000021")
VAPID = webpush.generate_vapid()


def browser_keys() -> dict:
    key = ec.generate_private_key(ec.SECP256R1())
    return {"p256dh": webpush.b64url(webpush._point(key.public_key())), "auth": webpush.b64url(os.urandom(16))}


def body(n: int | str = 1, **overrides) -> dict:
    return {"endpoint": f"https://fcm.googleapis.com/fcm/send/device-{n}", "keys": browser_keys(), "hour": 8,
            "tz": "America/Mexico_City", "lang": "en", **overrides}


@pytest.fixture
def push_api(api_factory):
    return api_factory(vapid_private_key=VAPID[0], vapid_public_key=VAPID[1])


def rows(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT user_id, guest_id, endpoint, lang, tz, hour, fails FROM push_subscriptions"
                            " ORDER BY endpoint").fetchall()


def test_the_key_is_given_only_when_reminders_are_on(api, push_api):
    assert api.client.get("/api/push/key").json() == {"enabled": False, "public_key": ""}
    assert push_api.client.get("/api/push/key").json() == {"enabled": True, "public_key": VAPID[1]}


def test_a_guest_subscribes_for_this_cookie_and_an_account_for_itself(push_api):
    guest = uuid.uuid4()
    response = push_api.new_client().post("/api/push/subscription", json=body(1), headers=guest_headers(guest))
    assert response.status_code == 201 and response.json() == {"hour": 8, "tz": "America/Mexico_City"}
    assert push_api.new_client().post("/api/push/subscription", json=body(2, hour=7, lang="es"),
                                      headers=bearer(ANA)).status_code == 201
    assert [(r["user_id"], r["guest_id"], r["hour"], r["lang"]) for r in rows(push_api)] == [
        (None, guest, 8, "en"), (ANA, None, 7, "es")]


def test_the_same_browser_again_replaces_its_row(push_api):
    client = push_api.new_client()
    first = body(1)
    client.post("/api/push/subscription", json=first, headers=guest_headers(uuid.uuid4()))
    with push_api.db.connect() as conn:
        conn.execute("UPDATE push_subscriptions SET fails = 2")
    client.post("/api/push/subscription", json={**first, "hour": 21}, headers=bearer(ANA))
    [row] = rows(push_api)
    assert (row["user_id"], row["guest_id"], row["hour"], row["fails"]) == (ANA, None, 21, 0)


def test_an_unknown_zone_is_stored_as_utc(push_api):
    push_api.client.post("/api/push/subscription", json=body(1, tz="Mars/Olympus"), headers=bearer(ANA))
    assert rows(push_api)[0]["tz"] == "UTC"


@pytest.mark.parametrize("endpoint", ["http://fcm.googleapis.com/fcm/send/x", "https://169.254.169.254/latest",
                                      "https://example.com/push", "https://fcm.googleapis.com.evil.example/x"])
def test_only_a_known_push_service_is_taken(push_api, endpoint):
    response = push_api.client.post("/api/push/subscription", json=body(1, endpoint=endpoint), headers=bearer(ANA))
    assert response.status_code == 422 and response.json()["fields"] == ["endpoint"]
    assert rows(push_api) == []


def test_bad_keys_are_refused(push_api):
    keys = {"p256dh": webpush.b64url(b"\x04" + bytes(64)), "auth": webpush.b64url(os.urandom(16))}
    response = push_api.client.post("/api/push/subscription", json=body(1, keys=keys), headers=bearer(ANA))
    assert response.status_code == 422 and response.json()["fields"] == ["keys"]


@pytest.mark.parametrize("change, field", [({"hour": 24}, "hour"), ({"lang": "fr"}, "lang"),
                                           ({"expirationTime": None}, "expirationTime")])
def test_a_bad_body_is_422(push_api, change, field):
    response = push_api.client.post("/api/push/subscription", json=body(1, **change), headers=bearer(ANA))
    assert response.status_code == 422 and response.json()["fields"] == [field]


def test_reminders_off_is_503_and_stores_nothing(api):
    response = api.client.post("/api/push/subscription", json=body(1), headers=bearer(ANA))
    assert response.status_code == 503 and response.json() == {"reason": "push_off"}
    assert rows(api) == []


def test_one_owner_has_at_most_ten_browsers(push_api):
    for n in range(PUSH_SUBSCRIPTIONS_PER_OWNER):
        assert push_api.new_client().post("/api/push/subscription", json=body(n), headers=bearer(ANA)).status_code == 201
    push_api.clock.advance(minutes=2)  # not the address limit
    over = push_api.new_client().post("/api/push/subscription", json=body("x"), headers=bearer(ANA))
    assert over.status_code == 429 and over.json() == {"reason": "subscriptions"}
    again = push_api.new_client().post("/api/push/subscription", json=body(0), headers=bearer(ANA))
    assert again.status_code == 201  # a browser already in the list may refresh


def test_one_address_is_limited_per_minute(push_api):
    codes = [push_api.new_client().post("/api/push/subscription", json=body(n), headers=from_ip("198.51.100.9"))
             .status_code for n in range(PUSH_PER_MINUTE + 1)]
    assert codes == [201] * PUSH_PER_MINUTE + [429]


def test_unsubscribing_deletes_the_row_and_is_always_204(push_api):
    push_api.client.post("/api/push/subscription", json=body(1), headers=bearer(ANA))
    out = {"endpoint": body(1)["endpoint"]}
    assert push_api.new_client().request("DELETE", "/api/push/subscription", json=out).status_code == 204
    assert rows(push_api) == []
    assert push_api.new_client().request("DELETE", "/api/push/subscription", json=out).status_code == 204


def test_a_deleted_account_cannot_subscribe(push_api):
    assert push_api.client.request("DELETE", "/api/account", json={"confirm": "DELETE"},
                                   headers=bearer(ANA)).status_code == 200
    assert push_api.new_client().post("/api/push/subscription", json=body(1), headers=bearer(ANA)).status_code == 401
    assert rows(push_api) == []
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_api_push.py)
```

Expected: FAIL — `ImportError: cannot import name 'PUSH_PER_MINUTE' from 'app.config'`.

- [ ] **Step 3: Implement**

In `api/app/config.py`, replace:

```python
CALENDAR_GUEST_DAYS = 7        # stage 8.1 §2.4: a guest's calendar shows this device's last 7 days, without marks
```

with:

```python
CALENDAR_GUEST_DAYS = 7        # stage 8.1 §2.4: a guest's calendar shows this device's last 7 days, without marks
PUSH_PER_MINUTE = 10           # stage 8.1: POST /api/push/subscription per address per minute
PUSH_SUBSCRIPTIONS_PER_OWNER = 10  # stage 8.1: browsers with reminders per account or guest cookie
```

In `api/app/repo.py`, replace:

```python
def touch_guest_push(conn, guest_id, now) -> None:
```

with:

```python
def upsert_push(conn, sub: dict) -> None:
    """Stage 8.1: one row per browser endpoint; the same browser subscribing again (another hour, a refresh, another
    owner on a shared computer) replaces its row and clears its failures. last_sent_day stays: at most one a day."""
    conn.execute(
        "INSERT INTO push_subscriptions (user_id, guest_id, endpoint, p256dh, auth, lang, tz, hour, created_at,"
        " active_at) VALUES (%(user_id)s, %(guest_id)s, %(endpoint)s, %(p256dh)s, %(auth)s, %(lang)s, %(tz)s,"
        " %(hour)s, %(now)s, %(now)s) ON CONFLICT (endpoint) DO UPDATE SET user_id = EXCLUDED.user_id,"
        " guest_id = EXCLUDED.guest_id, p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth, lang = EXCLUDED.lang,"
        " tz = EXCLUDED.tz, hour = EXCLUDED.hour, fails = 0, active_at = EXCLUDED.active_at", sub)


def count_push(conn, user_id, guest_id, endpoint: str) -> int:
    """The owner's other subscriptions (the browser asking now is not counted twice)."""
    where, args = _daily_owner(user_id, guest_id)
    return conn.execute(f"SELECT count(*) AS n FROM push_subscriptions WHERE {where} AND endpoint <> %s",
                        (*args, endpoint)).fetchone()["n"]


def delete_push(conn, endpoint: str) -> bool:
    return conn.execute("DELETE FROM push_subscriptions WHERE endpoint = %s RETURNING id", (endpoint,)).fetchone() \
        is not None


def touch_guest_push(conn, guest_id, now) -> None:
```

Create `api/app/routes/push.py`:

```python
"""Browser reminders (stage 8.1 §2.5, §3): "Remind me each morning" under the Card of the Day.

- GET /api/push/key → {"enabled", "public_key"}: the VAPID public key the browser subscribes with; "enabled" false
  (and no key) while VAPID_* is not set in deploy/.env — the site then offers nothing.
- POST /api/push/subscription {"endpoint", "keys": {"p256dh", "auth"}, "hour", "tz", "lang"} → 201 {"hour", "tz"}:
  stores the browser's subscription for the account when signed in, otherwise for this guest cookie. Only an https
  address of a known push service is taken (422 "endpoint"), only real keys (422 "keys"); reminders off → 503
  "push_off"; more than PUSH_PER_MINUTE a minute from one address → 429 "rate"; more than
  PUSH_SUBSCRIPTIONS_PER_OWNER browsers of one owner → 429 "subscriptions". Asking again replaces the row.
- DELETE /api/push/subscription {"endpoint"} → 204: whoever knows the endpoint is that browser; always 204, so the
  answer tells nothing about other people's rows.
"""
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app import account_repo, limits, repo, webpush
from app.config import PUSH_PER_MINUTE, PUSH_SUBSCRIPTIONS_PER_OWNER
from app.context import get_ctx
from app.routes.common import respond, viewer

router = APIRouter(prefix="/api")


class PushKeys(BaseModel):
    model_config = ConfigDict(extra="forbid")
    p256dh: str = Field(max_length=200)
    auth: str = Field(max_length=50)


class PushIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str = Field(max_length=webpush.ENDPOINT_MAX)
    keys: PushKeys
    hour: int = Field(ge=0, le=23)
    tz: str | None = Field(default=None, max_length=64)
    lang: Literal["en", "es"]


class PushOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str = Field(max_length=webpush.ENDPOINT_MAX)


@router.get("/push/key")
def push_key(request: Request):
    vapid = get_ctx(request).vapid
    return respond(200, {"enabled": vapid is not None, "public_key": vapid.public_key if vapid else ""})


@router.post("/push/subscription")
def subscribe(body: PushIn, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    now = ctx.clock()
    if ctx.vapid is None:
        return respond(503, {"reason": "push_off"}, who.new_guest)
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    if ctx.push_burst.hit(ip_hash, now) > PUSH_PER_MINUTE:
        return respond(429, {"reason": "rate"}, who.new_guest)
    if not webpush.valid_endpoint(body.endpoint):
        return respond(422, {"reason": "invalid", "fields": ["endpoint"]}, who.new_guest)
    if not webpush.valid_keys(body.keys.p256dh, body.keys.auth):
        return respond(422, {"reason": "invalid", "fields": ["keys"]}, who.new_guest)
    user_id = who.user.id if who.user else None
    guest_id = None if who.user else who.guest_id
    tz = limits.resolve_tz(body.tz).key
    with ctx.db.connect() as conn:
        if who.user:
            account_repo.lock_account(conn, who.user.id)  # takes turns with delete_account
            account_repo.refuse_deleted(conn, who.user.id)
        if repo.count_push(conn, user_id, guest_id, body.endpoint) >= PUSH_SUBSCRIPTIONS_PER_OWNER:
            return respond(429, {"reason": "subscriptions"}, who.new_guest)
        repo.upsert_push(conn, {"user_id": user_id, "guest_id": guest_id, "endpoint": body.endpoint,
                                "p256dh": body.keys.p256dh, "auth": body.keys.auth, "lang": body.lang, "tz": tz,
                                "hour": body.hour, "now": now})
    return respond(201, {"hour": body.hour, "tz": tz}, who.new_guest)


@router.delete("/push/subscription")
def unsubscribe(body: PushOut, request: Request):
    ctx = get_ctx(request)
    with ctx.db.connect() as conn:
        repo.delete_push(conn, body.endpoint)
    return Response(status_code=204)
```

In `api/app/main.py`, replace:

```python
from app.routes import account, auth_config, claim, daily, diary, events, followups, plus, readings
```

with:

```python
from app.routes import account, auth_config, claim, daily, diary, events, followups, plus, push, readings
```

In `api/app/main.py`, replace:

```python
    app.include_router(auth_config.router, dependencies=API_AUTH)
```

with:

```python
    app.include_router(auth_config.router, dependencies=API_AUTH)
    app.include_router(push.router, dependencies=API_AUTH)
```

- [ ] **Step 4: Run the tests**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_api_push.py)
```

Expected: `17 passed`.

Run:

```bash
(cd api && .venv/bin/pytest -q )
```

Expected: `1741 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/routes/push.py api/app/config.py api/app/repo.py api/app/main.py api/tests/test_api_push.py
git commit -m "feat(api): browser reminder subscriptions — key, subscribe (known push services only), unsubscribe (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 8: The morning reminder job and the VAPID key script

**Files:**
- Create: `api/app/push.py`, `deploy/gen-vapid.sh`, `deploy/test-gen-vapid.sh`
- Modify: `api/app/repo.py`, `api/app/housekeeping.py`, `deploy/docker-compose.yml`, `deploy/.env.example`,
  `api/README.md`
- Test: `api/tests/test_push_job.py` (new), `deploy/test-gen-vapid.sh`

**Interfaces:**
- Consumes: Tasks 6–7 (`webpush.push_request`, `ctx.vapid`, `settings.vapid_subject`, `settings.push_job_interval_s`,
  `repo.upsert_push`), Task 2 (`repo._daily_owner`, `repo.account_daily_draw`), `limits.resolve_tz`;
  `tests/test_webpush.decrypt` (the browser side, for the tests).
- Produces:
  - `repo.push_subscriptions(conn) -> list[dict]`, `repo.claim_push_day(conn, sub_id, day) -> bool`,
    `repo.opened_daily(conn, user_id, guest_id, day) -> bool`, `repo.push_delivered(conn, sub_id) -> None`,
    `repo.push_failed(conn, sub_id) -> int | None`, `repo.delete_push_by_id(conn, sub_id) -> None`
  - `push.SEND_WINDOW_H = 2`, `push.MAX_FAILS = 3`, `push.GONE = {404, 410}`, `push.REFUSED_KEY = {401, 403}`
  - `push.due_day(sub, now) -> date | None`, `push.http_post(url, headers, body) -> int`,
    `push.send_due(ctx, now, post=http_post) -> {"sent", "skipped", "failed", "deleted"}`,
    `async push.push_loop(ctx, interval_s)`; `run_background` starts it only when `ctx.vapid` is set (read with
    `getattr`, as the housekeeping tests pass a `SimpleNamespace` without it)
  - message payload: `{"lang": "en"|"es"}` only
  - `deploy/gen-vapid.sh`: appends `VAPID_PRIVATE_KEY=` / `VAPID_PUBLIC_KEY=` to `ENV_FILE` (default `deploy/.env`),
    prints only `ключи VAPID дописаны в .env`, exit 3 when keys are already there; `ENV_FILE` / `PYTHON` overridable
    for its test only

- [ ] **Step 1: Write the failing tests**

Create `api/tests/test_push_job.py`:

```python
"""Stage 8.1 (spec 2026-11-27 §2.5, §3): the morning reminder job — its hour, once a day, not when the card is open,
what the message says, and what a failed delivery does."""
import asyncio
import json
import os
import uuid
from dataclasses import replace
from datetime import date, datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import housekeeping, repo, webpush
from app.config import load_settings
from app.housekeeping import run_background
from app.push import due_day, send_due
from test_webpush import decrypt

VAPID = webpush.generate_vapid()
MX = "America/Mexico_City"
EIGHT_THIRTY_MX = datetime(2026, 11, 20, 14, 30, tzinfo=timezone.utc)  # 08:30 in Mexico City


class FakePost:
    def __init__(self, *statuses):
        self.statuses = list(statuses)
        self.calls: list[tuple[str, dict, bytes]] = []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, body))
        status = self.statuses.pop(0) if self.statuses else 201
        if isinstance(status, Exception):
            raise status
        return status


@pytest.fixture
def push_api(api_factory):
    api = api_factory(vapid_private_key=VAPID[0], vapid_public_key=VAPID[1])
    api.clock.now = EIGHT_THIRTY_MX
    return api


def subscribe(api, *, user_id=None, guest_id=None, hour=8, tz=MX, lang="en"):
    key = ec.generate_private_key(ec.SECP256R1())
    auth = webpush.b64url(os.urandom(16))
    endpoint = f"https://fcm.googleapis.com/fcm/send/{uuid.uuid4()}"
    if user_id is None and guest_id is None:
        guest_id = uuid.uuid4()
    with api.db.connect() as conn:
        repo.upsert_push(conn, {"user_id": user_id, "guest_id": guest_id, "endpoint": endpoint,
                                "p256dh": webpush.b64url(webpush._point(key.public_key())), "auth": auth,
                                "lang": lang, "tz": tz, "hour": hour, "now": api.clock()})
    return SimpleNamespace(key=key, auth=auth, endpoint=endpoint, guest_id=guest_id, user_id=user_id)


def run(api, post):
    return send_due(api.ctx, api.clock(), post=post)


def subs(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT fails, last_sent_day FROM push_subscriptions").fetchall()


def test_the_hour_is_the_subscribers_own():
    sub = {"tz": MX, "hour": 8, "last_sent_day": None}
    assert due_day(sub, datetime(2026, 11, 20, 13, 59, tzinfo=timezone.utc)) is None  # 07:59 there
    assert due_day(sub, EIGHT_THIRTY_MX) == date(2026, 11, 20)
    assert due_day(sub, datetime(2026, 11, 20, 16, 0, tzinfo=timezone.utc)) is None  # 10:00: the window is over
    assert due_day({**sub, "last_sent_day": date(2026, 11, 20)}, EIGHT_THIRTY_MX) is None
    assert due_day({**sub, "tz": "Europe/Madrid", "hour": 15}, EIGHT_THIRTY_MX) == date(2026, 11, 20)  # 15:30


def test_one_reminder_a_day_that_names_no_card(push_api):
    sub = subscribe(push_api, lang="es")
    post = FakePost()
    assert run(push_api, post) == {"sent": 1, "skipped": 0, "failed": 0, "deleted": 0}
    assert run(push_api, post)["sent"] == 0  # the next run of the same day
    [(url, headers, body)] = post.calls
    assert url == sub.endpoint and headers["Authorization"].startswith("vapid t=")
    assert json.loads(decrypt(body, sub.key, sub.auth)) == {"lang": "es"}  # only the language, never the card
    assert subs(push_api) == [{"fails": 0, "last_sent_day": date(2026, 11, 20)}]
    push_api.clock.advance(days=1)
    assert run(push_api, post)["sent"] == 1


def test_no_reminder_when_the_card_is_already_open(push_api):
    sub = subscribe(push_api)
    with push_api.db.connect() as conn:
        repo.record_daily_draw(conn, sub.guest_id, date(2026, 11, 20), "major-18-moon", False)
    post = FakePost()
    assert run(push_api, post)["skipped"] == 1 and post.calls == []
    assert run(push_api, post)["skipped"] == 0  # the day is marked: not looked at again


def test_an_accounts_open_card_counts_on_any_device(push_api):
    user = uuid.uuid4()
    subscribe(push_api, user_id=user)
    with push_api.db.connect() as conn:
        repo.account_daily_draw(conn, user, date(2026, 11, 20), "major-18-moon", False)
    assert run(push_api, FakePost())["skipped"] == 1


def test_a_gone_subscription_is_deleted_at_once(push_api):
    subscribe(push_api)
    assert run(push_api, FakePost(410))["deleted"] == 1 and subs(push_api) == []


def test_three_failures_in_a_row_delete_and_a_success_resets(push_api):
    subscribe(push_api)
    post = FakePost(500, httpx.ConnectError("down"), 201, 503, 429, 500)
    for expected in (1, 2, 0, 1, 2):
        run(push_api, post)
        assert subs(push_api)[0]["fails"] == expected
        push_api.clock.advance(days=1)
    assert run(push_api, post)["deleted"] == 1 and subs(push_api) == []


def test_a_refused_vapid_key_is_logged_and_never_counted(push_api, caplog):
    subscribe(push_api)
    with caplog.at_level("ERROR", logger="arcana.push"):
        for _ in range(4):
            run(push_api, FakePost(403))
            push_api.clock.advance(days=1)
    assert subs(push_api)[0]["fails"] == 0 and "VAPID" in caplog.text


def test_without_keys_nothing_is_sent(api):
    api.clock.now = EIGHT_THIRTY_MX
    subscribe(api)
    post = FakePost()
    assert run(api, post) == {"sent": 0, "skipped": 0, "failed": 0, "deleted": 0} and post.calls == []


def test_the_job_starts_only_with_keys(db, monkeypatch):
    started = []

    async def fake(*args, **kwargs):
        started.append(args[-1] if args else None)

    async def fake_push(ctx, interval_s):
        started.append(("push", interval_s))

    monkeypatch.setattr(housekeeping, "daily_loop", fake)
    monkeypatch.setattr(housekeeping, "cleanup_loop", fake)
    monkeypatch.setattr(housekeeping, "push_loop", fake_push)
    settings = replace(load_settings({}), database_url=db.url, run_migrations=False, daily_job_interval_s=0.0)
    keys = webpush.load_vapid(*VAPID)
    asyncio.run(run_background(SimpleNamespace(settings=settings, db=db, clock=lambda: EIGHT_THIRTY_MX, vapid=keys)))
    assert ("push", 600.0) in started
    started.clear()
    asyncio.run(run_background(SimpleNamespace(settings=settings, db=db, clock=lambda: EIGHT_THIRTY_MX, vapid=None)))
    assert all(not (isinstance(s, tuple) and s[0] == "push") for s in started)
```

Create `deploy/test-gen-vapid.sh`:

```bash
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
[ "$fails" -eq 0 ] && echo "OK: gen-vapid.sh" || { echo "FAIL: $fails"; exit 1; }
```

```bash
chmod +x deploy/test-gen-vapid.sh
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_push_job.py)
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.push'`.

Run:

```bash
deploy/test-gen-vapid.sh
```

Expected: FAIL — `deploy/gen-vapid.sh: No such file or directory` (`grep` stops with exit 2: "gen-vapid.sh has no ENV_FILE: stop").

- [ ] **Step 3: Implement**

In `api/app/repo.py`, replace:

```python
def touch_guest_push(conn, guest_id, now) -> None:
```

with:

```python
def push_subscriptions(conn) -> list[dict]:
    """Every subscription; the reminder job picks the due ones by their own zone and hour."""
    return conn.execute("SELECT id, user_id, guest_id, endpoint, p256dh, auth, lang, tz, hour, last_sent_day"
                        " FROM push_subscriptions ORDER BY created_at").fetchall()


def claim_push_day(conn, sub_id, day) -> bool:
    """At most one reminder a day: the first run that marks the day sends; a parallel or repeated run finds it
    marked. False when the day is already marked or the row is gone."""
    return conn.execute("UPDATE push_subscriptions SET last_sent_day = %s WHERE id = %s"
                        " AND last_sent_day IS DISTINCT FROM %s RETURNING id", (day, sub_id, day)).fetchone() \
        is not None


def opened_daily(conn, user_id, guest_id, day) -> bool:
    where, args = _daily_owner(user_id, guest_id)
    return conn.execute(f"SELECT 1 FROM daily_draws WHERE {where} AND day = %s", (*args, day)).fetchone() is not None


def push_delivered(conn, sub_id) -> None:
    conn.execute("UPDATE push_subscriptions SET fails = 0 WHERE id = %s", (sub_id,))


def push_failed(conn, sub_id) -> int | None:
    """One more failed delivery in a row; the new count, None when the row is gone."""
    row = conn.execute("UPDATE push_subscriptions SET fails = fails + 1 WHERE id = %s RETURNING fails",
                       (sub_id,)).fetchone()
    return row["fails"] if row else None


def delete_push_by_id(conn, sub_id) -> None:
    conn.execute("DELETE FROM push_subscriptions WHERE id = %s", (sub_id,))


def touch_guest_push(conn, guest_id, now) -> None:
```

Create `api/app/push.py`:

```python
"""The morning reminder (stage 8.1 §2.5, §3): every PUSH_JOB_INTERVAL_S the job looks for subscriptions whose local
hour has come and sends one Web Push message — at most one a day per browser, none on a day the owner's card is
already open (the day is marked anyway). The message names no card: it carries only the language, and the service
worker shows "Your card for today is waiting" (the lock screen). No model is called.

Delivery: 2xx — the failure count goes back to 0; 404 / 410 — the browser dropped the subscription, the row goes at
once; 401 / 403 — the push service refused our VAPID key (a server problem, not the browser's): logged, not counted,
so a key mistake never wipes everyone's subscriptions; anything else (5xx, 429, a network error) — one more failure
in a row, and MAX_FAILS in a row delete the row. Nothing about the person or the endpoint is logged.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

import httpx

from app import repo, webpush
from app.limits import resolve_tz

log = logging.getLogger("arcana.push")

SEND_WINDOW_H = 2      # from the chosen hour up to 2 hours later; a day missed by then is skipped, not sent late
MAX_FAILS = 3          # spec §3: three failed deliveries in a row delete the subscription
GONE = frozenset({404, 410})
REFUSED_KEY = frozenset({401, 403})
POST_TIMEOUT_S = 10.0


def due_day(sub: dict, now: datetime) -> date | None:
    """The subscriber's local day when its hour has come and that day has had no reminder yet; else None."""
    local = now.astimezone(resolve_tz(sub["tz"]))
    if sub["last_sent_day"] == local.date():
        return None
    start = local.replace(hour=sub["hour"], minute=0, second=0, microsecond=0)
    return local.date() if start <= local < start + timedelta(hours=SEND_WINDOW_H) else None


def http_post(url: str, headers: dict, body: bytes) -> int:
    return httpx.post(url, headers=headers, content=body, timeout=POST_TIMEOUT_S, follow_redirects=False).status_code


def send_due(ctx, now: datetime, post=http_post) -> dict[str, int]:
    counts = {"sent": 0, "skipped": 0, "failed": 0, "deleted": 0}
    if ctx.vapid is None:
        return counts
    with ctx.db.connect() as conn:
        subs = repo.push_subscriptions(conn)
    for sub in subs:
        day = due_day(sub, now)
        if day is None:
            continue
        with ctx.db.connect() as conn:
            if not repo.claim_push_day(conn, sub["id"], day):
                continue
            opened = repo.opened_daily(conn, sub["user_id"], sub["guest_id"], day)
        if opened:
            counts["skipped"] += 1
            continue
        headers, body = webpush.push_request(sub["endpoint"], sub["p256dh"], sub["auth"], {"lang": sub["lang"]},
                                             ctx.vapid, ctx.settings.vapid_subject, now.timestamp())
        try:
            status = post(sub["endpoint"], headers, body)
        except httpx.HTTPError:
            status = 0
        with ctx.db.connect() as conn:
            if 200 <= status < 300:
                repo.push_delivered(conn, sub["id"])
                counts["sent"] += 1
            elif status in GONE:
                repo.delete_push_by_id(conn, sub["id"])
                counts["deleted"] += 1
            elif status in REFUSED_KEY:
                log.error("a push service refused our VAPID key (HTTP %s): check VAPID_* in deploy/.env", status)
                counts["failed"] += 1
            elif (repo.push_failed(conn, sub["id"]) or 0) >= MAX_FAILS:
                repo.delete_push_by_id(conn, sub["id"])
                counts["deleted"] += 1
            else:
                counts["failed"] += 1
    return counts


async def push_loop(ctx, interval_s: float) -> None:
    while True:
        try:
            counts = await asyncio.to_thread(send_due, ctx, ctx.clock())
            if any(counts.values()):
                log.info("morning reminders: %s", counts)
        except Exception:  # a failed run must not stop the loop or the API
            log.exception("morning reminder run failed")
        await asyncio.sleep(interval_s)
```

In `api/app/housekeeping.py`, replace:

```python
from app.daily import daily_loop
```

with:

```python
from app.daily import daily_loop
from app.push import push_loop
```

In `api/app/housekeeping.py`, replace:

```python
    if settings.daily_job_interval_s > 0:
        jobs.append(("daily", daily_loop(ctx, settings.daily_job_interval_s)))
```

with:

```python
    if settings.daily_job_interval_s > 0:
        jobs.append(("daily", daily_loop(ctx, settings.daily_job_interval_s)))
    if getattr(ctx, "vapid", None) is not None and settings.push_job_interval_s > 0:  # stage 8.1: keys set
        jobs.append(("push", push_loop(ctx, settings.push_job_interval_s)))
```

In `api/app/housekeeping.py`, replace:

```python
- the card-of-the-day job (app.daily.daily_loop).
"""
```

with:

```python
- the card-of-the-day job (app.daily.daily_loop);
- stage 8.1: the morning reminder job (app.push.push_loop), only with VAPID keys in deploy/.env.
"""
```

Create `deploy/gen-vapid.sh`:

```bash
#!/usr/bin/env bash
# Дописывает в deploy/.env ключи VAPID для напоминаний в браузере (этап 8.1): VAPID_PRIVATE_KEY (секрет) и
# VAPID_PUBLIC_KEY. Ключи не печатаются: их пишет Python прямо во временный файл с правами 600, который затем
# дописывается в конец .env. Если ключи уже есть — ничего не меняет и выходит с кодом 3: новые ключи молча
# отрезали бы все уже оформленные подписки. Запуск — шаг оператора по слову владельца, затем выкладка.
# ENV_FILE и PYTHON — только для deploy/test-gen-vapid.sh.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${ENV_FILE:-$DIR/.env}"
PYTHON="${PYTHON:-$DIR/../api/.venv/bin/python}"
[ -f "$ENV_FILE" ] || { echo "нет файла $(basename "$ENV_FILE")" >&2; exit 1; }
if grep -q '^VAPID_PRIVATE_KEY=' "$ENV_FILE"; then
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
{ printf '\n# stage 8.1: browser reminders (Web Push, VAPID), made by deploy/gen-vapid.sh; never print or commit\n'; cat "$tmp"; } >> "$ENV_FILE"
echo "ключи VAPID дописаны в $(basename "$ENV_FILE")"
```

```bash
chmod +x deploy/gen-vapid.sh
```

The script is **not** run against `deploy/.env` in this task: that is the operator step after the merge (see «Operator steps»).

In `deploy/docker-compose.yml`, the `api` service's `environment`, replace:

```yaml
      GOOGLE_SIGNIN: ${GOOGLE_SIGNIN:-}
```

with:

```yaml
      GOOGLE_SIGNIN: ${GOOGLE_SIGNIN:-}
      # stage 8.1: browser reminders; the keys are written into deploy/.env by deploy/gen-vapid.sh (empty — off)
      VAPID_PRIVATE_KEY: ${VAPID_PRIVATE_KEY:-}
      VAPID_PUBLIC_KEY: ${VAPID_PUBLIC_KEY:-}
      VAPID_SUBJECT: ${VAPID_SUBJECT:-}
      PUSH_JOB_INTERVAL_S: ${PUSH_JOB_INTERVAL_S:-}
```

Append to the end of `deploy/.env.example` (names only, empty values — the example never holds a key):

```bash
# --- stage 8.1: browser reminders (Web Push). NEVER typed by hand: deploy/gen-vapid.sh appends both keys to
# deploy/.env without printing them; it refuses to run twice (new keys would cut every subscription). Empty — off.
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
# who sends (RFC 8292 "sub"): the site address (default) or mailto:<address>
VAPID_SUBJECT=
# how often the reminder job runs, seconds (default 600); 0 — off
PUSH_JOB_INTERVAL_S=
```

In `api/README.md`, the table «Переменные окружения», replace:

```markdown
| `RUN_MIGRATIONS` | `true` | применять миграции при старте |
```

with:

```markdown
| `RUN_MIGRATIONS` | `true` | применять миграции при старте |
| `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY` | пусто | ключи напоминаний в браузере (Web Push, этап 8.1); их дописывает в `deploy/.env` скрипт `deploy/gen-vapid.sh`, не печатая; пусто, испорчено или не пара — напоминания выключены (строка в журнале без ключа), API работает |
| `VAPID_SUBJECT` | `https://arcanadiary.com` | кто шлёт напоминания (поле `sub` VAPID): адрес сайта или `mailto:` |
| `PUSH_JOB_INTERVAL_S` | `600` | как часто задача напоминаний ищет подписки, у которых наступил их час; `0` — выключить |
```

In `api/README.md`, replace:

```markdown
## Ограничения, о которых надо помнить
```

with:

```markdown
## Карта дня как привычка (этап 8.1)

Спецификация — `docs/superpowers/specs/2026-11-27-stage8-1-daily-habit-design.md`, план —
`docs/superpowers/plans/2026-11-27-stage8-1-daily-habit.md`. Модель здесь не вызывается нигде: тексты дня пишет прежняя
задача, календарь берёт их из `daily_cache` или из базы карт.

- `GET /api/daily` — у вошедшего карта считается по аккаунту (`daily_draws.user_id`, одна на местный день на всех
  устройствах), у гостя — по куке, как раньше. В ответе ещё `streak`, `best_streak` и `mark` (`{"felt", "note"}` у
  вошедшего, `null` у гостя).
- `GET /api/daily/calendar?lang=&month=YYYY-MM&tz=` — месяц аккаунта: карты, тексты, отметки, заметки, серии, самая
  частая карта (от 2 раз). Бесплатно — текущий и прошлый месяц; старше — `locked: true`, данные хранятся. Гость получает
  последние 7 дней этой куки без отметок и заметок.
- `PUT /api/daily/{day}` `{"felt": "yes"|"partly"|"no"|null, "note": "…"|null}` — только вошедший (`401 sign_in`), только
  за день с картой (`404`), заметка до 280 знаков. Заметка и отметка не уходят ни в модель, ни в события.
- `POST /api/account/claim` с `device` (по умолчанию) переносит и карты дня этой куки (день, где у аккаунта уже есть карта,
  остаётся с картой аккаунта), и её подписки на напоминания. Выгрузка — `daily_cards` и `push_subscriptions` (только имя
  службы push, без адреса и ключей); удаление аккаунта удаляет и то и другое.
- `GET /api/push/key`, `POST`/`DELETE /api/push/subscription` — подписка браузера. Принимаются только https-адреса
  известных служб push (`app/webpush.py: PUSH_HOSTS`), иначе `422 endpoint`: сервер никогда не шлёт запросы по чужому
  адресу. Без ключей VAPID — `GET` отвечает `enabled: false`, `POST` — `503 push_off`.
- Задача напоминаний (раз в `PUSH_JOB_INTERVAL_S`, только при ключах): подписке, у которой по её часовому поясу наступил её
  час (окно 2 часа), — одно сообщение в день; если карта дня сегодня уже открыта — не шлёт (день всё равно отмечен).
  Сообщение зашифровано (RFC 8291) и несёт только язык; текст «Your card for today is waiting» показывает service worker
  сайта. `404`/`410` — подписка удаляется сразу; `401`/`403` — служба отвергла наш ключ VAPID: строка в журнале, отказ не
  считается; остальные отказы — три подряд удаляют подписку. Своя реализация на `cryptography` и PyJWT (решение плана 1),
  проверена примером RFC 8291.
- Хранение: карты дня гостя — 60 дней; подписка гостя без визита на карту дня — 90 дней; у аккаунта — до удаления;
  тексты дня в `daily_cache` — 62 дня (решение владельца 54: в календаре текущего и прошлого месяца — тот текст,
  что был прочитан утром).
- Миграция `009_daily_journal` повторяема (`IF EXISTS`/`IF NOT EXISTS`); до неё новый код отвечает `503`, не `500`.
  **Откат API на код до 8.1 после 009:** простой возврат к f1b3c38 нельзя — старая уборка удаляет все `daily_draws`
  старше 7 дней, и календари аккаунтов тоже (переменная `CLEANUP_INTERVAL_S` тут не помогает: в контейнер она не
  передаётся, а первая уборка идёт сразу при старте). Откат = выкладка содержимого локальной ветки `rollback-pre-8.1`
  (f1b3c38 + один коммит: уборка `daily_draws` трогает только гостевые строки, `AND user_id IS NULL`) в `main` — по
  слову владельца. Ветку выкладывать только на базу, где уже есть 009. Миграция 009 не откатывается. Старое
  `delete_account` не знает о `user_id` и подписках: аккаунт, удалённый во время отката, оставит заметки и подписки —
  после возврата 8.1 удалить их по `deleted_accounts`.

## Ограничения, о которых надо помнить
```

- [ ] **Step 4: Run the tests**

Run:

```bash
(cd api && .venv/bin/pytest -q tests/test_push_job.py tests/test_housekeeping.py)
```

Expected: `27 passed`.

Run:

```bash
deploy/test-gen-vapid.sh
```

Expected: nine `PASS` lines and `OK: gen-vapid.sh`; nothing in the output looks like a key.

Run:

```bash
git status --short deploy/
```

Expected: only `deploy/docker-compose.yml`, `deploy/.env.example`, `deploy/gen-vapid.sh`, `deploy/test-gen-vapid.sh` (`deploy/.env` and `deploy/caddy/stage_auth.caddy*` are never opened).

Run:

```bash
(cd api && .venv/bin/pytest -q )
```

Expected: `1750 passed`.

- [ ] **Step 5: Commit**

```bash
git add api/app/push.py api/app/repo.py api/app/housekeeping.py api/tests/test_push_job.py deploy/gen-vapid.sh deploy/test-gen-vapid.sh deploy/docker-compose.yml deploy/.env.example api/README.md
git commit -m "feat(api): morning reminder job — once a day at the person's hour, not when the card is open, three failures delete; gen-vapid.sh (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 9: Site: the streak line, the calendar link and the evening mark under the Card of the Day

**Files:**
- Create: `site/src/lib/journal.ts` (+ `journal.test.ts`), `site/src/components/ui/EveningMark.tsx`
- Modify: `site/src/lib/types.ts`, `site/src/lib/daily.ts`, `site/src/islands/DailyIsland.tsx`,
  `site/src/i18n/{en,es}.ts`, `site/src/i18n/i18n.test.ts`, `site/src/styles/global.css`
- Test: `site/src/islands/DailyIsland.test.tsx`, `site/src/lib/journal.test.ts`, `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `GET /api/daily` fields `streak`, `best_streak`, `mark` (Task 2); `PUT /api/daily/{day}` (Task 3);
  `daily_felt` (Task 5); `callJson`, `withQuery`, `siteFetch`, `pagePath`, `sendEvent`/`analyticsEvent`.
- Produces:
  - `types.Felt = 'yes'|'partly'|'no'`, `types.FELTS`, `types.DailyMark {felt, note}`; `DailyCard.streak?`,
    `.best_streak?`, `.mark?`; `DailyShown.streak: number`, `.mark: DailyMark | null`
  - `journal.CALENDAR_TAB = 'daily'`, `DAILY_NOTE_MAX = 280`, `EVENING_HOUR = 17`, `STREAK_SHOWN_FROM = 2`;
    `calendarHref(lang) -> '/diary?tab=daily' | '/es/diario?tab=daily'`; `eveningOpen(now: Date) -> boolean`;
    types `CalendarDay`, `Calendar`, `MarkPatch`, `MarkSaved`, `JournalApi`; `createJournalApi(fetchFn): JournalApi`
    (`calendar(lang, month?, tz?)`, `mark(day, patch)`)
  - `<EveningMark lang idBase initial place surface save onSaved? onSignedOut? guest? />` — sends `daily_felt {place}`
    only on the first mark of the day; never the mark or the note. `guest` (owner decision 56): the same question, the
    answers `disabled`, no note field, the line `eveningSignIn`; nothing is sent
  - DailyIsland shows it from 17:00 for every card from the API (not for the card-base fallback): an account with
    its mark, a guest (`mark === null`) inactive
  - dictionary keys (11, total 277): `dailyStreak`, `dailyCalendarLink`, `eveningQuestion`, `feltYes`, `feltPartly`,
    `feltNo`, `eveningNoteLabel`, `eveningNoteSave`, `eveningSaved`, `eveningFailed`, `eveningSignIn`

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/journal.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { fakeFetch, jsonResponse } from './testing/fakes';
import { calendarHref, createJournalApi, eveningOpen } from './journal';

describe('the Card of the Day as a habit (stage 8.1)', () => {
  it('links the calendar tab of the diary in each language', () => {
    expect(calendarHref('en')).toBe('/diary?tab=daily');
    expect(calendarHref('es')).toBe('/es/diario?tab=daily');
  });

  it('opens the evening question at 17:00 local time', () => {
    expect(eveningOpen(new Date(2026, 10, 22, 16, 59))).toBe(false);
    expect(eveningOpen(new Date(2026, 10, 22, 17, 0))).toBe(true);
    expect(eveningOpen(new Date(2026, 10, 22, 23, 59))).toBe(true);
  });

  it('asks for a month and puts a mark with JSON', async () => {
    const served = fakeFetch(jsonResponse(200, { days: [] }), jsonResponse(200, { day: '2026-11-22', felt: 'yes', note: null, noted_at: 'x' }));
    const api = createJournalApi(served.fetch);
    await api.calendar('es', '2026-11', 'America/Mexico_City');
    const saved = await api.mark('2026-11-22', { felt: 'yes' });
    expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual([
      'GET /api/daily/calendar?lang=es&month=2026-11&tz=America%2FMexico_City', 'PUT /api/daily/2026-11-22']);
    expect(served.calls[1].body).toEqual({ felt: 'yes' });
    expect(saved.ok && saved.data.felt).toBe('yes');
  });
});
```

In `site/src/islands/DailyIsland.test.tsx`, replace:

```tsx
import { byText, cleanup, click, mount } from '../lib/testing/dom';
```

with:

```tsx
import { byText, cleanup, click, mount, submit, typeInto } from '../lib/testing/dom';
```

In `site/src/islands/DailyIsland.test.tsx`, replace:

```tsx
    const link = byText<HTMLAnchorElement>(root, text, 'a');
    expect(link.getAttribute('href')).toBe(href);
    expect(root.querySelectorAll('.daily a')).toHaveLength(1);
```

with:

```tsx
    const link = byText<HTMLAnchorElement>(root, text, 'a');
    expect(link.getAttribute('href')).toBe(href);
    const links = Array.from(root.querySelectorAll<HTMLAnchorElement>('.daily a')).map((a) => a.getAttribute('href'));
    expect(links.filter((h) => h === href)).toHaveLength(1); // stage 8.1: the calendar link is the only other one
    expect(links).toHaveLength(2);
```

Append to the end of `site/src/islands/DailyIsland.test.tsx`:

```tsx
// Stage 8.1 (spec 2026-11-27 §2.1, §2.3): the streak line, the calendar link and the evening mark.
describe('the Card of the Day as a habit (stage 8.1)', () => {
  const card = (extra: Record<string, unknown>) => () => jsonResponse(200, {
    day: '2026-11-22', card: { card_id: 'major-18-moon', name: 'The Moon', reversed: false }, text: 'Rest tonight.',
    source: 'cache', streak: 1, best_streak: 1, mark: null, ...extra,
  });

  afterEach(() => vi.useRealTimers());

  it.each([
    ['en', 'Day 4 in a row · Your month in cards', '/diary?tab=daily'],
    ['es', 'Día 4 seguido · Tu mes en cartas', '/es/diario?tab=daily'],
  ] as const)('%s: the streak line links the calendar', async (lang, line, href) => {
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': card({ streak: 4, best_streak: 6 }) }).fetch);
    const { root } = await mount(<DailyIsland lang={lang} />);
    await click(byText(root, t(lang).dailyTap, 'span').closest('button')!);
    const streak = root.querySelector('.daily__streak')!;
    expect(streak.textContent).toBe(line);
    expect(streak.querySelector('a')!.getAttribute('href')).toBe(href);
  });

  it('the first day shows only the calendar link', async () => {
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': card({}) }).fetch);
    const { root } = await mount(<DailyIsland lang="en" />);
    await click(byText(root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(root.querySelector('.daily__streak')!.textContent).toBe('Your month in cards');
  });

  it('an account sees the evening question from 17:00; a mark is saved and counted once, the note never', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 18, 0));
    const served = routeFetch({
      'GET /api/daily': card({ mark: { felt: null, note: null } }),
      'PUT /api/daily/2026-11-22': (call) => jsonResponse(200, { day: '2026-11-22', felt: 'partly', note: null, noted_at: 'x',
        ...(call.body as object) }),
    });
    vi.stubGlobal('fetch', served.fetch);
    vi.mocked(sendEvent).mockClear();
    const { root } = await mount(<DailyIsland lang="en" />);
    await click(byText(root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(byText(root, "Did today's card show up in your day?")).toBeTruthy();
    await click(byText(root, 'Partly', 'button'));
    expect(byText(root, 'Partly', 'button').getAttribute('aria-pressed')).toBe('true');
    await click(byText(root, 'Yes', 'button'));
    const input = root.querySelector<HTMLInputElement>('#daily-mark-note')!;
    expect(input.maxLength).toBe(280);
    await typeInto(input, 'The talk went well.');
    await submit(input.closest('form')!);
    expect(served.calls.filter((c) => c.method === 'PUT').map((c) => c.body)).toEqual([
      { felt: 'partly' }, { felt: 'yes' }, { note: 'The talk went well.' }]);
    const felt = vi.mocked(sendEvent).mock.calls.map(([e]) => e).filter((e) => e.name === 'daily_felt');
    expect(felt).toEqual([{ name: 'daily_felt', tool: null, lang: 'en', params: { place: 'daily' } }]);
    expect(JSON.stringify(vi.mocked(sendEvent).mock.calls)).not.toContain('talk went well');
  });

  it('before 17:00 there is no evening question; a guest after 17:00 sees it inactive, with the sign-in line', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 16, 59));
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': card({ mark: { felt: null, note: null } }) }).fetch);
    const first = await mount(<DailyIsland lang="en" />);
    await click(byText(first.root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(first.root.querySelector('.evening')).toBeNull();
    cleanup();
    vi.setSystemTime(new Date(2026, 10, 22, 21, 0));
    const served = routeFetch({ 'GET /api/daily': card({ mark: null }) });
    vi.stubGlobal('fetch', served.fetch);
    const guest = await mount(<DailyIsland lang="en" />);
    await click(byText(guest.root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(byText(guest.root, "Did today's card show up in your day?")).toBeTruthy();
    expect(byText(guest.root, 'Sign in to mark your days and keep your cards')).toBeTruthy();
    const yes = byText<HTMLButtonElement>(guest.root, 'Yes', 'button');
    expect(yes.disabled).toBe(true);
    await click(yes);
    expect(guest.root.querySelector('.evening input')).toBeNull();
    expect(served.calls.filter((c) => c.method === 'PUT')).toEqual([]);
  });
});
```

In `site/src/i18n/i18n.test.ts`, replace:

```ts
    expect(keys('en').length).toBe(266);
```

with:

```ts
    expect(keys('en').length).toBe(277);
```

In `site/src/i18n/i18n.test.ts`, replace:

```ts
  it('have the same keys in English and Spanish', () => {
```

with:

```ts
  it('use the exact words of the stage 8.1 spec (2026-11-27 §2.1, §2.3)', () => {
    expect([t('en').dailyStreak, t('en').dailyCalendarLink, t('es').dailyStreak, t('es').dailyCalendarLink]).toEqual([
      'Day {n} in a row', 'Your month in cards', 'Día {n} seguido', 'Tu mes en cartas']);
    expect([t('en').eveningQuestion, t('es').eveningQuestion]).toEqual([
      "Did today's card show up in your day?", '¿Apareció la carta de hoy en tu día?']);
    expect([t('en').feltYes, t('en').feltPartly, t('en').feltNo, t('es').feltYes, t('es').feltPartly, t('es').feltNo])
      .toEqual(['Yes', 'Partly', 'No', 'Sí', 'En parte', 'No']);
  });

  it('have the same keys in English and Spanish', () => {
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/journal.test.ts src/islands/DailyIsland.test.tsx src/i18n'
```

Expected: FAIL — `Failed to resolve import "./journal"`; DailyIsland finds no `.daily__streak`; i18n: `expected 266 to be 277`.

- [ ] **Step 3: Implement**

In `site/src/lib/types.ts`, replace:

```ts
/** 200 of GET /api/daily. */
export interface DailyCard {
  day: string;
  card: { card_id: string; name: string; reversed: boolean };
  text: string;
  source: 'cache' | 'fallback';
}
```

with:

```ts
/** The evening mark under the Card of the Day (stage 8.1 §2.3). */
export type Felt = 'yes' | 'partly' | 'no';
export const FELTS: readonly Felt[] = ['yes', 'partly', 'no'];

export interface DailyMark {
  felt: Felt | null;
  note: string | null;
}

/** 200 of GET /api/daily. Stage 8.1: the streak, and today's mark for an account (null for a guest). */
export interface DailyCard {
  day: string;
  card: { card_id: string; name: string; reversed: boolean };
  text: string;
  source: 'cache' | 'fallback';
  streak?: number;
  best_streak?: number;
  mark?: DailyMark | null;
}
```

In `site/src/lib/daily.ts`, replace:

```ts
import type { DailyCard, Lang } from './types';
```

with:

```ts
import type { DailyCard, DailyMark, Lang } from './types';
```

In `site/src/lib/daily.ts`, replace:

```ts
  day: string;
  fromBase: boolean; // true: the site's own card from the base (the API was unavailable)
}
```

with:

```ts
  day: string;
  fromBase: boolean; // true: the site's own card from the base (the API was unavailable)
  streak: number; // stage 8.1: days in a row; 0 for a card from the base
  mark: DailyMark | null; // stage 8.1: today's evening mark of an account; null for a guest and a card from the base
}
```

In `site/src/lib/daily.ts`, replace:

```ts
      text: result.data.text, day: result.data.day, fromBase: false,
    } };
```

with:

```ts
      text: result.data.text, day: result.data.day, fromBase: false,
      streak: typeof result.data.streak === 'number' ? result.data.streak : 0, mark: result.data.mark ?? null,
    } };
```

In `site/src/lib/daily.ts`, replace:

```ts
  return { card, name: cardName(card, lang), reversed: false, text: meaning.upright, day: isoDay, fromBase: true };
```

with:

```ts
  return { card, name: cardName(card, lang), reversed: false, text: meaning.upright, day: isoDay, fromBase: true,
    streak: 0, mark: null };
```

Create `site/src/lib/journal.ts`:

```ts
// The Card of the Day as a habit (stage 8.1, spec 2026-11-27 §2): the streak line, the evening mark's hour, the
// calendar's address and its requests — GET /api/daily/calendar and PUT /api/daily/{day}. A mark and a note go only
// to these two requests: never to an event, never to a model.
import { callJson, withQuery, type ApiResult, type FetchFn } from './api';
import { pagePath } from './routes';
import type { Felt, Lang } from './types';

export const CALENDAR_TAB = 'daily';
export const DAILY_NOTE_MAX = 280;
export const EVENING_HOUR = 17;
export const STREAK_SHOWN_FROM = 2; // "Day 1 in a row" says nothing: the line starts on the second day

/** "Your month in cards": the Card of the Day tab of the diary. */
export function calendarHref(lang: Lang): string {
  return `${pagePath('diary', lang)}?tab=${CALENDAR_TAB}`;
}

/** The evening question shows from 17:00 local time (spec §2.3). */
export function eveningOpen(now: Date): boolean {
  return now.getHours() >= EVENING_HOUR;
}

export interface CalendarDay {
  day: string;
  card: { card_id: string; name: string; reversed: boolean };
  text: string;
  source: 'cache' | 'fallback';
  felt?: Felt | null; // an account only
  note?: string | null;
}

export interface Calendar {
  guest: boolean;
  today: string;
  month: string | null;
  months: string[]; // the free months, oldest first
  locked: boolean;
  streak: number;
  best_streak: number;
  top_card: { card_id: string; name: string; count: number } | null;
  days: CalendarDay[];
}

export interface MarkPatch {
  felt?: Felt | null;
  note?: string | null;
}

export interface MarkSaved {
  day: string;
  felt: Felt | null;
  note: string | null;
  noted_at: string | null;
}

export interface JournalApi {
  calendar(lang: Lang, month: string | undefined, tz: string | undefined): Promise<ApiResult<Calendar>>;
  mark(day: string, patch: MarkPatch): Promise<ApiResult<MarkSaved>>;
}

export function createJournalApi(fetchFn: FetchFn): JournalApi {
  return {
    calendar: (lang, month, tz) => callJson(fetchFn, withQuery('/api/daily/calendar', { lang, month, tz })),
    mark: (day, patch) => callJson(fetchFn, `/api/daily/${encodeURIComponent(day)}`, {
      method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(patch),
    }),
  };
}
```

Create `site/src/components/ui/EveningMark.tsx`:

```tsx
// The evening mark (stage 8.1 §2.3): "Did today's card show up in your day?" — Yes / Partly / No and one optional
// line of up to 280 characters. Under the Card of the Day from 17:00 and in the calendar for any past day. A guest
// (owner decision 56) sees the same question with inactive answers and a sign-in line, no note field, and nothing is
// sent. The mark and the line go only to PUT /api/daily/{day}; the event daily_felt says only where a first mark was
// set. Everything shown back is text.
import { useState } from 'preact/hooks';
import { t, type DictKey } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import type { ApiResult } from '../../lib/api';
import { DAILY_NOTE_MAX, type MarkPatch, type MarkSaved } from '../../lib/journal';
import { FELTS, type DailyMark, type Felt, type Lang } from '../../lib/types';

const FELT_KEYS: Record<Felt, DictKey> = { yes: 'feltYes', partly: 'feltPartly', no: 'feltNo' };

interface Props {
  lang: Lang;
  idBase: string;
  initial: DailyMark;
  place: 'daily' | 'calendar';
  surface: 'night' | 'day';
  save: (patch: MarkPatch) => Promise<ApiResult<MarkSaved>>;
  onSaved?: (saved: MarkSaved) => void;
  onSignedOut?: () => void;
  guest?: boolean;
}

type State = 'idle' | 'saving' | 'saved' | 'failed';

export function EveningMark({ lang, idBase, initial, place, surface, save, onSaved, onSignedOut, guest = false }: Props) {
  const d = t(lang);
  const [felt, setFelt] = useState<Felt | null>(initial.felt);
  const [note, setNote] = useState(initial.note ?? '');
  const [state, setState] = useState<State>('idle');
  const day = surface === 'day';

  const send = async (patch: MarkPatch): Promise<boolean> => {
    setState('saving');
    const result = await save(patch);
    if (result.ok) {
      setFelt(result.data.felt);
      setNote(result.data.note ?? '');
      setState('saved');
      onSaved?.(result.data);
      return true;
    }
    if (result.status === 401 && onSignedOut) onSignedOut();
    setState('failed');
    return false;
  };

  const pick = async (value: Felt) => {
    if (guest || state === 'saving') return;
    const first = felt === null;
    if ((await send({ felt: value })) && first) sendEvent(analyticsEvent('daily_felt', null, lang, { place }));
  };

  const saveNote = async (event: Event) => {
    event.preventDefault();
    if (state === 'saving') return;
    await send({ note: note.trim() === '' ? null : note });
  };

  return (
    <section class="evening" aria-labelledby={`${idBase}-question`}>
      <h3 id={`${idBase}-question`} class="evening__question">{d.eveningQuestion}</h3>
      <div class="chips" role="group" aria-labelledby={`${idBase}-question`}>
        {FELTS.map((value) => (
          <button key={value} type="button" class={day ? 'chip chip--day' : 'chip'} aria-pressed={felt === value}
            disabled={guest} aria-disabled={state === 'saving'} onClick={() => void pick(value)}>
            {d[FELT_KEYS[value]]}
          </button>
        ))}
      </div>
      {guest ? <p class="small">{d.eveningSignIn}</p> : (
      <form class="field evening__note" onSubmit={(e) => void saveNote(e)}>
        <label for={`${idBase}-note`}>{d.eveningNoteLabel}</label>
        <input id={`${idBase}-note`} type="text" class={day ? 'input input--day' : 'input'} maxLength={DAILY_NOTE_MAX}
          value={note} onInput={(e) => setNote((e.target as HTMLInputElement).value)} />
        <button type="submit" class="btn btn--outline" disabled={state === 'saving'}>{d.eveningNoteSave}</button>
      </form>
      )}
      <p class="small" role="status">{state === 'saved' ? d.eveningSaved : ''}</p>
      {state === 'failed' ? <p role="alert">{d.eveningFailed}</p> : null}
    </section>
  );
}
```

In `site/src/islands/DailyIsland.tsx`, replace:

```tsx
// (L-EN-16, L-ES-16) is wave V1.1 (owner decision 42, 24.11.2026).
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../i18n';
import { analyticsEvent, sendEvent } from '../lib/analytics';
import { siteApi } from '../lib/siteApi';
```

with:

```tsx
// (L-EN-16, L-ES-16) is wave V1.1 (owner decision 42, 24.11.2026).
// Stage 8.1 (spec 2026-11-27 §2): under the text the streak line with the link to the calendar of the diary, and from
// 17:00 the evening mark — for an account (the API sends today's mark only to an account); a guest sees the question
// with inactive answers and a sign-in line (owner decision 56).
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { fill, t } from '../i18n';
import { analyticsEvent, sendEvent } from '../lib/analytics';
import { calendarHref, createJournalApi, eveningOpen, STREAK_SHOWN_FROM } from '../lib/journal';
import { siteApi, siteFetch } from '../lib/siteApi';
```

In `site/src/islands/DailyIsland.tsx`, replace:

```tsx
import { CardFace } from '../components/ui/CardFace';
import { HelpLine } from '../components/ui/HelpLine';
```

with:

```tsx
import { CardFace } from '../components/ui/CardFace';
import { EveningMark } from '../components/ui/EveningMark';
import { HelpLine } from '../components/ui/HelpLine';
```

In `site/src/islands/DailyIsland.tsx`, replace:

```tsx
  const tappedAt = useRef(0);
```

with:

```tsx
  const tappedAt = useRef(0);
  const journal = useMemo(() => createJournalApi(siteFetch()), []);
```

In `site/src/islands/DailyIsland.tsx`, replace:

```tsx
        ))}
        <button type="button" class="btn btn--outline" onClick={remind}>{d.remindTomorrow}</button>
```

with:

```tsx
        ))}
        <p class="daily__streak">
          {shown.streak >= STREAK_SHOWN_FROM ? `${fill(d.dailyStreak, { n: shown.streak })} · ` : ''}
          <a href={calendarHref(lang)}>{d.dailyCalendarLink}</a>
        </p>
        {!shown.fromBase && eveningOpen(new Date()) ? (
          <EveningMark lang={lang} idBase="daily-mark" initial={shown.mark ?? { felt: null, note: null }} place="daily"
            surface="night" guest={shown.mark === null} save={(patch) => journal.mark(shown.day, patch)} />
        ) : null}
        <button type="button" class="btn btn--outline" onClick={remind}>{d.remindTomorrow}</button>
```

In `site/src/i18n/en.ts`, replace:

```ts
  cardYesNoLink: 'Ask a yes or no question',
};
```

with:

```ts
  cardYesNoLink: 'Ask a yes or no question',
  // stage 8.1: the streak line and the evening mark under the Card of the Day (spec 2026-11-27 §2.1, §2.3)
  dailyStreak: 'Day {n} in a row',
  dailyCalendarLink: 'Your month in cards',
  eveningQuestion: "Did today's card show up in your day?",
  feltYes: 'Yes',
  feltPartly: 'Partly',
  feltNo: 'No',
  eveningNoteLabel: 'One line about your day (optional)',
  eveningNoteSave: 'Save',
  eveningSaved: 'Saved.',
  eveningFailed: "We couldn't save that. Please try again.",
  eveningSignIn: 'Sign in to mark your days and keep your cards',
};
```

In `site/src/i18n/es.ts`, replace:

```ts
  cardYesNoLink: 'Pregunta sí o no',
};
```

with:

```ts
  cardYesNoLink: 'Pregunta sí o no',
  // stage 8.1: the streak line and the evening mark under the Card of the Day (spec 2026-11-27 §2.1, §2.3)
  dailyStreak: 'Día {n} seguido',
  dailyCalendarLink: 'Tu mes en cartas',
  eveningQuestion: '¿Apareció la carta de hoy en tu día?',
  feltYes: 'Sí',
  feltPartly: 'En parte',
  feltNo: 'No',
  eveningNoteLabel: 'Una línea sobre tu día (opcional)',
  eveningNoteSave: 'Guardar',
  eveningSaved: 'Se guardó.',
  eveningFailed: 'No se pudo guardar. Intenta de nuevo.',
  eveningSignIn: 'Inicia sesión para marcar tus días y guardar tus cartas',
};
```

Append to the end of `site/src/styles/global.css` (tokens only):

```css
/* stage 8.1: the streak line and the evening mark under the Card of the Day, the same mark in the calendar */
.daily__streak { margin: 0; }
.evening { display: flex; flex-direction: column; gap: var(--space-3); width: 100%; max-width: 560px; text-align: left; }
.evening__question { margin: 0; font-size: var(--font-size-h-3); }
.evening__note { display: flex; flex-direction: column; gap: var(--space-2); }
.evening__note .btn { align-self: flex-start; }
```

- [ ] **Step 4: Run the tests**

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/journal.test.ts src/islands/DailyIsland.test.tsx src/i18n src/lib/daily.test.ts src/lib/guards.test.ts'
```

Expected: all pass (`DailyIsland.test.tsx` 8 tests, `journal.test.ts` 3).

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx astro check'
```

Expected: `0 errors`.

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npm run build'
```

Expected: no failures, `Tests … (500)` in total (skipped ones depend on whether `site/dist` exists), then `[build] Complete!`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/journal.ts site/src/lib/journal.test.ts site/src/components/ui/EveningMark.tsx site/src/lib/types.ts site/src/lib/daily.ts site/src/islands/DailyIsland.tsx site/src/islands/DailyIsland.test.tsx site/src/i18n site/src/styles/global.css
git commit -m "feat(site): streak line, link to the calendar and the evening mark under the Card of the Day (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 10: Site: the Card of the Day calendar in the diary

**Files:**
- Create: `site/src/components/ui/DailyCalendar.tsx` (+ `DailyCalendar.test.tsx`)
- Modify: `site/src/lib/journal.ts`, `site/src/islands/DiaryIsland.tsx`, `site/src/i18n/{en,es}.ts`,
  `site/src/i18n/i18n.test.ts`, `site/src/styles/global.css`
- Test: `site/src/lib/journal.test.ts`, `site/src/components/ui/DailyCalendar.test.tsx`,
  `site/src/islands/DiaryIsland.test.tsx`

**Interfaces:**
- Consumes: Task 9 (`journal.*`, `EveningMark`, `DailyMark`), `GET /api/daily/calendar` (Task 3),
  `daily_calendar_view` (Task 5), `formatDay`, `cardById`, `cardImage`, `errorMessageKey`, `SignInBlock`.
- Produces:
  - `journal.monthGrid(month) -> Array<Array<string | null>>` (Sunday first), `monthLabel(month, lang)`,
    `weekdayLabels(lang)`, `lastDays(today, count = 7)`
  - `<DailyCalendar lang api guest tz? onSignedOut? />` — sends `daily_calendar_view {signed_in}` once per mount
  - the diary: `/diary?tab=daily` (`/es/diario?tab=daily`) shows the calendar; `<nav class="diary__tabs">` with
    «Readings» / «Card of the Day» (`aria-current="page"` on the open one); a guest's sign-in returns to the tab
  - dictionary keys (12, total 289): `diaryTabsLabel`, `diaryTabReadings`, `calendarStreak`, `calendarBest`,
    `calendarTop`, `calendarPrev`, `calendarNext`, `calendarEmpty`, `calendarLocked`, `calendarGuestTitle`,
    `calendarSignIn`, `calendarDayCard` (the tab itself reuses `navDaily`)

- [ ] **Step 1: Write the failing tests**

Append to the end of `site/src/lib/journal.test.ts`:

```ts
describe('the calendar month (stage 8.1 §2.2)', () => {
  it('lays a month out in weeks from Sunday', async () => {
    const { monthGrid } = await import('./journal');
    const november = monthGrid('2026-11'); // 1 November 2026 is a Sunday
    expect(november[0]).toEqual(['2026-11-01', '2026-11-02', '2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06', '2026-11-07']);
    expect(november).toHaveLength(5);
    expect(november[4]).toEqual(['2026-11-29', '2026-11-30', null, null, null, null, null]);
    const february = monthGrid('2027-02'); // starts on a Monday, 28 days
    expect(february[0][0]).toBeNull();
    expect(february.flat().filter(Boolean)).toHaveLength(28);
  });

  it('names the month and the weekdays in each language', async () => {
    const { monthLabel, weekdayLabels } = await import('./journal');
    expect(monthLabel('2026-11', 'en')).toBe('November 2026');
    expect(monthLabel('2026-11', 'es')).toBe('noviembre de 2026');
    expect(weekdayLabels('en')[0]).toBe('Sun');
    expect(weekdayLabels('es')[0]).toBe('dom');
  });

  it('gives a guest the last seven days', async () => {
    const { lastDays } = await import('./journal');
    expect(lastDays('2026-12-02')).toEqual(['2026-11-26', '2026-11-27', '2026-11-28', '2026-11-29', '2026-11-30',
      '2026-12-01', '2026-12-02']);
  });
});
```

Create `site/src/components/ui/DailyCalendar.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../../lib/analytics';
import { createJournalApi } from '../../lib/journal';
import { byText, cleanup, click, mount, waitFor } from '../../lib/testing/dom';
import { jsonResponse, routeFetch } from '../../lib/testing/fakes';
import { DailyCalendar } from './DailyCalendar';

vi.mock('../../lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/analytics')>()), sendEvent: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.mocked(sendEvent).mockClear();
});

const MOON = { card_id: 'major-18-moon', name: 'The Moon', reversed: true };
const SUN = { card_id: 'major-19-sun', name: 'The Sun', reversed: false };
const month = (extra: Record<string, unknown> = {}) => ({
  guest: false, today: '2026-11-22', month: '2026-11', months: ['2026-10', '2026-11'], locked: false, streak: 3,
  best_streak: 5, top_card: { card_id: 'major-18-moon', name: 'The Moon', count: 2 },
  days: [
    { day: '2026-11-03', card: MOON, text: 'Rest <b>tonight</b>.', source: 'fallback', felt: 'partly', note: 'Slept early.' },
    { day: '2026-11-22', card: SUN, text: 'Go out.', source: 'cache', felt: null, note: null },
  ],
  ...extra,
});

function setup(routes: Parameters<typeof routeFetch>[0]) {
  const served = routeFetch(routes);
  return { served, api: createJournalApi(served.fetch) };
}

describe('the Card of the Day calendar (stage 8.1 §2.2)', () => {
  it('shows the month with small cards, the streaks and the most frequent card, and counts the view once', async () => {
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, month()) });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    expect(root.querySelector('.cal__stats')!.textContent).toBe('Streak now: 3 · Best streak: 5 · Most frequent this month: The Moon ×2');
    const days = Array.from(root.querySelectorAll<HTMLButtonElement>('.cal__day'));
    expect(days.map((b) => b.getAttribute('aria-label'))).toEqual(['Card of Tuesday 3 November', 'Card of Sunday 22 November']);
    expect(days[0].querySelector('img')!.classList.contains('is-reversed')).toBe(true);
    expect(root.querySelectorAll('.cal__empty')).toHaveLength(28);
    expect(vi.mocked(sendEvent).mock.calls.map(([e]) => e)).toEqual([
      { name: 'daily_calendar_view', tool: null, lang: 'en', params: { signed_in: true } }]);
  });

  it('a past day opens with its text as text and its mark and note', async () => {
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, month()) });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    await click(root.querySelector('.cal__day')!);
    const detail = root.querySelector('.cal__detail')!;
    expect(detail.querySelector('h3')!.textContent).toBe('The Moon · Reversed');
    expect(detail.querySelector('.cal__text')!.textContent).toBe('Rest <b>tonight</b>.');
    expect(detail.querySelector('b')).toBeNull();
    expect(byText(detail, 'Partly', 'button').getAttribute('aria-pressed')).toBe('true');
    expect(detail.querySelector<HTMLInputElement>('input')!.value).toBe('Slept early.');
  });

  it('today has no mark before 17:00', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 10, 0));
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, month()) });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    await click(root.querySelectorAll('.cal__day')[1]);
    expect(root.querySelector('.cal__detail .evening')).toBeNull();
  });

  it('moves to the previous month and no further', async () => {
    const { api, served } = setup({
      'GET /api/daily/calendar': () => jsonResponse(200, month()),
      'GET /api/daily/calendar?lang=en&month=2026-10': () => jsonResponse(200, month({ month: '2026-10', days: [], top_card: null })),
    });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    expect(byText<HTMLButtonElement>(root, 'Next month', 'button').disabled).toBe(true);
    await click(byText(root, 'Previous month', 'button'));
    await waitFor(() => byText(root, 'October 2026'));
    expect(byText<HTMLButtonElement>(root, 'Previous month', 'button').disabled).toBe(true);
    expect(byText(root, 'No cards this month yet.')).toBeTruthy();
    expect(served.calls.map((c) => c.url)).toEqual(['/api/daily/calendar?lang=en', '/api/daily/calendar?lang=en&month=2026-10']);
    expect(vi.mocked(sendEvent)).toHaveBeenCalledTimes(1);
  });

  it('a guest sees the last 7 days without marks, in Spanish', async () => {
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, { ...month(), guest: true, month: null,
      months: [], top_card: null, days: [{ day: '2026-11-22', card: SUN, text: 'Sal.', source: 'cache' }] }) });
    const { root } = await mount(<DailyCalendar lang="es" api={api} guest />);
    await waitFor(() => byText(root, 'Tus últimos 7 días'));
    expect(root.querySelectorAll('.cal__week > div')).toHaveLength(7);
    await click(root.querySelector('.cal__day')!);
    expect(root.querySelector('.cal__detail .evening')).toBeNull();
    expect(vi.mocked(sendEvent).mock.calls[0][0].params).toEqual({ signed_in: false });
  });
});
```

Append to the end of `site/src/islands/DiaryIsland.test.tsx`:

```tsx
// Stage 8.1 (spec 2026-11-27 §2.2, §2.4): the "Card of the Day" tab of the diary.
describe('the Card of the Day tab (stage 8.1)', () => {
  const CAL = { today: '2026-11-22', streak: 1, best_streak: 1, top_card: null, locked: false,
    days: [{ day: '2026-11-22', card: { card_id: 'major-19-sun', name: 'The Sun', reversed: false }, text: 'Go out.', source: 'cache' }] };

  it('a guest sees the last 7 days, then "Sign in to keep your cards" and the sign-in block that comes back here', async () => {
    history.replaceState(null, '', '/diary?tab=daily');
    const served = serve({ 'GET /api/daily/calendar': () => jsonResponse(200, { ...CAL, guest: true, month: null, months: [] }) });
    const { root } = await open((r) => byText(r, 'Your last 7 days'));
    expect(byText(root, 'Sign in to keep your cards')).toBeTruthy();
    expect(root.querySelector('input[type="email"]')).not.toBeNull();
    const tabs = Array.from(root.querySelectorAll<HTMLAnchorElement>('.diary__tabs a'));
    expect(tabs.map((a) => [a.textContent, a.getAttribute('href'), a.getAttribute('aria-current')])).toEqual([
      ['Readings', '/diary', null], ['Card of the Day', '/diary?tab=daily', 'page']]);
    expect(served.calls.some((c) => c.method === 'PUT')).toBe(false);
  });

  it('signed in: the month of the account instead of the list', async () => {
    history.replaceState(null, '', '/diary?tab=daily');
    h.session = { access_token: 'tok-a' };
    const served = serve({ 'GET /api/daily/calendar': () => jsonResponse(200, { ...CAL, guest: false, month: '2026-11',
      months: ['2026-10', '2026-11'] }) });
    const { root } = await open((r) => byText(r, 'November 2026'));
    expect(served.calls.some((c) => c.url.startsWith('/api/diary'))).toBe(false);
    expect(root.querySelector('.diary__tabs a[aria-current="page"]')!.textContent).toBe('Card of the Day');
  });

  it('the readings tab is the list, as before, with the tabs above it', async () => {
    h.session = { access_token: 'tok-a' };
    serve({ 'GET /api/diary': page([ITEM]) });
    const { root } = await open((r) => expect(r.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(root.querySelector('.diary__tabs a[aria-current="page"]')!.textContent).toBe('Readings');
  });
});
```

In `site/src/i18n/i18n.test.ts`, replace:

```ts
    expect(keys('en').length).toBe(277);
```

with:

```ts
    expect(keys('en').length).toBe(289);
```

In `site/src/i18n/i18n.test.ts`, replace:

```ts
      .toEqual(['Yes', 'Partly', 'No', 'Sí', 'En parte', 'No']);
  });
```

with:

```ts
      .toEqual(['Yes', 'Partly', 'No', 'Sí', 'En parte', 'No']);
    expect([t('en').navDaily, t('es').navDaily, t('en').calendarSignIn]).toEqual([
      'Card of the Day', 'Carta del día', 'Sign in to keep your cards']);
  });
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/journal.test.ts src/components/ui/DailyCalendar.test.tsx src/islands/DiaryIsland.test.tsx src/i18n'
```

Expected: FAIL — `monthGrid` is not exported, `Failed to resolve import "./DailyCalendar"`, the diary has no «Your last 7 days», i18n `expected 277 to be 289`.

- [ ] **Step 3: Implement**

Append to the end of `site/src/lib/journal.ts`:

```ts
const LOCALE: Record<Lang, string> = { en: 'en-US', es: 'es-MX' };

/** The weeks of a month "YYYY-MM", Sunday first (as in the United States and Mexico); null pads the first and last
 * week. Each day is "YYYY-MM-DD". */
export function monthGrid(month: string): Array<Array<string | null>> {
  const [year, number] = month.split('-').map(Number);
  const days = new Date(Date.UTC(year, number, 0)).getUTCDate();
  const cells: Array<string | null> = Array(new Date(Date.UTC(year, number - 1, 1)).getUTCDay()).fill(null);
  for (let day = 1; day <= days; day++) cells.push(`${month}-${String(day).padStart(2, '0')}`);
  while (cells.length % 7) cells.push(null);
  return Array.from({ length: cells.length / 7 }, (_, week) => cells.slice(week * 7, week * 7 + 7));
}

/** "November 2026" / "noviembre de 2026". */
export function monthLabel(month: string, lang: Lang): string {
  const [year, number] = month.split('-').map(Number);
  return new Intl.DateTimeFormat(LOCALE[lang], { month: 'long', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(year, number - 1, 1)));
}

/** Short weekday names, Sunday first: "Sun"… / "dom"…. */
export function weekdayLabels(lang: Lang): string[] {
  const format = new Intl.DateTimeFormat(LOCALE[lang], { weekday: 'short', timeZone: 'UTC' });
  return Array.from({ length: 7 }, (_, i) => format.format(new Date(Date.UTC(2026, 10, 1 + i)))); // 1.11.2026: Sunday
}

/** The days of a guest's calendar: the last `count` days up to `today`, oldest first. */
export function lastDays(today: string, count = 7): string[] {
  const end = Date.parse(`${today}T00:00:00Z`);
  return Array.from({ length: count }, (_, i) => new Date(end - (count - 1 - i) * 86_400_000).toISOString().slice(0, 10));
}
```

Create `site/src/components/ui/DailyCalendar.tsx`:

```tsx
// The Card of the Day calendar (stage 8.1 §2.2, §2.4) in the diary's "Card of the Day" tab. Signed in: the month as a
// grid, a small card on each day that had one (reversed cards turned), the streaks and the month's most frequent card
// above it; the free calendar moves between this month and the previous one. A day opens below the grid with its
// card, its text and, for a past day (today from 17:00), the evening mark. A guest gets the last 7 days of this
// device without marks; the sign-in block comes after it (DiaryIsland). Everything shown is text.
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import { formatDay } from '../../lib/daily';
import { cardById, cardImage } from '../../lib/deck';
import { errorMessageKey, type ErrorKind } from '../../lib/errors';
import {
  eveningOpen, lastDays, monthGrid, monthLabel, weekdayLabels, type Calendar, type CalendarDay, type JournalApi,
  type MarkSaved,
} from '../../lib/journal';
import type { Lang } from '../../lib/types';
import { EveningMark } from './EveningMark';

interface Props {
  lang: Lang;
  api: JournalApi;
  guest: boolean;
  tz?: string;
  onSignedOut?: () => void;
}

type State = { type: 'loading' } | { type: 'ready'; calendar: Calendar } | { type: 'failed'; error: ErrorKind };

export function DailyCalendar({ lang, api, guest, tz, onSignedOut }: Props) {
  const d = t(lang);
  const [month, setMonth] = useState<string | undefined>(undefined);
  const [state, setState] = useState<State>({ type: 'loading' });
  const [picked, setPicked] = useState<string | null>(null);
  const counted = useRef(false);

  const load = async (wanted: string | undefined) => {
    setState({ type: 'loading' });
    const result = await api.calendar(lang, wanted, tz);
    if (result.ok) {
      setState({ type: 'ready', calendar: result.data });
      if (!counted.current) {
        counted.current = true;
        sendEvent(analyticsEvent('daily_calendar_view', null, lang, { signed_in: !guest }));
      }
      return;
    }
    if (result.status === 401 && onSignedOut) return onSignedOut();
    setState({ type: 'failed', error: result.error });
  };

  useEffect(() => { void load(month); }, [month]);

  if (state.type === 'loading') return <section class="cal" aria-busy="true" />;
  if (state.type === 'failed') return <section class="cal"><p role="alert">{d[errorMessageKey(state.error)]}</p></section>;

  const { calendar } = state;
  const byDay = new Map(calendar.days.map((day) => [day.day, day]));
  const saved = (day: string, mark: MarkSaved) => setState({ type: 'ready', calendar: { ...calendar,
    days: calendar.days.map((item) => (item.day === day ? { ...item, felt: mark.felt, note: mark.note } : item)) } });

  const cell = (iso: string | null) => {
    if (iso === null) return <span class="cal__pad" />;
    const item = byDay.get(iso);
    const number = String(Number(iso.slice(8)));
    if (!item) return <span class="cal__empty">{number}</span>;
    const card = cardById(item.card.card_id);
    return (
      <button type="button" class="cal__day" aria-pressed={picked === iso} onClick={() => setPicked(iso)}
        aria-label={fill(d.calendarDayCard, { date: formatDay(iso, lang) })}>
        {card ? <img src={cardImage(card, 160)} alt="" width={160} height={274}
          class={item.card.reversed ? 'is-reversed' : undefined} /> : null}
        <span>{number}</span>
      </button>
    );
  };

  const pickedDay: CalendarDay | undefined = picked ? byDay.get(picked) : undefined;
  const canMark = (iso: string) => !guest && (iso < calendar.today || (iso === calendar.today && eveningOpen(new Date())));
  const [oldest, newest] = [calendar.months[0], calendar.months[calendar.months.length - 1]];

  return (
    <section class="cal" aria-labelledby="cal-title">
      <p class="cal__stats">
        {fill(d.calendarStreak, { n: calendar.streak })} · {fill(d.calendarBest, { n: calendar.best_streak })}
        {calendar.top_card ? ` · ${fill(d.calendarTop, { name: calendar.top_card.name, count: calendar.top_card.count })}` : ''}
      </p>
      {guest ? (
        <>
          <h2 id="cal-title" class="h2">{d.calendarGuestTitle}</h2>
          <div class="cal__week">{lastDays(calendar.today).map((iso) => <div key={iso}>{cell(iso)}</div>)}</div>
        </>
      ) : (
        <>
          <div class="cal__nav">
            <button type="button" class="btn btn--text" disabled={calendar.month === oldest}
              onClick={() => { setPicked(null); setMonth(oldest); }}>{d.calendarPrev}</button>
            <h2 id="cal-title" class="h2">{calendar.month ? monthLabel(calendar.month, lang) : ''}</h2>
            <button type="button" class="btn btn--text" disabled={calendar.month === newest}
              onClick={() => { setPicked(null); setMonth(newest); }}>{d.calendarNext}</button>
          </div>
          {calendar.locked ? <p>{d.calendarLocked}</p> : (
            <table class="cal__grid">
              <thead><tr>{weekdayLabels(lang).map((name) => <th key={name} scope="col">{name}</th>)}</tr></thead>
              <tbody>
                {monthGrid(calendar.month!).map((week, i) => (
                  <tr key={i}>{week.map((iso, j) => <td key={iso ?? `pad-${i}-${j}`}>{cell(iso)}</td>)}</tr>
                ))}
              </tbody>
            </table>
          )}
          {!calendar.locked && calendar.days.length === 0 ? <p class="small">{d.calendarEmpty}</p> : null}
        </>
      )}
      {pickedDay ? (
        <article class="cal__detail" aria-labelledby="cal-detail-title">
          <p class="eyebrow">{formatDay(pickedDay.day, lang)}</p>
          <h3 id="cal-detail-title">{pickedDay.card.name}{pickedDay.card.reversed ? ` · ${d.reversedTag}` : ''}</h3>
          <p class="cal__text">{pickedDay.text}</p>
          {canMark(pickedDay.day) ? (
            <EveningMark key={pickedDay.day} lang={lang} idBase={`cal-${pickedDay.day}`} place="calendar" surface="day"
              initial={{ felt: pickedDay.felt ?? null, note: pickedDay.note ?? null }}
              save={(patch) => api.mark(pickedDay.day, patch)} onSaved={(mark) => saved(pickedDay.day, mark)}
              onSignedOut={onSignedOut} />
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
// page, where it can be turned off (owner decision 16).
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
```

with:

```tsx
// page, where it can be turned off (owner decision 16).
// Stage 8.1 (spec 2026-11-27 §2.2, §2.4): two tabs, "Readings" (/diary) and "Card of the Day" (/diary?tab=daily, the
// calendar). A guest on the calendar tab sees this device's last 7 days, then "Sign in to keep your cards" and the
// sign-in block; the sign-in brings the tab back.
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
import { entryParam } from '../lib/diary';
```

with:

```tsx
import { entryParam } from '../lib/diary';
import { CALENDAR_TAB, calendarHref, createJournalApi } from '../lib/journal';
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
import { DiaryEntry } from '../components/ui/DiaryEntry';
```

with:

```tsx
import { DailyCalendar } from '../components/ui/DailyCalendar';
import { DiaryEntry } from '../components/ui/DiaryEntry';
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
type View =
  | { type: 'loading' }
```

with:

```tsx
type Tab = 'readings' | 'daily';

type View =
  | { type: 'loading' }
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
  const api = useMemo(() => createAccountApi(siteFetch()), []);
```

with:

```tsx
  const api = useMemo(() => createAccountApi(siteFetch()), []);
  const journal = useMemo(() => createJournalApi(siteFetch()), []);
  // read in the browser only: the page is built without an address (the build renders the loading view)
  const tab = useMemo<Tab>(() => (typeof location !== 'undefined'
    && new URLSearchParams(location.search).get('tab') === CALENDAR_TAB ? 'daily' : 'readings'), []);
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
    if (status.type === 'off') return <div class="diary"><p class="lead">{d.diarySignInSoon}</p></div>;
```

with:

```tsx
    if (status.type === 'off') {
      return (
        <div class="diary">
          <DiaryTabs lang={lang} tab={tab} />
          {tab === 'daily' ? <DailyCalendar lang={lang} api={journal} guest tz={deviceTimeZone()} /> : null}
          <p class="lead">{d.diarySignInSoon}</p>
        </div>
      );
    }
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
      <div class="diary diary--signin">
        <p class="lead">{d.diaryWhy}</p>
```

with:

```tsx
      <div class="diary diary--signin">
        <DiaryTabs lang={lang} tab={tab} />
        {tab === 'daily' ? <DailyCalendar lang={lang} api={journal} guest tz={deviceTimeZone()} /> : null}
        <p class="lead">{tab === 'daily' ? d.calendarSignIn : d.diaryWhy}</p>
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
            const entry = entryParam(location.search);
            if (entry) back.searchParams.set('r', entry);
```

with:

```tsx
            const entry = entryParam(location.search);
            if (entry) back.searchParams.set('r', entry);
            if (tab === 'daily') back.searchParams.set('tab', CALENDAR_TAB); // stage 8.1: back to the calendar
```

In `site/src/islands/DiaryIsland.tsx`, replace:

```tsx
      {view.entry ? (
        <DiaryEntry key={view.round} lang={lang} id={view.entry} api={api} tz={deviceTimeZone()} onSignedOut={() => void signedOut()} />
      ) : (
        <DiaryList key={view.round} lang={lang} api={api} onSignedOut={() => void signedOut()} />
      )}
```

with:

```tsx
      {view.entry ? null : <DiaryTabs lang={lang} tab={tab} />}
      {view.entry ? (
        <DiaryEntry key={view.round} lang={lang} id={view.entry} api={api} tz={deviceTimeZone()} onSignedOut={() => void signedOut()} />
      ) : tab === 'daily' ? (
        <DailyCalendar key={view.round} lang={lang} api={journal} guest={false} tz={deviceTimeZone()} onSignedOut={() => void signedOut()} />
      ) : (
        <DiaryList key={view.round} lang={lang} api={api} onSignedOut={() => void signedOut()} />
      )}
```

Append to the end of `site/src/islands/DiaryIsland.tsx`:

```tsx
/** Stage 8.1: the two parts of the diary as links (a page each), the current one marked. */
function DiaryTabs({ lang, tab }: { lang: Lang; tab: Tab }) {
  const d = t(lang);
  return (
    <nav class="diary__tabs" aria-label={d.diaryTabsLabel}>
      <a href={pagePath('diary', lang)} aria-current={tab === 'readings' ? 'page' : undefined}>{d.diaryTabReadings}</a>
      <a href={calendarHref(lang)} aria-current={tab === 'daily' ? 'page' : undefined}>{d.navDaily}</a>
    </nav>
  );
}
```

`location` is read inside `useMemo` behind `typeof location !== 'undefined'`: Astro renders the island once at build time, where there is no `location` (a plain read fails the build with `location is not defined`).

In `site/src/i18n/en.ts`, replace:

```ts
  eveningSignIn: 'Sign in to mark your days and keep your cards',
};
```

with:

```ts
  eveningSignIn: 'Sign in to mark your days and keep your cards',
  // stage 8.1: the Card of the Day calendar in the diary (spec 2026-11-27 §2.2, §2.4)
  diaryTabsLabel: 'Diary sections',
  diaryTabReadings: 'Readings',
  calendarStreak: 'Streak now: {n}',
  calendarBest: 'Best streak: {n}',
  calendarTop: 'Most frequent this month: {name} ×{count}',
  calendarPrev: 'Previous month',
  calendarNext: 'Next month',
  calendarEmpty: 'No cards this month yet.',
  calendarLocked: 'Older months are kept and will open with Plus.',
  calendarGuestTitle: 'Your last 7 days',
  calendarSignIn: 'Sign in to keep your cards',
  calendarDayCard: 'Card of {date}',
};
```

In `site/src/i18n/es.ts`, replace:

```ts
  eveningSignIn: 'Inicia sesión para marcar tus días y guardar tus cartas',
};
```

with:

```ts
  eveningSignIn: 'Inicia sesión para marcar tus días y guardar tus cartas',
  // stage 8.1: the Card of the Day calendar in the diary (spec 2026-11-27 §2.2, §2.4)
  diaryTabsLabel: 'Secciones del diario',
  diaryTabReadings: 'Lecturas',
  calendarStreak: 'Racha actual: {n}',
  calendarBest: 'Mejor racha: {n}',
  calendarTop: 'La más frecuente del mes: {name} ×{count}',
  calendarPrev: 'Mes anterior',
  calendarNext: 'Mes siguiente',
  calendarEmpty: 'Todavía no hay cartas este mes.',
  calendarLocked: 'Los meses anteriores se guardan y se abrirán con Plus.',
  calendarGuestTitle: 'Tus últimos 7 días',
  calendarSignIn: 'Inicia sesión para guardar tus cartas',
  calendarDayCard: 'Carta del {date}',
};
```

Append to the end of `site/src/styles/global.css` (tokens only):

```css
.diary__tabs { display: flex; flex-wrap: wrap; gap: var(--space-4); margin-bottom: var(--space-4); }
.diary__tabs a { min-height: 44px; display: inline-flex; align-items: center; }
.diary__tabs a[aria-current='page'] { font-weight: 600; text-decoration: none; }
.cal { display: flex; flex-direction: column; gap: var(--space-4); max-width: 720px; }
.cal__stats { margin: 0; }
.cal__nav { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
.cal__nav .h2 { margin: 0; text-align: center; }
.cal__grid { width: 100%; border-collapse: collapse; table-layout: fixed; }
.cal__grid th { font-weight: 600; font-size: var(--font-size-small); padding: var(--space-1) 0; }
.cal__grid td { padding: var(--space-1); vertical-align: top; text-align: center; }
.cal__week { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: var(--space-2); }
.cal__day { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); width: 100%; min-height: 44px; padding: var(--space-1); border: 1px solid var(--color-day-line); border-radius: var(--radius-card); background: transparent; color: var(--color-day-text); cursor: pointer; font: inherit; }
.cal__day[aria-pressed='true'] { border-color: var(--color-day-accent); }
.cal__day img { width: 100%; max-width: 48px; height: auto; border-radius: var(--radius-card); }
.cal__empty { display: block; min-height: 44px; padding: var(--space-1); color: var(--color-day-text-muted); }
.cal__detail { display: flex; flex-direction: column; gap: var(--space-3); }
.cal__detail h3 { margin: 0; font-size: var(--font-size-h-3); }
.cal__text { margin: 0; white-space: pre-line; }
```

- [ ] **Step 4: Run the tests**

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/journal.test.ts src/components/ui/DailyCalendar.test.tsx src/islands/DiaryIsland.test.tsx src/i18n'
```

Expected: all pass (`DailyCalendar.test.tsx` 5, `journal.test.ts` 6).

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx astro check'
```

Expected: `0 errors`.

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npm run build'
```

Expected: no failures, `(511)` tests in total, `[build] Complete!`.

- [ ] **Step 5: Commit**

```bash
git add site/src/components/ui/DailyCalendar.tsx site/src/components/ui/DailyCalendar.test.tsx site/src/lib/journal.ts site/src/lib/journal.test.ts site/src/islands/DiaryIsland.tsx site/src/islands/DiaryIsland.test.tsx site/src/i18n site/src/styles/global.css
git commit -m "feat(site): the Card of the Day calendar in the diary — month grid, streaks, the day's text and mark; guests see 7 days (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 11: Site: service worker, manifest, «Remind me each morning», iPhone hint, account switch

**Files:**
- Create: `site/src/lib/sw.ts` (+ `sw.test.ts`), `site/src/pages/sw.js.ts`, `site/src/lib/push.ts` (+ `push.test.ts`),
  `site/src/lib/testing/push.ts`, `site/src/components/ui/PushOffer.tsx` (+ test), `site/src/components/ui/PushSwitch.tsx`
  (+ test)
- Modify: `site/src/islands/DailyIsland.tsx`, `site/src/islands/AccountIsland.tsx`, `site/src/i18n/{en,es}.ts`,
  `site/src/i18n/i18n.test.ts`, `site/src/styles/global.css`, `site/public/site.webmanifest`, `tools/site/check_dist.py`,
  `deploy/Caddyfile`, `deploy/test-site-routes.sh`
- Test: the four new test files, `site/src/i18n/i18n.test.ts`, `tools/site/test_check_dist.py`, `deploy/test-site-routes.sh`

**Interfaces:**
- Consumes: `GET /api/push/key`, `POST`/`DELETE /api/push/subscription` (Task 7), `push_enabled`, `push_click` (Task 5),
  `DailyShown.streak`/`.fromBase` (Task 9), `StorageLike`/`browserStorage`, `deviceTimeZone`, `localIsoDay`.
- Produces:
  - `/sw.js` built by `src/pages/sw.js.ts` from `swSource(swTexts())`: `install`, `activate`, `push` (shows
    `notifTitle`/`notifBody` of the message's language, tag `daily`), `notificationclick` (POST `push_click`, focus or
    open `/daily` / `/es/carta-del-dia`); **no `fetch` handler** (nothing cached)
  - `push.SW_URL = '/sw.js'`, `HOUR_KEY = 'ad_push_hour'`, `REFRESHED_KEY = 'ad_push_refreshed'`,
    `DISMISSED_KEY = 'ad_push_dismissed'`, `DEFAULT_HOUR = 8`, `OFFER_STREAK = 3`, `DISMISS_DAYS = 30`;
    `PushEnv`, `browserEnv()`, `pushSupport(env) -> 'yes'|'ios-home'|'no'`, `hourLabel(hour, lang)`, `keyBytes(b64url)`,
    `storedHour(storage)`, `offerDismissed(now, storage)`, `createPushApi(fetchFn): PushApi`,
    `currentSubscription(env)`, `turnOn(deps, hour) -> 'on'|'denied'|'off'|'failed'`, `turnOff(deps)`,
    `refresh(deps, subscription)`
  - `<PushOffer lang streak env? api? storage? now? />` under the card; `<PushSwitch lang env? api? storage? />` on the
    account page
  - `site.webmanifest`: `"display": "standalone"` (`start_url` stays `/`)
  - `check_dist.DATA_FILES` includes `sw.js`; Caddy serves `/sw.js` with `Cache-Control: no-cache`
  - dictionary keys (13, total 302): `pushOffer`, `pushHourLabel`, `pushNotNow`, `pushOn`, `pushOff`, `pushDenied`,
    `pushFailed`, `pushIosHint`, `notifTitle`, `notifBody`, `accountPushTitle`, `accountPushOn`, `accountPushNone`

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/testing/push.ts`:

```ts
// A browser with (or without) Web Push, for the reminder tests: a fake service worker container, push manager and
// Notification permission. Nothing here talks to a real push service.
import type { PushEnv } from '../push';

export interface FakeBrowser {
  env: PushEnv;
  registered: string[];
  subscribed: Array<{ applicationServerKey: Uint8Array }>;
  unsubscribed: number;
  asked: number;
}

export function fakeBrowser(options: { permission?: NotificationPermission; answer?: NotificationPermission;
  subscribed?: boolean; userAgent?: string; standalone?: boolean; push?: boolean } = {}): FakeBrowser {
  const state: FakeBrowser = { env: undefined as unknown as PushEnv, registered: [], subscribed: [], unsubscribed: 0, asked: 0 };
  let subscription: PushSubscription | null = null;
  const make = () => ({
    endpoint: 'https://fcm.googleapis.com/fcm/send/device-1',
    toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/device-1', keys: { p256dh: 'BPk', auth: 'au' } }),
    unsubscribe: async () => { state.unsubscribed += 1; subscription = null; return true; },
  }) as unknown as PushSubscription;
  if (options.subscribed) subscription = make();
  const pushManager = {
    getSubscription: async () => subscription,
    subscribe: async (init: { applicationServerKey: Uint8Array }) => { state.subscribed.push(init); subscription = make(); return subscription; },
  };
  const registration = { pushManager } as unknown as ServiceWorkerRegistration;
  let registeredYet = Boolean(options.subscribed);
  const notification = {
    permission: options.permission ?? 'default',
    requestPermission: async () => { state.asked += 1; notification.permission = options.answer ?? 'granted'; return notification.permission; },
  };
  state.env = {
    serviceWorker: {
      register: async (url: string) => { state.registered.push(url); registeredYet = true; return registration; },
      getRegistration: async () => (registeredYet ? registration : undefined),
    } as unknown as ServiceWorkerContainer,
    pushManager: options.push ?? true,
    notification,
    userAgent: options.userAgent ?? 'Mozilla/5.0 (Linux; Android 14) Chrome/131',
    maxTouchPoints: 5,
    standalone: options.standalone ?? false,
  };
  return state;
}

export class MemoryStorage {
  items = new Map<string, string>();
  getItem(key: string) { return this.items.get(key) ?? null; }
  setItem(key: string, value: string) { this.items.set(key, value); }
  removeItem(key: string) { this.items.delete(key); }
}
```

Create `site/src/lib/sw.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import { swSource, swTexts } from './sw';

type Listener = (event: Record<string, unknown>) => void;

/** Runs the service worker's text against a stand-in for its global scope. */
function worker(windows: Array<{ url: string; focus: () => Promise<unknown> }> = []) {
  const listeners: Record<string, Listener> = {};
  const shown: Array<[string, Record<string, unknown>]> = [];
  const waits: Array<Promise<unknown>> = [];
  const scope = {
    addEventListener: (name: string, listener: Listener) => { listeners[name] = listener; },
    skipWaiting: vi.fn(),
    registration: { showNotification: async (title: string, options: Record<string, unknown>) => { shown.push([title, options]); } },
    clients: { claim: vi.fn(async () => {}), matchAll: vi.fn(async () => windows), openWindow: vi.fn(async () => null) },
  };
  const fetchFn = vi.fn(async () => new Response(null, { status: 204 }));
  new Function('self', 'fetch', swSource(swTexts()))(scope, fetchFn);
  const fire = async (name: string, event: Record<string, unknown>) => {
    listeners[name]({ ...event, waitUntil: (p: Promise<unknown>) => waits.push(p) });
    await Promise.all(waits);
  };
  return { listeners, shown, scope, fetchFn, fire };
}

describe('the service worker (stage 8.1 §4)', () => {
  it('shows the morning reminder in the language of the message, never a card', async () => {
    const sw = worker();
    await sw.fire('push', { data: { json: () => ({ lang: 'es', card: 'La Luna' }) } });
    expect(sw.shown).toEqual([['Arcana Diary', { body: 'Tu carta de hoy te espera', icon: '/icon-192.png', tag: 'daily',
      data: { lang: 'es' } }]]);
    await sw.fire('push', { data: { json: () => { throw new Error('not JSON'); } } });
    expect(sw.shown[1][1].body).toBe('Your card for today is waiting');
  });

  it('a click opens the Card of the Day of its language and is counted', async () => {
    const sw = worker();
    const close = vi.fn();
    await sw.fire('notificationclick', { notification: { close, data: { lang: 'es' } } });
    expect(close).toHaveBeenCalled();
    expect(sw.scope.clients.openWindow).toHaveBeenCalledWith('/es/carta-del-dia');
    const [url, init] = sw.fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/events');
    expect(JSON.parse(String(init.body))).toEqual({ name: 'push_click', tool: null, lang: 'es', params: {} });
  });

  it('a click focuses an open Card of the Day instead of opening another', async () => {
    const focus = vi.fn(async () => null);
    const sw = worker([{ url: 'https://arcanadiary.com/daily', focus }]);
    await sw.fire('notificationclick', { notification: { close: vi.fn(), data: { lang: 'en' } } });
    expect(focus).toHaveBeenCalled();
    expect(sw.scope.clients.openWindow).not.toHaveBeenCalled();
  });

  it('caches nothing: there is no fetch handler', () => {
    expect(Object.keys(worker().listeners).sort()).toEqual(['activate', 'install', 'notificationclick', 'push']);
  });
});
```

Create `site/src/lib/push.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { fakeFetch, jsonResponse } from './testing/fakes';
import { fakeBrowser, MemoryStorage } from './testing/push';
import {
  createPushApi, DISMISSED_KEY, HOUR_KEY, hourLabel, keyBytes, offerDismissed, pushSupport, REFRESHED_KEY, refresh,
  storedHour, turnOff, turnOn,
} from './push';

const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 Version/18.1 Mobile/15E148 Safari/604.1';
const IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.1 Safari/605.1.15';
const KEY = 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM';

describe('can this browser take a morning reminder (stage 8.1 §2.5)', () => {
  it('yes with a service worker, push and notifications; no without', () => {
    expect(pushSupport(fakeBrowser().env)).toBe('yes');
    expect(pushSupport(fakeBrowser({ push: false }).env)).toBe('no');
  });

  it('an iPhone or iPad outside the Home Screen app gets the hint, inside it the offer', () => {
    expect(pushSupport(fakeBrowser({ userAgent: IPHONE }).env)).toBe('ios-home');
    expect(pushSupport(fakeBrowser({ userAgent: IPAD }).env)).toBe('ios-home'); // iPadOS says Macintosh, with touch
    expect(pushSupport(fakeBrowser({ userAgent: IPHONE, standalone: true }).env)).toBe('yes');
  });

  it('names hours and reads the stored one', () => {
    expect([hourLabel(8, 'en'), hourLabel(20, 'en')]).toEqual(['8:00 AM', '8:00 PM']);
    expect(hourLabel(8, 'es')).toMatch(/^8:00/);
    const storage = new MemoryStorage();
    expect(storedHour(storage)).toBe(8);
    storage.setItem(HOUR_KEY, '6');
    expect(storedHour(storage)).toBe(6);
    storage.setItem(HOUR_KEY, '25');
    expect(storedHour(storage)).toBe(8);
  });

  it('turns the base64url key into the 65 bytes the browser wants', () => {
    const bytes = keyBytes(KEY);
    expect(bytes).toHaveLength(65);
    expect(bytes[0]).toBe(4);
  });

  it('"Not now" hides the offer for 30 days', () => {
    const storage = new MemoryStorage();
    storage.setItem(DISMISSED_KEY, String(Date.UTC(2026, 10, 1)));
    expect(offerDismissed(Date.UTC(2026, 10, 30), storage)).toBe(true);
    expect(offerDismissed(Date.UTC(2026, 11, 2), storage)).toBe(false);
    expect(offerDismissed(Date.UTC(2026, 11, 2), new MemoryStorage())).toBe(false);
  });
});

describe('turning the reminder on and off', () => {
  const deps = (browser: ReturnType<typeof fakeBrowser>, fetched: ReturnType<typeof fakeFetch>, storage = new MemoryStorage()) => ({
    env: browser.env, api: createPushApi(fetched.fetch), storage, lang: 'es' as const, tz: 'America/Mexico_City', today: '2026-11-22',
  });

  it('asks the permission, registers /sw.js, subscribes with the key and tells the API the hour', async () => {
    const browser = fakeBrowser();
    const fetched = fakeFetch(jsonResponse(200, { enabled: true, public_key: KEY }), jsonResponse(201, { hour: 7, tz: 'America/Mexico_City' }));
    const storage = new MemoryStorage();
    expect(await turnOn(deps(browser, fetched, storage), 7)).toBe('on');
    expect([browser.asked, browser.registered]).toEqual([1, ['/sw.js']]);
    expect(browser.subscribed[0].applicationServerKey).toHaveLength(65);
    expect(fetched.calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/push/key', 'POST /api/push/subscription']);
    expect(fetched.calls[1].body).toEqual({ endpoint: 'https://fcm.googleapis.com/fcm/send/device-1',
      keys: { p256dh: 'BPk', auth: 'au' }, hour: 7, tz: 'America/Mexico_City', lang: 'es' });
    expect([storage.getItem(HOUR_KEY), storage.getItem(REFRESHED_KEY)]).toEqual(['7', '2026-11-22']);
  });

  it('a refused permission registers nothing; reminders off on the server ask nothing', async () => {
    const refused = fakeBrowser({ answer: 'denied' });
    expect(await turnOn(deps(refused, fakeFetch(jsonResponse(200, { enabled: true, public_key: KEY }))), 8)).toBe('denied');
    expect(refused.registered).toEqual([]);
    const off = fakeBrowser();
    expect(await turnOn(deps(off, fakeFetch(jsonResponse(200, { enabled: false, public_key: '' }))), 8)).toBe('off');
    expect(off.asked).toBe(0);
  });

  it('turning off tells the API and drops the browser subscription', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const fetched = fakeFetch(jsonResponse(204, null));
    const storage = new MemoryStorage();
    storage.setItem(HOUR_KEY, '7');
    await turnOff(deps(browser, fetched, storage));
    expect(fetched.calls.map((c) => [c.method, c.url, c.body])).toEqual([
      ['DELETE', '/api/push/subscription', { endpoint: 'https://fcm.googleapis.com/fcm/send/device-1' }]]);
    expect(browser.unsubscribed).toBe(1);
    expect(storage.getItem(HOUR_KEY)).toBeNull();
  });

  it('refreshes once a day with the stored hour', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const fetched = fakeFetch(jsonResponse(201, { hour: 6, tz: 'UTC' }));
    const storage = new MemoryStorage();
    storage.setItem(HOUR_KEY, '6');
    const subscription = (await (await browser.env.serviceWorker!.getRegistration('/'))!.pushManager.getSubscription())!;
    await refresh(deps(browser, fetched, storage), subscription);
    await refresh(deps(browser, fetched, storage), subscription);
    expect(fetched.calls).toHaveLength(1);
    expect((fetched.calls[0].body as { hour: number }).hour).toBe(6);
  });
});
```

Create `site/src/components/ui/PushOffer.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../../lib/analytics';
import { createPushApi, DISMISSED_KEY } from '../../lib/push';
import { byText, cleanup, click, mount, queryText, waitFor } from '../../lib/testing/dom';
import { jsonResponse, routeFetch } from '../../lib/testing/fakes';
import { fakeBrowser, MemoryStorage } from '../../lib/testing/push';
import { PushOffer } from './PushOffer';

vi.mock('../../lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/analytics')>()), sendEvent: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.mocked(sendEvent).mockClear();
});

const KEY = 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM';
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 Version/18.1 Mobile/15E148 Safari/604.1';

function api() {
  const served = routeFetch({
    'GET /api/push/key': () => jsonResponse(200, { enabled: true, public_key: KEY }),
    'POST /api/push/subscription': (call) => jsonResponse(201, { hour: (call.body as { hour: number }).hour, tz: 'UTC' }),
    'DELETE /api/push/subscription': () => jsonResponse(204, null),
  });
  return { served, api: createPushApi(served.fetch) };
}

describe('"Remind me each morning" (stage 8.1 §2.5)', () => {
  it('comes after the third day in a row, at 8:00 by default, and turns on at the chosen hour', async () => {
    const browser = fakeBrowser();
    const { served, api: pushApi } = api();
    const { root } = await mount(<PushOffer lang="en" streak={3} env={browser.env} api={pushApi} storage={new MemoryStorage()} />);
    await waitFor(() => expect(root.querySelector('#push-hour')).not.toBeNull());
    const select = root.querySelector<HTMLSelectElement>('#push-hour')!;
    expect(select.value).toBe('8');
    expect(select.options[8].textContent).toBe('8:00 AM');
    await act(() => {
      select.value = '7';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await click(byText(root, 'Remind me each morning', 'button'));
    await waitFor(() => expect(root.querySelector('.push')!.textContent).toBe('Morning reminder on, at 7:00 AM. Turn off'));
    expect((served.calls.find((c) => c.method === 'POST')!.body as { hour: number }).hour).toBe(7);
    expect(vi.mocked(sendEvent)).toHaveBeenCalledWith({ name: 'push_enabled', tool: 'daily', lang: 'en', params: {} });
  });

  it('before the third day there is no offer', async () => {
    const { api: pushApi } = api();
    const { root } = await mount(<PushOffer lang="en" streak={2} env={fakeBrowser().env} api={pushApi} storage={new MemoryStorage()} />);
    expect(root.textContent).toBe('');
  });

  it('when it is on, it says so at any streak and turns off in the same place', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const { served, api: pushApi } = api();
    const storage = new MemoryStorage();
    storage.setItem('ad_push_hour', '6');
    storage.setItem('ad_push_refreshed', '2000-01-01');
    const { root } = await mount(<PushOffer lang="es" streak={1} env={browser.env} api={pushApi} storage={storage} />);
    await waitFor(() => byText(root, 'Desactivar', 'button'));
    expect(root.textContent).toContain('Aviso de la mañana activado, a las 6:00');
    await click(byText(root, 'Desactivar', 'button'));
    expect(served.calls.map((c) => c.method)).toEqual(['POST', 'DELETE']); // the daily refresh, then off
    expect(browser.unsubscribed).toBe(1);
  });

  it('"Not now" hides it on this device', async () => {
    const storage = new MemoryStorage();
    const { root } = await mount(<PushOffer lang="en" streak={5} env={fakeBrowser().env} api={api().api} storage={storage} now={() => 1000} />);
    await waitFor(() => byText(root, 'Not now', 'button'));
    await click(byText(root, 'Not now', 'button'));
    expect(storage.getItem(DISMISSED_KEY)).toBe('1000');
    expect(queryText(root, 'Remind me each morning')).toBeNull();
  });

  it('on an iPhone outside the Home Screen app: the hint, no button', async () => {
    const { root } = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser({ userAgent: IPHONE }).env} api={api().api} storage={new MemoryStorage()} />);
    expect(root.textContent).toContain('add this site to your Home Screen');
    expect(queryText(root, 'Remind me each morning', 'button')).toBeNull();
  });

  it('a browser where notifications are blocked says where to change it', async () => {
    const { root } = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser({ permission: 'denied' }).env} api={api().api} storage={new MemoryStorage()} />);
    expect(root.textContent).toBe('Notifications for this site are blocked in your browser settings.');
  });
});
```

Create `site/src/components/ui/PushSwitch.test.tsx`:

```tsx
// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest';
import { createPushApi } from '../../lib/push';
import { byText, cleanup, click, mount, waitFor } from '../../lib/testing/dom';
import { jsonResponse, routeFetch } from '../../lib/testing/fakes';
import { fakeBrowser, MemoryStorage } from '../../lib/testing/push';
import { PushSwitch } from './PushSwitch';

afterEach(() => cleanup());

describe('the morning reminder on the account page (stage 8.1 §2.5)', () => {
  it('shows the hour of this browser and turns it off', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const served = routeFetch({ 'DELETE /api/push/subscription': () => jsonResponse(204, null) });
    const storage = new MemoryStorage();
    storage.setItem('ad_push_hour', '9');
    const { root } = await mount(<PushSwitch lang="en" env={browser.env} api={createPushApi(served.fetch)} storage={storage} />);
    await waitFor(() => byText(root, 'Turn off', 'button'));
    expect(root.textContent).toContain('Morning reminder in this browser');
    expect(root.textContent).toContain('On, at 9:00 AM.');
    await click(byText(root, 'Turn off', 'button'));
    await waitFor(() => byText(root, 'Off. You can turn it on under the Card of the Day.'));
    expect(browser.unsubscribed).toBe(1);
  });

  it('says it is off and registers nothing', async () => {
    const browser = fakeBrowser();
    const { root } = await mount(<PushSwitch lang="es" env={browser.env} api={createPushApi(routeFetch({}).fetch)} storage={new MemoryStorage()} />);
    await waitFor(() => byText(root, 'Desactivado. Puedes activarlo debajo de la carta del día.'));
    expect(browser.registered).toEqual([]);
  });

  it('a browser without push shows nothing', async () => {
    const { root } = await mount(<PushSwitch lang="en" env={fakeBrowser({ push: false }).env} api={createPushApi(routeFetch({}).fetch)} storage={null} />);
    expect(root.textContent).toBe('');
  });
});
```

In `site/src/i18n/i18n.test.ts`, replace:

```ts
    expect(keys('en').length).toBe(289);
```

with:

```ts
    expect(keys('en').length).toBe(302);
```

In `site/src/i18n/i18n.test.ts`, replace:

```ts
      'Card of the Day', 'Carta del día', 'Sign in to keep your cards']);
  });
```

with:

```ts
      'Card of the Day', 'Carta del día', 'Sign in to keep your cards']);
    expect([t('en').notifBody, t('es').notifBody, t('en').pushOffer]).toEqual([
      'Your card for today is waiting', 'Tu carta de hoy te espera', 'Remind me each morning']);
  });
```

In `tools/site/test_check_dist.py`, in `site()`, replace:

```python
    write(dist, "robots.txt", ROBOTS_TXT)
    return dist
```

with:

```python
    write(dist, "robots.txt", ROBOTS_TXT)
    write(dist, "sw.js", "self.addEventListener('push', () => {});\n")  # stage 8.1: the reminder's service worker
    return dist
```

Append to the end of `tools/site/test_check_dist.py`:

```python
def test_a_build_without_the_service_worker_fails(tmp_path, capsys):
    """Stage 8.1: /sw.js is a file of the build (src/pages/sw.js.ts); without it the morning reminder cannot work."""
    dist = site(tmp_path)
    (dist / "sw.js").unlink()
    assert check_dist.main(dist) == 1
    assert "missing: " in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests to see them fail**

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/sw.test.ts src/lib/push.test.ts src/components/ui/PushOffer.test.tsx src/components/ui/PushSwitch.test.tsx src/i18n'
```

Expected: FAIL — `Failed to resolve import "./sw"` / `"./push"` / `"./PushOffer"` / `"./PushSwitch"`, i18n `expected 289 to be 302`.

Run:

```bash
api/.venv/bin/pytest -q tools/site/test_check_dist.py
```

Expected: FAIL — `test_a_build_without_the_service_worker_fails`: `assert 0 == 1`.

- [ ] **Step 3: Implement**

Create `site/src/lib/sw.ts`:

```ts
// The service worker /sw.js (stage 8.1 §4), written at build time by src/pages/sw.js.ts so that its two lines come
// from the dictionaries. It only shows the morning reminder and opens the Card of the Day: no fetch handler, nothing
// of the site is cached. The message from the server carries only the language; the address it opens is fixed here,
// so a message can never send the browser anywhere else. A click is counted as push_click (no tool, no params).
import { DICTS } from '../i18n';
import { pagePath } from './routes';
import { LANGS, type Lang } from './types';

export type SwTexts = Record<Lang, { title: string; body: string; url: string }>;

export function swTexts(): SwTexts {
  const entry = (lang: Lang) => ({ title: DICTS[lang].notifTitle, body: DICTS[lang].notifBody, url: pagePath('daily', lang) });
  return Object.fromEntries(LANGS.map((lang) => [lang, entry(lang)])) as SwTexts;
}

export function swSource(texts: SwTexts): string {
  return `// Arcana Diary service worker (stage 8.1): shows the morning reminder and opens the Card of the Day.
// No fetch handler: the site is never cached here.
const TEXTS = ${JSON.stringify(texts)};
const langOf = (value) => (value === 'es' ? 'es' : 'en');
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (error) { data = {}; }
  const lang = langOf(data && data.lang);
  event.waitUntil(self.registration.showNotification(TEXTS[lang].title, {
    body: TEXTS[lang].body, icon: '/icon-192.png', tag: 'daily', data: { lang },
  }));
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const lang = langOf(event.notification.data && event.notification.data.lang);
  const url = TEXTS[lang].url;
  const counted = fetch('/api/events', {
    method: 'POST', headers: { 'content-type': 'application/json' }, keepalive: true, credentials: 'same-origin',
    body: JSON.stringify({ name: 'push_click', tool: null, lang, params: {} }),
  }).catch(() => {});
  const opened = self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const client of list) {
      if (new URL(client.url).pathname === url && 'focus' in client) return client.focus();
    }
    return self.clients.openWindow(url);
  });
  event.waitUntil(Promise.all([counted, opened]));
});
`;
}
```

Create `site/src/pages/sw.js.ts`:

```ts
// /sw.js (stage 8.1 §4): the service worker of the morning reminder, written once at build time (src/lib/sw.ts).
import { swSource, swTexts } from '../lib/sw';

export function GET() {
  return new Response(swSource(swTexts()), { headers: { 'content-type': 'application/javascript; charset=utf-8' } });
}
```

Create `site/src/lib/push.ts`:

```ts
// The morning reminder in the browser (stage 8.1 §2.5): can this browser take it, turn it on (permission, the
// service worker, the subscription, POST /api/push/subscription), turn it off, and refresh it once a day so the server
// knows the time zone and that the browser still wants it. The service worker is registered only when the person
// turns the reminder on. Local storage keeps only the chosen hour and two dates (the privacy page says so).
import { callJson, type ApiResult, type FetchFn } from './api';
import type { StorageLike } from './authState';
import type { Lang } from './types';

export const SW_URL = '/sw.js';
export const HOUR_KEY = 'ad_push_hour';
export const REFRESHED_KEY = 'ad_push_refreshed';
export const DISMISSED_KEY = 'ad_push_dismissed';
export const DEFAULT_HOUR = 8;
export const OFFER_STREAK = 3; // spec §2.5: the offer comes after the third day in a row
export const DISMISS_DAYS = 30;

export interface PushEnv {
  serviceWorker?: ServiceWorkerContainer;
  pushManager: boolean;
  notification?: { permission: NotificationPermission; requestPermission(): Promise<NotificationPermission> };
  userAgent: string;
  maxTouchPoints: number;
  standalone: boolean;
}

export function browserEnv(): PushEnv {
  const nav = typeof navigator === 'undefined' ? undefined : navigator;
  const standalone = typeof matchMedia === 'function' && matchMedia('(display-mode: standalone)').matches;
  return {
    serviceWorker: nav && 'serviceWorker' in nav ? nav.serviceWorker : undefined,
    pushManager: typeof window !== 'undefined' && 'PushManager' in window,
    notification: typeof Notification === 'undefined' ? undefined : Notification,
    userAgent: nav?.userAgent ?? '',
    maxTouchPoints: nav?.maxTouchPoints ?? 0,
    standalone: standalone || (nav as { standalone?: boolean } | undefined)?.standalone === true,
  };
}

/** 'yes' — the offer; 'ios-home' — an iPhone or iPad outside the Home Screen app: the hint how to add it there
 * (Safari gives reminders only to sites opened from the Home Screen); 'no' — nothing. */
export type Support = 'yes' | 'ios-home' | 'no';

export function pushSupport(env: PushEnv): Support {
  const ios = /iPhone|iPad|iPod/.test(env.userAgent) || (/Macintosh/.test(env.userAgent) && env.maxTouchPoints > 1);
  if (ios && !env.standalone) return 'ios-home';
  return env.serviceWorker && env.pushManager && env.notification ? 'yes' : 'no';
}

/** "8:00 AM" / "8:00 a.m." — an hour of the day as people read it. */
export function hourLabel(hour: number, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-US' : 'es-MX', { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })
    .format(new Date(Date.UTC(2026, 0, 1, hour)));
}

export function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (base64url.length % 4)) % 4);
  const text = atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(text.length));
  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i);
  return bytes;
}

export function storedHour(storage: StorageLike | null): number {
  const text = storage?.getItem(HOUR_KEY) ?? null;
  const hour = text === null || text === '' ? NaN : Number(text);
  return Number.isInteger(hour) && hour >= 0 && hour <= 23 ? hour : DEFAULT_HOUR;
}

export function offerDismissed(now: number, storage: StorageLike | null): boolean {
  const at = Number(storage?.getItem(DISMISSED_KEY));
  return Number.isFinite(at) && at > 0 && now - at < DISMISS_DAYS * 86_400_000;
}

export interface SubscriptionBody {
  endpoint: string;
  keys: { p256dh: string; auth: string };
  hour: number;
  tz?: string;
  lang: Lang;
}

export interface PushApi {
  key(): Promise<ApiResult<{ enabled: boolean; public_key: string }>>;
  subscribe(body: SubscriptionBody): Promise<ApiResult<{ hour: number; tz: string }>>;
  unsubscribe(endpoint: string): Promise<ApiResult<null>>;
}

export function createPushApi(fetchFn: FetchFn): PushApi {
  const json = (method: string, body: unknown): RequestInit => ({
    method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
  });
  return {
    key: () => callJson(fetchFn, '/api/push/key'),
    subscribe: (body) => callJson(fetchFn, '/api/push/subscription', json('POST', body)),
    unsubscribe: (endpoint) => callJson(fetchFn, '/api/push/subscription', json('DELETE', { endpoint })),
  };
}

function bodyOf(subscription: PushSubscription, hour: number, tz: string | undefined, lang: Lang): SubscriptionBody {
  const keys = subscription.toJSON().keys ?? {};
  return { endpoint: subscription.endpoint, keys: { p256dh: keys.p256dh ?? '', auth: keys.auth ?? '' }, hour, tz, lang };
}

/** The browser's subscription, without registering anything. */
export async function currentSubscription(env: PushEnv): Promise<PushSubscription | null> {
  try {
    const registration = await env.serviceWorker?.getRegistration('/');
    return (await registration?.pushManager.getSubscription()) ?? null;
  } catch {
    return null;
  }
}

export type TurnOn = 'on' | 'denied' | 'off' | 'failed';

export interface PushDeps {
  env: PushEnv;
  api: PushApi;
  storage: StorageLike | null;
  lang: Lang;
  tz: string | undefined;
  today: string;
}

export async function turnOn(deps: PushDeps, hour: number): Promise<TurnOn> {
  const { env, api, storage, lang, tz, today } = deps;
  if (!env.serviceWorker || !env.notification) return 'off';
  const key = await api.key();
  if (!key.ok || !key.data.enabled || !key.data.public_key) return 'off';
  try {
    const permission = await env.notification.requestPermission();
    if (permission === 'denied') return 'denied';
    if (permission !== 'granted') return 'failed';
    const registration = await env.serviceWorker.register(SW_URL, { scope: '/' });
    const subscription = (await registration.pushManager.getSubscription())
      ?? (await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(key.data.public_key) }));
    const saved = await api.subscribe(bodyOf(subscription, hour, tz, lang));
    if (!saved.ok) return 'failed';
    storage?.setItem(HOUR_KEY, String(hour));
    storage?.setItem(REFRESHED_KEY, today);
    return 'on';
  } catch {
    return 'failed';
  }
}

export async function turnOff(deps: Pick<PushDeps, 'env' | 'api' | 'storage'>): Promise<boolean> {
  const subscription = await currentSubscription(deps.env);
  if (subscription) {
    await deps.api.unsubscribe(subscription.endpoint);
    try {
      await subscription.unsubscribe();
    } catch {
      // the server row is gone already: nothing more is sent
    }
  }
  deps.storage?.removeItem(HOUR_KEY);
  deps.storage?.removeItem(REFRESHED_KEY);
  return true;
}

/** Once a day while the reminder is on: the same subscription again, with today's time zone. */
export async function refresh(deps: PushDeps, subscription: PushSubscription): Promise<void> {
  if (deps.storage?.getItem(REFRESHED_KEY) === deps.today) return;
  const saved = await deps.api.subscribe(bodyOf(subscription, storedHour(deps.storage), deps.tz, deps.lang));
  if (saved.ok) deps.storage?.setItem(REFRESHED_KEY, deps.today);
}
```

Create `site/src/components/ui/PushOffer.tsx`:

```tsx
// "Remind me each morning" under the Card of the Day (stage 8.1 §2.5): shown quietly after the third day in a row,
// with the hour (8:00 by default, local time); on an iPhone or iPad outside the Home Screen app, the hint how to add
// the site there instead. Once on, the same place says so and turns it off. "Not now" hides the offer on this device
// for DISMISS_DAYS. Nothing is registered or asked before the person presses the button.
import { useEffect, useMemo, useState } from 'preact/hooks';
import { fill, t } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import { browserStorage, type StorageLike } from '../../lib/authState';
import { localIsoDay } from '../../lib/daily';
import {
  browserEnv, createPushApi, currentSubscription, DEFAULT_HOUR, DISMISSED_KEY, hourLabel, OFFER_STREAK, offerDismissed,
  pushSupport, refresh, storedHour, turnOff, turnOn, type PushApi, type PushEnv,
} from '../../lib/push';
import { siteFetch } from '../../lib/siteApi';
import { deviceTimeZone } from '../../lib/timeZone';
import type { Lang } from '../../lib/types';

interface Props {
  lang: Lang;
  streak: number;
  env?: PushEnv;
  api?: PushApi;
  storage?: StorageLike | null;
  now?: () => number;
}

type State = 'checking' | 'offer' | 'busy' | 'on' | 'denied' | 'failed' | 'hidden';

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

export function PushOffer({ lang, streak, env: givenEnv, api: givenApi, storage: givenStorage, now = Date.now }: Props) {
  const d = t(lang);
  const env = useMemo(() => givenEnv ?? browserEnv(), []);
  const api = useMemo(() => givenApi ?? createPushApi(siteFetch()), []);
  const storage = givenStorage === undefined ? browserStorage() : givenStorage;
  const support = pushSupport(env);
  const [state, setState] = useState<State>('checking');
  const [hour, setHour] = useState(DEFAULT_HOUR);
  const deps = () => ({ env, api, storage, lang, tz: deviceTimeZone(), today: localIsoDay(new Date(now())) });

  useEffect(() => {
    if (support !== 'yes') return setState('offer');
    void currentSubscription(env).then((subscription) => {
      if (subscription && env.notification?.permission === 'granted') {
        setHour(storedHour(storage));
        setState('on');
        void refresh(deps(), subscription);
      } else setState(env.notification?.permission === 'denied' ? 'denied' : 'offer');
    });
  }, []);

  if (support === 'no' || state === 'checking' || state === 'hidden') return null;
  if (state === 'on') {
    return (
      <p class="small push">
        {fill(d.pushOn, { hour: hourLabel(hour, lang) })}{' '}
        <button type="button" class="btn btn--text" onClick={() => void turnOff(deps()).then(() => setState('offer'))}>
          {d.pushOff}
        </button>
      </p>
    );
  }
  if (streak < OFFER_STREAK || offerDismissed(now(), storage)) return null;

  const dismiss = () => {
    storage?.setItem(DISMISSED_KEY, String(now()));
    setState('hidden');
  };
  const notNow = <button type="button" class="btn btn--text" onClick={dismiss}>{d.pushNotNow}</button>;

  if (support === 'ios-home') return <div class="push"><p class="small">{d.pushIosHint}</p>{notNow}</div>;
  if (state === 'denied') return <p class="small push">{d.pushDenied}</p>;

  const enable = async () => {
    if (state === 'busy') return;
    setState('busy');
    const result = await turnOn(deps(), hour);
    if (result === 'on') sendEvent(analyticsEvent('push_enabled', 'daily', lang));
    setState(result === 'on' ? 'on' : result === 'denied' ? 'denied' : result === 'off' ? 'hidden' : 'failed');
  };

  return (
    <div class="push">
      <label for="push-hour">{d.pushHourLabel}</label>
      <select id="push-hour" class="input push__hour" value={String(hour)}
        onChange={(e) => setHour(Number((e.target as HTMLSelectElement).value))}>
        {HOURS.map((h) => <option key={h} value={String(h)}>{hourLabel(h, lang)}</option>)}
      </select>
      <button type="button" class="btn btn--outline" aria-disabled={state === 'busy'} onClick={() => void enable()}>
        {d.pushOffer}
      </button>
      {notNow}
      {state === 'failed' ? <p role="alert" class="small">{d.pushFailed}</p> : null}
    </div>
  );
}
```

Create `site/src/components/ui/PushSwitch.tsx`:

```tsx
// The account page's line about the morning reminder in this browser (stage 8.1 §2.5: "turned off there and in the
// account"). It reads the browser's own subscription and never registers anything; turning on stays under the card.
import { useEffect, useMemo, useState } from 'preact/hooks';
import { fill, t } from '../../i18n';
import { browserStorage, type StorageLike } from '../../lib/authState';
import { browserEnv, createPushApi, currentSubscription, hourLabel, pushSupport, storedHour, turnOff, type PushApi,
  type PushEnv } from '../../lib/push';
import { siteFetch } from '../../lib/siteApi';
import type { Lang } from '../../lib/types';

interface Props {
  lang: Lang;
  env?: PushEnv;
  api?: PushApi;
  storage?: StorageLike | null;
}

export function PushSwitch({ lang, env: givenEnv, api: givenApi, storage: givenStorage }: Props) {
  const d = t(lang);
  const env = useMemo(() => givenEnv ?? browserEnv(), []);
  const api = useMemo(() => givenApi ?? createPushApi(siteFetch()), []);
  const storage = givenStorage === undefined ? browserStorage() : givenStorage;
  const [on, setOn] = useState<boolean | null>(null);

  useEffect(() => {
    if (pushSupport(env) !== 'yes') return;
    void currentSubscription(env).then((subscription) => setOn(subscription !== null));
  }, []);

  if (on === null) return null;
  return (
    <section class="account__push" aria-labelledby="account-push-title">
      <h2 id="account-push-title" class="h3">{d.accountPushTitle}</h2>
      {on ? (
        <p>
          {fill(d.accountPushOn, { hour: hourLabel(storedHour(storage), lang) })}{' '}
          <button type="button" class="btn btn--text" onClick={() => void turnOff({ env, api, storage }).then(() => setOn(false))}>
            {d.pushOff}
          </button>
        </p>
      ) : <p class="small">{d.accountPushNone}</p>}
    </section>
  );
}
```

In `site/src/islands/DailyIsland.tsx`, replace:

```tsx
import { HelpLine } from '../components/ui/HelpLine';
```

with:

```tsx
import { HelpLine } from '../components/ui/HelpLine';
import { PushOffer } from '../components/ui/PushOffer';
```

In `site/src/islands/DailyIsland.tsx`, replace:

```tsx
        <button type="button" class="btn btn--outline" onClick={remind}>{d.remindTomorrow}</button>
        <p class="small" role="status">{reminded ? d.remindDone : ''}</p>
```

with:

```tsx
        <button type="button" class="btn btn--outline" onClick={remind}>{d.remindTomorrow}</button>
        <p class="small" role="status">{reminded ? d.remindDone : ''}</p>
        {shown.fromBase ? null : <PushOffer lang={lang} streak={shown.streak} />}
```

In `site/src/islands/AccountIsland.tsx`, replace:

```tsx
import { HelpLine } from '../components/ui/HelpLine';
```

with:

```tsx
import { HelpLine } from '../components/ui/HelpLine';
import { PushSwitch } from '../components/ui/PushSwitch';
```

In `site/src/islands/AccountIsland.tsx`, replace:

```tsx
        {problem('consent')}
      </div>
```

with:

```tsx
        {problem('consent')}
      </div>
      <PushSwitch lang={lang} />
```

In `site/src/i18n/en.ts`, replace:

```ts
  calendarDayCard: 'Card of {date}',
};
```

with:

```ts
  calendarDayCard: 'Card of {date}',
  // stage 8.1: the morning reminder in the browser (spec 2026-11-27 §2.5); notifBody is the spec's exact text
  pushOffer: 'Remind me each morning',
  pushHourLabel: 'At',
  pushNotNow: 'Not now',
  pushOn: 'Morning reminder on, at {hour}.',
  pushOff: 'Turn off',
  pushDenied: 'Notifications for this site are blocked in your browser settings.',
  pushFailed: "We couldn't turn on the reminder. Please try again.",
  pushIosHint: 'To get a morning reminder on iPhone, add this site to your Home Screen: tap Share, then “Add to Home Screen”, and open it from there.',
  notifTitle: 'Arcana Diary',
  notifBody: 'Your card for today is waiting',
  accountPushTitle: 'Morning reminder in this browser',
  accountPushOn: 'On, at {hour}.',
  accountPushNone: 'Off. You can turn it on under the Card of the Day.',
};
```

In `site/src/i18n/es.ts`, replace:

```ts
  calendarDayCard: 'Carta del {date}',
};
```

with:

```ts
  calendarDayCard: 'Carta del {date}',
  // stage 8.1: the morning reminder in the browser (spec 2026-11-27 §2.5); notifBody is the spec's exact text
  pushOffer: 'Avísame cada mañana',
  pushHourLabel: 'A las',
  pushNotNow: 'Ahora no',
  pushOn: 'Aviso de la mañana activado, a las {hour}.',
  pushOff: 'Desactivar',
  pushDenied: 'Las notificaciones de este sitio están bloqueadas en la configuración de tu navegador.',
  pushFailed: 'No se pudo activar el aviso. Intenta de nuevo.',
  pushIosHint: 'Para recibir el aviso en iPhone, agrega este sitio a tu pantalla de inicio: toca Compartir, luego «Agregar a inicio», y ábrelo desde ahí.',
  notifTitle: 'Arcana Diary',
  notifBody: 'Tu carta de hoy te espera',
  accountPushTitle: 'Aviso de la mañana en este navegador',
  accountPushOn: 'Activado, a las {hour}.',
  accountPushNone: 'Desactivado. Puedes activarlo debajo de la carta del día.',
};
```

Append to the end of `site/src/styles/global.css` (tokens only):

```css
.push { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: var(--space-2); margin: 0; }
.push__hour { width: auto; min-height: 44px; }
```

In `site/public/site.webmanifest`, replace:

```json
  "display": "browser",
```

with:

```json
  "display": "standalone",
```

In `tools/site/check_dist.py`, replace:

```python
DATA_FILES = ("data/daily-en.json", "data/daily-es.json", "sitemap.xml", "robots.txt")
```

with:

```python
DATA_FILES = ("data/daily-en.json", "data/daily-es.json", "sitemap.xml", "robots.txt", "sw.js")  # sw.js: stage 8.1
```

In `deploy/Caddyfile`, replace:

```caddy
	header @private Cache-Control "no-store"
```

with:

```caddy
	header @private Cache-Control "no-store"
	# stage 8.1: the browser checks the reminder's service worker for a new version on every visit; never a stale
	# copy from Cloudflare or the browser cache
	header /sw.js Cache-Control "no-cache"
```

In `deploy/test-site-routes.sh`, replace:

```bash
expect "/ — без Cache-Control: no-store" "$(cache /)" ""
```

with:

```bash
expect "/ — без Cache-Control: no-store" "$(cache /)" ""
# stage 8.1: the service worker of the morning reminder is never served stale
expect "/sw.js" "$(status /sw.js)" 200
expect "/sw.js — Cache-Control" "$(cache /sw.js)" "no-cache"
```

The service worker is registered only by `turnOn` (the button): a visitor who never asks for reminders gets no service worker. `sw.ts` uses no `new Function`/`eval` (guards.test.ts); only its test does.

- [ ] **Step 4: Run the tests**

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/sw.test.ts src/lib/push.test.ts src/components/ui src/islands src/i18n'
```

Expected: all pass.

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx astro check'
```

Expected: `0 errors`.

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npm run build'
```

Expected: no failures, `(533)` tests in total, `[build] Complete!`; `head -2 site/dist/sw.js` prints the service worker's comment line.

Run:

```bash
api/.venv/bin/pytest -q tools/site
python3 tools/site/check_dist.py --launched
deploy/test-site-routes.sh
```

Expected: `67 passed`; `OK: 187 pages`; in the route test `PASS /sw.js (200)` and `PASS /sw.js — Cache-Control (no-cache)`. Three lines about hidden service pages (`/about — скрыта`, `/es/privacidad — скрыта`, `sitemap.xml без скрытых`) fail on `main` too since the launch opened those pages — not this stage; report them, do not fix them here.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/sw.ts site/src/lib/sw.test.ts site/src/pages/sw.js.ts site/src/lib/push.ts site/src/lib/push.test.ts site/src/lib/testing/push.ts site/src/components/ui/PushOffer.tsx site/src/components/ui/PushOffer.test.tsx site/src/components/ui/PushSwitch.tsx site/src/components/ui/PushSwitch.test.tsx site/src/islands/DailyIsland.tsx site/src/islands/AccountIsland.tsx site/src/i18n site/src/styles/global.css site/public/site.webmanifest tools/site/check_dist.py tools/site/test_check_dist.py deploy/Caddyfile deploy/test-site-routes.sh
git commit -m "feat(site): morning reminder — service worker, standalone manifest, the offer after 3 days, iPhone Home Screen hint, account switch (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 12: Texts: the Card of the Day pages and the privacy policy; all checks

**Files:**
- Modify: `content/pages/en/daily.json`, `content/pages/es/carta-del-dia.json`, `content/pages/en/privacy.json`,
  `content/pages/es/privacidad.json` (edited in place, never re-serialised)
- Generated: `site/src/data/pages/{en,es}/*.json` by `python3 tools/site/sync_site_data.py`
- Not modified: the terms (`terms.json`, `terminos.json`) — spec §4.

**Interfaces:**
- Consumes: what Tasks 1–11 store and show — the privacy texts must say exactly that: guest cards of the day 60 days;
  account cards, marks (yes/partly/no) and lines (≤ 280) until the account is deleted; reminder subscriptions — endpoint,
  two keys, hour, time zone, language, day of the last reminder, failures in a row, account or device number; deleted
  after 3 failed deliveries in a row, a guest's 90 days after the last Card of the Day visit; the push services of
  Google, Mozilla, Apple, Microsoft; the service worker and the three local-storage entries; the four events without
  the mark or the line; the export and the deletion.
- Produces: the daily pages gain the block `calendar` / `calendario` and the FAQ «Is my daily card saved?» /
  «¿Se guarda mi carta del día?» (at the end: `faq:5` EN, `faq:6` ES — no `intents` index moves); the privacy pages gain
  the block `reminders` / `avisos`. Word counts (checked with the checker on these exact texts): EN daily 698 (plan
  500–700), ES daily 1029 (800–1000, within the 10 % margin), EN privacy 3119 and ES privacy 3273 (1200–3000, within
  the margin — the ES page is 27 words under the 3300 ceiling).

- [ ] **Step 1: Edit the texts in place**

Use the Edit tool (exact string replacement) for each block below, in this order; never load and re-dump the JSON.

**EN Card of the Day** (`content/pages/en/daily.json`):

In `content/pages/en/daily.json`, replace:

```json
Here your card is drawn once for your local day in this browser, so it stays the same if you come back at lunch.
```

with:

```json
Here your card is drawn once for your local day, in this browser or, once you sign in, in your account, so it stays the same if you come back at lunch.
```

In `content/pages/en/daily.json`, replace:

```json
    {
      "id": "repeat",
```

with:

```json
    {
      "id": "calendar",
      "heading": "Your month in cards",
      "paragraphs": [
        "Each card you turn goes into a calendar in your diary. Tap a day to see its card and text again, along with your streak, your best run and the month's most frequent card. Missing a day just starts a new count. In the evening you can mark whether the card showed up in your day and add one line."
      ]
    },
    {
      "id": "repeat",
```

In `content/pages/en/daily.json`, replace:

```json
use the love spread."
    }
  ],
```

with:

```json
use the love spread."
    },
    {
      "q": "Is my daily card saved?",
      "a": "Yes. Signed in, each day's card, mark and line stay in your account, the same on every device. Without an account, this browser keeps your last 7 days."
    }
  ],
```

**ES carta del día** (`content/pages/es/carta-del-dia.json`):

In `content/pages/es/carta-del-dia.json`, replace:

```json
Se elige para este navegador y para tu día:
```

with:

```json
Se elige para tu día, en este navegador o en tu cuenta si inicias sesión:
```

In `content/pages/es/carta-del-dia.json`, replace:

```json
Puedes anotarlo donde quieras. La carta del día no se guarda en el diario, porque no es una lectura, pero si te late volver mañana,
```

with:

```json
Con sesión iniciada, debajo de la carta te preguntamos si apareció en tu día y puedes dejar una línea. Si te late volver mañana,
```

In `content/pages/es/carta-del-dia.json`, replace:

```json
Un detalle práctico: tu carta está ligada al navegador. Si abres el sitio en otro celular o en otra computadora, puede salir una distinta. Lo más útil es elegir un solo lugar para verla cada mañana y quedarte con lo que te diga ahí.
```

with:

```json
Un detalle práctico: sin cuenta, tu carta está ligada al navegador, y en otro celular o en otra computadora puede salir una distinta. Con sesión iniciada es la misma en todos tus dispositivos.
```

In `content/pages/es/carta-del-dia.json`, replace:

```json
    {
      "id": "se-repite",
```

with:

```json
    {
      "id": "calendario",
      "heading": "¿Dónde quedan tus cartas de cada día?",
      "paragraphs": [
        "En tu diario hay un calendario del mes con una cartita por cada día que volteaste. Toca un día para ver otra vez su carta y su texto. Arriba ves cuántos días seguidos llevas, tu mejor racha y la carta que más se repitió en el mes. Si un día no la abres, la cuenta empieza de nuevo y tu mejor racha se queda.",
        "En la noche, debajo de la carta, puedes contestar «¿Apareció la carta de hoy en tu día?» con sí, en parte o no, y agregar una línea si quieres. Sin cuenta, este navegador guarda tus últimos 7 días; al iniciar sesión, esas cartas pasan a tu cuenta y ahí se quedan todas."
      ]
    },
    {
      "id": "se-repite",
```

In `content/pages/es/carta-del-dia.json`, replace:

```json
sí cuenta para tu límite diario."
    }
  ],
```

with:

```json
sí cuenta para tu límite diario."
    },
    {
      "q": "¿Se guarda mi carta del día?",
      "a": "Sí. Con sesión iniciada, cada carta del día queda en tu cuenta con tu respuesta de la noche y tu línea, y ves la misma carta en el celular y en la computadora. Sin cuenta, este navegador muestra tus últimos 7 días."
    }
  ],
```

**EN privacy** (`content/pages/en/privacy.json`):

In `content/pages/en/privacy.json`, replace:

```json
For the Card of the Day we store your device's random number with the card it drew and the date, for up to 8 days, so that your card stays the same all day.
```

with:

```json
For the Card of the Day we store your device's random number with the card it drew and the date for 60 days, so that your card stays the same all day, your streak can be counted and your last 7 days show in the calendar. When you sign in, these cards move into your account.
```

In `content/pages/en/privacy.json`, replace:

```json
we keep only a scrambled form (hash) of that link's code.
```

with:

```json
we keep only a scrambled form (hash) of that link's code. Your calendar keeps each day's card, your answer to “Did today's card show up in your day?” (yes, partly or no) and an optional line of up to 280 characters, with their date; they never go to the AI reader either.
```

In `content/pages/en/privacy.json`, replace:

```json
    {
      "id": "counter-logs",
```

with:

```json
    {
      "id": "reminders",
      "heading": "Morning reminders in your browser",
      "paragraphs": [
        "Under the Card of the Day you can ask for a reminder each morning at an hour you choose, with your browser's permission. The browser gives us an address at its push service (run by Google, Mozilla, Apple or Microsoft) and two keys for encrypting messages. We store that address, the keys, the hour, your time zone name, the language, the day of the last reminder and the failed deliveries in a row, with your account number or, without an account, your device's random number.",
        "We send at most one reminder a day, and none once you have opened your card. It is encrypted and says only “Your card for today is waiting”, never which card, because it may show on a locked screen. You can turn it off under the card, on your account page or in your browser's settings."
      ]
    },
    {
      "id": "counter-logs",
```

In `content/pages/en/privacy.json`, replace:

```json
“sign-in finished” and “reminder pressed”,
```

with:

```json
“sign-in finished”, “reminder pressed”, “card of the day marked”, “calendar opened”, “morning reminder turned on” and “morning reminder opened”,
```

In `content/pages/en/privacy.json`, replace:

```json
the sign-in method, and your answer to “Did it come true?”.
```

with:

```json
the sign-in method, your answer to “Did it come true?”, whether a calendar was opened signed in and where a card of the day was marked, never that answer or your line.
```

In `content/pages/en/privacy.json`, replace:

```json
notes or “Did it come true?” marks.
```

with:

```json
notes, “Did it come true?” marks or Card of the Day answers and lines.
```

In `content/pages/en/privacy.json`, replace:

```json
{email_provider} sends sign-in links and, if you agree to them, reminder e-mails.
```

with:

```json
{email_provider} sends sign-in links and, if you agree to them, reminder e-mails. Morning reminders are delivered by your browser's push service.
```

In `content/pages/en/privacy.json`, replace:

```json
Anthropic, Cloudflare and Google are based in the United States
```

with:

```json
Anthropic, Cloudflare and Google, like the push services of Mozilla, Apple and Microsoft, are based in the United States
```

In `content/pages/en/privacy.json`, replace:

```json
nothing is sent to us except the count that the button was pressed.
```

with:

```json
nothing is sent to us except the count that the button was pressed. Morning reminders install a small script (a service worker) that only shows the reminder and opens the page, and local storage keeps the chosen hour and the dates of the last refresh and of “Not now”.
```

In `content/pages/en/privacy.json`, replace:

```json
Card of the Day draws: up to 8 days.
```

with:

```json
Card of the Day without an account: 60 days; in your account, with its answers and lines, until you delete the account. Morning reminders: until you turn them off; deleted after three failed deliveries in a row and, without an account, 90 days after your last visit to the Card of the Day.
```

In `content/pages/en/privacy.json`, replace:

```json
every reading with its question, cards, answer, follow-ups, mark and note, and your Plus waitlist entry.
```

with:

```json
every reading with its question, cards, answer, follow-ups, mark and note, your Card of the Day calendar with its answers and lines, your morning reminder settings, and your Plus waitlist entry.
```

In `content/pages/en/privacy.json`, replace:

```json
your readings, follow-ups, saving links, profile, Plus waitlist entry and sign-in record are erased.
```

with:

```json
your readings, follow-ups, saving links, Card of the Day calendar with its answers and lines, morning reminder subscriptions, profile, Plus waitlist entry and sign-in record are erased.
```

In `content/pages/en/privacy.json`, replace:

```json
We send reminder e-mails, and one e-mail when Plus opens, only with your consent,
```

with:

```json
We send reminder e-mails, morning reminders in your browser and one e-mail when Plus opens only with your consent,
```

**ES privacidad** (`content/pages/es/privacidad.json`):

In `content/pages/es/privacidad.json`, replace:

```json
Para la carta del día guardamos el número al azar de tu dispositivo, la carta que salió y la fecha hasta por 8 días, para que tu carta no cambie en todo el día.
```

with:

```json
Para la carta del día guardamos el número al azar de tu dispositivo, la carta que salió y la fecha durante 60 días, para que tu carta no cambie en todo el día, para contar tu racha y para mostrarte tus últimos 7 días en el calendario. Si inicias sesión, esas cartas pasan a tu cuenta.
```

In `content/pages/es/privacidad.json`, replace:

```json
de ese enlace solo guardamos un hash.
```

with:

```json
de ese enlace solo guardamos un hash. Tu calendario guarda la carta de cada día, tu respuesta a “¿Apareció la carta de hoy en tu día?” (sí, en parte o no) y una línea opcional de hasta 280 caracteres, con su fecha; tampoco van al lector de IA.
```

In `content/pages/es/privacidad.json`, replace:

```json
    {
      "id": "contador",
```

with:

```json
    {
      "id": "avisos",
      "heading": "Avisos de la mañana en tu navegador",
      "paragraphs": [
        "Debajo de la carta del día puedes pedir un aviso cada mañana a la hora que elijas, con el permiso de tu navegador. El navegador nos da una dirección de su servicio de notificaciones (de Google, Mozilla, Apple o Microsoft) y dos claves para cifrar los mensajes. Guardamos esa dirección, las claves, la hora, tu zona horaria, el idioma, el día del último aviso y las entregas fallidas seguidas, junto con tu número de cuenta o, sin cuenta, el número al azar de tu dispositivo.",
        "Mandamos como máximo un aviso al día, y ninguno si ya abriste tu carta. Va cifrado y solo dice «Tu carta de hoy te espera», nunca qué carta salió, porque puede verse con la pantalla bloqueada. Puedes desactivarlo debajo de la carta, en tu cuenta o en la configuración del navegador."
      ]
    },
    {
      "id": "contador",
```

In `content/pages/es/privacidad.json`, replace:

```json
“se completó el acceso” y “se pidió un recordatorio”,
```

with:

```json
“se completó el acceso”, “se pidió un recordatorio”, “se marcó la carta del día”, “se abrió el calendario”, “se activó el aviso de la mañana” y “se abrió el aviso de la mañana”,
```

In `content/pages/es/privacidad.json`, replace:

```json
el método de acceso y tu respuesta a “¿Se cumplió?”.
```

with:

```json
el método de acceso, tu respuesta a “¿Se cumplió?”, si el calendario se abrió con sesión iniciada y dónde se marcó la carta del día, nunca esa respuesta ni tu línea.
```

In `content/pages/es/privacidad.json`, replace:

```json
tus notas ni tus marcas de “¿Se cumplió?”.
```

with:

```json
tus notas, tus marcas de “¿Se cumplió?” ni tus respuestas y líneas de la carta del día.
```

In `content/pages/es/privacidad.json`, replace:

```json
{email_provider} envía los enlaces de acceso y, si los aceptas, los correos de recordatorio.
```

with:

```json
{email_provider} envía los enlaces de acceso y, si los aceptas, los correos de recordatorio. El aviso de la mañana lo entrega el servicio de notificaciones de tu navegador.
```

In `content/pages/es/privacidad.json`, replace:

```json
Anthropic, Cloudflare y Google tienen su sede en Estados Unidos
```

with:

```json
Anthropic, Cloudflare y Google, igual que los servicios de notificaciones de Mozilla, Apple y Microsoft, tienen su sede en Estados Unidos
```

In `content/pages/es/privacidad.json`, replace:

```json
a nosotros solo nos llega el conteo de que se tocó el botón.
```

with:

```json
a nosotros solo nos llega el conteo de que se tocó el botón. El aviso de la mañana instala un pequeño script (service worker) que solo muestra el aviso y abre la página, y el almacenamiento local guarda la hora elegida y las fechas de la última renovación y de «Ahora no».
```

In `content/pages/es/privacidad.json`, replace:

```json
Lecturas de la carta del día: hasta 8 días.
```

with:

```json
Carta del día sin cuenta: 60 días; en tu cuenta, con sus respuestas y líneas, hasta que elimines la cuenta. Avisos de la mañana: hasta que los desactives; se borran tras tres entregas fallidas seguidas y, sin cuenta, 90 días después de tu última visita a la carta del día.
```

In `content/pages/es/privacidad.json`, replace:

```json
cada lectura con su pregunta, cartas, respuesta, preguntas de seguimiento, marca y nota, y tu registro en la lista de espera de Plus.
```

with:

```json
cada lectura con su pregunta, cartas, respuesta, preguntas de seguimiento, marca y nota, tu calendario de la carta del día con sus respuestas y líneas, la configuración de tus avisos de la mañana y tu registro en la lista de espera de Plus.
```

In `content/pages/es/privacidad.json`, replace:

```json
se borran tus lecturas, preguntas de seguimiento, enlaces para guardar, perfil, registro en la lista de Plus y tu usuario de acceso.
```

with:

```json
se borran tus lecturas, preguntas de seguimiento, enlaces para guardar, calendario de la carta del día con sus respuestas y líneas, suscripciones al aviso de la mañana, perfil, registro en la lista de Plus y tu usuario de acceso.
```

In `content/pages/es/privacidad.json`, replace:

```json
los correos de recordatorio y un solo correo de aviso cuando abra Plus.
```

with:

```json
los correos de recordatorio, el aviso de la mañana en tu navegador y un solo correo de aviso cuando abra Plus.
```

- [ ] **Step 2: Check the texts and regenerate the site data**

Run:

```bash
python3 -c "import json,sys; [json.load(open(f)) for f in sys.argv[1:]]" content/pages/en/daily.json content/pages/es/carta-del-dia.json content/pages/en/privacy.json content/pages/es/privacidad.json && echo json-ok
python3 -I tools/cards/check_tool_pages.py content/pages/en/daily.json content/pages/es/carta-del-dia.json content/pages/en/privacy.json content/pages/es/privacidad.json
```

Expected: `json-ok`; four `OK` lines — `слов 698 (план 500–700)`, `слов 1029 (план 800–1000)` with the «в допуске» warning, `слов 3119`, `слов 3273` with the same warning; overlaps ≤ 2.6 %.

Run:

```bash
python3 tools/site/sync_site_data.py
git status --short site/src/data
```

Expected: exactly the four page files `site/src/data/pages/en/daily.json`, `es/carta-del-dia.json`, `en/privacy.json`, `es/privacidad.json` changed.

- [ ] **Step 3: Run every check of the project**

Run:

```bash
(cd api && .venv/bin/pytest -q)
```

Expected: `1750 passed`.

Run:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npm run build'
```

Expected: no failures, `(533)` tests, `[build] Complete!`.

Run:

```bash
python3 tools/site/sync_site_data.py --check
python3 tools/site/check_dist.py --launched
python3 tools/site/check_links.py
python3 -I tools/cards/check_tool_pages.py
```

Expected: `--check` exits 0; `OK: 187 pages`; check_links exits 0; check_tool_pages: every page `OK` (warnings «в допуске» only).

Run:

```bash
api/.venv/bin/pytest -q tools/site
deploy/test-gen-vapid.sh
```

Expected: `67 passed`; `OK: gen-vapid.sh`.

Run:

```bash
grep -ln "app.reader\|anthropic" api/app/journal.py api/app/push.py api/app/webpush.py api/app/routes/push.py | wc -l
```

Expected: `0` — none of the new modules imports the reader or a model client (no paid call in this stage).

- [ ] **Step 4: Commit**

```bash
git add content/pages/en/daily.json content/pages/es/carta-del-dia.json content/pages/en/privacy.json content/pages/es/privacidad.json site/src/data/pages
git commit -m "content: Card of the Day calendar block and FAQ, privacy — cards, marks, notes, browser reminders and their retention (stage 8.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Ask for the reviews (no merge, no deploy)**

1. Per-task reviews ran on Sonnet after each task (superpowers:subagent-driven-development).
2. Final whole-branch review on **Fable**: `git diff main...stage8-daily-habit`, with the spec, this plan and the focus list — private notes storage (no note or mark in events, logs, model input or the export beyond the person's own file; text-only rendering), deletion and export completeness, the push sender (SSRF allowlist, at most one a day, no card on the lock screen, failure handling, no key in logs or output), the migration's rollback safety, and the privacy texts against the code.
3. Report the branch, the review findings and the open questions to the owner. **Stop.** Merge, push, `deploy/gen-vapid.sh` and the deploy happen only on the owner's word (see «Operator steps»).
---

## Operator steps (outside the tasks, only on the owner's word)

In this order, after the owner has read the Fable review and the texts table below and said yes:

1. **Merge** `stage8-daily-habit` into `main` (no push before the owner says so).
2. **Effective date of the privacy policy = the day of the deploy** (owner decision 55: a new effective date only, no
   notice line on the site). On that day, in `content/operator.json`, set `effective_date` for both `en` and `es` to that
   date, written as the existing values are (edit the strings in place, never re-serialise the file); then
   `python3 tools/site/sync_site_data.py && python3 tools/site/sync_site_data.py --check` and
   `python3 -I tools/cards/check_tool_pages.py content/pages/en/privacy.json content/pages/es/privacidad.json`, and commit
   `content/operator.json` with the regenerated `site/src/data` files (trailer as in every commit). This is not a task
   step: the date is the deploy's, not the day the code was written.
3. **VAPID keys:** `deploy/gen-vapid.sh` — prints only `ключи VAPID дописаны в .env`; exit 3 means the keys are already
   there (nothing changed). Never print `deploy/.env` to check: `grep -c '^VAPID_' deploy/.env` prints only a count (2).
4. **Deploy** with `deploy/deploy.sh` (builds the site with its checks, rebuilds the API image; migration 009 runs at the
   API start — until it has run, `/api/daily` answers 503 and the site shows the card from the card base).
5. **After the deploy:** `curl -sI https://arcanadiary.com/sw.js | grep -i cache-control` → `no-cache`;
   `curl -s https://arcanadiary.com/api/push/key` → `"enabled":true`. Then the owner's phone check (spec §6): the card,
   the mark after 17:00 (signed in, and inactive with the sign-in line as a guest), the calendar, a reminder on Android
   or a computer (set the hour to the next hour), on iPhone from the Home Screen.
6. **Rollback:** never plain f1b3c38. Going back to pre-8.1 API code after 009 is safe for the tables, but the old hourly
   cleanup (it runs at start) deletes every `daily_draws` row older than 7 days, account calendars included, and cached
   texts older than 2 days. The rollback is the content of the local branch `rollback-pre-8.1` (f1b3c38 plus one commit:
   the cleanup deletes guest rows only, `AND user_id IS NULL`) deployed to `main` on the owner's word, and only onto a
   database that already has 009. Migration 009 is not reverted. The old `delete_account` knows nothing of `user_id` or
   push subscriptions: after returning to 8.1, delete the notes and subscriptions of accounts deleted meanwhile
   (`deleted_accounts`). api/README.md says the same.
7. **Back up `deploy/.env` after `gen-vapid.sh`:** the owner copies it somewhere private. Lost VAPID keys make every
   subscription dead.
8. **Phone test:** a reminder offer appears after 3 days in a row (or at once in the iPhone Home Screen app).

## Decisions on the open questions (owner, forms 27–28.11.2026; controller, 28.11.2026)

| # | Question | Decision | Where in the plan |
|---|---|---|---|
| 1 | `daily_open` does not exist in the code | no new event; the existing `tool_view {tool: daily}`; spec §4 corrected (controller) | decision 8, Task 5 |
| 2 | «Day 1 in a row» | the streak line from day 2 (controller) | decision 4, Task 9 |
| 3 | guest draws 8 → 60 days on data already given | 60 days with only a new effective date of the policy, no on-site notice; the date is the deploy day (owner decision 55) | Task 12 texts; Operator step 2 |
| 4 | labels the spec does not give | EN and ES drafts stay; all listed below for the owner to read before the merge (controller) | «Texts for the owner to read» |
| 5 | texts of past days | `daily_cache` keeps 62 days: the calendar shows the text read that morning (owner decision 54) | decision 6, Task 4 |
| 6 | guests in the evening | the same question, inactive answers, a sign-in line (owner decision 56) | decision 7, Task 9 |
| 7 | guest activity column | `active_at`, renewed on each Card of the Day visit (controller) | Task 1, Task 2 |
| 8 | failure rule | 404/410 delete at once; 401/403 not counted; other failures 3 in a row delete (controller) | decision 10, Task 8 |
| 9 | send window | hour .. hour + 2, otherwise the day is skipped (controller) | decision 10, Task 8 |
| 10 | a reminder after sign-out | stays with the account until turned off; the account page has the switch; account deletion removes it (controller) | decision 11, Tasks 4, 11 |
| 11 | a guest's best streak ≤ 60 days | fine (controller) | — |
| 12 | ES privacy close to the ceiling | noted, no limit change now (controller) | note below |
| 13 | stale checks in `deploy/test-site-routes.sh` | fixed in Task 1, Step 2, in its own commit (controller) | Task 1 |
| — | push dependency | no new package (own RFC 8291/8292 code on the pinned `cryptography`, PyJWT, httpx) as the recommendation; the STOP step of Task 6 stays — the owner confirms it when execution starts | decision 1, Task 6 |

**Note (question 12):** after Task 12 the Spanish privacy page has 3273 words, 27 under the checker's ceiling for
`privacidad` (3000 + 10 %). The next text added to it needs a trim elsewhere or a higher plan limit in
`tools/cards/check_tool_pages.py`; the limit is not changed in this stage.

## Texts for the owner to read

Every new interface string of this stage (`site/src/i18n/{en,es}.ts`), in the order the tasks add them. «Spec» means the
text is fixed by the spec or the owner; «draft» means it is the plan's wording and waits for the owner's read before the
merge. The page texts (the Card of the Day block and FAQ, the privacy additions) are in Task 12, Step 1, word for word.
`{n}`, `{name}`, `{count}`, `{date}`, `{hour}` are filled in by the site.

| Key | EN | ES | Status |
|---|---|---|---|
| `dailyStreak` | Day {n} in a row | Día {n} seguido | spec |
| `dailyCalendarLink` | Your month in cards | Tu mes en cartas | spec |
| `eveningQuestion` | Did today's card show up in your day? | ¿Apareció la carta de hoy en tu día? | spec |
| `feltYes` | Yes | Sí | spec |
| `feltPartly` | Partly | En parte | spec |
| `feltNo` | No | No | spec |
| `eveningNoteLabel` | One line about your day (optional) | Una línea sobre tu día (opcional) | draft |
| `eveningNoteSave` | Save | Guardar | draft |
| `eveningSaved` | Saved. | Se guardó. | draft |
| `eveningFailed` | We couldn't save that. Please try again. | No se pudo guardar. Intenta de nuevo. | draft |
| `eveningSignIn` | Sign in to mark your days and keep your cards | Inicia sesión para marcar tus días y guardar tus cartas | EN owner's draft (decision 56), ES draft |
| `diaryTabsLabel` | Diary sections | Secciones del diario | draft |
| `diaryTabReadings` | Readings | Lecturas | draft |
| `calendarStreak` | Streak now: {n} | Racha actual: {n} | draft |
| `calendarBest` | Best streak: {n} | Mejor racha: {n} | draft |
| `calendarTop` | Most frequent this month: {name} ×{count} | La más frecuente del mes: {name} ×{count} | draft |
| `calendarPrev` | Previous month | Mes anterior | draft |
| `calendarNext` | Next month | Mes siguiente | draft |
| `calendarEmpty` | No cards this month yet. | Todavía no hay cartas este mes. | draft |
| `calendarLocked` | Older months are kept and will open with Plus. | Los meses anteriores se guardan y se abrirán con Plus. | draft |
| `calendarGuestTitle` | Your last 7 days | Tus últimos 7 días | draft |
| `calendarSignIn` | Sign in to keep your cards | Inicia sesión para guardar tus cartas | EN spec, ES draft |
| `calendarDayCard` | Card of {date} | Carta del {date} | draft |
| `pushOffer` | Remind me each morning | Avísame cada mañana | EN spec, ES draft |
| `pushHourLabel` | At | A las | draft |
| `pushNotNow` | Not now | Ahora no | draft |
| `pushOn` | Morning reminder on, at {hour}. | Aviso de la mañana activado, a las {hour}. | draft |
| `pushOff` | Turn off | Desactivar | draft |
| `pushDenied` | Notifications for this site are blocked in your browser settings. | Las notificaciones de este sitio están bloqueadas en la configuración de tu navegador. | draft |
| `pushFailed` | We couldn't turn on the reminder. Please try again. | No se pudo activar el aviso. Intenta de nuevo. | draft |
| `pushIosHint` | To get a morning reminder on iPhone, add this site to your Home Screen: tap Share, then “Add to Home Screen”, and open it from there. | Para recibir el aviso en iPhone, agrega este sitio a tu pantalla de inicio: toca Compartir, luego «Agregar a inicio», y ábrelo desde ahí. | draft |
| `notifTitle` | Arcana Diary | Arcana Diary | brand name, both |
| `notifBody` | Your card for today is waiting | Tu carta de hoy te espera | spec |
| `accountPushTitle` | Morning reminder in this browser | Aviso de la mañana en este navegador | draft |
| `accountPushOn` | On, at {hour}. | Activado, a las {hour}. | draft |
| `accountPushNone` | Off. You can turn it on under the Card of the Day. | Desactivado. Puedes activarlo debajo de la carta del día. | draft |

Reused without change: `navDaily` («Card of the Day» / «Carta del día») as the diary tab, `reversedTag`, `retry`, the error lines. Count: 36 new keys (266 → 302).
