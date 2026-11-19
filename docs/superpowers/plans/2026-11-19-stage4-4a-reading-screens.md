# Stage 4.4a: Reading Screens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On the closed site a person can make a real reading — open a tool, draw cards in the night room, read the reader's answer as it streams, ask follow-ups, turn the Card of the Day — on a phone and a desktop, in English and Spanish; the API gets our own event counter for the funnel.

**Revision 19.11.2026 (Fable 5.2 review `.superpowers/sdd/s44a-plan-fable-review.md`, READY WITH FIXES, 0/6/11; owner decisions by form):** yes/no is one card in 4.4a and "yes/no with three cards" becomes its own sub-stage before launch (spec §3 updated); the screens follow the prototypes exactly — with the answer the question sits small at top left and the headline is the large title (2e, 5b), the desktop room has cards left and text right (13d), the Plus card is a day block (11a); no Plus price on the closed stage; the Card of the Day 503 fallback, the hidden links (restore list in spec §11) and the corrected /retry sentence (spec §4) are accepted. Applied: I1 Escape on the document and focus back to the title, I2 focus ring in the surface's text colour, I3 a broken follow-up is read back, I4 502/504 = unavailable, I5 SMS link, help link and the question cleared on a crisis, I6 one history entry for the room; M1–M7, M9, M10; M11 (self-hosted fonts) is a stage 7 note in the spec.

**Architecture:** Astro static build in `site/` (one HTML file per page, `build.format: 'file'`) with three Preact islands: `ReadingIsland` (draw panel, night room, Plus card), `DailyIsland`, `MenuToggle`. Everything without a screen is a plain TS module in `site/src/lib` or `site/src/i18n` with Vitest tests in Node: the night-room state machine (`nightRoom.ts`), the SSE parser (`sse.ts`), the API client (`api.ts`), the request flow with restore/retry/Turnstile (`readingFlow.ts`), answer sections (`answer.ts`), follow-up rules (`followups.ts`), per-page panel settings (`panel.ts`), routes and language pairs (`routes.ts`), dictionaries. Islands only draw state, run timers and move focus. The build container sees only `site/`, so `tools/site/sync_site_data.py` copies the tokens and generates the card data and the language pairs into `site/src` (committed, with a `--check` test). The API gets `POST /api/events` with migration `004_events.sql`; Caddy serves `/one-card` from `one-card.html` and each language's 404 page.

**Tech Stack:** Astro 5.18.2, @astrojs/preact 4.1.3, preact 10.29.8, Vitest 5.1.0 — all already locked in `site/package-lock.json` (commit 4d0c01b, owner-approved); Node 22 only in Docker; FastAPI 0.115.6, psycopg 3.3.9, pytest 8.3.4 in `api/.venv` (nothing new); Caddy 2.8.4 for route checks on a throwaway container.

**Spec:** `docs/superpowers/specs/2026-11-19-stage4-4a-reading-screens-design.md` (owner-approved; its decisions are not reopened here). Screens, copy and components: the stage 3 prototypes and design system (private Artifacts linked in `docs/design/00-design.md`); API contract: `api/README.md` ("Передача в 4.4") and spec 4.2 ("Передача в 4.3, 4.4").

## Global Constraints

- Pages (spec §3): EN `/`, `/one-card`, `/yes-no`, `/love`, `/daily`, `/cards/{slug_en}` ×78, `/404`; ES `/es` (one-card mode = section `/es#una-carta`), `/es/si-o-no`, `/es/amor`, `/es/carta-del-dia`, `/es/cartas/{slug_es}` ×78, `/es/404`. 167 HTML files in `site/dist`. Slugs: `docs/research/stage1/cards.csv` (the same as `content/cards/deck.json`); language pairs: `docs/research/stage2/hreflang.csv`. Simple card page = picture, keywords, upright and reversed meaning from `content/cards/meanings.*.json`, at the final address (stage 6 replaces the template).
- Not in 4.4a and not shown anywhere: "Save to diary", sign-in, diary, account, "Remind me tomorrow" (4.4b); card hubs, full card pages, the yes/no reference, the "Card Meanings" menu item and "All 78 card meanings" (stage 6); privacy/about links (stage 7). No `hreflang` tags (all rows of `hreflang.csv` are `in_hreflang=no` until launch); the stage stays closed by Caddy (password, `X-Robots-Tag: noindex`).
- Night room (spec §4, 00-design.md): a full-screen layer over the current page without an address of its own (it adds one history entry with the same address, so the phone's Back closes it); closed by "×", Escape and Back; focus trapped inside and returned to the draw button; on a desktop a stage up to 960 px wide over the dimmed page. States: opening → dealing → cards turn (up to 1 s per card) → the reader's answer streams → the answer by sections (headline, cards, synthesis, one step; "why" with a verdict) → follow-up field and "More about these cards". `prefers-reduced-motion`: a fade, the cards already turned. Layout as the prototypes: while dealing — positions on top, the question as the large title (2b–2d); with the answer — the question small at top left, the headline as the large title (2e, 5b); desktop — cards left, text right (13d).
- API (spec §4): `POST /api/readings` (kind, question, topic/situation, lang, `tz`) → `GET /api/readings/{id}/stream` read with `fetch`, not `EventSource`; on a break — `GET /api/readings/{id}` (the API keeps writing, spec 4.2 §8.11); `POST /api/readings/{id}/retry` only after a fallback answer (a refused retry restores via GET). Follow-ups: `POST /api/readings/{id}/followups` with the same `tz`. Two free; a paid one is offered only when `followups_left == 0` and `followup_attempts_left > 0`: the first request goes without `use_reading`, the API's `402 confirm` brings the warning "this will use 1 reading" with the readings left, then the same request with `"use_reading": true`; `402 confirm`, `402 plus` and `done.used_reading` are handled; after a crisis in a follow-up the shown text is cleared; a broken follow-up stream is read back from `GET /api/readings/{id}`.
- Crisis answer: the warm message and help lines from the API; no reading is shown. Errors `429` (daily limit, burst, the address's day cap, follow-up attempts), `403 turnstile`, `503` (and `502`/`504` while the API restarts): plain strings and a link to help lines (`https://findahelpline.com`). On a crisis answer the question field is emptied. `403 turnstile` → the invisible Cloudflare Turnstile widget with the site key from the 403 answer (`TURNSTILE_SITEKEY` on the server), then the request again; the Turnstile script is loaded only at that moment. Limit reached → the Plus card (screen 11a, a day block in place of the night panel) with the e-mail field "tell me when it opens" (`POST /api/plus/waitlist`); no price on the closed stage (owner, 19.11.2026; the owner names it before launch).
- Answers, names and labels are rendered as text (Preact/Astro text nodes, i.e. `textContent`), never as markup: no `innerHTML`, `dangerouslySetInnerHTML`, `set:html` (a Vitest test scans the sources).
- Card of the Day (spec §5): `GET /api/daily` (lang, `tz`) → tap the back → the card and its meaning for today; on `503` (or `502`/`504`) one card for everyone that local day, upright, from the card base, with a note.
- Analytics (spec §6): `POST /api/events {"name", "tool", "lang", "params"}`; only the events and parameters of `docs/design/analytics-events.md` are accepted (each listed parameter required, nothing else); no address, cookie or identifiers stored; more than 30 requests a minute from one address or 600 from all addresses → `429`; table `events` (migration 004: day, name, tool, language, parameters, time) with RLS on and no rights for `anon` / `authenticated`, like the other tables. 4.4a sends `tool_view`, `draw_click`, `night_open`, `cards_revealed`, `reading_shown`, `more_about_cards`, `plus_view` with `navigator.sendBeacon` (else `fetch` with `keepalive`); a counter failure never reaches the reading; a one-card draw on the Spanish home counts as `one_card`. The funnel SQL lives in `api/README.md` and starts from the launch day.
- Code rules (00-design.md): colours, fonts, spacing, radii and motion only from `docs/design/tokens.css` (copied to `site/src/styles/tokens.css`); fonts from Google Fonts — Cormorant Garamond 500/600, Manrope 400–700; touch targets ≥ 44 px (main buttons 52 px); focus ring 2 px, offset 2 px, in the text colour of the surface (`currentColor` by default; `--color-night-text` in night areas, `--color-day-text` on the Plus card); real `<button>`, `<a>`, `<label>`; field, chip and outline-button borders use `control-border`. Card pictures from `site/public/cards/` in three sizes with `srcset`.
- Copy: one dictionary per language (`site/src/i18n/en.ts`, `es.ts`); prototype strings verbatim; strings the prototypes lack are drafted and listed in `enDrafts` / `esDrafts` under the comment `// draft — review with stage 5 texts`. Spanish: Mexican, `tú`, no gendered forms for the person.
- No secrets in `site/`. Builds and Node commands only in Docker `node:22`: build — `deploy/build-site.sh` (runs `npm ci` and `npm run build`; it also provides `site/node_modules` for Vitest); Vitest — from the repository root `docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run [files]`.
- Install nothing: the site uses only the packages of commit 4d0c01b (`@astrojs/preact` 4.1.3, `preact` 10.29.8, `vitest` 5.1.0, Astro 5.18.2); the API only `api/requirements*.txt`.
- Never read, print or commit `deploy/.env` or `deploy/caddy/stage_auth.caddy*`; never touch, reload or restart `arcana-caddy-1` / `arcana-api-1`; never run `deploy/deploy.sh` or `docker compose` in `deploy/` — deploying is the owner's step; Caddy is checked only on throwaway containers. No paid API calls.
- Counts (measured by applying this revised plan to a scratch copy of `stage4-screens` at 4d0c01b): API `cd ~/arcana-diary/api && .venv/bin/pytest -q` — baseline `1048 passed`, after Task 1 `1083 passed`; Vitest after Task 8 — `122 passed` in 17 files; `api/.venv/bin/pytest -q tools/site` — `7 passed`; the build — 167 HTML pages.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## File Structure

| File | Responsibility |
|---|---|
| `api/migrations/004_events.sql` (new) | table `events` (no person data), index, RLS |
| `api/app/events.py` (new) | the event whitelist (`EVENTS`, `TOOLS`), `check_event`, `record_event` |
| `api/app/routes/events.py` (new) | `POST /api/events`: burst limit, whitelist, insert, `204` |
| `api/app/config.py`, `api/app/context.py`, `api/app/db.py`, `api/app/main.py` | `EVENTS_PER_MINUTE`, `events_burst`, `events` in `APP_TABLES`, the router |
| `api/README.md` | the endpoint, the event rules and the funnel SQL |
| `tools/site/sync_site_data.py`, `tools/site/check_dist.py` (new) | data from outside `site/` into `site/src`; the list of pages the build must produce |
| `site/src/styles/tokens.css`, `site/src/data/{deck,meanings.en,meanings.es,pairs}.json` (generated) | tokens, 78 cards, short meanings, language pairs of the 4.4a pages |
| `site/astro.config.mjs`, `site/tsconfig.json`, `site/vitest.config.ts`, `site/package.json` | Preact integration, file-per-page output, Vitest in Node, `npm test` |
| `site/src/lib/types.ts` | shared types: languages, tools, kinds, API shapes |
| `site/src/lib/deck.ts`, `site/src/lib/routes.ts` | cards (names, slugs, pictures, neighbours, the fallback daily card); page paths, language pairs, menu |
| `site/src/i18n/{en,es,index}.ts` | dictionaries, drafts, `t`, `fill` |
| `site/src/lib/errors.ts`, `sse.ts`, `followups.ts`, `api.ts` | error kinds, SSE parsing, follow-up rules, API client |
| `site/src/lib/testing/fakes.ts` | fake `fetch` and API responses for tests |
| `site/src/lib/answer.ts`, `nightRoom.ts`, `readingFlow.ts` | answer sections, the night-room state machine, the requests behind it |
| `site/src/lib/panel.ts`, `turnstile.ts`, `analytics.ts`, `focus.ts`, `helplines.ts`, `daily.ts` | per-page panel settings, Turnstile on demand, event sending, focus trap, safe help-line links, Card of the Day logic |
| `site/src/styles/global.css` | all styles, from tokens only |
| `site/src/layouts/Base.astro`, `site/src/components/{Header,Footer,LangSwitch,MoonMark,CardFigure}.astro` | page frame, menu, footer, EN/ES switch, card face on day pages |
| `site/src/islands/{MenuToggle,ReadingIsland,DailyIsland}.tsx` | the three islands |
| `site/src/components/ui/{icons,CardFace,HelpLine,CrisisView,PlusCard,NightRoom}.tsx` | Preact pieces the islands draw |
| `site/src/views/{HomeView,ToolView,CardView,DailyView,NotFoundView}.astro` | page templates by language |
| `site/src/pages/**` | one small file per address (and `/data/daily-<lang>.json`) |
| `deploy/Caddyfile`, `deploy/test-site-routes.sh` (new), `deploy/check-indexing.sh` | `try_files {path}.html`, redirects of `/x/` and `/x.html` to `/x`, the 404 page per language; their checks |
| `docs/design/00-design.md` | the focus-ring rule: the surface's text colour |

---

### Task 1: The event counter in the API (`POST /api/events`, migration 004)

**Files:**
- Create: `api/migrations/004_events.sql`
- Create: `api/app/events.py`
- Create: `api/app/routes/events.py`
- Modify: `api/app/config.py`, `api/app/db.py`, `api/app/context.py`, `api/app/main.py`, `api/README.md`
- Test: `api/tests/test_api_events.py` (new), `api/tests/test_db.py`

**Interfaces:**
- Consumes: `app.limits.utc_day(now) -> date`, `limits.client_ip(request, trust_cloudflare) -> str`, `ctx.salt.hash_ip(ip, now) -> str`, `app.limits.BurstCounter().hit(key, now) -> int`, `app.routes.common.respond(status, payload) -> JSONResponse`, router dependency `API_AUTH` in `app/main.py`; `app.db.split_sql` (a statement ends with `;` at the end of a line — no other line of the migration may end with `;`).
- Produces:
  - Table `events (id uuid PK DEFAULT gen_random_uuid(), day date, name text CHECK (10 names), tool text NULL CHECK (6 tools), lang text CHECK ('en','es'), params jsonb DEFAULT '{}', created_at timestamptz)`, index `events_day_name_idx (day, name)`, RLS on; `"events"` is the last item of `app.db.APP_TABLES` (tests truncate it; `migrate()` revokes the browser roles on it). No sequence (the id is `gen_random_uuid()`), so `APP_SEQUENCES` is unchanged.
  - `app.events.TOOLS: tuple[str, ...]`, `app.events.EVENTS: dict[str, tuple[bool, dict[str, Callable]]]`, `app.events.InvalidEvent(field)` with `.field`, `app.events.check_event(name, tool, params) -> None` (raises `InvalidEvent`), `app.events.record_event(conn, name, tool, lang, params, now) -> None`.
  - `app.config.EVENTS_PER_MINUTE = 30`, `app.config.EVENTS_GLOBAL_PER_MINUTE = 600`; `AppContext.events_burst: BurstCounter` (per address and, under the key `app.routes.events.ALL_ADDRESSES = "all"`, for all addresses).
  - `POST /api/events {"name": str, "tool": str | null, "lang": "en" | "es", "params": {}}` → `204` (no body, no cookie); invalid → `422 {"reason": "invalid", "fields": ["name" | "tool" | "params.<key>"]}`; over the burst (per address or all together) → `429 {"reason": "rate"}`; a bad Bearer token → `401` (router dependency).
  - `api/README.md` section `## Счётчик событий (этап 4.4а)` with one ```` ```sql ```` block (named parameters `%(day_from)s`, `%(day_to)s`) — `test_api_events.py` runs it.

- [ ] **Step 1: Write the failing tests**

Create `api/tests/test_api_events.py`:

````python
"""POST /api/events (spec 2026-11-19 stage 4.4a §6): only the events and parameters of
docs/design/analytics-events.md, nothing about the person, a burst limit per address."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.config import EVENTS_PER_MINUTE
from app.routes import events as events_route
from helpers import from_ip, guest_headers

VALID = [
    {"name": "tool_view", "tool": "home", "lang": "en", "params": {}},
    {"name": "draw_click", "tool": "yes_no", "lang": "es", "params": {"has_question": True, "entry": "tool"}},
    {"name": "draw_click", "tool": "one_card", "lang": "en", "params": {"has_question": False, "entry": "card_page"}},
    {"name": "night_open", "tool": "love", "lang": "en", "params": {}},
    {"name": "cards_revealed", "tool": "home", "lang": "en", "params": {"cards_count": 3}},
    {"name": "reading_shown", "tool": "one_card", "lang": "es", "params": {"ms_from_draw": 5400}},
    {"name": "save_click", "tool": "home", "lang": "en", "params": {}},
    {"name": "signup_done", "lang": "en", "params": {"method": "email"}},
    {"name": "more_about_cards", "tool": "yes_no", "lang": "en", "params": {}},
    {"name": "outcome_answered", "lang": "es", "params": {"after_days": 7, "answer": "partly"}},
    {"name": "plus_view", "lang": "en", "params": {"place": "limit"}},
    {"name": "tool_view", "tool": "daily", "lang": "es"},
]

INVALID = [
    ({"name": "page_view", "tool": "home", "lang": "en"}, "name"),
    ({"name": "tool_view", "lang": "en"}, "tool"),
    ({"name": "tool_view", "tool": "diary", "lang": "en"}, "tool"),
    ({"name": "plus_view", "tool": "home", "lang": "en", "params": {"place": "limit"}}, "tool"),
    ({"name": "tool_view", "tool": "home", "lang": "en", "params": {"question": "Will he call?"}}, "params.question"),
    ({"name": "draw_click", "tool": "home", "lang": "en", "params": {"has_question": True}}, "params.entry"),
    ({"name": "draw_click", "tool": "home", "lang": "en", "params": {"has_question": "yes", "entry": "tool"}},
     "params.has_question"),
    ({"name": "cards_revealed", "tool": "home", "lang": "en", "params": {"cards_count": True}}, "params.cards_count"),
    ({"name": "cards_revealed", "tool": "home", "lang": "en", "params": {"cards_count": 2}}, "params.cards_count"),
    ({"name": "reading_shown", "tool": "home", "lang": "en", "params": {"ms_from_draw": -1}}, "params.ms_from_draw"),
    ({"name": "reading_shown", "tool": "home", "lang": "en", "params": {"ms_from_draw": 1.5}}, "params.ms_from_draw"),
    ({"name": "outcome_answered", "lang": "en", "params": {"after_days": 14, "answer": "yes"}}, "params.after_days"),
]


def rows(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT * FROM events ORDER BY created_at, name").fetchall()


@pytest.mark.parametrize("body", VALID, ids=[f"{b['name']}-{i}" for i, b in enumerate(VALID)])
def test_a_listed_event_is_stored(api, body):
    response = api.client.post("/api/events", json=body)
    assert response.status_code == 204 and response.content == b""
    [row] = rows(api)
    assert (row["name"], row["tool"], row["lang"], row["params"]) == (body["name"], body.get("tool"), body["lang"],
                                                                      body.get("params", {}))
    assert row["day"].isoformat() == "2026-11-20"


@pytest.mark.parametrize("body,field", INVALID, ids=[f for _, f in INVALID])
def test_anything_else_is_refused_and_not_stored(api, body, field):
    response = api.client.post("/api/events", json=body)
    assert response.status_code == 422
    assert response.json() == {"reason": "invalid", "fields": [field]}
    assert rows(api) == []


def test_a_wrong_language_is_refused(api):
    response = api.client.post("/api/events", json={"name": "tool_view", "tool": "home", "lang": "fr"})
    assert response.status_code == 422 and rows(api) == []


def test_no_address_cookie_or_id_is_kept(api):
    headers = {**from_ip("203.0.113.77"), **guest_headers("4d5e6f70-0000-4000-8000-0000000000aa")}
    response = api.client.post("/api/events", json=VALID[1], headers=headers)
    assert response.status_code == 204
    assert "set-cookie" not in response.headers
    with api.db.connect() as conn:
        columns = [r["column_name"] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'events' ORDER BY ordinal_position")]
        dump = conn.execute("SELECT row_to_json(e)::text AS t FROM events e").fetchone()["t"]
    assert columns == ["id", "day", "name", "tool", "lang", "params", "created_at"]
    assert "203.0.113" not in dump and "4d5e6f70" not in dump


def test_a_new_visitor_gets_no_guest_cookie(api):
    response = api.client.post("/api/events", json=VALID[0])
    assert response.status_code == 204 and "set-cookie" not in response.headers


def test_a_burst_from_one_address_is_cut(api):
    here, there = from_ip("198.51.100.7"), from_ip("198.51.100.8")
    statuses = [api.client.post("/api/events", json=VALID[0], headers=here).status_code
                for _ in range(EVENTS_PER_MINUTE + 1)]
    assert statuses == [204] * EVENTS_PER_MINUTE + [429]
    assert api.client.post("/api/events", json=VALID[0], headers=here).json() == {"reason": "rate"}
    assert api.client.post("/api/events", json=VALID[0], headers=there).status_code == 204
    api.clock.advance(seconds=61)
    assert api.client.post("/api/events", json=VALID[0], headers=here).status_code == 204
    assert len(rows(api)) == EVENTS_PER_MINUTE + 2


def test_a_flood_from_many_addresses_is_cut(api, monkeypatch):
    monkeypatch.setattr(events_route, "EVENTS_GLOBAL_PER_MINUTE", 3)
    statuses = [api.client.post("/api/events", json=VALID[0], headers=from_ip(f"198.51.100.{i}")).status_code
                for i in range(5)]
    assert statuses == [204, 204, 204, 429, 429]
    assert len(rows(api)) == 3


def test_a_bad_token_is_refused_before_anything(api):
    response = api.client.post("/api/events", json=VALID[0], headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401 and rows(api) == []


def test_the_funnel_query_of_the_readme_counts_the_steps(api):
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    sql = readme.split("## Счётчик событий (этап 4.4а)", 1)[1].split("```sql\n", 1)[1].split("```", 1)[0]
    assert api.client.post("/api/events", json=VALID[0]).status_code == 204  # the closed stage: not counted
    api.clock.now = datetime(2026, 12, 15, 18, 0, tzinfo=timezone.utc)
    for body in (VALID[0], VALID[0], {**VALID[1], "tool": "home"}, VALID[4],
                 {"name": "reading_shown", "tool": "home", "lang": "en", "params": {"ms_from_draw": 900}},
                 {"name": "draw_click", "tool": "home", "lang": "en", "params": {"has_question": False, "entry": "tool"}}):
        assert api.client.post("/api/events", json=body).status_code == 204
    with api.db.connect() as conn:
        rows = conn.execute(sql, {"day_from": "2026-11-01", "day_to": "2026-12-31"}).fetchall()
    assert [(r["tool"], r["lang"], r["views"], r["draws"], r["shown"], r["saves"], float(r["shown_pct"])) for r in rows] == [
        ("home", "en", 2, 1, 1, 0, 100.0), ("home", "es", 0, 1, 0, 0, 0.0)]
````

In `api/tests/test_db.py`, replace:

```python
    assert migrate(fresh_db, MIGRATIONS) == ["001_init", "002_accounts", "003_guard_source"]
```

with:

```python
    assert migrate(fresh_db, MIGRATIONS) == ["001_init", "002_accounts", "003_guard_source", "004_events"]
```

In `api/tests/test_db.py`, replace:

```python
                            " has_table_privilege('authenticated', 'public.deleted_accounts', 'SELECT') AS f"
                            ).fetchone()
    assert rows == {"a": False, "b": False, "c": False, "d": False, "e": False, "f": False}
```

with:

```python
                            " has_table_privilege('authenticated', 'public.deleted_accounts', 'SELECT') AS f,"
                            " has_table_privilege('anon', 'public.events', 'INSERT') AS g,"
                            " has_table_privilege('authenticated', 'public.events', 'SELECT') AS h"
                            ).fetchone()
    assert rows == {"a": False, "b": False, "c": False, "d": False, "e": False, "f": False, "g": False, "h": False}
```

In `api/tests/test_db.py`, replace:

```python
    assert migrate(fresh_db, MIGRATIONS) == ["002_accounts", "003_guard_source"]
```

with:

```python
    assert migrate(fresh_db, MIGRATIONS) == ["002_accounts", "003_guard_source", "004_events"]
```

In `api/tests/test_db.py`, replace:

```python
    assert migrate(fresh_db, MIGRATIONS) == ["003_guard_source"]
```

with:

```python
    assert migrate(fresh_db, MIGRATIONS) == ["003_guard_source", "004_events"]
```

Append to `api/tests/test_db.py`:

```python


# --- stage 4.4a: migration 004 (spec 2026-11-19 §6) ---

def test_004_applies_over_003(fresh_db):
    apply_up_to(fresh_db, "001_init", "002_accounts", "003_guard_source")  # the live database after stage 4.3
    assert migrate(fresh_db, MIGRATIONS) == ["004_events"]
    with fresh_db.connect() as conn:
        security = conn.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'events'").fetchone()
        names = {r["indexname"] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'events'")}
    assert security == {"relrowsecurity": True}
    assert "events_day_name_idx" in names


@pytest.mark.parametrize("sql", [
    "INSERT INTO events (day, name, lang, created_at) VALUES ('2026-11-20', 'page_view', 'en', now())",
    "INSERT INTO events (day, name, tool, lang, created_at) VALUES ('2026-11-20', 'tool_view', 'diary', 'en', now())",
    "INSERT INTO events (day, name, lang, created_at) VALUES ('2026-11-20', 'tool_view', 'fr', now())",
])
def test_004_checks(db, sql):
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.connect() as conn:
            conn.execute(sql)
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_events.py tests/test_db.py`
Expected: FAIL — `ImportError: cannot import name 'EVENTS_PER_MINUTE' from 'app.config'` while collecting `test_api_events.py`; in `test_db.py` the migration lists miss `"004_events"`.

- [ ] **Step 3: Write the migration, the whitelist and the route**

Create `api/migrations/004_events.sql`:

```sql
-- 004_events: stage 4.4a (spec 2026-11-19 §6): our own event counter for the funnel of
-- docs/design/analytics-events.md. No address, cookie, account or device id is stored: a row is the event name,
-- the tool, the page language, the whitelisted parameters, the UTC day and the time. As for the other tables:
-- row level security on, no policies, no rights for the browser roles (migrate() revokes them). The id is a
-- random row key, not a person, and needs no sequence.
CREATE TABLE events (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    day        date NOT NULL,
    name       text NOT NULL CHECK (name IN ('tool_view', 'draw_click', 'night_open', 'cards_revealed',
                                             'reading_shown', 'save_click', 'signup_done', 'more_about_cards',
                                             'outcome_answered', 'plus_view')),
    tool       text CHECK (tool IN ('home', 'one_card', 'yes_no', 'love', 'daily', 'three_cards')),
    lang       text NOT NULL CHECK (lang IN ('en', 'es')),
    params     jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL
);
CREATE INDEX events_day_name_idx ON events (day, name);

ALTER TABLE events ENABLE ROW LEVEL SECURITY;
```

Create `api/app/events.py`:

```python
"""Our own event counter (spec 2026-11-19 stage 4.4a §6). Only the events and parameters of
docs/design/analytics-events.md are accepted, each with exactly its listed parameters; nothing about the person is
stored — no address, no cookie, no account or device id (the address is used only, hashed and in memory, for the
burst limit in routes/events.py)."""
from datetime import datetime

from psycopg.types.json import Jsonb

from app.limits import utc_day

TOOLS = ("home", "one_card", "yes_no", "love", "daily", "three_cards")


def _one_of(*allowed):
    """A value equal to one of `allowed` and of the same JSON type (true is not 1, 1.0 is not 1)."""
    return lambda value: any(type(value) is type(item) and value == item for item in allowed)


def _ms(value) -> bool:
    return type(value) is int and 0 <= value <= 600_000


# name → (carries a tool?, {parameter: check}); every listed parameter is required, nothing else is accepted
EVENTS = {
    "tool_view": (True, {}),
    "draw_click": (True, {"has_question": _one_of(True, False), "entry": _one_of("tool", "card_page", "hub")}),
    "night_open": (True, {}),
    "cards_revealed": (True, {"cards_count": _one_of(1, 3)}),
    "reading_shown": (True, {"ms_from_draw": _ms}),
    "save_click": (True, {}),
    "signup_done": (False, {"method": _one_of("email", "google", "apple")}),
    "more_about_cards": (True, {}),
    "outcome_answered": (False, {"after_days": _one_of(7, 30), "answer": _one_of("yes", "partly", "no")}),
    "plus_view": (False, {"place": _one_of("limit", "diary")}),
}


class InvalidEvent(ValueError):
    """field: what was wrong, as in the 422 answer ("name", "tool", "params.<key>")."""

    def __init__(self, field: str):
        super().__init__(field)
        self.field = field


def check_event(name: str, tool: str | None, params: dict) -> None:
    if name not in EVENTS:
        raise InvalidEvent("name")
    with_tool, checks = EVENTS[name]
    if with_tool != (tool is not None) or (tool is not None and tool not in TOOLS):
        raise InvalidEvent("tool")
    for key in params:
        if key not in checks:
            raise InvalidEvent(f"params.{key}")
    for key, ok in checks.items():
        if key not in params or not ok(params[key]):
            raise InvalidEvent(f"params.{key}")


def record_event(conn, name: str, tool: str | None, lang: str, params: dict, now: datetime) -> None:
    conn.execute("INSERT INTO events (day, name, tool, lang, params, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                 (utc_day(now), name, tool, lang, Jsonb(params), now))
```

Create `api/app/routes/events.py`:

```python
"""POST /api/events (spec 2026-11-19 stage 4.4a §6): {"name", "tool", "lang", "params"} → 204. The site sends it
with navigator.sendBeacon; nothing here reads or sets a cookie, and the answer carries no body. More than
EVENTS_PER_MINUTE requests a minute from one address, or more than EVENTS_GLOBAL_PER_MINUTE from all addresses together
(a flood from many addresses) → 429 {"reason": "rate"}, nothing stored."""
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app import events, limits
from app.config import EVENTS_GLOBAL_PER_MINUTE, EVENTS_PER_MINUTE
from app.context import get_ctx
from app.routes.common import respond

router = APIRouter(prefix="/api")
ALL_ADDRESSES = "all"  # the key of the global counter; address keys are sha256 hex, so they never collide


class EventIn(BaseModel):
    name: str = Field(max_length=40)
    tool: str | None = Field(default=None, max_length=40)
    lang: Literal["en", "es"]
    params: dict[str, Any] = Field(default_factory=dict, max_length=8)


@router.post("/events")
def post_event(body: EventIn, request: Request):
    ctx = get_ctx(request)
    now = ctx.clock()
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    if ctx.events_burst.hit(ip_hash, now) > EVENTS_PER_MINUTE:
        return respond(429, {"reason": "rate"})
    if ctx.events_burst.hit(ALL_ADDRESSES, now) > EVENTS_GLOBAL_PER_MINUTE:
        return respond(429, {"reason": "rate"})
    try:
        events.check_event(body.name, body.tool, body.params)
    except events.InvalidEvent as exc:
        return respond(422, {"reason": "invalid", "fields": [exc.field]})
    with ctx.db.connect() as conn:
        events.record_event(conn, body.name, body.tool, body.lang, body.params, now)
    return Response(status_code=204)
```

In `api/app/config.py`, replace:

```python
WAITLIST_IP_LIMIT = 5          # stage 4.3 §8: Plus waitlist requests per address per UTC day
```

with:

```python
WAITLIST_IP_LIMIT = 5          # stage 4.3 §8: Plus waitlist requests per address per UTC day
EVENTS_PER_MINUTE = 30         # stage 4.4a §6: POST /api/events per address per minute (a reading sends about 6)
EVENTS_GLOBAL_PER_MINUTE = 600  # stage 4.4a §6: POST /api/events per minute from all addresses together (plan review M9)
```

In `api/app/db.py`, replace:

```python
              "claim_tokens", "profiles", "plus_waitlist", "deleted_accounts")
```

with:

```python
              "claim_tokens", "profiles", "plus_waitlist", "deleted_accounts", "events")
```

In `api/app/context.py`, replace:

```python
    daily_burst: BurstCounter  # GET /api/daily per address
```

with:

```python
    daily_burst: BurstCounter  # GET /api/daily per address
    events_burst: BurstCounter  # POST /api/events per address (stage 4.4a)
```

In `api/app/context.py`, replace:

```python
        salt=DailySalt(), burst=BurstCounter(), daily_burst=BurstCounter(), clock=clock or utc_now,
```

with:

```python
        salt=DailySalt(), burst=BurstCounter(), daily_burst=BurstCounter(), events_burst=BurstCounter(),
        clock=clock or utc_now,
```

In `api/app/main.py`, replace:

```python
from app.routes import account, claim, daily, diary, followups, plus, readings
```

with:

```python
from app.routes import account, claim, daily, diary, events, followups, plus, readings
```

In `api/app/main.py`, replace:

```python
    app.include_router(plus.router, dependencies=API_AUTH)
```

with:

```python
    app.include_router(plus.router, dependencies=API_AUTH)
    app.include_router(events.router, dependencies=API_AUTH)
```

- [ ] **Step 4: Document the endpoint and the funnel query**

In `api/README.md`, replace:

```markdown
(SSE), `POST /api/readings/{id}/followups` (SSE), `GET /api/daily?lang=&tz=`, `GET /api/limits?tz=`. Поддомен `api.`
```

with:

```markdown
(SSE), `POST /api/readings/{id}/followups` (SSE), `GET /api/daily?lang=&tz=`, `GET /api/limits?tz=`, `POST /api/events`
(этап 4.4а, ниже). Поддомен `api.`
```

In `api/README.md`, replace:

```markdown
## Тестовый набор чтеца
```

with:

````markdown
## Счётчик событий (этап 4.4а)

Спецификация — `docs/superpowers/specs/2026-11-19-stage4-4a-reading-screens-design.md`, §6. Сайт шлёт
`POST /api/events {"name", "tool", "lang", "params"}` через `navigator.sendBeacon`; ответ — `204` без тела. Принимаются
только события и параметры из `docs/design/analytics-events.md` (`app/events.py`, каждый параметр события обязателен,
лишний — `422 {"reason": "invalid", "fields": ["params.<имя>"]}`). Ни адреса, ни cookie, ни номера гостя или аккаунта
не пишется: таблица `events` (миграция 004) — день UTC, имя, инструмент, язык, параметры, время. Больше
`EVENTS_PER_MINUTE` (30) запросов в минуту с адреса или `EVENTS_GLOBAL_PER_MINUTE` (600) со всех адресов вместе —
`429 {"reason": "rate"}`, ничего не пишется (счётчики в памяти, как у всплеска раскладов).

Воронка `tool_view → draw_click → reading_shown → save_click` по инструментам и языкам за период (разбор — через
2–3 недели после запуска); `signup_done` без инструмента считается отдельно. Запрос берёт строки только с дня запуска
(14.12.2026; сдвинется запуск — поправить дату): события закрытого стенда — проверки, а не посетители.

```sql
SELECT tool, lang,
       count(*) FILTER (WHERE name = 'tool_view')     AS views,
       count(*) FILTER (WHERE name = 'draw_click')    AS draws,
       count(*) FILTER (WHERE name = 'reading_shown') AS shown,
       count(*) FILTER (WHERE name = 'save_click')    AS saves,
       round(100.0 * count(*) FILTER (WHERE name = 'reading_shown')
             / nullif(count(*) FILTER (WHERE name = 'draw_click'), 0), 1) AS shown_pct
FROM events
WHERE day >= DATE '2026-12-14' AND day BETWEEN %(day_from)s AND %(day_to)s AND tool IS NOT NULL
GROUP BY tool, lang
ORDER BY tool, lang;
```

В SQL Editor Supabase вместо `%(day_from)s` и `%(day_to)s` подставить даты, например `'2026-12-14'` и `'2027-01-04'`.

## Тестовый набор чтеца
````

- [ ] **Step 5: Run the new and changed tests**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q tests/test_api_events.py tests/test_db.py tests/test_api_auth.py`
Expected: `77 passed` (31 in `test_api_events.py`; `test_api_auth.py::test_every_api_route_checks_a_bearer_token_first` now also checks `POST /api/events`).

- [ ] **Step 6: Run the whole API suite**

Run: `cd ~/arcana-diary/api && .venv/bin/pytest -q`
Expected: `1083 passed` (1048 before + 31 + 4).

- [ ] **Step 7: Commit**

```bash
cd ~/arcana-diary
git add api/migrations/004_events.sql api/app/events.py api/app/routes/events.py api/app/config.py api/app/db.py \
  api/app/context.py api/app/main.py api/README.md api/tests/test_api_events.py api/tests/test_db.py
git commit -m "feat(api): POST /api/events — our own event counter (migration 004)

Only the events and parameters of docs/design/analytics-events.md; no address, cookie or id; 30 a minute per
address; RLS and no rights for the browser roles; the funnel SQL in api/README.md.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Site data from outside `site/` and the site configuration

**Files:**
- Create: `tools/site/sync_site_data.py`, `tools/site/check_dist.py`
- Test: `tools/site/test_sync_site_data.py`
- Generated (by the script, committed): `site/src/styles/tokens.css`, `site/src/data/deck.json`, `site/src/data/meanings.en.json`, `site/src/data/meanings.es.json`, `site/src/data/pairs.json`
- Modify: `site/astro.config.mjs` (whole file), `site/package.json`
- Create: `site/tsconfig.json`, `site/vitest.config.ts`

**Interfaces:**
- Consumes: `content/cards/deck.json` (`card_id`, `numeral`, `arcana`, `suit`, `order`, `image`, `slug_en`, `slug_es`), `content/cards/meanings.<lang>.json` (`card_id`, `name`, `keywords`, `upright`, `reversed`), `docs/research/stage2/hreflang.csv` (`entity_id`, `url`, `wave`, `switch_to`), `docs/design/tokens.css`.
- Produces:
  - `site/src/data/deck.json`: 78 objects in deck order `{card_id, numeral, arcana, suit, image, slug_en, slug_es, name_en, name_es}`.
  - `site/src/data/meanings.<lang>.json`: 78 objects `{card_id, keywords: string[], upright, reversed}`.
  - `site/src/data/pairs.json`: `{url: switch_to}` for the launch rows of `page:home`, `tool:one-card`, `tool:daily`, `tool:yes-no`, `tool:love` and `card:*` — 165 entries.
  - `site/src/styles/tokens.css`: byte copy of `docs/design/tokens.css` (custom properties `--color-*`, `--font-*`, `--font-size-*`, `--space-1…8`, `--radius-*`, `--motion-*`, `--card-ratio`).
  - `python3 tools/site/sync_site_data.py [--check]`; `tools/site/check_dist.py`: `expected_pages() -> list[str]` (167), `dist_file(path) -> str`, `missing(dist) -> list[str]`, CLI prints `OK: 167 pages`.
  - Astro: `trailingSlash: 'never'`, `build.format: 'file'` (`/one-card` → `one-card.html`, `/es` → `es.html`), `integrations: [preact()]`; Vitest runs `src/**/*.test.ts` in Node; `npm test` = `vitest run`.

- [ ] **Step 1: Write the failing test**

Create `tools/site/test_sync_site_data.py`:

```python
from check_dist import dist_file, expected_pages
from sync_site_data import ROOT, SITE, build, deck, meanings, pairs, stale


def test_committed_site_data_matches_its_sources():
    assert stale(build()) == []


def test_deck_has_78_cards_in_deck_order_with_both_names():
    cards = deck()
    assert len(cards) == 78
    assert cards[0]["card_id"] == "major-00-fool" and cards[0]["name_es"] == "El Loco"
    assert cards[18]["slug_en"] == "the-moon" and cards[18]["slug_es"] == "la-luna" and cards[18]["numeral"] == "XVIII"
    assert all(c["name_en"] and c["name_es"] for c in cards)


def test_every_card_has_its_three_image_sizes():
    for card in deck():
        for suffix in ("", "@350", "@160"):
            assert (SITE / "public/cards" / f"{card['image']}{suffix}.webp").exists(), card["image"]


def test_meanings_cover_the_deck_in_both_languages():
    ids = {c["card_id"] for c in deck()}
    for lang in ("en", "es"):
        records = meanings(lang)
        assert {m["card_id"] for m in records} == ids
        assert all(m["upright"] and m["reversed"] and m["keywords"] for m in records)


def test_pairs_are_the_44a_pages_of_hreflang_csv():
    table = pairs()
    assert len(table) == 9 + 78 * 2
    assert table["/"] == "/es" and table["/es"] == "/"
    assert table["/one-card"] == "/es"
    assert table["/yes-no"] == "/es/si-o-no" and table["/es/si-o-no"] == "/yes-no"
    assert table["/love"] == "/es/amor" and table["/daily"] == "/es/carta-del-dia"
    for card in deck():
        en, es = f"/cards/{card['slug_en']}", f"/es/cartas/{card['slug_es']}"
        assert table[en] == es and table[es] == en


def test_tokens_css_is_the_design_copy():
    assert (SITE / "src/styles/tokens.css").read_text() == (ROOT / "docs/design/tokens.css").read_text()


def test_the_build_check_expects_167_pages_with_their_files():
    pages = expected_pages()
    assert len(pages) == 167
    assert {"/", "/es", "/404", "/es/404", "/one-card", "/es/cartas/la-luna"} <= set(pages)
    assert [dist_file(p) for p in ("/", "/es", "/es/404", "/cards/the-moon")] == [
        "index.html", "es.html", "es/404.html", "cards/the-moon.html"]
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd ~/arcana-diary && api/.venv/bin/pytest -q tools/site`
Expected: FAIL — `ModuleNotFoundError: No module named 'sync_site_data'`.

- [ ] **Step 3: Write the generator and the page list**

Create `tools/site/sync_site_data.py`:

```python
"""Data the site build needs from outside site/ (stage 4.4a). The site is built in a node:22 container that sees
only site/ (deploy/build-site.sh), so these files are generated into site/ and committed:

  site/src/styles/tokens.css        — a copy of docs/design/tokens.css (made by tools/design/tokens.py)
  site/src/data/deck.json           — 78 cards in deck order: id, numeral, arcana, suit, image, slugs, EN/ES names
  site/src/data/meanings.en.json    — short meanings (keywords, upright, reversed) for the simple card pages
  site/src/data/meanings.es.json
  site/src/data/pairs.json          — language pairs of the 4.4a pages (url → switch_to) from hreflang.csv

Run from the repository root:
  python3 tools/site/sync_site_data.py          — write the files
  python3 tools/site/sync_site_data.py --check  — exit 1 if a file is missing or differs from its sources
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS = ROOT / "content/cards"
HREFLANG = ROOT / "docs/research/stage2/hreflang.csv"
TOKENS_CSS = ROOT / "docs/design/tokens.css"
SITE = ROOT / "site"
# the pages of spec 2026-11-19 stage 4.4a §3 that have a row in hreflang.csv (404 pages have none)
PAGE_ENTITIES = ("page:home", "tool:one-card", "tool:daily", "tool:yes-no", "tool:love")


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _load(name: str):
    return json.loads((CARDS / name).read_text(encoding="utf-8"))


def deck() -> list[dict]:
    names = {lang: {m["card_id"]: m["name"] for m in _load(f"meanings.{lang}.json")} for lang in ("en", "es")}
    cards = sorted(_load("deck.json"), key=lambda c: c["order"])
    return [{"card_id": c["card_id"], "numeral": c["numeral"], "arcana": c["arcana"], "suit": c["suit"],
             "image": c["image"], "slug_en": c["slug_en"], "slug_es": c["slug_es"],
             "name_en": names["en"][c["card_id"]], "name_es": names["es"][c["card_id"]]} for c in cards]


def meanings(lang: str) -> list[dict]:
    return [{"card_id": m["card_id"], "keywords": m["keywords"], "upright": m["upright"], "reversed": m["reversed"]}
            for m in _load(f"meanings.{lang}.json")]


def pairs() -> dict[str, str]:
    with open(HREFLANG, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["url"]: r["switch_to"] for r in rows
            if r["wave"] == "запуск" and (r["entity_id"] in PAGE_ENTITIES or r["entity_id"].startswith("card:"))}


def build() -> dict[Path, str]:
    return {
        SITE / "src/styles/tokens.css": TOKENS_CSS.read_text(encoding="utf-8"),
        SITE / "src/data/deck.json": _json(deck()),
        SITE / "src/data/meanings.en.json": _json(meanings("en")),
        SITE / "src/data/meanings.es.json": _json(meanings("es")),
        SITE / "src/data/pairs.json": _json(pairs()),
    }


def stale(files: dict[Path, str]) -> list[Path]:
    return [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]


def main(argv: list[str]) -> int:
    files = build()
    if "--check" in argv:
        bad = stale(files)
        for path in bad:
            print(f"out of date: {path.relative_to(ROOT)} (run python3 tools/site/sync_site_data.py)")
        return 1 if bad else 0
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Create `tools/site/check_dist.py`:

```python
"""After the site build: every page of spec 2026-11-19 stage 4.4a §3 exists in site/dist for EN and ES.

The pages are the language pairs of site/src/data/pairs.json (tools, 78 cards per language) plus the two 404 pages;
Astro writes one file per page (build.format "file"): / → index.html, /es → es.html, /cards/x → cards/x.html.

  python3 tools/site/check_dist.py   — prints "OK: 167 pages" or the missing files (exit 1)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
EXTRA = ("/404", "/es/404")
DATA_FILES = ("data/daily-en.json", "data/daily-es.json")


def expected_pages() -> list[str]:
    pairs = json.loads((SITE / "src/data/pairs.json").read_text(encoding="utf-8"))
    return sorted(set(pairs) | set(EXTRA))


def dist_file(path: str) -> str:
    return "index.html" if path == "/" else f"{path[1:]}.html"


def missing(dist: Path) -> list[str]:
    files = [dist_file(p) for p in expected_pages()] + list(DATA_FILES)
    return [f for f in files if not (dist / f).is_file()]


def main() -> int:
    dist = SITE / "dist"
    gone = missing(dist)
    for name in gone:
        print(f"missing: site/dist/{name}")
    if gone:
        return 1
    print(f"OK: {len(expected_pages())} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Generate the data**

Run: `cd ~/arcana-diary && python3 tools/site/sync_site_data.py`
Expected:

```
wrote site/src/styles/tokens.css
wrote site/src/data/deck.json
wrote site/src/data/meanings.en.json
wrote site/src/data/meanings.es.json
wrote site/src/data/pairs.json
```

- [ ] **Step 5: Run the tests**

Run: `cd ~/arcana-diary && api/.venv/bin/pytest -q tools/site && python3 tools/site/sync_site_data.py --check && echo current`
Expected: `7 passed`, then `current`.

- [ ] **Step 6: Configure Astro, TypeScript and Vitest**

Replace the whole of `site/astro.config.mjs` with:

```js
import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

// Addresses without a trailing slash (/one-card, /es/si-o-no): one HTML file per page, served by Caddy with
// try_files {path} {path}.html (deploy/Caddyfile).
export default defineConfig({
  site: 'https://arcanadiary.com',
  output: 'static',
  trailingSlash: 'never',
  build: { format: 'file' },
  integrations: [preact()],
});
```

Create `site/tsconfig.json`:

```json
{
  "extends": "astro/tsconfigs/strict",
  "include": [".astro/types.d.ts", "**/*"],
  "exclude": ["dist"],
  "compilerOptions": {
    "jsx": "react-jsx",
    "jsxImportSource": "preact"
  }
}
```

Create `site/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config';

// Logic without a screen lives in src/lib and src/i18n and is tested here in Node; islands stay thin.
export default defineConfig({
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
});
```

In `site/package.json`, replace:

```json
    "build": "astro build"
```

with:

```json
    "build": "astro build",
    "test": "vitest run"
```

- [ ] **Step 7: Build to check the configuration**

Run: `cd ~/arcana-diary && deploy/build-site.sh 2>&1 | tail -3 && ls site/dist`
Expected: `1 page(s) built`, `Complete!`; `site/dist` holds `_astro`, `cards`, `index.html` (the old stub), `robots.txt`.

- [ ] **Step 8: Commit**

```bash
cd ~/arcana-diary
git add tools/site site/src/styles/tokens.css site/src/data site/astro.config.mjs site/tsconfig.json \
  site/vitest.config.ts site/package.json
git commit -m "build(site): data from outside site/, Preact integration, page files, Vitest config

tools/site/sync_site_data.py copies the tokens and generates the deck, short meanings and language pairs into
site/src (the build container sees only site/); --check keeps them current.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Shared types, the deck and the routes

**Files:**
- Create: `site/src/lib/types.ts`, `site/src/lib/deck.ts`, `site/src/lib/routes.ts`
- Test: `site/src/lib/deck.test.ts`, `site/src/lib/routes.test.ts`

**Interfaces:**
- Consumes: `site/src/data/deck.json`, `site/src/data/pairs.json` (Task 2).
- Produces (`site/src/lib/types.ts`): `Lang = 'en' | 'es'`, `LANGS`, `Tool = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily'`, `Kind = 'one' | 'three' | 'yes_no' | 'card_page'`, `Position = 'past' | 'present' | 'path' | 'card'`, `Situation`, `SITUATIONS` (`single`, `relationship`, `after_breakup`, `complicated`), `DrawnCard {card_id, position, reversed, name}`, `Verdict {value, label}`, `ReadingCreated {id, lang, kind, cards, verdict, soft_line, remaining}`, `HelpLine`, `CrisisPayload {group: 'crisis', crisis: {title, body, not_saved, contacts_intro, emergency_line, fallback_contacts, closing}, helplines: {country, source, lines}}`, `FollowupCounts {followups_left, followup_attempts_left}`, `ReadingView` (owner view of `GET /api/readings/{id}`: `answer`, `answer_shown`, `status`, `retries_left`, counts, `followups: SavedFollowup[]`), `SavedFollowup {n, question, answer, soft_line}`, `DailyCard {day, card: {card_id, name, reversed}, text, source}`, `CreateBody {lang, kind, question?, topic?, situation?, card_id?, tz?, turnstile_token?}`.
- Produces (`deck.ts`): `DeckCard`, `DECK: readonly DeckCard[]` (78), `CARD_BACK = '/cards/back.svg'`, `CardWidth = 160 | 350 | 700`, `cardById(id) -> DeckCard | undefined`, `cardName(card, lang)`, `cardSlug(card, lang)`, `cardImage(card, width)`, `cardSrcset(card)`, `neighbors(card) -> {prev, next}`, `fallbackDailyCard(isoDay) -> DeckCard`.
- Produces (`routes.ts`): `PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'not_found'`, `HELP_URL = 'https://findahelpline.com'`, `NAV_KEYS = ['home','yes_no','love','daily']`, `pagePath(key, lang)`, `cardPath(card, lang)`, `langOf(path)`, `switchPath(path)`, `allPagePaths() -> string[]` (167), `distFile(path)`.

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/deck.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { CARD_BACK, DECK, cardById, cardImage, cardName, cardSlug, cardSrcset, fallbackDailyCard, neighbors } from './deck';

describe('deck', () => {
  it('has the 78 cards in deck order', () => {
    expect(DECK).toHaveLength(78);
    expect(DECK[0].card_id).toBe('major-00-fool');
    expect(new Set(DECK.map((c) => c.card_id)).size).toBe(78);
  });

  it('finds a card by id and names it in both languages', () => {
    const moon = cardById('major-18-moon')!;
    expect(cardName(moon, 'en')).toBe('The Moon');
    expect(cardName(moon, 'es')).toBe('La Luna');
    expect(cardSlug(moon, 'es')).toBe('la-luna');
    expect(moon.numeral).toBe('XVIII');
    expect(cardById('nope')).toBeUndefined();
  });

  it('builds the three picture sizes and the srcset', () => {
    const moon = cardById('major-18-moon')!;
    expect(cardImage(moon, 700)).toBe('/cards/the-moon.webp');
    expect(cardImage(moon, 160)).toBe('/cards/the-moon@160.webp');
    expect(cardSrcset(moon)).toBe('/cards/the-moon@160.webp 160w, /cards/the-moon@350.webp 350w, /cards/the-moon.webp 700w');
    expect(CARD_BACK).toBe('/cards/back.svg');
  });

  it('gives neighbours in deck order, wrapping at the ends', () => {
    const fool = DECK[0];
    expect(neighbors(fool).prev).toBe(DECK[77]);
    expect(neighbors(fool).next).toBe(DECK[1]);
    expect(neighbors(DECK[77]).next).toBe(fool);
  });

  it('picks the same fallback card of the day for the same day and changes with the day', () => {
    expect(fallbackDailyCard('2026-11-20')).toBe(fallbackDailyCard('2026-11-20'));
    const days = Array.from({ length: 30 }, (_, i) => `2026-12-${String(i + 1).padStart(2, '0')}`);
    expect(new Set(days.map((d) => fallbackDailyCard(d).card_id)).size).toBeGreaterThan(10);
  });
});
```

Create `site/src/lib/routes.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import pairs from '../data/pairs.json';
import { DECK } from './deck';
import { NAV_KEYS, allPagePaths, cardPath, distFile, langOf, pagePath, switchPath } from './routes';

describe('routes', () => {
  it('lists every page of spec §3 for both languages', () => {
    const paths = allPagePaths();
    expect(paths).toHaveLength(6 + 78 + 5 + 78);
    for (const p of ['/', '/one-card', '/yes-no', '/love', '/daily', '/404', '/es', '/es/si-o-no', '/es/amor',
      '/es/carta-del-dia', '/es/404', '/cards/the-moon', '/es/cartas/la-luna']) {
      expect(paths).toContain(p);
    }
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('puts the Spanish one-card mode on the home page section #una-carta', () => {
    expect(pagePath('one_card', 'es')).toBe('/es#una-carta');
    expect(pagePath('one_card', 'en')).toBe('/one-card');
  });

  it('switches language by the pairs of hreflang.csv', () => {
    expect(switchPath('/')).toBe('/es');
    expect(switchPath('/es')).toBe('/');
    expect(switchPath('/one-card')).toBe('/es');
    expect(switchPath('/es/si-o-no')).toBe('/yes-no');
    expect(switchPath('/daily')).toBe('/es/carta-del-dia');
    expect(switchPath('/cards/the-moon')).toBe('/es/cartas/la-luna');
    expect(switchPath('/es/cartas/el-loco')).toBe('/cards/the-fool');
    expect(switchPath('/404')).toBe('/es/404');
    expect(switchPath('/es/404')).toBe('/404');
  });

  it('has a pair for every page except the 404 pages, and every pair is a page', () => {
    const paths = allPagePaths();
    for (const p of paths) {
      if (!p.endsWith('/404')) expect(Object.keys(pairs)).toContain(p);
      expect(paths).toContain(switchPath(p));
    }
  });

  it('builds card addresses from the slugs', () => {
    const moon = DECK.find((c) => c.card_id === 'major-18-moon')!;
    expect(cardPath(moon, 'en')).toBe('/cards/the-moon');
    expect(cardPath(moon, 'es')).toBe('/es/cartas/la-luna');
  });

  it('knows the language of an address', () => {
    expect(langOf('/es')).toBe('es');
    expect(langOf('/es#una-carta')).toBe('es');
    expect(langOf('/es/cartas/la-luna')).toBe('es');
    expect(langOf('/espanol')).toBe('en');
    expect(langOf('/')).toBe('en');
  });

  it('has the four menu items of 4.4a in both languages', () => {
    expect(NAV_KEYS).toEqual(['home', 'yes_no', 'love', 'daily']);
    expect(NAV_KEYS.map((k) => pagePath(k, 'es'))).toEqual(['/es', '/es/si-o-no', '/es/amor', '/es/carta-del-dia']);
  });

  it('names the file the static build writes for each address', () => {
    expect(distFile('/')).toBe('index.html');
    expect(distFile('/one-card')).toBe('one-card.html');
    expect(distFile('/es')).toBe('es.html');
    expect(distFile('/es/404')).toBe('es/404.html');
    expect(distFile('/es/cartas/la-luna')).toBe('es/cartas/la-luna.html');
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/deck.test.ts src/lib/routes.test.ts`
Expected: FAIL — `Error: Cannot find module './deck' imported from /app/src/lib/deck.test.ts` (and `./routes`).

- [ ] **Step 3: Write the modules**

Create `site/src/lib/types.ts`:

```ts
// Shapes shared by the site's modules: page language, tools, and what the API (api/README.md) sends back.

export type Lang = 'en' | 'es';
export const LANGS: readonly Lang[] = ['en', 'es'];

/** The `tool` of docs/design/analytics-events.md that the 4.4a pages use. */
export type Tool = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily';

/** `kind` of POST /api/readings. */
export type Kind = 'one' | 'three' | 'yes_no' | 'card_page';

export type Position = 'past' | 'present' | 'path' | 'card';

export type Situation = 'single' | 'relationship' | 'after_breakup' | 'complicated';
export const SITUATIONS: readonly Situation[] = ['single', 'relationship', 'after_breakup', 'complicated'];

export interface DrawnCard {
  card_id: string;
  position: Position;
  reversed: boolean;
  name: string;
}

export interface Verdict {
  value: 'yes' | 'no' | 'unclear';
  label: string;
}

/** 201 of POST /api/readings. */
export interface ReadingCreated {
  id: string;
  lang: Lang;
  kind: Kind;
  cards: DrawnCard[];
  verdict: Verdict | null;
  soft_line: string | null;
  remaining: number;
}

export interface HelpLine {
  name: string;
  number?: string;
  sms?: string;
  url?: string;
  note?: string;
  channels: string[];
  hours: string | null;
  topic: string;
  purpose: string;
}

/** 200 {"group": "crisis", ...} of POST /api/readings and of a follow-up, and the `crisis` stream event. */
export interface CrisisPayload {
  group: 'crisis';
  crisis: {
    title: string;
    body: string;
    not_saved: string;
    contacts_intro: string;
    emergency_line: string;
    fallback_contacts: string;
    closing: string;
  };
  helplines: { country: string | null; source: string; lines: HelpLine[] };
}

export interface FollowupCounts {
  followups_left: number;
  followup_attempts_left: number;
}

/** GET /api/readings/{id} for its owner (the fields 4.4a uses). */
export interface ReadingView extends FollowupCounts {
  id: string;
  kind: Kind;
  cards: DrawnCard[];
  verdict: Verdict | null;
  soft_line: string | null;
  answer: Record<string, string> | null;
  answer_shown: 'model' | 'fallback' | 'crisis' | null;
  status: 'pending' | 'streaming' | 'done';
  retries_left: number;
  followups: SavedFollowup[];
}

/** A follow-up with its answer as GET /api/readings/{id} keeps it (answered ones only). */
export interface SavedFollowup {
  n: number;
  question: string;
  answer: string | null;
  soft_line: string | null;
}

/** 200 of GET /api/daily. */
export interface DailyCard {
  day: string;
  card: { card_id: string; name: string; reversed: boolean };
  text: string;
  source: 'cache' | 'fallback';
}

/** Body of POST /api/readings. */
export interface CreateBody {
  lang: Lang;
  kind: Kind;
  question?: string;
  topic?: 'love';
  situation?: Situation;
  card_id?: string;
  tz?: string;
  turnstile_token?: string;
}
```

Create `site/src/lib/deck.ts`:

```ts
// The 78 cards for the screens: names, slugs and pictures (site/src/data/deck.json, made by
// tools/site/sync_site_data.py from content/cards). Pictures: site/public/cards/<image>.webp (700 × 1200),
// <image>@350.webp, <image>@160.webp; the back is back.svg.
import deckData from '../data/deck.json';
import type { Lang } from './types';

export interface DeckCard {
  card_id: string;
  numeral: string;
  arcana: 'major' | 'minor';
  suit: string | null;
  image: string;
  slug_en: string;
  slug_es: string;
  name_en: string;
  name_es: string;
}

export const DECK: readonly DeckCard[] = deckData as DeckCard[];
export const CARD_BACK = '/cards/back.svg';
export type CardWidth = 160 | 350 | 700;

const BY_ID = new Map(DECK.map((card) => [card.card_id, card]));

export function cardById(cardId: string): DeckCard | undefined {
  return BY_ID.get(cardId);
}

export function cardName(card: DeckCard, lang: Lang): string {
  return lang === 'en' ? card.name_en : card.name_es;
}

export function cardSlug(card: DeckCard, lang: Lang): string {
  return lang === 'en' ? card.slug_en : card.slug_es;
}

export function cardImage(card: DeckCard, width: CardWidth): string {
  return width === 700 ? `/cards/${card.image}.webp` : `/cards/${card.image}@${width}.webp`;
}

export function cardSrcset(card: DeckCard): string {
  return `${cardImage(card, 160)} 160w, ${cardImage(card, 350)} 350w, ${cardImage(card, 700)} 700w`;
}

/** Previous and next card in deck order, wrapping at both ends. */
export function neighbors(card: DeckCard): { prev: DeckCard; next: DeckCard } {
  const i = DECK.indexOf(card);
  return { prev: DECK[(i + DECK.length - 1) % DECK.length], next: DECK[(i + 1) % DECK.length] };
}

/** When GET /api/daily answers 503 the site picks the day's card itself: the same card for everyone on that
 * local day (YYYY-MM-DD), upright, with its meaning from the card base. */
export function fallbackDailyCard(isoDay: string): DeckCard {
  let hash = 0;
  for (const ch of isoDay) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return DECK[hash % DECK.length];
}
```

Create `site/src/lib/routes.ts`:

```ts
// Addresses of the 4.4a pages (spec 2026-11-19 stage 4.4a §3) and their language pairs
// (site/src/data/pairs.json, from docs/research/stage2/hreflang.csv via tools/site/sync_site_data.py).
import pairsData from '../data/pairs.json';
import { DECK, cardSlug, type DeckCard } from './deck';
import type { Lang } from './types';

export type PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'not_found';

/** Where the 429 / 403 / 503 messages and the footer send people who need help now (§10.8 of spec 4.2). */
export const HELP_URL = 'https://findahelpline.com';

const PAIRS: Readonly<Record<string, string>> = pairsData;
const NOT_FOUND_PAIRS: Readonly<Record<string, string>> = { '/404': '/es/404', '/es/404': '/404' };

const PAGE_PATHS: Record<Lang, Record<PageKey, string>> = {
  en: { home: '/', one_card: '/one-card', yes_no: '/yes-no', love: '/love', daily: '/daily', not_found: '/404' },
  // Spanish has no one-card page: the one-card mode is the #una-carta section of the home page (stage 2 map)
  es: {
    home: '/es', one_card: '/es#una-carta', yes_no: '/es/si-o-no', love: '/es/amor', daily: '/es/carta-del-dia',
    not_found: '/es/404',
  },
};

/** The menu (stage 2 structure, design screens 11c/11d). "Card Meanings" and the diary arrive with stages 6 and
 * 4.4b; until then the menu has these four items. */
export const NAV_KEYS: readonly PageKey[] = ['home', 'yes_no', 'love', 'daily'];

export function pagePath(key: PageKey, lang: Lang): string {
  return PAGE_PATHS[lang][key];
}

export function cardPath(card: DeckCard, lang: Lang): string {
  return lang === 'en' ? `/cards/${cardSlug(card, 'en')}` : `/es/cartas/${cardSlug(card, 'es')}`;
}

export function langOf(path: string): Lang {
  return path === '/es' || path.startsWith('/es/') || path.startsWith('/es#') ? 'es' : 'en';
}

/** The other language's address for the language switch; a page without a pair goes to that language's home. */
export function switchPath(path: string): string {
  const pair = PAIRS[path] ?? NOT_FOUND_PAIRS[path];
  if (pair) return pair;
  return langOf(path) === 'en' ? '/es' : '/';
}

/** Every page the build must produce, both languages: tools, 78 card pages each, 404. */
export function allPagePaths(): string[] {
  const tools = (lang: Lang) =>
    (Object.keys(PAGE_PATHS[lang]) as PageKey[]).map((key) => PAGE_PATHS[lang][key]).filter((p) => !p.includes('#'));
  return [...tools('en'), ...DECK.map((c) => cardPath(c, 'en')), ...tools('es'), ...DECK.map((c) => cardPath(c, 'es'))];
}

/** The file Astro writes for a path with build.format "file" (served by Caddy's try_files {path}.html). */
export function distFile(path: string): string {
  return path === '/' ? 'index.html' : `${path.slice(1)}.html`;
}
```

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/deck.test.ts src/lib/routes.test.ts`
Expected: `Test Files  2 passed (2)`, `Tests  13 passed (13)`.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add site/src/lib/types.ts site/src/lib/deck.ts site/src/lib/routes.ts site/src/lib/deck.test.ts site/src/lib/routes.test.ts
git commit -m "feat(site): shared types, the deck and the 4.4a routes with language pairs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Dictionaries EN / ES

**Files:**
- Create: `site/src/i18n/en.ts`, `site/src/i18n/es.ts`, `site/src/i18n/index.ts`
- Test: `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `Lang` from `site/src/lib/types.ts`.
- Produces: `en` (156 keys), `DictKey = keyof typeof en`, `Dict = Record<DictKey, string>`, `es: Dict`, `enDrafts` (57 keys), `esDrafts` (115 keys); from `site/src/i18n/index.ts`: `DICTS`, `DRAFTS`, `t(lang) -> Dict`, `fill(template, vars) -> string` (`{name}` placeholders; an unknown one stays), `placeholders(template) -> string[]`, re-exported types `Dict`, `DictKey`. Later tasks use these keys by name, e.g. `drawThree`, `drawOne`, `drawLove`, `drawForQuestion`, `questionLabel`, `yesNoLabel`, `*Placeholder`, `shuffling`, `dealtThree`, `dealtOne`, `writing`, `readingReady`, `restoring`, `streamLost`, `followup*` (incl. `followupReady`), `err*` (incl. `errDayCap`), `plus*` (incl. `plusNotNow`), `crisis*`, `fullMeaning`, `backTo`, `closeBackTo`, `notGuarantee`.

- [ ] **Step 1: Write the failing test**

Create `site/src/i18n/i18n.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { DICTS, DRAFTS, fill, placeholders, t } from './index';

const keys = (lang: 'en' | 'es') => Object.keys(DICTS[lang]).sort();

describe('dictionaries', () => {
  it('have the same keys in English and Spanish', () => {
    expect(keys('es')).toEqual(keys('en'));
    expect(keys('en').length).toBe(156);
  });

  it('have no empty strings', () => {
    for (const lang of ['en', 'es'] as const) {
      for (const [key, value] of Object.entries(DICTS[lang])) expect(value.trim(), `${lang}.${key}`).not.toBe('');
    }
  });

  it('use the same placeholders in both languages', () => {
    for (const key of keys('en')) {
      const k = key as keyof typeof DICTS.en;
      expect(placeholders(DICTS.es[k]), key).toEqual(placeholders(DICTS.en[k]));
    }
  });

  it('mark drafts only with real keys, each once', () => {
    for (const lang of ['en', 'es'] as const) {
      expect(new Set(DRAFTS[lang]).size).toBe(DRAFTS[lang].length);
      for (const key of DRAFTS[lang]) expect(keys(lang)).toContain(key);
    }
    expect(DRAFTS.en.length).toBe(57);
    expect(DRAFTS.es.length).toBe(115);
  });

  it('keep the prototype copy', () => {
    expect(t('en').homeH1).toBe('Ask the cards.');
    expect(t('en').drawThree).toBe('Draw three cards');
    expect(t('es').drawThree).toBe('Saca tres cartas');
    expect(t('es').homeH1).toBe('Pregunta a las cartas.');
    expect(t('en').disclaimer).toBe('Tarot is a way to think about your question, not a guarantee.');
    expect(t('es').disclaimer).toBe('El tarot es una forma de reflexionar, no una garantía.');
    expect(t('es').whyPrefix).toBe('Por qué:');
  });

  it('never call a reading a forecast (design decision 13.11.2026)', () => {
    for (const lang of ['en', 'es'] as const) {
      for (const value of Object.values(DICTS[lang])) expect(value.toLowerCase()).not.toMatch(/forecast|pronóstico|predic/);
    }
  });
});

describe('fill', () => {
  it('puts values into placeholders and leaves unknown ones', () => {
    expect(fill('{name} — full meaning', { name: 'The Moon' })).toBe('The Moon — full meaning');
    expect(fill('{n} left of {m}', { n: 2 })).toBe('2 left of {m}');
    expect(placeholders('{a} {b} {a}')).toEqual(['a', 'b']);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/i18n`
Expected: FAIL — `Error: Cannot find module './index' imported from /app/src/i18n/i18n.test.ts`.

- [ ] **Step 3: Write the dictionaries**

Create `site/src/i18n/en.ts`:

```ts
// English interface strings. Source: the stage 3 prototypes (design canvas, screens 1–13) and the design system.
// Keys in `enDrafts` are not in the prototypes: draft — review with stage 5 texts.
// Every answer, card name and verdict label comes from the API or the card base, not from here.

export const en = {
  siteName: 'Arcana Diary',
  skipToContent: 'Skip to content',
  menuOpen: 'Open menu',
  menuClose: 'Close menu',
  navLabel: 'Main',
  navHome: 'Reading',
  navYesNo: 'Yes or No',
  navLove: 'Love',
  navDaily: 'Card of the Day',
  langLabel: 'Language',
  footerLabel: 'Footer',
  footerOneCard: 'One card',
  disclaimer: 'Tarot is a way to think about your question, not a guarantee.',
  cardArtCredit: 'Card art: Rider–Waite–Smith deck, 1909 (public domain).',
  helpLead: 'Need to talk to someone now?',
  helpLink: 'Free, confidential help lines',

  questionLabel: 'Your question — optional',
  freeNoSignup: 'Free · no sign-up',
  countGroupLabel: 'Number of cards',
  oneCardChip: '1 card',
  threeCardsChip: '3 cards',
  drawThree: 'Draw three cards',
  drawOne: 'Draw a card',

  homeTitle: 'Free tarot reading — Arcana Diary',
  homeEyebrow: 'Free tarot reading',
  homeH1: 'Ask the cards.',
  homeLead: 'One question, three cards and an honest reading. No sign-up.',
  homePlaceholder: 'e.g. Will this move be good for me?',
  otherWays: 'Other ways to ask',
  fmtOneCard: 'One card',
  fmtOneCardHint: 'A single card for right now',
  fmtYesNo: 'Yes or No',
  fmtYesNoHint: 'A clear answer, and why',
  fmtLove: 'Love',
  fmtLoveHint: 'For your relationship or crush',
  fmtDaily: 'Card of the Day',
  fmtDailyHint: 'One card for today, every morning',
  dailyTileEyebrow: 'Card of the day',
  dailyTileText: 'Your card for today is waiting',
  dailyTileLink: 'Turn it over',
  learnTitle: 'Learn the cards',
  learnLead: 'What each of the 78 cards means, upright and reversed.',
  howTitle: 'How a reading works',
  howStep1: 'Ask anything about your life — or just draw.',
  howStep2: 'The reader explains each card in plain words.',
  howStep3: 'Ask up to two follow-up questions, free.',

  oneCardTitle: 'One card tarot — Arcana Diary',
  oneCardEyebrow: 'One card',
  oneCardH1: 'A single card for right now.',
  oneCardLead: 'One card, read for your question — a quick look when you need it.',
  oneCardPlaceholder: 'e.g. What should I focus on today?',

  yesNoTitle: 'Yes or No tarot — Arcana Diary',
  yesNoEyebrow: 'Yes or No tarot',
  yesNoH1: 'A clear answer, and why.',
  yesNoLead: 'Ask a question that can be answered yes or no. The card gives a lean — the choice stays yours.',
  yesNoLabel: 'Your yes-or-no question — optional',
  yesNoPlaceholder: 'e.g. Should I apply for this job?',

  loveTitle: 'Love tarot — Arcana Diary',
  loveEyebrow: 'Love tarot',
  loveH1: 'What does your heart need?',
  loveLead: 'Three cards about you and your relationship: where you stand, what blocks you, and a next step.',
  situationLabel: 'Your situation — optional',
  sitSingle: 'Single',
  sitRelationship: 'In a relationship',
  sitAfterBreakup: 'After a breakup',
  sitComplicated: "It's complicated",
  lovePlaceholder: 'e.g. How can I feel closer in my relationship?',
  drawLove: 'Draw for love',
  loveNote: 'The cards talk about you and what you can do — never what another person thinks or feels.',

  dailyTitle: 'Card of the Day — Arcana Diary',
  dailyEyebrow: 'Card of the Day',
  dailyH1: 'Your card for today',
  dailyTap: 'Tap to turn your card',
  dailyNote: 'One card a day · a new one tomorrow morning',
  dailyLoading: 'Turning your card…',
  dailyFallbackNote: "We couldn't reach your own card right now, so here is today's card from our card base.",
  dailyError: "Your card can't be turned right now. Please try again in a moment.",
  fullMeaning: '{name} — full meaning',
  reversedTag: 'Reversed',

  cardTitle: '{name} tarot card meaning — Arcana Diary',
  cardEyebrowMajor: 'Major Arcana · {numeral}',
  cardEyebrowMinor: 'Minor Arcana',
  uprightTitle: 'Upright meaning',
  reversedTitle: '{name} reversed',
  cardDrawHeading: 'Have a question of your own?',
  cardDrawLead: 'The night room opens right here — free, no sign-up.',
  cardPlaceholder: 'e.g. What should I pay attention to?',
  drawForQuestion: 'Draw a card for your question',
  prevCard: '← Previous',
  nextCard: 'Next →',
  cardNav: 'Keep exploring',

  notFoundTitle: 'Page not found — Arcana Diary',
  notFoundEyebrow: 'Error 404',
  notFoundH1: 'This card fell out of the deck',
  notFoundLead: "The page you're looking for isn't here. Try one of these instead.",
  notFoundNav: 'Popular',
  notFoundReading: 'Get a free reading',

  close: 'Close',
  closeBackTo: 'Close and go back to {name}',
  shuffling: 'Shuffling the deck…',
  dealtThree: 'Your three cards are on the table. They turn over one by one.',
  dealtOne: 'Your card is on the table.',
  writing: 'Your reader is writing…',
  readingReady: 'Your reading is ready.',
  noQuestionOne: 'Your card for right now',
  noQuestionThree: 'Your three cards for right now',
  posPast: 'Past',
  posPresent: 'Present',
  posPath: 'Next step',
  cardAlt: '{name}, upright',
  cardAltReversed: '{name}, reversed',
  stepLabel: 'One step to take',
  whyPrefix: 'Why:',
  moreAbout: 'More about these cards',
  askAnother: 'Ask another question',
  backTo: 'Back to {name}',
  notGuarantee: 'A reading is a way to think things through, not a guarantee.',
  retry: 'Try again',
  restoring: 'The connection dropped. Getting your reading back…',
  streamLost: "We couldn't get your reading back. Check your connection and try again.",

  followupLabel: 'Ask a follow-up question',
  followupPlaceholder: 'e.g. What can I do this week?',
  followupSend: 'Ask',
  followupFreeLeft: 'Free follow-up questions left: {n}',
  followupPaidWarning: 'This question will use 1 of your readings for today ({n} left).',
  followupConfirm: 'Use 1 reading and ask',
  followupCancel: 'Not now',
  followupUsedReading: 'This question used 1 of your readings for today.',
  followupNone: "You've asked all the follow-up questions this reading can take.",
  followupYouAsked: 'You asked',
  followupReady: 'The answer to your question is ready.',

  errBusy: 'Too many requests right now. Please wait a minute and try again.',
  errDayCap: 'This connection has made a lot of readings today. Please come back tomorrow.',
  errTurnstile: "We couldn't check that this is a person and not a robot. Please try again.",
  errUnavailable: 'The service is unavailable right now. Please try again in a few minutes.',
  errNetwork: 'You seem to be offline. Check your connection and try again.',
  errStage: 'Your session on this preview site has expired. Reload the page to continue.',
  errGone: 'This reading is no longer available.',
  errOther: 'Something went wrong. Please try again.',

  plusTitle: "That's today's free readings",
  plusLead: 'You can draw again tomorrow, and your Card of the Day is always free.',
  plusGives: 'What Plus gives you',
  plusBenefit1: 'Unlimited readings, any day',
  plusBenefit2: 'Longer spreads, like the Celtic Cross',
  plusBenefit3: 'Your whole diary, with no limit',
  plusEmailLabel: "Your e-mail — we'll write once, when Plus opens",
  plusEmailPlaceholder: 'e.g. you@example.com',
  plusNotify: 'Tell me when it opens',
  plusDone: "Thank you — we'll write when Plus opens.",
  plusNotNow: 'Not now',
  plusEmailError: 'Please check the e-mail address and try again.',
  plusDaily: 'Open your free Card of the Day',

  crisisCall: 'Call {number}',
  crisisText: 'Text {sms}',
  crisisHours: 'Hours: {hours}',
  crisisWeb: 'Open {name}',
};

export type DictKey = keyof typeof en;
export type Dict = Record<DictKey, string>;

// draft — review with stage 5 texts
export const enDrafts: readonly DictKey[] = [
  'skipToContent', 'langLabel', 'helpLead', 'helpLink', 'freeNoSignup', 'homeTitle', 'dailyTileText', 'learnLead',
  'howStep3', 'oneCardTitle', 'oneCardEyebrow', 'oneCardH1', 'oneCardLead', 'oneCardPlaceholder', 'yesNoTitle',
  'loveTitle', 'dailyTitle', 'dailyLoading', 'dailyFallbackNote', 'dailyError', 'cardTitle', 'cardEyebrowMinor',
  'notFoundTitle', 'dealtOne', 'readingReady', 'noQuestionThree', 'stepLabel', 'restoring', 'streamLost',
  'followupLabel', 'followupPlaceholder', 'followupSend', 'followupFreeLeft', 'followupPaidWarning',
  'followupConfirm', 'followupCancel', 'followupUsedReading', 'followupNone', 'followupYouAsked', 'errBusy',
  'errTurnstile', 'errUnavailable', 'errNetwork', 'errStage', 'errGone', 'errOther', 'plusEmailLabel',
  'plusEmailPlaceholder', 'plusNotify', 'plusDone', 'plusEmailError', 'crisisCall', 'crisisText', 'crisisHours',
  'crisisWeb', 'errDayCap', 'followupReady',
];
```

Create `site/src/i18n/es.ts`:

```ts
// Spanish (Mexico, tú) interface strings. Source: the stage 3 prototypes (screens 11d, 12a–12d) and the design
// system. Keys in `esDrafts` are not in the prototypes: draft — review with stage 5 texts. No gendered forms for
// the person (design review); a card name is followed by "carta invertida", which agrees with every card.
import type { Dict, DictKey } from './en';

export const es: Dict = {
  siteName: 'Arcana Diary',
  skipToContent: 'Ir al contenido',
  menuOpen: 'Abrir menú',
  menuClose: 'Cerrar menú',
  navLabel: 'Principal',
  navHome: 'Tirada',
  navYesNo: 'Sí o no',
  navLove: 'Amor',
  navDaily: 'Carta del día',
  langLabel: 'Idioma',
  footerLabel: 'Pie de página',
  footerOneCard: 'Una carta',
  disclaimer: 'El tarot es una forma de reflexionar, no una garantía.',
  cardArtCredit: 'Ilustración: baraja Rider–Waite–Smith, 1909 (dominio público).',
  helpLead: '¿Necesitas hablar con alguien ahora?',
  helpLink: 'Líneas de ayuda gratuitas y confidenciales',

  questionLabel: 'Tu pregunta — opcional',
  freeNoSignup: 'Gratis · sin registro',
  countGroupLabel: 'Número de cartas',
  oneCardChip: '1 carta',
  threeCardsChip: '3 cartas',
  drawThree: 'Saca tres cartas',
  drawOne: 'Saca una carta',

  homeTitle: 'Tarot gratis — Arcana Diary',
  homeEyebrow: 'Tarot gratis',
  homeH1: 'Pregunta a las cartas.',
  homeLead: 'Una pregunta, tres cartas y una lectura honesta. Sin registro.',
  homePlaceholder: 'p. ej. ¿Me conviene este cambio?',
  otherWays: 'Otras formas de preguntar',
  fmtOneCard: 'Una carta',
  fmtOneCardHint: 'Una sola carta para este momento',
  fmtYesNo: 'Sí o no',
  fmtYesNoHint: 'Una respuesta clara, y por qué',
  fmtLove: 'Tarot del amor',
  fmtLoveHint: 'Para tu relación o tu corazón',
  fmtDaily: 'Carta del día',
  fmtDailyHint: 'Una carta para hoy, cada mañana',
  dailyTileEyebrow: 'Carta del día',
  dailyTileText: 'Tu carta de hoy te espera',
  dailyTileLink: 'Dale la vuelta',
  learnTitle: 'Significado de las cartas',
  learnLead: 'Qué significa cada una de las 78 cartas, al derecho y al revés.',
  howTitle: 'Cómo funciona una lectura',
  howStep1: 'Pregunta lo que quieras sobre tu vida, o solo saca las cartas.',
  howStep2: 'Cada carta se explica con palabras sencillas.',
  howStep3: 'Haz hasta dos preguntas de seguimiento, gratis.',

  oneCardTitle: 'Una carta — Arcana Diary',
  oneCardEyebrow: 'Una carta',
  oneCardH1: 'Una sola carta para este momento.',
  oneCardLead: 'Una carta, leída para tu pregunta: una mirada rápida cuando la necesitas.',
  oneCardPlaceholder: 'p. ej. ¿En qué me conviene enfocarme hoy?',

  yesNoTitle: 'Tarot sí o no — Arcana Diary',
  yesNoEyebrow: 'Tarot sí o no',
  yesNoH1: 'Una respuesta clara, y por qué.',
  yesNoLead: 'Haz una pregunta que se pueda responder con sí o no. La carta muestra una inclinación; la decisión sigue siendo tuya.',
  yesNoLabel: 'Tu pregunta de sí o no — opcional',
  yesNoPlaceholder: 'p. ej. ¿Debo aceptar esta oferta?',

  loveTitle: 'Tarot del amor — Arcana Diary',
  loveEyebrow: 'Tarot del amor',
  loveH1: '¿Qué necesita tu corazón?',
  loveLead: 'Tres cartas sobre ti y tu relación: dónde estás, qué te frena y un siguiente paso.',
  situationLabel: 'Tu situación — opcional',
  sitSingle: 'Sin pareja',
  sitRelationship: 'En pareja',
  sitAfterBreakup: 'Después de una ruptura',
  sitComplicated: 'Es complicado',
  lovePlaceholder: 'p. ej. ¿Cómo puedo sentir más cercanía en mi relación?',
  drawLove: 'Saca tus cartas del amor',
  loveNote: 'Las cartas hablan de ti y de lo que puedes hacer, nunca de lo que otra persona piensa o siente.',

  dailyTitle: 'Carta del día — Arcana Diary',
  dailyEyebrow: 'Carta del día',
  dailyH1: 'Tu carta de hoy',
  dailyTap: 'Toca para voltear tu carta',
  dailyNote: 'Una carta al día · otra nueva mañana',
  dailyLoading: 'Volteando tu carta…',
  dailyFallbackNote: 'Ahora mismo no pudimos traer tu carta personal; aquí tienes la carta de hoy según nuestra base.',
  dailyError: 'Ahora mismo no se puede voltear tu carta. Inténtalo de nuevo en un momento.',
  fullMeaning: '{name} — significado completo',
  reversedTag: 'Invertida',

  cardTitle: '{name}: significado en el tarot — Arcana Diary',
  cardEyebrowMajor: 'Arcanos mayores · {numeral}',
  cardEyebrowMinor: 'Arcanos menores',
  uprightTitle: 'Significado',
  reversedTitle: '{name}, carta invertida',
  cardDrawHeading: '¿Tienes tu propia pregunta?',
  cardDrawLead: 'La sala nocturna se abre aquí mismo, gratis y sin registro.',
  cardPlaceholder: 'p. ej. ¿A qué debo prestar atención?',
  drawForQuestion: 'Saca una carta para tu pregunta',
  prevCard: '← Anterior',
  nextCard: 'Siguiente →',
  cardNav: 'Sigue explorando',

  notFoundTitle: 'Página no encontrada — Arcana Diary',
  notFoundEyebrow: 'Error 404',
  notFoundH1: 'Esta carta se cayó de la baraja',
  notFoundLead: 'La página que buscas no está aquí. Prueba con una de estas.',
  notFoundNav: 'Populares',
  notFoundReading: 'Haz una tirada gratis',

  close: 'Cerrar',
  closeBackTo: 'Cerrar y volver a {name}',
  shuffling: 'Barajando las cartas…',
  dealtThree: 'Tus tres cartas están sobre la mesa. Se voltean una por una.',
  dealtOne: 'Tu carta está sobre la mesa.',
  writing: 'Tu lectura se está escribiendo…',
  readingReady: 'Tu lectura está lista.',
  noQuestionOne: 'Tu carta para este momento',
  noQuestionThree: 'Tus tres cartas para este momento',
  posPast: 'Pasado',
  posPresent: 'Presente',
  posPath: 'Siguiente paso',
  cardAlt: '{name}, al derecho',
  cardAltReversed: '{name}, carta invertida',
  stepLabel: 'Siguiente paso',
  whyPrefix: 'Por qué:',
  moreAbout: 'Más sobre estas cartas',
  askAnother: 'Hacer otra pregunta',
  backTo: 'Volver a {name}',
  notGuarantee: 'Una lectura es una forma de pensar las cosas, no una garantía.',
  retry: 'Intentar de nuevo',
  restoring: 'Se cortó la conexión. Estamos recuperando tu lectura…',
  streamLost: 'No pudimos recuperar tu lectura. Revisa tu conexión e inténtalo de nuevo.',

  followupLabel: 'Haz una pregunta de seguimiento',
  followupPlaceholder: 'p. ej. ¿Qué puedo hacer esta semana?',
  followupSend: 'Preguntar',
  followupFreeLeft: 'Preguntas de seguimiento gratis que te quedan: {n}',
  followupPaidWarning: 'Esta pregunta usará 1 de tus lecturas de hoy (te quedan {n}).',
  followupConfirm: 'Usar 1 lectura y preguntar',
  followupCancel: 'Ahora no',
  followupUsedReading: 'Esta pregunta usó 1 de tus lecturas de hoy.',
  followupNone: 'Ya hiciste todas las preguntas de seguimiento que admite esta lectura.',
  followupYouAsked: 'Preguntaste',
  followupReady: 'La respuesta a tu pregunta está lista.',

  errBusy: 'Hay demasiadas solicitudes en este momento. Espera un minuto e inténtalo de nuevo.',
  errDayCap: 'Desde esta conexión se hicieron muchas lecturas hoy. Vuelve mañana.',
  errTurnstile: 'No pudimos comprobar que eres una persona y no un robot. Inténtalo de nuevo.',
  errUnavailable: 'El servicio no está disponible en este momento. Inténtalo de nuevo en unos minutos.',
  errNetwork: 'Parece que no tienes conexión. Revísala e inténtalo de nuevo.',
  errStage: 'Tu sesión en este sitio de prueba caducó. Vuelve a cargar la página para seguir.',
  errGone: 'Esta lectura ya no está disponible.',
  errOther: 'Algo salió mal. Inténtalo de nuevo.',

  plusTitle: 'Ya usaste tus lecturas gratis de hoy',
  plusLead: 'Mañana puedes volver a sacar cartas, y tu Carta del día siempre es gratis.',
  plusGives: 'Qué te da Plus',
  plusBenefit1: 'Lecturas sin límite, cualquier día',
  plusBenefit2: 'Tiradas más largas, como la Cruz Celta',
  plusBenefit3: 'Todo tu diario, sin límite',
  plusEmailLabel: 'Tu correo: te escribimos una sola vez, cuando abra Plus',
  plusEmailPlaceholder: 'p. ej. tu@ejemplo.com',
  plusNotify: 'Avísame cuando abra',
  plusDone: 'Gracias: te escribiremos cuando abra Plus.',
  plusNotNow: 'Ahora no',
  plusEmailError: 'Revisa la dirección de correo e inténtalo de nuevo.',
  plusDaily: 'Abre tu Carta del día gratis',

  crisisCall: 'Llama al {number}',
  crisisText: 'Envía {sms}',
  crisisHours: 'Horario: {hours}',
  crisisWeb: 'Abrir {name}',
};

// draft — review with stage 5 texts
export const esDrafts: readonly DictKey[] = [
  'skipToContent', 'langLabel', 'footerLabel', 'footerOneCard', 'helpLead', 'helpLink', 'freeNoSignup',
  'countGroupLabel', 'homeTitle', 'fmtOneCard', 'fmtOneCardHint', 'dailyTileText', 'learnLead', 'howTitle',
  'howStep1', 'howStep2', 'howStep3', 'oneCardTitle', 'oneCardEyebrow', 'oneCardH1', 'oneCardLead',
  'oneCardPlaceholder', 'yesNoTitle', 'yesNoEyebrow', 'yesNoH1', 'yesNoLead', 'yesNoLabel', 'yesNoPlaceholder',
  'loveTitle', 'loveEyebrow', 'loveH1', 'loveLead', 'situationLabel', 'sitSingle', 'sitRelationship',
  'sitAfterBreakup', 'sitComplicated', 'lovePlaceholder', 'drawLove', 'loveNote', 'dailyTitle', 'dailyEyebrow',
  'dailyH1', 'dailyTap', 'dailyNote', 'dailyLoading', 'dailyFallbackNote', 'dailyError',
  'reversedTag', 'cardTitle', 'cardEyebrowMajor', 'cardEyebrowMinor', 'reversedTitle', 'cardDrawLead',
  'cardPlaceholder', 'prevCard', 'nextCard', 'cardNav', 'notFoundTitle', 'notFoundH1', 'notFoundLead',
  'notFoundNav', 'notFoundReading', 'closeBackTo', 'shuffling', 'dealtThree',
  'dealtOne', 'writing', 'readingReady', 'noQuestionOne', 'noQuestionThree', 'cardAlt', 'cardAltReversed',
  'moreAbout', 'backTo', 'notGuarantee', 'retry', 'restoring', 'streamLost', 'followupLabel',
  'followupPlaceholder', 'followupSend', 'followupFreeLeft', 'followupPaidWarning', 'followupConfirm',
  'followupCancel', 'followupUsedReading', 'followupNone', 'followupYouAsked', 'errBusy', 'errTurnstile',
  'errUnavailable', 'errNetwork', 'errStage', 'errGone', 'errOther', 'plusTitle', 'plusLead', 'plusGives',
  'plusBenefit1', 'plusBenefit2', 'plusBenefit3', 'plusEmailLabel', 'plusEmailPlaceholder', 'plusNotify',
  'plusDone', 'plusEmailError', 'plusDaily', 'crisisCall', 'crisisText', 'crisisHours', 'crisisWeb',
  'errDayCap', 'followupReady', 'plusNotNow',
];
```

Create `site/src/i18n/index.ts`:

```ts
// One dictionary per language (spec 4.4a §7). Pages and islands take strings only from here.
import type { Lang } from '../lib/types';
import { en, enDrafts, type Dict, type DictKey } from './en';
import { es, esDrafts } from './es';

export type { Dict, DictKey };

export const DICTS: Readonly<Record<Lang, Dict>> = { en, es };
export const DRAFTS: Readonly<Record<Lang, readonly DictKey[]>> = { en: enDrafts, es: esDrafts };

export function t(lang: Lang): Dict {
  return DICTS[lang];
}

/** "{name} — full meaning" + {name: "The Moon"}; an unknown placeholder stays as it is. */
export function fill(template: string, vars: Readonly<Record<string, string | number>>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => (key in vars ? String(vars[key]) : match));
}

export function placeholders(template: string): string[] {
  return [...new Set([...template.matchAll(/\{(\w+)\}/g)].map((m) => m[1]))].sort();
}
```

- [ ] **Step 4: Run the test**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/i18n`
Expected: `Tests  7 passed (7)`.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add site/src/i18n
git commit -m "feat(site): EN and ES dictionaries with the prototype copy; drafts marked for stage 5

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Errors, SSE parsing, follow-up rules and the API client

**Files:**
- Create: `site/src/lib/errors.ts`, `site/src/lib/sse.ts`, `site/src/lib/followups.ts`, `site/src/lib/api.ts`, `site/src/lib/testing/fakes.ts`
- Test: `site/src/lib/errors.test.ts`, `site/src/lib/sse.test.ts`, `site/src/lib/followups.test.ts`, `site/src/lib/api.test.ts`

**Interfaces:**
- Consumes: types from `site/src/lib/types.ts`; `DictKey` from `site/src/i18n`.
- Produces (`errors.ts`): `ErrorKind = 'limit' | 'busy' | 'daycap' | 'attempts' | 'turnstile' | 'unavailable' | 'stage' | 'gone' | 'network' | 'other'`, `reasonOf(body)`, `classifyError(status, body) -> ErrorKind` (429 limit → `limit`, 429 ip_limit → `daycap`, 429 attempts → `attempts`, other 429 → `busy`, 403 turnstile → `turnstile`, 502 / 503 / 504 → `unavailable`, 401 without JSON reason → `stage`, 404 → `gone`, no answer (status 0) → `network`), `needsHelpLink(kind)` (true for limit, busy, daycap, attempts, turnstile, unavailable), `errorMessageKey(kind) -> DictKey` (`daycap` → `errDayCap`, `attempts` → `followupNone`).
- Produces (`sse.ts`): `SseEvent {event: string, data: unknown}`, `class SseParser(onEvent)` with `feed(chunk)`, `finish()`; `readSse(body: ReadableStream<Uint8Array>, onEvent) -> Promise<void>` (rejects when the connection breaks).
- Produces (`followups.ts`): `Offer = 'free' | 'paid' | 'none'`, `followupOffer(counts | null) -> Offer`, `FollowupBody {question, tz?, use_reading}`, `followupBody(question, tz, useReading)`, `FollowupRefusal = {type: 'confirm', remaining} | {type: 'plus'} | {type: 'crisis', payload} | {type: 'error', error}`, `followupRefusal(status, body)`, `Followup {question, text, status: 'streaming' | 'done' | 'replaced' | 'failed', softLine, usedReading}`, `newFollowup(question)`, `FollowupUpdate {followup, counts?, crisis?}`, `applyFollowupEvent(followup, event) -> FollowupUpdate`.
- Produces (`api.ts`): `FetchFn`, `ApiResult<T> = {ok: true, status, data} | {ok: false, status, error, body}`, `CreateResult = {type: 'reading', reading} | {type: 'crisis', payload} | {type: 'error', error, body}`, `StreamEnd = {type: 'ended'} | {type: 'broken'} | {type: 'error', error, body}`, `FollowupResult = {type: 'stream', end} | {type: 'refused', refusal}`, `interface Api {createReading(body); streamReading(id, tz, onEvent); retryReading(id, tz, onEvent); getReading(id, tz); postFollowup(id, body, onEvent); getDaily(lang, tz); joinWaitlist(email, lang)}`, `createApi(fetchFn) -> Api`, `browserFetch() -> FetchFn`, `withQuery(path, params)`.
- Produces (`testing/fakes.ts`, tests only): `sseText(events)`, `sseResponse(text)`, `brokenSseResponse(text)`, `jsonResponse(status, body)`, `fakeFetch(...queue) -> {fetch, calls}`, `Call {url, method, body, headers}`.

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/errors.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { classifyError, errorMessageKey, needsHelpLink, reasonOf } from './errors';

describe('classifyError', () => {
  it('maps every answer of api/README.md to a kind', () => {
    expect(classifyError(429, { reason: 'limit', remaining: 0 })).toBe('limit');
    expect(classifyError(429, { reason: 'ip_limit', remaining: 0 })).toBe('daycap');
    expect(classifyError(429, { reason: 'attempts' })).toBe('attempts');
    expect(classifyError(429, { reason: 'rate' })).toBe('busy');
    expect(classifyError(403, { reason: 'turnstile', sitekey: 'k' })).toBe('turnstile');
    expect(classifyError(403, { reason: 'owner_only' })).toBe('other');
    expect(classifyError(503, { reason: 'unavailable' })).toBe('unavailable');
    expect(classifyError(503, { reason: 'db' })).toBe('unavailable');
    expect(classifyError(503, null)).toBe('unavailable');
    expect(classifyError(502, null)).toBe('unavailable'); // Caddy while the API restarts
    expect(classifyError(504, null)).toBe('unavailable');
    expect(classifyError(401, null)).toBe('stage');
    expect(classifyError(401, { reason: 'auth' })).toBe('other');
    expect(classifyError(404, { reason: 'not_found' })).toBe('gone');
    expect(classifyError(0, null)).toBe('network');
    expect(classifyError(422, { reason: 'invalid', fields: ['question'] })).toBe('other');
    expect(classifyError(409, { reason: 'busy' })).toBe('other');
  });

  it('adds the help link to the 429, 403 turnstile and 503 messages only', () => {
    expect(['limit', 'busy', 'daycap', 'attempts', 'turnstile', 'unavailable'].every((k) => needsHelpLink(k as never))).toBe(true);
    expect(['stage', 'gone', 'network', 'other'].some((k) => needsHelpLink(k as never))).toBe(false);
  });

  it('has a message for every kind', () => {
    expect(errorMessageKey('busy')).toBe('errBusy');
    expect(errorMessageKey('unavailable')).toBe('errUnavailable');
    expect(errorMessageKey('limit')).toBe('plusTitle');
    expect(errorMessageKey('daycap')).toBe('errDayCap');
    expect(errorMessageKey('attempts')).toBe('followupNone');
  });

  it('reads the reason only when it is a string', () => {
    expect(reasonOf({ reason: 'limit' })).toBe('limit');
    expect(reasonOf({ reason: 3 })).toBeUndefined();
    expect(reasonOf('text')).toBeUndefined();
  });
});
```

Create `site/src/lib/sse.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { SseParser, readSse, type SseEvent } from './sse';

const STREAM =
  'event: meta\ndata: {"reading_id": "r1", "soft_line": null}\n\n' +
  'event: section\ndata: {"name": "headline"}\n\n' +
  'event: text\ndata: {"name": "headline", "text": "Un cambio que no elegiste, señal"}\n\n' +
  'event: done\ndata: {"answer_shown": "model"}\n\n';

function collect(chunks: string[]): SseEvent[] {
  const events: SseEvent[] = [];
  const parser = new SseParser((e) => events.push(e));
  for (const c of chunks) parser.feed(c);
  parser.finish();
  return events;
}

function body(parts: Uint8Array[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      for (const p of parts) controller.enqueue(p);
      controller.close();
    },
  });
}

describe('SseParser', () => {
  it('reads the API stream in one piece', () => {
    const events = collect([STREAM]);
    expect(events.map((e) => e.event)).toEqual(['meta', 'section', 'text', 'done']);
    expect(events[2].data).toEqual({ name: 'headline', text: 'Un cambio que no elegiste, señal' });
  });

  it('gives the same events however the stream is cut', () => {
    const whole = collect([STREAM]);
    for (let size = 1; size <= 7; size++) {
      const chunks = STREAM.match(new RegExp(`[\\s\\S]{1,${size}}`, 'g'))!;
      expect(collect(chunks)).toEqual(whole);
    }
  });

  it('accepts CRLF line ends, also split between chunks', () => {
    const crlf = STREAM.replace(/\n/g, '\r\n');
    expect(collect([crlf])).toEqual(collect([STREAM]));
    const cut = crlf.indexOf('\r\n\r\n') + 1;
    expect(collect([crlf.slice(0, cut), crlf.slice(cut)])).toEqual(collect([STREAM]));
  });

  it('skips comments and blocks without data, joins multi-line data, keeps non-JSON as text', () => {
    const events = collect([': keep-alive\n\nevent: ping\n\nevent: note\ndata: line one\ndata: line two\n\n']);
    expect(events).toEqual([{ event: 'note', data: 'line one\nline two' }]);
  });

  it('dispatches a last block that has no blank line after it', () => {
    expect(collect(['event: done\ndata: {"answer_shown": "fallback"}'])).toEqual([
      { event: 'done', data: { answer_shown: 'fallback' } },
    ]);
  });
});

describe('readSse', () => {
  it('decodes UTF-8 split across network chunks', async () => {
    const bytes = new TextEncoder().encode(STREAM);
    const at = bytes.indexOf(0xc3); // the first byte of "ñ"
    const events: SseEvent[] = [];
    await readSse(body([bytes.slice(0, at + 1), bytes.slice(at + 1)]), (e) => events.push(e));
    expect(events[2].data).toEqual({ name: 'headline', text: 'Un cambio que no elegiste, señal' });
    expect(events).toHaveLength(4);
  });

  it('rejects when the connection breaks, after passing on what arrived', async () => {
    const events: SseEvent[] = [];
    let pulls = 0;
    const broken = new ReadableStream<Uint8Array>({
      pull(controller) {
        pulls += 1;
        if (pulls === 1) controller.enqueue(new TextEncoder().encode('event: section\ndata: {"name": "card1"}\n\n'));
        else controller.error(new Error('network'));
      },
    });
    await expect(readSse(broken, (e) => events.push(e))).rejects.toThrow('network');
    expect(events).toEqual([{ event: 'section', data: { name: 'card1' } }]);
  });
});
```

Create `site/src/lib/followups.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { applyFollowupEvent, followupBody, followupOffer, followupRefusal, newFollowup } from './followups';

describe('followupOffer', () => {
  it('offers free follow-ups while any are left', () => {
    expect(followupOffer({ followups_left: 2, followup_attempts_left: 8 })).toBe('free');
    expect(followupOffer({ followups_left: 1, followup_attempts_left: 1 })).toBe('free');
  });

  it('offers a paid one only when followups_left == 0 and attempts are left', () => {
    expect(followupOffer({ followups_left: 0, followup_attempts_left: 3 })).toBe('paid');
    expect(followupOffer({ followups_left: 0, followup_attempts_left: 0 })).toBe('none');
    expect(followupOffer({ followups_left: 2, followup_attempts_left: 0 })).toBe('none');
    expect(followupOffer(null)).toBe('none');
  });
});

describe('followupBody', () => {
  it('sends the same tz and use_reading only as asked', () => {
    expect(followupBody('  And work? ', 'Europe/Madrid', false)).toEqual({ question: 'And work?', tz: 'Europe/Madrid', use_reading: false });
    expect(followupBody('And work?', undefined, true)).toEqual({ question: 'And work?', use_reading: true });
  });
});

describe('followupRefusal', () => {
  it('reads 402 confirm with the readings left, 402 plus, a crisis answer and errors', () => {
    expect(followupRefusal(402, { reason: 'confirm', remaining: 1 })).toEqual({ type: 'confirm', remaining: 1 });
    expect(followupRefusal(402, { reason: 'plus', remaining: 0 })).toEqual({ type: 'plus' });
    const crisis = { group: 'crisis', crisis: {}, helplines: { lines: [] } };
    expect(followupRefusal(200, crisis)).toEqual({ type: 'crisis', payload: crisis });
    expect(followupRefusal(429, { reason: 'attempts' })).toEqual({ type: 'error', error: 'attempts' });
    expect(followupRefusal(503, { reason: 'unavailable' })).toEqual({ type: 'error', error: 'unavailable' });
    expect(followupRefusal(409, { reason: 'busy' })).toEqual({ type: 'error', error: 'other' });
  });
});

describe('applyFollowupEvent', () => {
  it('streams text and takes the counts and used_reading from done', () => {
    let f = newFollowup(' And work? ');
    f = applyFollowupEvent(f, { event: 'meta', data: { soft_line: null, paid: true } }).followup;
    f = applyFollowupEvent(f, { event: 'text', data: { name: 'followup', text: 'It may ' } }).followup;
    f = applyFollowupEvent(f, { event: 'text', data: { name: 'followup', text: 'help.' } }).followup;
    const update = applyFollowupEvent(f, { event: 'done', data: { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true } });
    expect(update.followup).toEqual({ question: 'And work?', text: 'It may help.', status: 'done', softLine: null, usedReading: true });
    expect(update.counts).toEqual({ followups_left: 0, followup_attempts_left: 5 });
  });

  it('shows the base line on replace and fallback', () => {
    const f = newFollowup('q');
    expect(applyFollowupEvent(f, { event: 'replace', data: { sections: { followup: 'Base' } } }).followup).toMatchObject({ text: 'Base', status: 'replaced' });
    const failed = applyFollowupEvent(f, { event: 'fallback', data: { sections: { followup: 'Not counted' } } }).followup;
    expect(failed).toMatchObject({ text: 'Not counted', status: 'failed' });
    expect(applyFollowupEvent(failed, { event: 'done', data: { answer_shown: 'fallback' } }).followup.status).toBe('failed');
  });

  it('clears the shown text on a crisis event and hands the crisis on', () => {
    let f = applyFollowupEvent(newFollowup('q'), { event: 'text', data: { name: 'followup', text: 'Some words' } }).followup;
    const update = applyFollowupEvent(f, { event: 'crisis', data: { group: 'crisis', crisis: { title: 'T' }, helplines: { lines: [] } } });
    expect(update.followup.text).toBe('');
    expect(update.crisis).toMatchObject({ group: 'crisis' });
    f = applyFollowupEvent(newFollowup('q'), { event: 'error', data: { reason: 'db' } }).followup;
    expect(f.status).toBe('failed');
  });
});
```

Create `site/src/lib/api.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { createApi, withQuery } from './api';
import type { SseEvent } from './sse';
import { brokenSseResponse, fakeFetch, jsonResponse, sseResponse, sseText } from './testing/fakes';

const CREATED = {
  id: 'r1', lang: 'en', kind: 'three', soft_line: null, verdict: null, remaining: 2,
  cards: [{ card_id: 'major-16-tower', position: 'past', reversed: false, name: 'The Tower' }],
};
const CRISIS = { group: 'crisis', crisis: { title: 'You don’t have to carry this alone' }, helplines: { lines: [] }, remaining: 3 };

describe('createReading', () => {
  it('posts the body as JSON and returns the reading', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(201, CREATED));
    const result = await createApi(fetch).createReading({ lang: 'en', kind: 'three', question: 'Move?', tz: 'Europe/Madrid' });
    expect(result).toEqual({ type: 'reading', reading: CREATED });
    expect(calls[0]).toMatchObject({
      url: '/api/readings', method: 'POST', body: { lang: 'en', kind: 'three', question: 'Move?', tz: 'Europe/Madrid' },
    });
  });

  it('returns the crisis answer, never a reading', async () => {
    const { fetch } = fakeFetch(jsonResponse(200, CRISIS));
    expect(await createApi(fetch).createReading({ lang: 'en', kind: 'one' })).toEqual({ type: 'crisis', payload: CRISIS });
  });

  it('classifies refusals and network failures', async () => {
    const { fetch } = fakeFetch(
      jsonResponse(429, { reason: 'limit', remaining: 0 }),
      jsonResponse(403, { reason: 'turnstile', sitekey: '0xSITE' }),
      new TypeError('offline'),
    );
    const api = createApi(fetch);
    expect(await api.createReading({ lang: 'en', kind: 'one' })).toEqual({ type: 'error', error: 'limit', body: { reason: 'limit', remaining: 0 } });
    expect(await api.createReading({ lang: 'en', kind: 'one' })).toMatchObject({ type: 'error', error: 'turnstile', body: { sitekey: '0xSITE' } });
    expect(await api.createReading({ lang: 'en', kind: 'one' })).toEqual({ type: 'error', error: 'network', body: null });
  });
});

describe('streams', () => {
  it('reads the reading stream with the same tz', async () => {
    const text = sseText([['meta', { reading_id: 'r1' }], ['done', { answer_shown: 'model' }]]);
    const { fetch, calls } = fakeFetch(sseResponse(text));
    const events: SseEvent[] = [];
    const end = await createApi(fetch).streamReading('r1', 'America/Mexico_City', (e) => events.push(e));
    expect(end).toEqual({ type: 'ended' });
    expect(events.map((e) => e.event)).toEqual(['meta', 'done']);
    expect(calls[0].url).toBe('/api/readings/r1/stream?tz=America%2FMexico_City');
    expect(calls[0].headers.accept).toBe('text/event-stream');
  });

  it('reports a broken stream after passing on what arrived', async () => {
    const { fetch } = fakeFetch(brokenSseResponse(sseText([['section', { name: 'headline' }]])));
    const events: SseEvent[] = [];
    expect(await createApi(fetch).streamReading('r1', undefined, (e) => events.push(e))).toEqual({ type: 'broken' });
    expect(events).toHaveLength(1);
  });

  it('turns a JSON refusal of a stream into an error', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(409, { reason: 'retries' }));
    expect(await createApi(fetch).retryReading('r1', 'UTC', () => {})).toEqual({ type: 'error', error: 'other', body: { reason: 'retries' } });
    expect(calls[0]).toMatchObject({ url: '/api/readings/r1/retry?tz=UTC', method: 'POST' });
  });
});

describe('follow-ups', () => {
  it('streams an answer', async () => {
    const { fetch, calls } = fakeFetch(sseResponse(sseText([['text', { name: 'followup', text: 'Yes.' }]])));
    const events: SseEvent[] = [];
    const result = await createApi(fetch).postFollowup('r1', { question: 'And work?', tz: 'UTC', use_reading: false }, (e) => events.push(e));
    expect(result).toEqual({ type: 'stream', end: { type: 'ended' } });
    expect(calls[0]).toMatchObject({ url: '/api/readings/r1/followups', method: 'POST', body: { question: 'And work?', tz: 'UTC', use_reading: false } });
    expect(events).toHaveLength(1);
  });

  it('turns 402 confirm, 402 plus and a crisis answer into refusals', async () => {
    const { fetch } = fakeFetch(
      jsonResponse(402, { reason: 'confirm', remaining: 2 }),
      jsonResponse(402, { reason: 'plus', remaining: 0 }),
      jsonResponse(200, CRISIS),
      jsonResponse(429, { reason: 'attempts' }),
    );
    const api = createApi(fetch);
    const ask = () => api.postFollowup('r1', { question: 'q', use_reading: false }, () => {});
    expect(await ask()).toEqual({ type: 'refused', refusal: { type: 'confirm', remaining: 2 } });
    expect(await ask()).toEqual({ type: 'refused', refusal: { type: 'plus' } });
    expect(await ask()).toEqual({ type: 'refused', refusal: { type: 'crisis', payload: CRISIS } });
    expect(await ask()).toEqual({ type: 'refused', refusal: { type: 'error', error: 'attempts' } });
  });
});

describe('other calls', () => {
  it('gets the reading, the card of the day and joins the Plus waitlist', async () => {
    const { fetch, calls } = fakeFetch(
      jsonResponse(200, { id: 'r1', status: 'done' }),
      jsonResponse(503, { reason: 'db' }),
      jsonResponse(200, { ok: true }),
    );
    const api = createApi(fetch);
    expect(await api.getReading('r1', 'UTC')).toEqual({ ok: true, status: 200, data: { id: 'r1', status: 'done' } });
    expect(await api.getDaily('es', 'America/Bogota')).toEqual({ ok: false, status: 503, error: 'unavailable', body: { reason: 'db' } });
    expect(await api.joinWaitlist('ana@example.com', 'es')).toEqual({ ok: true, status: 200, data: { ok: true } });
    expect(calls.map((c) => c.url)).toEqual(['/api/readings/r1?tz=UTC', '/api/daily?lang=es&tz=America%2FBogota', '/api/plus/waitlist']);
    expect(calls[2].body).toEqual({ email: 'ana@example.com', lang: 'es' });
  });

  it('leaves out empty query values', () => {
    expect(withQuery('/api/daily', { lang: 'en', tz: undefined })).toBe('/api/daily?lang=en');
    expect(withQuery('/x', {})).toBe('/x');
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/errors.test.ts src/lib/sse.test.ts src/lib/followups.test.ts src/lib/api.test.ts`
Expected: FAIL — `Error: Cannot find module './errors' imported from /app/src/lib/errors.test.ts` (and `./sse`, `./followups`, `./api`).

- [ ] **Step 3: Write the modules**

Create `site/src/lib/errors.ts`:

```ts
// What a failed API answer means for the screen (spec 4.4a §4, api/README.md "Передача в 4.4").
import type { DictKey } from '../i18n';

export type ErrorKind =
  | 'limit' // 429 {"reason": "limit"}: today's free readings are used — the Plus card (screen 11a)
  | 'busy' // 429 burst or rate: wait a minute
  | 'daycap' // 429 {"reason": "ip_limit"}: this address's cap for the day — try again tomorrow
  | 'attempts' // 429 {"reason": "attempts"}: this reading takes no more follow-ups
  | 'turnstile' // 403 {"reason": "turnstile"}: run the invisible Turnstile check and repeat the request
  | 'unavailable' // 503 (database, model budget, sign-in keys) and 502 / 504 (the API restarts, e.g. a deploy)
  | 'stage' // 401 without a JSON reason: the stage cookie is stale — reload the page
  | 'gone' // 404: the reading expired or is not ours
  | 'network' // no answer at all
  | 'other';

export function reasonOf(body: unknown): string | undefined {
  if (body && typeof body === 'object' && 'reason' in body) {
    const reason = (body as { reason: unknown }).reason;
    return typeof reason === 'string' ? reason : undefined;
  }
  return undefined;
}

export function classifyError(status: number, body: unknown): ErrorKind {
  const reason = reasonOf(body);
  if (status === 0) return 'network';
  if (status === 429) {
    if (reason === 'limit') return 'limit';
    if (reason === 'ip_limit') return 'daycap';
    return reason === 'attempts' ? 'attempts' : 'busy';
  }
  if (status === 403 && reason === 'turnstile') return 'turnstile';
  if (status === 502 || status === 503 || status === 504) return 'unavailable';
  if (status === 401 && reason === undefined) return 'stage';
  if (status === 404) return 'gone';
  return 'other';
}

/** §10.8 of spec 4.2: the 429, 403 and 503 messages also link to help lines. */
export function needsHelpLink(kind: ErrorKind): boolean {
  return kind === 'limit' || kind === 'busy' || kind === 'daycap' || kind === 'attempts' || kind === 'turnstile'
    || kind === 'unavailable';
}

const MESSAGES: Record<ErrorKind, DictKey> = {
  limit: 'plusTitle',
  busy: 'errBusy',
  daycap: 'errDayCap',
  attempts: 'followupNone',
  turnstile: 'errTurnstile',
  unavailable: 'errUnavailable',
  stage: 'errStage',
  gone: 'errGone',
  network: 'errNetwork',
  other: 'errOther',
};

export function errorMessageKey(kind: ErrorKind): DictKey {
  return MESSAGES[kind];
}
```

Create `site/src/lib/sse.ts`:

```ts
// Server-sent events read from a fetch() body (spec 4.4a §4: not EventSource, which cannot send headers).
// The API sends `event: <name>` and one `data: <json>` line per event, blocks separated by a blank line.

export interface SseEvent {
  event: string;
  data: unknown;
}

export class SseParser {
  private buffer = '';

  constructor(private readonly onEvent: (event: SseEvent) => void) {}

  /** Any split of the stream is fine, a CRLF cut in half included. */
  feed(chunk: string): void {
    let text = this.buffer + chunk;
    const heldCR = text.endsWith('\r');
    if (heldCR) text = text.slice(0, -1);
    text = text.replace(/\r\n?/g, '\n');
    let end = text.indexOf('\n\n');
    while (end >= 0) {
      this.dispatch(text.slice(0, end));
      text = text.slice(end + 2);
      end = text.indexOf('\n\n');
    }
    this.buffer = text + (heldCR ? '\r' : '');
  }

  /** The stream ended: a last block without its blank line still counts. */
  finish(): void {
    const rest = this.buffer.replace(/\r\n?/g, '\n');
    this.buffer = '';
    if (rest.trim()) this.dispatch(rest);
  }

  private dispatch(block: string): void {
    let event = 'message';
    const data: string[] = [];
    for (const line of block.split('\n')) {
      if (!line || line.startsWith(':')) continue;
      const colon = line.indexOf(':');
      const field = colon < 0 ? line : line.slice(0, colon);
      let value = colon < 0 ? '' : line.slice(colon + 1);
      if (value.startsWith(' ')) value = value.slice(1);
      if (field === 'event') event = value;
      else if (field === 'data') data.push(value);
    }
    if (data.length === 0) return;
    const raw = data.join('\n');
    let parsed: unknown = raw;
    try {
      parsed = JSON.parse(raw);
    } catch {
      // not JSON: passed on as text
    }
    this.onEvent({ event, data: parsed });
  }
}

/** Reads a whole SSE body; resolves when the body ends, rejects if the connection breaks. */
export async function readSse(body: ReadableStream<Uint8Array>, onEvent: (event: SseEvent) => void): Promise<void> {
  const parser = new SseParser(onEvent);
  const decoder = new TextDecoder('utf-8');
  const reader = body.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parser.feed(decoder.decode(value, { stream: true }));
  }
  parser.feed(decoder.decode());
  parser.finish();
}
```

Create `site/src/lib/followups.ts`:

```ts
// Follow-up questions (spec 4.2 §10.1, api/README.md): two free per reading; after them each one uses a reading
// of today's limit, offered only when followups_left == 0 and followup_attempts_left > 0, first with a warning
// ("this will use 1 reading"), then sent again with use_reading: true. 402 confirm / 402 plus / done.used_reading.
import { classifyError, reasonOf, type ErrorKind } from './errors';
import type { SseEvent } from './sse';
import type { CrisisPayload, FollowupCounts } from './types';

export type Offer = 'free' | 'paid' | 'none';

export function followupOffer(counts: FollowupCounts | null): Offer {
  if (!counts || counts.followup_attempts_left <= 0) return 'none';
  return counts.followups_left > 0 ? 'free' : 'paid';
}

export interface FollowupBody {
  question: string;
  tz?: string;
  use_reading: boolean;
}

/** The same tz as the reading was created with (api/README.md: otherwise the day is UTC). */
export function followupBody(question: string, tz: string | undefined, useReading: boolean): FollowupBody {
  return tz ? { question: question.trim(), tz, use_reading: useReading } : { question: question.trim(), use_reading: useReading };
}

export type FollowupRefusal =
  | { type: 'confirm'; remaining: number }
  | { type: 'plus' }
  | { type: 'crisis'; payload: CrisisPayload }
  | { type: 'error'; error: ErrorKind };

/** A follow-up answered with JSON instead of a stream. */
export function followupRefusal(status: number, body: unknown): FollowupRefusal {
  const reason = reasonOf(body);
  if (status === 402 && reason === 'confirm') {
    const remaining = (body as { remaining?: unknown }).remaining;
    return { type: 'confirm', remaining: typeof remaining === 'number' ? remaining : 0 };
  }
  if (status === 402) return { type: 'plus' };
  if (status === 200 && body && typeof body === 'object' && (body as { group?: unknown }).group === 'crisis') {
    return { type: 'crisis', payload: body as CrisisPayload };
  }
  return { type: 'error', error: classifyError(status, body) };
}

export interface Followup {
  question: string;
  text: string;
  status: 'streaming' | 'done' | 'replaced' | 'failed';
  softLine: string | null;
  usedReading: boolean | null;
}

export function newFollowup(question: string): Followup {
  return { question: question.trim(), text: '', status: 'streaming', softLine: null, usedReading: null };
}

export interface FollowupUpdate {
  followup: Followup;
  counts?: FollowupCounts;
  crisis?: CrisisPayload;
}

function sectionText(data: Record<string, unknown>): string {
  const sections = data.sections as Record<string, unknown> | undefined;
  return typeof sections?.followup === 'string' ? sections.followup : '';
}

export function applyFollowupEvent(followup: Followup, event: SseEvent): FollowupUpdate {
  const data = (event.data && typeof event.data === 'object' ? event.data : {}) as Record<string, unknown>;
  switch (event.event) {
    case 'meta':
      return { followup: { ...followup, softLine: typeof data.soft_line === 'string' ? data.soft_line : null } };
    case 'text':
      return typeof data.text === 'string' ? { followup: { ...followup, text: followup.text + data.text } } : { followup };
    case 'replace':
      return { followup: { ...followup, text: sectionText(data), status: 'replaced' } };
    case 'fallback':
      return { followup: { ...followup, text: sectionText(data), status: 'failed' } };
    case 'crisis': // the shown text is cleared; the room shows the crisis answer instead
      return { followup: { ...followup, text: '', status: 'failed' }, crisis: data as unknown as CrisisPayload };
    case 'error':
      return { followup: { ...followup, status: 'failed' } };
    case 'done': {
      const update: FollowupUpdate = {
        followup: {
          ...followup,
          status: data.answer_shown === 'model' ? 'done' : followup.status === 'streaming' ? 'failed' : followup.status,
          usedReading: typeof data.used_reading === 'boolean' ? data.used_reading : null,
        },
      };
      if (typeof data.followups_left === 'number' && typeof data.followup_attempts_left === 'number') {
        update.counts = { followups_left: data.followups_left, followup_attempts_left: data.followup_attempts_left };
      }
      return update;
    }
    default:
      return { followup };
  }
}
```

Create `site/src/lib/api.ts`:

```ts
// The API calls of the reading screens (api/README.md "Адреса"). Same origin, path /api; the guest cookie goes
// with every request. Streams are read through fetch (spec 4.4a §4). Nothing here touches the page.
import { classifyError, type ErrorKind } from './errors';
import { followupRefusal, type FollowupBody, type FollowupRefusal } from './followups';
import { readSse, type SseEvent } from './sse';
import type { CreateBody, CrisisPayload, DailyCard, Lang, ReadingCreated, ReadingView } from './types';

export type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; error: ErrorKind; body: Record<string, unknown> | null };

export type CreateResult =
  | { type: 'reading'; reading: ReadingCreated }
  | { type: 'crisis'; payload: CrisisPayload }
  | { type: 'error'; error: ErrorKind; body: Record<string, unknown> | null };

/** ended — the body ended (with or without `done`); broken — the connection failed mid-way. */
export type StreamEnd =
  | { type: 'ended' }
  | { type: 'broken' }
  | { type: 'error'; error: ErrorKind; body: Record<string, unknown> | null };

export type FollowupResult = { type: 'stream'; end: StreamEnd } | { type: 'refused'; refusal: FollowupRefusal };

export interface Api {
  createReading(body: CreateBody): Promise<CreateResult>;
  streamReading(id: string, tz: string | undefined, onEvent: (event: SseEvent) => void): Promise<StreamEnd>;
  retryReading(id: string, tz: string | undefined, onEvent: (event: SseEvent) => void): Promise<StreamEnd>;
  getReading(id: string, tz: string | undefined): Promise<ApiResult<ReadingView>>;
  postFollowup(id: string, body: FollowupBody, onEvent: (event: SseEvent) => void): Promise<FollowupResult>;
  getDaily(lang: Lang, tz: string | undefined): Promise<ApiResult<DailyCard>>;
  joinWaitlist(email: string, lang: Lang): Promise<ApiResult<{ ok: boolean }>>;
}

const JSON_HEADERS = { 'content-type': 'application/json' };

export function withQuery(path: string, params: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value) query.set(key, value);
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}

function readingPath(id: string, tail = ''): string {
  return `/api/readings/${encodeURIComponent(id)}${tail}`;
}

async function jsonBody(response: Response): Promise<Record<string, unknown> | null> {
  try {
    const body = await response.json();
    return body && typeof body === 'object' ? (body as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function isStream(response: Response): boolean {
  return response.ok && response.body !== null && (response.headers.get('content-type') ?? '').includes('text/event-stream');
}

export function createApi(fetchFn: FetchFn): Api {
  async function call<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
    let response: Response;
    try {
      response = await fetchFn(path, init);
    } catch {
      return { ok: false, status: 0, error: 'network', body: null };
    }
    const body = await jsonBody(response);
    if (response.ok) return { ok: true, status: response.status, data: body as T };
    return { ok: false, status: response.status, error: classifyError(response.status, body), body };
  }

  async function stream(path: string, init: RequestInit, onEvent: (event: SseEvent) => void): Promise<StreamEnd> {
    let response: Response;
    try {
      response = await fetchFn(path, { ...init, headers: { ...(init.headers ?? {}), accept: 'text/event-stream' } });
    } catch {
      return { type: 'broken' };
    }
    if (!isStream(response)) {
      const body = await jsonBody(response);
      return { type: 'error', error: classifyError(response.ok ? 500 : response.status, body), body };
    }
    try {
      await readSse(response.body!, onEvent);
      return { type: 'ended' };
    } catch {
      return { type: 'broken' };
    }
  }

  return {
    async createReading(body) {
      const result = await call<Record<string, unknown>>('/api/readings', {
        method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(body),
      });
      if (!result.ok) return { type: 'error', error: result.error, body: result.body };
      if (result.data?.group === 'crisis') return { type: 'crisis', payload: result.data as unknown as CrisisPayload };
      return { type: 'reading', reading: result.data as unknown as ReadingCreated };
    },
    streamReading(id, tz, onEvent) {
      return stream(withQuery(readingPath(id, '/stream'), { tz }), { method: 'GET' }, onEvent);
    },
    retryReading(id, tz, onEvent) {
      return stream(withQuery(readingPath(id, '/retry'), { tz }), { method: 'POST' }, onEvent);
    },
    getReading(id, tz) {
      return call<ReadingView>(withQuery(readingPath(id), { tz }));
    },
    async postFollowup(id, body, onEvent) {
      let response: Response;
      try {
        response = await fetchFn(readingPath(id, '/followups'), {
          method: 'POST', headers: { ...JSON_HEADERS, accept: 'text/event-stream' }, body: JSON.stringify(body),
        });
      } catch {
        return { type: 'refused', refusal: { type: 'error', error: 'network' } };
      }
      if (!isStream(response)) return { type: 'refused', refusal: followupRefusal(response.status, await jsonBody(response)) };
      try {
        await readSse(response.body!, onEvent);
        return { type: 'stream', end: { type: 'ended' } };
      } catch {
        return { type: 'stream', end: { type: 'broken' } };
      }
    },
    getDaily(lang, tz) {
      return call<DailyCard>(withQuery('/api/daily', { lang, tz }));
    },
    joinWaitlist(email, lang) {
      return call<{ ok: boolean }>('/api/plus/waitlist', {
        method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ email, lang }),
      });
    },
  };
}

/** The browser's fetch, called with the right `this`. */
export function browserFetch(): FetchFn {
  return (input, init) => fetch(input, init);
}
```

Create `site/src/lib/testing/fakes.ts`:

```ts
// Test doubles for the API: Responses as the API sends them, and a fetch that answers from a queue.
import type { FetchFn } from '../api';

export interface Call {
  url: string;
  method: string;
  body: unknown;
  headers: Record<string, string>;
}

export function sseText(events: ReadonlyArray<readonly [string, unknown]>): string {
  return events.map(([name, data]) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`).join('');
}

function bytes(text: string): Uint8Array {
  return new TextEncoder().encode(text);
}

export function sseResponse(text: string): Response {
  return new Response(bytes(text), { status: 200, headers: { 'content-type': 'text/event-stream' } });
}

/** A stream that sends `text` and then breaks (the phone lost its connection). */
export function brokenSseResponse(text: string): Response {
  let pulls = 0;
  const body = new ReadableStream<Uint8Array>({
    pull(controller) {
      pulls += 1;
      if (pulls === 1) controller.enqueue(bytes(text));
      else controller.error(new TypeError('network error'));
    },
  });
  return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } });
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === null ? null : JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  });
}

/** Answers calls in order; an Error in the queue is thrown (no network). */
export function fakeFetch(...queue: Array<Response | Error>): { fetch: FetchFn; calls: Call[] } {
  const calls: Call[] = [];
  const fetchFn: FetchFn = async (url, init) => {
    const headers = (init?.headers ?? {}) as Record<string, string>;
    calls.push({ url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : undefined, headers });
    const next = queue.shift();
    if (!next) throw new Error(`unexpected call ${url}`);
    if (next instanceof Error) throw next;
    return next;
  };
  return { fetch: fetchFn, calls };
}
```

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/errors.test.ts src/lib/sse.test.ts src/lib/followups.test.ts src/lib/api.test.ts`
Expected: `Test Files  4 passed (4)`, `Tests  28 passed (28)`.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add site/src/lib/errors.ts site/src/lib/sse.ts site/src/lib/followups.ts site/src/lib/api.ts site/src/lib/testing \
  site/src/lib/errors.test.ts site/src/lib/sse.test.ts site/src/lib/followups.test.ts site/src/lib/api.test.ts
git commit -m "feat(site): SSE over fetch, the API client, error kinds and follow-up rules

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Answer sections, the night-room state machine and the request flow

> **Amendment after the Fable re-check (R2), required:** `restoreFollowup` must not match a saved follow-up by question text. Pass the number of answered follow-ups known before the request and accept a restored answer only when the API's `followups.length` is greater than that number (take the last one). Add a `readingFlow.test.ts` case where the same question is asked twice.

**Files:**
- Create: `site/src/lib/answer.ts`, `site/src/lib/nightRoom.ts`, `site/src/lib/readingFlow.ts`
- Test: `site/src/lib/answer.test.ts`, `site/src/lib/nightRoom.test.ts`, `site/src/lib/readingFlow.test.ts`

**Interfaces:**
- Consumes: `SseEvent` (Task 5), `ErrorKind`, `applyFollowupEvent`, `followupOffer`, `newFollowup`, `Followup`, `FollowupRefusal`, `Offer`, `followupBody`, `Api` (Task 5), `DictKey` (Task 4), types (Task 3).
- Produces (`answer.ts`): `SECTION_ORDER = ['headline','card1','card2','card3','synthesis','step','why']`, `SectionName`, `Sections`, `Answer {sections, started, shown: 'model' | 'fallback' | null, replaced: 'replace' | 'fallback' | null, retry}`, `EMPTY_ANSWER`, `pickSections(raw)`, `applyAnswerEvent(answer, event) -> Answer`, `answerFromView(view) -> Answer`, `AnswerBlock`, `answerBlocks(answer, cards) -> AnswerBlock[]`.
- Produces (`nightRoom.ts`): `Phase = 'closed' | 'opening' | 'reading' | 'crisis' | 'limit' | 'error'`, `StreamState = 'waiting' | 'streaming' | 'done' | 'restoring' | 'lost'`, `DEAL_MS = 600`, `FLIP_INTERVAL_MS = 900`, `NightState {phase, reading, revealed, answer, softLine, stream, crisis, error, counts, remaining, followups, confirm, followupError, followupPlus}`, `CLOSED`, `NightAction` (`open`, `created {reading, reducedMotion}`, `crisis {payload}`, `failed {error}`, `flip`, `stream {event}`, `streamEnded {outcome: 'done' | 'lost'}`, `restoring`, `restored {view}`, `retrying`, `counts {counts}`, `followupAsk {question}`, `followupCancel`, `followupEvent {event}`, `followupRefused {question, refusal}` (a `402 confirm` refusal sets `confirm {question, remaining}` — the paid warning), `followupRestored {followup: SavedFollowup}`, `followupLost`, `close`; every `meta` stream event empties the answer), `nightReducer(state, action) -> NightState`, `cardsCount`, `allRevealed`, `answerVisible`, `readingShown`, `statusKey(state) -> DictKey | null` (also `writing` / `followupReady` for follow-ups), `followupNow(state) -> Offer`, `RoomEvent`, `transitionEvents(prev, next) -> RoomEvent[]`.
- Produces (`readingFlow.ts`): `FlowDeps {api, dispatch, turnstileToken(sitekey) -> Promise<string | null>, sleep(ms), reducedMotion}`, `RESTORE_TRIES = 10`, `RESTORE_WAIT_MS = 2000`, `DEFAULT_COUNTS = {followups_left: 2, followup_attempts_left: 8}`, `startReading(deps, body)`, `streamReading(deps, id, tz, mode: 'stream' | 'retry', restoreOnLoss = true)` (a refused retry restores via GET), `restoreReading(deps, id, tz)`, `loadCounts(deps, id, tz)` (two tries, then `DEFAULT_COUNTS`), `restoreFollowup(deps, id, question, tz)`, `askFollowup(deps, id, question, tz, useReading)` (a broken stream → `restoreFollowup`) — all `Promise<void>`.

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/answer.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { EMPTY_ANSWER, answerBlocks, answerFromView, applyAnswerEvent, type Answer } from './answer';
import type { SseEvent } from './sse';
import type { DrawnCard, ReadingView } from './types';

const CARDS: DrawnCard[] = [
  { card_id: 'major-16-tower', position: 'past', reversed: false, name: 'The Tower' },
  { card_id: 'major-18-moon', position: 'present', reversed: true, name: 'The Moon' },
  { card_id: 'major-19-sun', position: 'path', reversed: false, name: 'The Sun' },
];

const run = (events: SseEvent[], start: Answer = EMPTY_ANSWER) => events.reduce(applyAnswerEvent, start);
const text = (name: string, t: string): SseEvent => ({ event: 'text', data: { name, text: t } });

describe('applyAnswerEvent', () => {
  it('builds sections from streamed pieces', () => {
    const answer = run([
      { event: 'section', data: { name: 'headline' } },
      text('headline', 'A change '), text('headline', 'you did not choose.'),
      text('card1', 'The Tower may point to a sudden change.'),
      { event: 'done', data: { answer_shown: 'model' } },
    ]);
    expect(answer.sections).toEqual({ headline: 'A change you did not choose.', card1: 'The Tower may point to a sudden change.' });
    expect(answer).toMatchObject({ started: true, shown: 'model', replaced: null, retry: false });
  });

  it('replaces the whole answer on replace and fallback, keeping the retry flag', () => {
    const replaced = run([text('headline', 'Bad'), { event: 'replace', data: { sections: { headline: 'Good', step: 'Breathe.' }, reason: 'why' } }]);
    expect(replaced.sections).toEqual({ headline: 'Good', step: 'Breathe.' });
    expect(replaced.replaced).toBe('replace');
    const fallback = run([{ event: 'fallback', data: { sections: { headline: 'The reader is unavailable…' }, reason: 'timeout', retry: true } }]);
    expect(fallback).toMatchObject({ replaced: 'fallback', retry: true, started: true });
  });

  it('ignores unknown sections, foreign events and the crisis marker', () => {
    const answer = run([text('crisis', 'x'), text('followup', 'y'), { event: 'meta', data: {} }, { event: 'ping', data: 'z' }]);
    expect(answer).toEqual(EMPTY_ANSWER);
  });
});

describe('answerBlocks', () => {
  it('orders blocks and ties each card section to its card', () => {
    const answer = run([text('step', ' Talk to someone. '), text('card2', 'Moon text'), text('headline', 'Head'),
      text('synthesis', 'Together'), text('card1', 'Tower text')]);
    expect(answerBlocks(answer, CARDS)).toEqual([
      { kind: 'headline', text: 'Head' },
      { kind: 'card', text: 'Tower text', card: CARDS[0] },
      { kind: 'card', text: 'Moon text', card: CARDS[1] },
      { kind: 'synthesis', text: 'Together' },
      { kind: 'step', text: 'Talk to someone.' },
    ]);
  });

  it('drops empty sections and card sections without a card', () => {
    const answer = run([text('headline', '   '), text('card3', 'Third'), text('why', 'Because')]);
    expect(answerBlocks(answer, CARDS.slice(0, 1))).toEqual([{ kind: 'why', text: 'Because' }]);
  });
});

describe('answerFromView', () => {
  it('restores the saved answer of GET /api/readings/{id}', () => {
    const view = { answer: { headline: 'H', card1: 'C', extra: 'x' }, answer_shown: 'fallback', retries_left: 1 } as unknown as ReadingView;
    expect(answerFromView(view)).toEqual({ sections: { headline: 'H', card1: 'C' }, started: true, shown: 'fallback', replaced: 'fallback', retry: true });
  });
});
```

Create `site/src/lib/nightRoom.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  CLOSED, DEAL_MS, FLIP_INTERVAL_MS, allRevealed, answerVisible, followupNow, nightReducer, readingShown, statusKey,
  transitionEvents, type NightAction, type NightState,
} from './nightRoom';
import type { CrisisPayload, ReadingCreated, ReadingView } from './types';

const THREE: ReadingCreated = {
  id: 'r1', lang: 'en', kind: 'three', verdict: null, soft_line: null, remaining: 2,
  cards: [
    { card_id: 'major-16-tower', position: 'past', reversed: false, name: 'The Tower' },
    { card_id: 'major-18-moon', position: 'present', reversed: true, name: 'The Moon' },
    { card_id: 'major-19-sun', position: 'path', reversed: false, name: 'The Sun' },
  ],
};
const CRISIS = { group: 'crisis', crisis: { title: 'T' }, helplines: { country: 'US', source: 'timezone', lines: [] } } as unknown as CrisisPayload;

const run = (actions: NightAction[], start: NightState = CLOSED) => actions.reduce(nightReducer, start);
const text = (name: string, t: string): NightAction => ({ type: 'stream', event: { event: 'text', data: { name, text: t } } });
const done = (shown = 'model'): NightAction => ({ type: 'stream', event: { event: 'done', data: { answer_shown: shown } } });
const flips = (n: number): NightAction[] => Array.from({ length: n }, () => ({ type: 'flip' }) as NightAction);
const created = (reducedMotion = false): NightAction => ({ type: 'created', reading: THREE, reducedMotion });
const counts = (left: number, attempts: number): NightAction => ({ type: 'counts', counts: { followups_left: left, followup_attempts_left: attempts } });

describe('opening and dealing', () => {
  it('opens, deals face down and turns the cards one by one', () => {
    let s = run([{ type: 'open' }]);
    expect(s.phase).toBe('opening');
    expect(statusKey(s)).toBe('shuffling');
    s = nightReducer(s, created());
    expect(s).toMatchObject({ phase: 'reading', revealed: 0, remaining: 2, stream: 'waiting' });
    expect(statusKey(s)).toBe('dealtThree');
    s = run(flips(2), s);
    expect(allRevealed(s)).toBe(false);
    s = run(flips(5), s);
    expect(s.revealed).toBe(3);
    expect(allRevealed(s)).toBe(true);
  });

  it('turns the cards at once with reduced motion', () => {
    const s = run([{ type: 'open' }, created(true)]);
    expect(allRevealed(s)).toBe(true);
  });

  it('keeps each card turn under a second', () => {
    expect(FLIP_INTERVAL_MS).toBeLessThanOrEqual(1000);
    expect(DEAL_MS).toBe(600);
  });

  it('ignores a late answer after the room was closed', () => {
    expect(run([{ type: 'open' }, { type: 'close' }, created()])).toEqual(CLOSED);
    expect(run([{ type: 'failed', error: 'busy' }])).toEqual(CLOSED);
  });
});

describe('the answer', () => {
  it('waits for the cards before showing streamed text', () => {
    let s = run([{ type: 'open' }, created(), text('headline', 'A change')]);
    expect(answerVisible(s)).toBe(false);
    s = run([...flips(3)], s);
    expect(answerVisible(s)).toBe(true);
    expect(statusKey(s)).toBe('writing');
    s = nightReducer(s, done());
    expect(readingShown(s)).toBe(true);
    expect(statusKey(s)).toBe('readingReady');
  });

  it('takes the soft line from meta', () => {
    const s = run([{ type: 'open' }, created(), { type: 'stream', event: { event: 'meta', data: { soft_line: 'Cards don’t predict this.' } } }]);
    expect(s.softLine).toBe('Cards don’t predict this.');
    expect(s.stream).toBe('streaming');
  });

  it('shows the crisis answer and nothing of the reading', () => {
    const s = run([{ type: 'open' }, created(true), text('headline', 'x'), { type: 'stream', event: { event: 'crisis', data: CRISIS } }]);
    expect(s.phase).toBe('crisis');
    expect(s.crisis).toEqual(CRISIS);
    expect(s.reading).toBeNull();
    expect(s.answer.started).toBe(false);
  });

  it('shows a crisis answer of the question check without a reading', () => {
    const s = run([{ type: 'open' }, { type: 'crisis', payload: CRISIS }]);
    expect(s).toMatchObject({ phase: 'crisis', reading: null });
  });

  it('closes into the Plus card at the daily limit, other errors stay in the room', () => {
    expect(run([{ type: 'open' }, { type: 'failed', error: 'limit' }]).phase).toBe('limit');
    expect(run([{ type: 'open' }, { type: 'failed', error: 'unavailable' }])).toMatchObject({ phase: 'error', error: 'unavailable' });
  });

  it('marks a lost stream, restores it from GET and clears for a retry', () => {
    let s = run([{ type: 'open' }, created(true), text('headline', 'Half'), { type: 'streamEnded', outcome: 'lost' }]);
    expect(statusKey(s)).toBe('streamLost');
    s = nightReducer(s, { type: 'restoring' });
    expect(statusKey(s)).toBe('restoring');
    const view = {
      answer: { headline: 'Whole' }, answer_shown: 'model', retries_left: 0, soft_line: null, followups_left: 2,
      followup_attempts_left: 8,
    } as unknown as ReadingView;
    s = nightReducer(s, { type: 'restored', view });
    expect(s.answer.sections).toEqual({ headline: 'Whole' });
    expect(s.counts).toEqual({ followups_left: 2, followup_attempts_left: 8 });
    expect(readingShown(s)).toBe(true);
    s = nightReducer(s, { type: 'retrying' });
    expect(s.answer.started).toBe(false);
    expect(s.stream).toBe('waiting');
  });

  it('starts the answer again on every meta, so a repeated stream never appends', () => {
    const s = run([{ type: 'open' }, created(true), text('headline', 'Half'), { type: 'stream', event: { event: 'error', data: { reason: 'db' } } },
      { type: 'stream', event: { event: 'meta', data: {} } }, text('headline', 'Whole')]);
    expect(s.answer.sections).toEqual({ headline: 'Whole' });
  });

  it('turns a stream error event into a lost stream, and done is final', () => {
    const lost = run([{ type: 'open' }, created(true), { type: 'stream', event: { event: 'error', data: { reason: 'db' } } }]);
    expect(lost.stream).toBe('lost');
    const final = run([{ type: 'open' }, created(true), text('headline', 'H'), done(), { type: 'streamEnded', outcome: 'lost' }]);
    expect(final.stream).toBe('done');
  });

  it('restores a crisis reading as the crisis answer', () => {
    const view = { ...CRISIS, answer_shown: 'crisis' } as unknown as ReadingView;
    expect(run([{ type: 'open' }, created(true), { type: 'restored', view }]).phase).toBe('crisis');
  });
});

describe('follow-ups', () => {
  const shown = () => run([{ type: 'open' }, created(true), text('headline', 'H'), done()]);

  it('offers a free follow-up only under a finished model answer', () => {
    expect(followupNow(run([{ type: 'open' }, created(true), text('headline', 'H')]))).toBe('none');
    expect(followupNow(shown())).toBe('none'); // no counts yet
    expect(followupNow(nightReducer(shown(), counts(2, 8)))).toBe('free');
    const fallback = run([{ type: 'open' }, created(true), { type: 'stream', event: { event: 'fallback', data: { sections: { headline: 'Base' }, retry: true } } }, done('fallback'), counts(2, 8)]);
    expect(followupNow(fallback)).toBe('none');
  });

  it('streams a follow-up, updates the counts and offers no second one while it streams', () => {
    let s = run([counts(1, 8), { type: 'followupAsk', question: 'And work?' }], shown());
    expect(followupNow(s)).toBe('none');
    expect(statusKey(s)).toBe('writing');
    s = run([
      { type: 'followupEvent', event: { event: 'text', data: { name: 'followup', text: 'Maybe.' } } },
      { type: 'followupEvent', event: { event: 'done', data: { answer_shown: 'model', followups_left: 0, followup_attempts_left: 7 } } },
    ], s);
    expect(s.followups).toEqual([{ question: 'And work?', text: 'Maybe.', status: 'done', softLine: null, usedReading: null }]);
    expect(followupNow(s)).toBe('paid');
  });

  it('warns before a paid follow-up when the API asks (402 confirm) and counts the reading it used', () => {
    let s = run([counts(0, 6), { type: 'followupAsk', question: 'More?' },
      { type: 'followupRefused', question: 'More?', refusal: { type: 'confirm', remaining: 2 } }], shown());
    expect(s.confirm).toEqual({ question: 'More?', remaining: 2 });
    expect(s.followups).toEqual([]);
    s = run([{ type: 'followupCancel' }], s);
    expect(s.confirm).toBeNull();
    s = run([
      { type: 'followupAsk', question: 'More?' },
      { type: 'followupEvent', event: { event: 'done', data: { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true } } },
    ], s);
    expect(s.remaining).toBe(1);
    expect(s.followups[0].usedReading).toBe(true);
  });

  it('handles 402 confirm, 402 plus and errors without keeping the unasked question', () => {
    const asked = run([counts(0, 6), { type: 'followupAsk', question: 'More?' }], shown());
    const confirm = nightReducer(asked, { type: 'followupRefused', question: 'More?', refusal: { type: 'confirm', remaining: 1 } });
    expect(confirm).toMatchObject({ followups: [], confirm: { question: 'More?', remaining: 1 } });
    const plus = nightReducer(asked, { type: 'followupRefused', question: 'More?', refusal: { type: 'plus' } });
    expect(plus).toMatchObject({ followups: [], followupPlus: true });
    const busy = nightReducer(asked, { type: 'followupRefused', question: 'More?', refusal: { type: 'error', error: 'busy' } });
    expect(busy).toMatchObject({ followups: [], followupError: 'busy' });
  });

  it('clears everything shown on a crisis in a follow-up', () => {
    const s = run([
      counts(2, 8), { type: 'followupAsk', question: 'q' },
      { type: 'followupEvent', event: { event: 'text', data: { name: 'followup', text: 'words' } } },
      { type: 'followupEvent', event: { event: 'crisis', data: CRISIS } },
    ], shown());
    expect(s).toMatchObject({ phase: 'crisis', followups: [], reading: null });
    const refused = run([counts(2, 8), { type: 'followupAsk', question: 'q' },
      { type: 'followupRefused', question: 'q', refusal: { type: 'crisis', payload: CRISIS } }], shown());
    expect(refused.phase).toBe('crisis');
  });

  it('puts a saved answer into a follow-up whose stream broke, and announces it', () => {
    const s = run([counts(2, 8), { type: 'followupAsk', question: 'q' },
      { type: 'followupEvent', event: { event: 'text', data: { name: 'followup', text: 'Half' } } },
      { type: 'followupRestored', followup: { n: 1, question: 'q', answer: 'Whole answer', soft_line: null } }], shown());
    expect(s.followups[0]).toMatchObject({ text: 'Whole answer', status: 'done' });
    expect(statusKey(s)).toBe('followupReady');
  });

  it('marks a follow-up whose stream broke', () => {
    const s = run([counts(2, 8), { type: 'followupAsk', question: 'q' }, { type: 'followupLost' }], shown());
    expect(s.followups[0].status).toBe('failed');
    expect(s.followupError).toBe('network');
  });
});

describe('transitionEvents', () => {
  it('reports night_open, cards_revealed and reading_shown once each', () => {
    const actions: NightAction[] = [{ type: 'open' }, created(), ...flips(3), text('headline', 'H'), done(), { type: 'streamEnded', outcome: 'done' }];
    const seen: string[] = [];
    let s = CLOSED;
    for (const a of actions) {
      const next = nightReducer(s, a);
      seen.push(...transitionEvents(s, next));
      s = next;
    }
    expect(seen).toEqual(['night_open', 'cards_revealed', 'reading_shown']);
  });
});
```

Create `site/src/lib/readingFlow.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { createApi } from './api';
import { CLOSED, nightReducer, type NightAction, type NightState } from './nightRoom';
import {
  DEFAULT_COUNTS, RESTORE_TRIES, askFollowup, loadCounts, restoreReading, startReading, streamReading, type FlowDeps,
} from './readingFlow';
import { brokenSseResponse, fakeFetch, jsonResponse, sseResponse, sseText } from './testing/fakes';

const CREATED = {
  id: 'r1', lang: 'en', kind: 'one', verdict: null, soft_line: null, remaining: 2,
  cards: [{ card_id: 'major-18-moon', position: 'card', reversed: false, name: 'The Moon' }],
};
const STREAM = sseText([
  ['meta', { reading_id: 'r1', soft_line: null }], ['section', { name: 'headline' }],
  ['text', { name: 'headline', text: 'Slow down.' }], ['done', { answer_shown: 'model' }],
]);
const VIEW = { id: 'r1', status: 'done', answer: { headline: 'Slow down.' }, answer_shown: 'model', retries_left: 0,
  soft_line: null, followups_left: 2, followup_attempts_left: 8, cards: CREATED.cards, kind: 'one', verdict: null,
  followups: [] as Array<{ n: number; question: string; answer: string | null; soft_line: string | null }> };

function harness(...responses: Array<Response | Error>) {
  const { fetch, calls } = fakeFetch(...responses);
  const actions: NightAction[] = [];
  const tokens: string[] = [];
  let state: NightState = nightReducer(CLOSED, { type: 'open' });
  const deps: FlowDeps = {
    api: createApi(fetch),
    dispatch: (a) => { actions.push(a); state = nightReducer(state, a); },
    turnstileToken: async (sitekey) => { tokens.push(sitekey); return sitekey === 'none' ? null : 'tok-1'; },
    sleep: async () => {},
    reducedMotion: true,
  };
  return { deps, calls, actions, tokens, state: () => state };
}

describe('startReading', () => {
  it('creates, streams and loads the follow-up counts', async () => {
    const h = harness(jsonResponse(201, CREATED), sseResponse(STREAM), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'one', tz: 'UTC' });
    expect(h.calls.map((c) => c.url)).toEqual(['/api/readings', '/api/readings/r1/stream?tz=UTC', '/api/readings/r1?tz=UTC']);
    expect(h.state()).toMatchObject({ phase: 'reading', stream: 'done', counts: { followups_left: 2, followup_attempts_left: 8 } });
    expect(h.state().answer.sections.headline).toBe('Slow down.');
  });

  it('runs the invisible Turnstile check on 403 and repeats the request with the token', async () => {
    const h = harness(jsonResponse(403, { reason: 'turnstile', sitekey: '0xSITE' }), jsonResponse(201, CREATED),
      sseResponse(STREAM), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.tokens).toEqual(['0xSITE']);
    expect(h.calls[1].body).toMatchObject({ turnstile_token: 'tok-1' });
    expect(h.state().stream).toBe('done');
  });

  it('shows the Turnstile error when no token comes', async () => {
    const h = harness(jsonResponse(403, { reason: 'turnstile', sitekey: 'none' }));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.state()).toMatchObject({ phase: 'error', error: 'turnstile' });
    expect(h.calls).toHaveLength(1);
  });

  it('goes to the Plus card on 429 limit and shows a crisis answer without a reading', async () => {
    const limit = harness(jsonResponse(429, { reason: 'limit', remaining: 0 }));
    await startReading(limit.deps, { lang: 'en', kind: 'three' });
    expect(limit.state().phase).toBe('limit');
    const crisis = harness(jsonResponse(200, { group: 'crisis', crisis: {}, helplines: { lines: [] }, remaining: 3 }));
    await startReading(crisis.deps, { lang: 'en', kind: 'three', question: '…' });
    expect(crisis.state()).toMatchObject({ phase: 'crisis', reading: null });
    expect(crisis.calls).toHaveLength(1);
  });
});

describe('a broken stream', () => {
  it('restores the answer the API kept writing', async () => {
    const h = harness(jsonResponse(201, CREATED), brokenSseResponse(sseText([['meta', {}]])),
      jsonResponse(200, { ...VIEW, status: 'streaming' }), jsonResponse(200, VIEW));
    await startReading(h.deps, { lang: 'en', kind: 'one' });
    expect(h.state()).toMatchObject({ stream: 'done', counts: { followups_left: 2 } });
    expect(h.actions.map((a) => a.type)).toContain('restored');
  });

  it('streams again when nobody is writing, without looping', async () => {
    const h = harness(jsonResponse(200, { ...VIEW, status: 'pending', answer: null }), brokenSseResponse(''));
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    await restoreReading(h.deps, 'r1', undefined);
    expect(h.calls.map((c) => c.url)).toEqual(['/api/readings/r1', '/api/readings/r1/stream']);
    expect(h.state().stream).toBe('lost');
  });

  it('gives up after a bounded number of tries', async () => {
    const h = harness(...Array.from({ length: RESTORE_TRIES }, () => new TypeError('offline')));
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    await restoreReading(h.deps, 'r1', undefined);
    expect(h.calls).toHaveLength(RESTORE_TRIES);
    expect(h.state().stream).toBe('lost');
  });

  it('keeps the saved answer when the API refuses a retry', async () => {
    const h = harness(jsonResponse(409, { reason: 'retries' }), jsonResponse(200, { ...VIEW, answer_shown: 'fallback', answer: { headline: 'Base' } }));
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    await streamReading(h.deps, 'r1', undefined, 'retry');
    expect(h.state()).toMatchObject({ phase: 'reading', stream: 'done' });
    expect(h.state().answer.sections).toEqual({ headline: 'Base' });
  });

  it('retries a fallback answer with POST /retry', async () => {
    const h = harness(sseResponse(STREAM), jsonResponse(200, VIEW));
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    await streamReading(h.deps, 'r1', 'UTC', 'retry');
    expect(h.calls[0]).toMatchObject({ url: '/api/readings/r1/retry?tz=UTC', method: 'POST' });
    expect(h.state().stream).toBe('done');
  });
});

describe('askFollowup', () => {
  const ready = (...responses: Array<Response | Error>) => {
    const h = harness(...responses);
    h.deps.dispatch({ type: 'created', reading: CREATED as never, reducedMotion: true });
    h.deps.dispatch({ type: 'stream', event: { event: 'text', data: { name: 'headline', text: 'H' } } });
    h.deps.dispatch({ type: 'stream', event: { event: 'done', data: { answer_shown: 'model' } } });
    return h;
  };

  it('sends the question with the same tz and streams the answer', async () => {
    const h = ready(sseResponse(sseText([['text', { name: 'followup', text: 'Yes, gently.' }],
      ['done', { answer_shown: 'model', followups_left: 1, followup_attempts_left: 7 }]])));
    await askFollowup(h.deps, 'r1', 'And work?', 'Europe/Madrid', false);
    expect(h.calls[0].body).toEqual({ question: 'And work?', tz: 'Europe/Madrid', use_reading: false });
    expect(h.state().followups[0]).toMatchObject({ text: 'Yes, gently.', status: 'done' });
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
  });

  it('asks for confirmation on 402 confirm and sends use_reading only after it', async () => {
    const h = ready(jsonResponse(402, { reason: 'confirm', remaining: 2 }),
      sseResponse(sseText([['done', { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true }]])));
    await askFollowup(h.deps, 'r1', 'More?', undefined, false);
    expect(h.state().confirm).toEqual({ question: 'More?', remaining: 2 });
    await askFollowup(h.deps, 'r1', 'More?', undefined, true);
    expect(h.calls[1].body).toEqual({ question: 'More?', use_reading: true });
    expect(h.state().remaining).toBe(1);
  });

  it('reads back the answer of a follow-up whose stream broke', async () => {
    const saved = { n: 1, question: 'q', answer: 'Saved answer.', soft_line: null };
    const h = ready(brokenSseResponse(sseText([['text', { name: 'followup', text: 'Sav' }]])),
      jsonResponse(200, { ...VIEW, status: 'done' }),
      jsonResponse(200, { ...VIEW, followups: [saved], followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', ' q ', undefined, false);
    expect(h.state().followups[0]).toMatchObject({ text: 'Saved answer.', status: 'done' });
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
    expect(h.state().followupError).toBeNull();
  });

  it('gives up on a lost follow-up after a bounded number of tries and resyncs the counts', async () => {
    const h = ready(brokenSseResponse(''), ...Array.from({ length: RESTORE_TRIES }, () => jsonResponse(200, VIEW)),
      jsonResponse(200, { ...VIEW, followups_left: 1, followup_attempts_left: 7 }));
    await askFollowup(h.deps, 'r1', 'q', undefined, false);
    expect(h.state().followups[0].status).toBe('failed');
    expect(h.state().followupError).toBe('network');
    expect(h.state().counts).toEqual({ followups_left: 1, followup_attempts_left: 7 });
  });

  it('offers follow-ups with the defaults when the counts cannot be read', async () => {
    const h = ready(new TypeError('offline'), new TypeError('offline'));
    await loadCounts(h.deps, 'r1', undefined);
    expect(h.state().counts).toEqual(DEFAULT_COUNTS);
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/answer.test.ts src/lib/nightRoom.test.ts src/lib/readingFlow.test.ts`
Expected: FAIL — `Error: Cannot find module './answer' imported from /app/src/lib/answer.test.ts` (and `./nightRoom`, `./readingFlow`).

- [ ] **Step 3: Write the modules**

Create `site/src/lib/answer.ts`:

```ts
// The reader's answer by sections (spec 4.2 §2.2): built from `text` events while it streams, replaced whole by
// `replace` / `fallback`, laid out in a fixed order for the screen. Texts are shown with textContent only.
import type { SseEvent } from './sse';
import type { DrawnCard, ReadingView } from './types';

export const SECTION_ORDER = ['headline', 'card1', 'card2', 'card3', 'synthesis', 'step', 'why'] as const;
export type SectionName = (typeof SECTION_ORDER)[number];
export type Sections = Partial<Record<SectionName, string>>;

export interface Answer {
  sections: Sections;
  started: boolean; // some text has arrived
  shown: 'model' | 'fallback' | null; // from `done` (or the restored reading)
  replaced: 'replace' | 'fallback' | null; // the last whole-answer replacement, if any
  retry: boolean; // a fallback answer that POST /retry may still replace
}

export const EMPTY_ANSWER: Answer = { sections: {}, started: false, shown: null, replaced: null, retry: false };

function isSection(name: unknown): name is SectionName {
  return typeof name === 'string' && (SECTION_ORDER as readonly string[]).includes(name);
}

export function pickSections(raw: unknown): Sections {
  const out: Sections = {};
  if (raw && typeof raw === 'object') {
    for (const [name, text] of Object.entries(raw)) if (isSection(name) && typeof text === 'string') out[name] = text;
  }
  return out;
}

export function applyAnswerEvent(answer: Answer, event: SseEvent): Answer {
  const data = (event.data && typeof event.data === 'object' ? event.data : {}) as Record<string, unknown>;
  switch (event.event) {
    case 'text': {
      if (!isSection(data.name) || typeof data.text !== 'string') return answer;
      const name = data.name;
      return { ...answer, started: true, sections: { ...answer.sections, [name]: (answer.sections[name] ?? '') + data.text } };
    }
    case 'replace':
    case 'fallback':
      return {
        ...answer,
        started: true,
        sections: pickSections(data.sections),
        replaced: event.event,
        retry: event.event === 'fallback' && data.retry === true,
      };
    case 'done':
      if (data.answer_shown === 'model' || data.answer_shown === 'fallback') return { ...answer, shown: data.answer_shown };
      return answer;
    default:
      return answer;
  }
}

/** The answer of GET /api/readings/{id} (after a broken stream). */
export function answerFromView(view: ReadingView): Answer {
  const shown = view.answer_shown === 'model' || view.answer_shown === 'fallback' ? view.answer_shown : null;
  return {
    sections: pickSections(view.answer),
    started: view.answer !== null,
    shown,
    replaced: shown === 'fallback' ? 'fallback' : null,
    retry: shown === 'fallback' && view.retries_left > 0,
  };
}

export type AnswerBlock =
  | { kind: 'headline' | 'synthesis' | 'step' | 'why'; text: string }
  | { kind: 'card'; text: string; card: DrawnCard };

/** What the screen shows, in order: headline, a block per drawn card, synthesis, one step, why. */
export function answerBlocks(answer: Answer, cards: readonly DrawnCard[]): AnswerBlock[] {
  const blocks: AnswerBlock[] = [];
  for (const name of SECTION_ORDER) {
    const text = answer.sections[name]?.trim();
    if (!text) continue;
    if (name === 'card1' || name === 'card2' || name === 'card3') {
      const card = cards[Number(name.slice(4)) - 1];
      if (card) blocks.push({ kind: 'card', text, card });
    } else {
      blocks.push({ kind: name, text });
    }
  }
  return blocks;
}
```

Create `site/src/lib/nightRoom.ts`:

```ts
// The night room as a state machine (spec 4.4a §4): opening → cards dealt → cards turn (≤ 1 s each) → the
// reader's answer streams → the answer by sections → follow-ups. Pure: the island dispatches actions and draws
// the state; timers and requests live in the island and in readingFlow.ts.
import { EMPTY_ANSWER, answerFromView, applyAnswerEvent, type Answer } from './answer';
import type { DictKey } from '../i18n';
import type { ErrorKind } from './errors';
import { applyFollowupEvent, followupOffer, newFollowup, type Followup, type FollowupRefusal, type Offer } from './followups';
import type { SseEvent } from './sse';
import type { CrisisPayload, FollowupCounts, ReadingCreated, ReadingView, SavedFollowup } from './types';

/** closed — not shown; limit — closed, the panel shows the Plus card (screen 11a) instead. */
export type Phase = 'closed' | 'opening' | 'reading' | 'crisis' | 'limit' | 'error';
export type StreamState = 'waiting' | 'streaming' | 'done' | 'restoring' | 'lost';

export const DEAL_MS = 600; // the room opens (--motion-night-open), then the first card turns
export const FLIP_INTERVAL_MS = 900; // one card after another, ≤ 1 s each (--motion-card-flip is 800 ms)

export interface NightState {
  phase: Phase;
  reading: ReadingCreated | null;
  revealed: number;
  answer: Answer;
  softLine: string | null;
  stream: StreamState;
  crisis: CrisisPayload | null;
  error: ErrorKind | null;
  counts: FollowupCounts | null;
  remaining: number | null; // readings left today (from creation; the paid warning uses 402 confirm's number)
  followups: Followup[];
  confirm: { question: string; remaining: number } | null;
  followupError: ErrorKind | null;
  followupPlus: boolean;
}

export const CLOSED: NightState = {
  phase: 'closed', reading: null, revealed: 0, answer: EMPTY_ANSWER, softLine: null, stream: 'waiting', crisis: null,
  error: null, counts: null, remaining: null, followups: [], confirm: null, followupError: null, followupPlus: false,
};

export type NightAction =
  | { type: 'open' }
  | { type: 'created'; reading: ReadingCreated; reducedMotion: boolean }
  | { type: 'crisis'; payload: CrisisPayload }
  | { type: 'failed'; error: ErrorKind }
  | { type: 'flip' }
  | { type: 'stream'; event: SseEvent }
  | { type: 'streamEnded'; outcome: 'done' | 'lost' }
  | { type: 'restoring' }
  | { type: 'restored'; view: ReadingView }
  | { type: 'retrying' }
  | { type: 'counts'; counts: FollowupCounts }
  | { type: 'followupAsk'; question: string }
  | { type: 'followupCancel' }
  | { type: 'followupEvent'; event: SseEvent }
  | { type: 'followupRefused'; question: string; refusal: FollowupRefusal }
  | { type: 'followupRestored'; followup: SavedFollowup }
  | { type: 'followupLost' }
  | { type: 'close' };

function toCrisis(state: NightState, payload: CrisisPayload): NightState {
  // nothing of the reading stays on screen: no cards, no answer, no follow-up text (spec 4.2 hand-off)
  return { ...CLOSED, phase: 'crisis', crisis: payload };
}

function lastFollowup(state: NightState, update: (f: Followup) => Followup): NightState {
  if (state.followups.length === 0) return state;
  const followups = state.followups.slice();
  followups[followups.length - 1] = update(followups[followups.length - 1]);
  return { ...state, followups };
}

export function nightReducer(state: NightState, action: NightAction): NightState {
  switch (action.type) {
    case 'open':
      return { ...CLOSED, phase: 'opening' };
    case 'created': {
      if (state.phase !== 'opening') return state;
      const n = action.reading.cards.length;
      return {
        ...state, phase: 'reading', reading: action.reading, revealed: action.reducedMotion ? n : 0,
        softLine: action.reading.soft_line, remaining: action.reading.remaining, stream: 'waiting',
      };
    }
    case 'crisis':
      return state.phase === 'closed' ? state : toCrisis(state, action.payload);
    case 'failed':
      if (state.phase === 'closed') return state;
      return action.error === 'limit' ? { ...CLOSED, phase: 'limit' } : { ...state, phase: 'error', error: action.error };
    case 'flip':
      if (state.phase !== 'reading' || !state.reading || state.revealed >= state.reading.cards.length) return state;
      return { ...state, revealed: state.revealed + 1 };
    case 'stream': {
      if (state.phase !== 'reading') return state;
      const { event } = action;
      const data = (event.data && typeof event.data === 'object' ? event.data : {}) as Record<string, unknown>;
      if (event.event === 'crisis') return toCrisis(state, data as unknown as CrisisPayload);
      if (event.event === 'meta') { // every stream starts again from nothing: a repeated stream never appends
        const softLine = typeof data.soft_line === 'string' ? data.soft_line : state.softLine;
        return { ...state, softLine, stream: 'streaming', answer: EMPTY_ANSWER };
      }
      if (event.event === 'error') return { ...state, stream: 'lost' };
      const answer = applyAnswerEvent(state.answer, event);
      return { ...state, answer, stream: event.event === 'done' ? 'done' : 'streaming' };
    }
    case 'streamEnded':
      if (state.phase !== 'reading' || state.stream === 'done') return state;
      return { ...state, stream: action.outcome };
    case 'restoring':
      return state.phase === 'reading' ? { ...state, stream: 'restoring' } : state;
    case 'restored': {
      if (state.phase !== 'reading') return state;
      const { view } = action;
      if (view.answer_shown === 'crisis') return toCrisis(state, view as unknown as CrisisPayload);
      return {
        ...state, answer: answerFromView(view), stream: 'done', softLine: view.soft_line ?? state.softLine,
        counts: { followups_left: view.followups_left, followup_attempts_left: view.followup_attempts_left },
      };
    }
    case 'retrying':
      return state.phase === 'reading' ? { ...state, answer: EMPTY_ANSWER, stream: 'waiting' } : state;
    case 'counts':
      return state.phase === 'reading' ? { ...state, counts: action.counts } : state;
    case 'followupAsk':
      if (state.phase !== 'reading') return state;
      return { ...state, confirm: null, followupError: null, followupPlus: false, followups: [...state.followups, newFollowup(action.question)] };
    case 'followupCancel':
      return { ...state, confirm: null };
    case 'followupEvent': {
      if (state.phase !== 'reading' || state.followups.length === 0) return state;
      const update = applyFollowupEvent(state.followups[state.followups.length - 1], action.event);
      if (update.crisis) return toCrisis(state, update.crisis);
      let next = lastFollowup(state, () => update.followup);
      if (update.counts) next = { ...next, counts: update.counts };
      if (action.event.event === 'done' && update.followup.usedReading === true && next.remaining !== null) {
        next = { ...next, remaining: Math.max(next.remaining - 1, 0) };
      }
      return next;
    }
    case 'followupRefused': {
      if (state.phase !== 'reading') return state;
      const { refusal } = action;
      if (refusal.type === 'crisis') return toCrisis(state, refusal.payload);
      const next = { ...state, followups: state.followups.slice(0, -1) }; // nothing was asked
      if (refusal.type === 'confirm') return { ...next, confirm: { question: action.question, remaining: refusal.remaining } };
      if (refusal.type === 'plus') return { ...next, followupPlus: true };
      return { ...next, followupError: refusal.error };
    }
    case 'followupRestored': // the stream broke but the API saved the answer (spec 4.2 §8.11)
      if (state.phase !== 'reading') return state;
      return lastFollowup({ ...state, followupError: null }, (f) => ({
        ...f, text: action.followup.answer ?? '', softLine: action.followup.soft_line, status: 'done',
      }));
    case 'followupLost':
      return lastFollowup({ ...state, followupError: 'network' }, (f) => (f.status === 'streaming' ? { ...f, status: 'failed' } : f));
    case 'close':
      return CLOSED;
  }
}

export function cardsCount(state: NightState): number {
  return state.reading ? state.reading.cards.length : 0;
}

export function allRevealed(state: NightState): boolean {
  return state.phase === 'reading' && state.reading !== null && state.revealed >= state.reading.cards.length;
}

/** The answer is on screen once every card is turned and some text has arrived. */
export function answerVisible(state: NightState): boolean {
  return allRevealed(state) && state.answer.started;
}

/** The whole answer is shown: the moment of the `reading_shown` event. */
export function readingShown(state: NightState): boolean {
  return answerVisible(state) && state.stream === 'done';
}

/** The polite status line (aria-live) for the current moment. */
export function statusKey(state: NightState): DictKey | null {
  if (state.phase === 'opening') return 'shuffling';
  if (state.phase !== 'reading') return null;
  if (state.stream === 'restoring') return 'restoring';
  if (state.stream === 'lost') return 'streamLost';
  if (!allRevealed(state)) return cardsCount(state) === 3 ? 'dealtThree' : 'dealtOne';
  if (!state.answer.started) return 'writing';
  if (state.stream !== 'done') return 'writing';
  const last = state.followups[state.followups.length - 1];
  if (last?.status === 'streaming') return 'writing';
  if (last?.status === 'done' || last?.status === 'replaced') return 'followupReady';
  return 'readingReady';
}

/** Which follow-up the room may offer now: only under a finished model answer, one at a time. */
export function followupNow(state: NightState): Offer {
  if (!readingShown(state) || state.answer.shown !== 'model') return 'none';
  if (state.followups.some((f) => f.status === 'streaming')) return 'none';
  return followupOffer(state.counts);
}

export type RoomEvent = 'night_open' | 'cards_revealed' | 'reading_shown';

/** Analytics events due on a transition (docs/design/analytics-events.md). */
export function transitionEvents(prev: NightState, next: NightState): RoomEvent[] {
  const events: RoomEvent[] = [];
  if (prev.phase !== 'opening' && next.phase === 'opening') events.push('night_open');
  if (!allRevealed(prev) && allRevealed(next)) events.push('cards_revealed');
  if (!readingShown(prev) && readingShown(next)) events.push('reading_shown');
  return events;
}
```

Create `site/src/lib/readingFlow.ts`:

```ts
// The requests behind the night room (spec 4.4a §4): create → (403 turnstile → token → create again) → stream;
// a broken stream is restored with GET /api/readings/{id} (wait while it is still being written, stream again if
// nobody is writing); POST /retry only after a fallback answer; follow-ups stream the same way and a broken one
// is read back from GET /api/readings/{id} too (the API keeps writing it, spec 4.2 §8.11).
import type { Api } from './api';
import { followupBody } from './followups';
import type { NightAction } from './nightRoom';
import type { CreateBody, FollowupCounts } from './types';

export interface FlowDeps {
  api: Api;
  dispatch: (action: NightAction) => void;
  turnstileToken: (sitekey: string) => Promise<string | null>;
  sleep: (ms: number) => Promise<void>;
  reducedMotion: boolean;
}

export const RESTORE_TRIES = 10;
export const RESTORE_WAIT_MS = 2000;
/** What a new reading allows (two free follow-ups, eight attempts); used only when the counts cannot be read —
 * the API still refuses what is not allowed (402 / 429). */
export const DEFAULT_COUNTS: FollowupCounts = { followups_left: 2, followup_attempts_left: 8 };

export async function startReading(deps: FlowDeps, body: CreateBody): Promise<void> {
  let result = await deps.api.createReading(body);
  if (result.type === 'error' && result.error === 'turnstile') {
    const sitekey = typeof result.body?.sitekey === 'string' ? result.body.sitekey : '';
    const token = sitekey ? await deps.turnstileToken(sitekey) : null;
    if (token) result = await deps.api.createReading({ ...body, turnstile_token: token });
  }
  if (result.type === 'crisis') {
    deps.dispatch({ type: 'crisis', payload: result.payload });
    return;
  }
  if (result.type === 'error') {
    deps.dispatch({ type: 'failed', error: result.error });
    return;
  }
  deps.dispatch({ type: 'created', reading: result.reading, reducedMotion: deps.reducedMotion });
  await streamReading(deps, result.reading.id, body.tz, 'stream');
}

export async function streamReading(deps: FlowDeps, id: string, tz: string | undefined, mode: 'stream' | 'retry',
  restoreOnLoss = true): Promise<void> {
  if (mode === 'retry') deps.dispatch({ type: 'retrying' });
  let done = false;
  let crisis = false;
  let failed = false;
  const onEvent = (event: { event: string; data: unknown }) => {
    if (event.event === 'done') done = true;
    if (event.event === 'crisis') crisis = true;
    if (event.event === 'error') failed = true;
    deps.dispatch({ type: 'stream', event });
  };
  const end = mode === 'stream' ? await deps.api.streamReading(id, tz, onEvent) : await deps.api.retryReading(id, tz, onEvent);
  if (end.type === 'error') {
    if (mode === 'retry' && restoreOnLoss) await restoreReading(deps, id, tz); // a refused retry keeps the saved answer
    else deps.dispatch({ type: 'failed', error: end.error });
    return;
  }
  if (crisis) return;
  if (done && !failed) {
    deps.dispatch({ type: 'streamEnded', outcome: 'done' });
    await loadCounts(deps, id, tz);
    return;
  }
  deps.dispatch({ type: 'streamEnded', outcome: 'lost' });
  if (restoreOnLoss) await restoreReading(deps, id, tz);
}

/** After a broken stream: the API keeps writing the answer (spec 4.2 §8.11), so read it back. */
export async function restoreReading(deps: FlowDeps, id: string, tz: string | undefined): Promise<void> {
  deps.dispatch({ type: 'restoring' });
  for (let attempt = 0; attempt < RESTORE_TRIES; attempt++) {
    const result = await deps.api.getReading(id, tz);
    if (result.ok && result.data.status === 'done') {
      deps.dispatch({ type: 'restored', view: result.data });
      return;
    }
    if (result.ok && result.data.status === 'pending') {
      await streamReading(deps, id, tz, 'stream', false);
      return;
    }
    if (!result.ok && result.error === 'gone') {
      deps.dispatch({ type: 'failed', error: 'gone' });
      return;
    }
    await deps.sleep(RESTORE_WAIT_MS);
  }
  deps.dispatch({ type: 'streamEnded', outcome: 'lost' });
}

export async function loadCounts(deps: FlowDeps, id: string, tz: string | undefined): Promise<void> {
  for (let attempt = 0; attempt < 2; attempt++) {
    const result = await deps.api.getReading(id, tz);
    if (result.ok) {
      deps.dispatch({ type: 'counts', counts: {
        followups_left: result.data.followups_left, followup_attempts_left: result.data.followup_attempts_left,
      } });
      return;
    }
    if (attempt === 0) await deps.sleep(RESTORE_WAIT_MS);
  }
  deps.dispatch({ type: 'counts', counts: DEFAULT_COUNTS });
}

/** A follow-up stream broke: read the answer the API saved (it is listed once it is complete). */
export async function restoreFollowup(deps: FlowDeps, id: string, question: string, tz: string | undefined): Promise<void> {
  const asked = question.trim();
  for (let attempt = 0; attempt < RESTORE_TRIES; attempt++) {
    const result = await deps.api.getReading(id, tz);
    if (result.ok) {
      const saved = result.data.followups?.[result.data.followups.length - 1];
      if (saved && saved.question === asked && saved.answer) {
        deps.dispatch({ type: 'followupRestored', followup: saved });
        deps.dispatch({ type: 'counts', counts: {
          followups_left: result.data.followups_left, followup_attempts_left: result.data.followup_attempts_left,
        } });
        return;
      }
    } else if (result.error === 'gone') {
      break;
    }
    await deps.sleep(RESTORE_WAIT_MS);
  }
  deps.dispatch({ type: 'followupLost' });
  await loadCounts(deps, id, tz);
}

export async function askFollowup(deps: FlowDeps, id: string, question: string, tz: string | undefined,
  useReading: boolean): Promise<void> {
  deps.dispatch({ type: 'followupAsk', question });
  let done = false;
  const result = await deps.api.postFollowup(id, followupBody(question, tz, useReading), (event) => {
    if (event.event === 'done') done = true;
    deps.dispatch({ type: 'followupEvent', event });
  });
  if (result.type === 'refused') {
    deps.dispatch({ type: 'followupRefused', question, refusal: result.refusal });
    return;
  }
  if (!done) await restoreFollowup(deps, id, question, tz);
}
```

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/answer.test.ts src/lib/nightRoom.test.ts src/lib/readingFlow.test.ts`
Expected: `Test Files  3 passed (3)`, `Tests  41 passed (41)`.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add site/src/lib/answer.ts site/src/lib/nightRoom.ts site/src/lib/readingFlow.ts \
  site/src/lib/answer.test.ts site/src/lib/nightRoom.test.ts site/src/lib/readingFlow.test.ts
git commit -m "feat(site): night-room state machine, answer sections and the request flow

Restore after a broken stream, retry after a fallback, Turnstile on 403, follow-ups with the paid warning.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Panel settings, Turnstile, analytics, focus trap, help lines, Card of the Day logic

**Files:**
- Create: `site/src/lib/panel.ts`, `site/src/lib/turnstile.ts`, `site/src/lib/analytics.ts`, `site/src/lib/focus.ts`, `site/src/lib/helplines.ts`, `site/src/lib/daily.ts`
- Test: `site/src/lib/panel.test.ts`, `site/src/lib/turnstile.test.ts`, `site/src/lib/analytics.test.ts`, `site/src/lib/focus.test.ts`, `site/src/lib/helplines.test.ts`, `site/src/lib/daily.test.ts`

**Interfaces:**
- Consumes: `t`, `DictKey` (Task 4); `ApiResult` (Task 5); `ErrorKind` (Task 5); `cardById`, `cardName`, `fallbackDailyCard`, `DeckCard` (Task 3); types (Task 3).
- Produces (`panel.ts`): `PanelPage = 'home' | 'one_card' | 'yes_no' | 'love' | 'card'`, `PanelConfig {page, lang, tool, entry: 'tool' | 'card_page', kind, countToggle, situations, topic: 'love' | null, cardId, labelKey, placeholderKey}`, `ONE_CARD_ANCHOR = '#una-carta'`, `QUESTION_MAX = 500`, `panelConfig(page, lang, cardId = null)`, `initialKind(config, hash) -> Kind`, `drawLabelKey(config, kind) -> DictKey`, `toolFor(config, kind) -> Tool` (one card on the Spanish home → `one_card`), `cardsFor(kind) -> 1 | 3`, `cleanQuestion(question)`, `buildCreateBody(config, {kind, question, situation, tz}) -> CreateBody`, `situationKey(situation) -> DictKey`.
- Produces (`turnstile.ts`): `TURNSTILE_SRC`, `TOKEN_TIMEOUT_MS = 15000`, `TurnstileApi`, `TurnstileHost {document, window}`, `loadTurnstile(host) -> Promise<TurnstileApi>` (adds the script once), `turnstileToken(sitekey, host) -> Promise<string | null>`, `resetTurnstileForTests()`.
- Produces (`analytics.ts`): `EventName` (the seven 4.4a events), `Params`, `AnalyticsEvent {name, tool, lang, params}`, `EVENTS_URL = '/api/events'`, `analyticsEvent(name, tool, lang, params = {})` (`plus_view` → `tool: null`), `Transport`, `browserTransport()`, `sendEvent(event, transport = browserTransport()) -> void` (never throws).
- Produces (`focus.ts`): `FOCUSABLE`, `trapIndex(count, current, backwards) -> number | null`, `handleDialogKey(event, container, onEscape) -> void`.
- Produces (`helplines.ts`): `telHref(number) -> string | null`, `smsHref(number) -> string | null`, `safeUrl(url) -> string | null` (https only), `canCall(line) -> boolean`, `canText(line) -> boolean` (channel `sms` without an `sms` keyword, e.g. 988).
- Produces (`daily.ts`): `DailyShown {card, name, reversed, text, day, fromBase}`, `BaseMeaning {card_id, upright}`, `DailyNext = {type: 'shown', shown} | {type: 'base'} | {type: 'error', error}`, `localIsoDay(date, timeZone?)`, `formatDay(isoDay, lang)`, `dailyNext(result, lang) -> DailyNext`, `shownFromBase(isoDay, lang, meanings) -> DailyShown | null`, `baseUrl(lang) -> '/data/daily-<lang>.json'`.

- [ ] **Step 1: Write the failing tests**

Create `site/src/lib/panel.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { t } from '../i18n';
import { buildCreateBody, cardsFor, drawLabelKey, initialKind, panelConfig, situationKey, toolFor } from './panel';
import { SITUATIONS } from './types';

describe('panelConfig', () => {
  it('draws three cards on the home pages, with the 1 / 3 toggle only in Spanish', () => {
    expect(panelConfig('home', 'en')).toMatchObject({ tool: 'home', kind: 'three', countToggle: false });
    expect(panelConfig('home', 'es')).toMatchObject({ tool: 'home', kind: 'three', countToggle: true });
  });

  it('sets up one card, yes/no, love and the card page', () => {
    expect(panelConfig('one_card', 'en')).toMatchObject({ tool: 'one_card', kind: 'one' });
    expect(panelConfig('yes_no', 'es')).toMatchObject({ tool: 'yes_no', kind: 'yes_no', labelKey: 'yesNoLabel' });
    expect(panelConfig('love', 'en')).toMatchObject({ tool: 'love', kind: 'three', topic: 'love', situations: true });
    expect(panelConfig('card', 'en', 'major-18-moon')).toMatchObject({
      tool: 'one_card', entry: 'card_page', kind: 'card_page', cardId: 'major-18-moon',
    });
  });

  it('counts one card on the Spanish home as the one-card tool', () => {
    expect(toolFor(panelConfig('home', 'es'), 'one')).toBe('one_card');
    expect(toolFor(panelConfig('home', 'es'), 'three')).toBe('home');
    expect(toolFor(panelConfig('card', 'en', 'x'), 'card_page')).toBe('one_card');
    expect(toolFor(panelConfig('yes_no', 'en'), 'yes_no')).toBe('yes_no');
  });

  it('starts the Spanish home with one card at #una-carta', () => {
    expect(initialKind(panelConfig('home', 'es'), '#una-carta')).toBe('one');
    expect(initialKind(panelConfig('home', 'es'), '')).toBe('three');
    expect(initialKind(panelConfig('home', 'en'), '#una-carta')).toBe('three');
  });
});

describe('draw button', () => {
  it('says what happens', () => {
    expect(t('en')[drawLabelKey(panelConfig('home', 'en'), 'three')]).toBe('Draw three cards');
    expect(t('es')[drawLabelKey(panelConfig('home', 'es'), 'one')]).toBe('Saca una carta');
    expect(t('en')[drawLabelKey(panelConfig('yes_no', 'en'), 'yes_no')]).toBe('Draw a card');
    expect(t('en')[drawLabelKey(panelConfig('love', 'en'), 'three')]).toBe('Draw for love');
    expect(t('es')[drawLabelKey(panelConfig('card', 'es', 'x'), 'card_page')]).toBe('Saca una carta para tu pregunta');
    expect(cardsFor('three')).toBe(3);
    expect(cardsFor('yes_no')).toBe(1);
  });
});

describe('buildCreateBody', () => {
  it('sends only what was given, the question trimmed and cut to 500', () => {
    expect(buildCreateBody(panelConfig('home', 'en'), { kind: 'three', question: '   ', situation: null, tz: undefined }))
      .toEqual({ lang: 'en', kind: 'three' });
    const long = 'a'.repeat(600);
    expect(buildCreateBody(panelConfig('one_card', 'es'), { kind: 'one', question: ` ${long} `, situation: null, tz: 'America/Bogota' }))
      .toEqual({ lang: 'es', kind: 'one', question: 'a'.repeat(500), tz: 'America/Bogota' });
  });

  it('adds the love topic and situation, and the card of a card page', () => {
    expect(buildCreateBody(panelConfig('love', 'en'), { kind: 'three', question: 'Closer?', situation: 'after_breakup', tz: 'UTC' }))
      .toEqual({ lang: 'en', kind: 'three', question: 'Closer?', topic: 'love', situation: 'after_breakup', tz: 'UTC' });
    expect(buildCreateBody(panelConfig('love', 'en'), { kind: 'three', question: '', situation: null, tz: undefined }))
      .toEqual({ lang: 'en', kind: 'three', topic: 'love' });
    expect(buildCreateBody(panelConfig('card', 'en', 'major-18-moon'), { kind: 'card_page', question: '', situation: null, tz: undefined }))
      .toEqual({ lang: 'en', kind: 'card_page', card_id: 'major-18-moon' });
  });

  it('names the four love situations of stage 3', () => {
    expect(SITUATIONS.map((s) => t('en')[situationKey(s)])).toEqual(['Single', 'In a relationship', 'After a breakup', "It's complicated"]);
  });
});
```

Create `site/src/lib/turnstile.test.ts`:

```ts
import { beforeEach, describe, expect, it } from 'vitest';
import { TURNSTILE_SRC, loadTurnstile, resetTurnstileForTests, turnstileToken, type TurnstileApi, type TurnstileHost } from './turnstile';

interface FakeEl { tagName: string; src?: string; async?: boolean; className?: string; onload?: () => void; onerror?: () => void; removed?: boolean; remove(): void }

function fakeHost(behaviour: 'token' | 'error' | 'silent' | 'noscript') {
  const appended: FakeEl[] = [];
  const timers: Array<() => void> = [];
  const api: TurnstileApi & { rendered: Record<string, unknown>[]; removed: string[] } = {
    rendered: [], removed: [],
    render(_el, options) {
      this.rendered.push(options);
      if (behaviour === 'token') (options.callback as (t: string) => void)('tok-1');
      if (behaviour === 'error') (options['error-callback'] as () => void)();
      return 'w1';
    },
    remove(id) { this.removed.push(id); },
  };
  const host = {
    document: {
      createElement: (tag: string) => ({ tagName: tag, remove() { this.removed = true; } }) as FakeEl,
      querySelector: () => null,
      head: { appendChild: (el: FakeEl) => { appended.push(el); if (behaviour === 'noscript') el.onerror!(); else { (host.window as { turnstile?: TurnstileApi }).turnstile = api; el.onload!(); } } },
      body: { appendChild: (el: FakeEl) => { appended.push(el); } },
    },
    window: {
      turnstile: undefined as TurnstileApi | undefined,
      setTimeout: ((fn: () => void) => { timers.push(fn); return 1; }) as unknown as typeof setTimeout,
      clearTimeout: (() => {}) as typeof clearTimeout,
    },
  };
  return { host: host as unknown as TurnstileHost, appended, api, timers };
}

beforeEach(() => resetTurnstileForTests());

describe('turnstile', () => {
  it('loads the script only when asked, once', async () => {
    const { host, appended } = fakeHost('token');
    expect(appended).toHaveLength(0);
    const [a, b] = await Promise.all([loadTurnstile(host), loadTurnstile(host)]);
    expect(a).toBe(b);
    const scripts = appended.filter((el) => el.tagName === 'script');
    expect(scripts).toHaveLength(1);
    expect(scripts[0].src).toBe(TURNSTILE_SRC);
  });

  it('gets a token from the invisible widget with the API’s site key and cleans up', async () => {
    const { host, api, appended } = fakeHost('token');
    expect(await turnstileToken('0xSITE', host)).toBe('tok-1');
    expect(api.rendered[0].sitekey).toBe('0xSITE');
    expect(appended.find((el) => el.className === 'turnstile-slot')!.removed).toBe(true);
  });

  it('gives null when the check fails, times out or the script is blocked', async () => {
    expect(await turnstileToken('k', fakeHost('error').host)).toBeNull();
    const silent = fakeHost('silent');
    const pending = turnstileToken('k', silent.host);
    while (silent.timers.length === 0) await new Promise((r) => setTimeout(r, 0));
    silent.timers.forEach((fire) => fire());
    expect(await pending).toBeNull();
    resetTurnstileForTests();
    expect(await turnstileToken('k', fakeHost('noscript').host)).toBeNull();
  });
});
```

Create `site/src/lib/analytics.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { EVENTS_URL, analyticsEvent, sendEvent } from './analytics';

describe('analyticsEvent', () => {
  it('builds the whitelisted shape', () => {
    expect(analyticsEvent('draw_click', 'yes_no', 'es', { has_question: true, entry: 'tool' })).toEqual({
      name: 'draw_click', tool: 'yes_no', lang: 'es', params: { has_question: true, entry: 'tool' },
    });
    expect(analyticsEvent('tool_view', 'home', 'en')).toEqual({ name: 'tool_view', tool: 'home', lang: 'en', params: {} });
  });

  it('sends plus_view without a tool', () => {
    expect(analyticsEvent('plus_view', 'home', 'en', { place: 'limit' }).tool).toBeNull();
  });
});

describe('sendEvent', () => {
  const event = analyticsEvent('reading_shown', 'home', 'en', { ms_from_draw: 4200 });

  it('uses sendBeacon with a JSON blob', async () => {
    const sent: Array<[string, Blob]> = [];
    sendEvent(event, { sendBeacon: (url, data) => { sent.push([url, data]); return true; }, fetch: () => { throw new Error('no'); } });
    expect(sent[0][0]).toBe(EVENTS_URL);
    expect(sent[0][1].type).toBe('application/json');
    expect(JSON.parse(await sent[0][1].text())).toEqual(event);
  });

  it('falls back to fetch with keepalive and without cookies when the beacon is refused', () => {
    const calls: Array<[string, RequestInit]> = [];
    sendEvent(event, { sendBeacon: () => false, fetch: async (url, init) => { calls.push([url, init]); } });
    expect(calls[0][0]).toBe(EVENTS_URL);
    expect(calls[0][1]).toMatchObject({ method: 'POST', keepalive: true, credentials: 'omit' });
  });

  it('never throws', () => {
    expect(() => sendEvent(event, { sendBeacon: () => { throw new Error('x'); }, fetch: () => Promise.reject(new Error('y')) })).not.toThrow();
    expect(() => sendEvent(event, {})).not.toThrow();
  });
});
```

Create `site/src/lib/focus.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { trapIndex } from './focus';

describe('trapIndex', () => {
  it('wraps Tab from the last element to the first and Shift+Tab back', () => {
    expect(trapIndex(4, 3, false)).toBe(0);
    expect(trapIndex(4, 0, true)).toBe(3);
  });

  it('lets the browser move inside the dialog', () => {
    expect(trapIndex(4, 1, false)).toBeNull();
    expect(trapIndex(4, 2, true)).toBeNull();
  });

  it('pulls focus back in from outside, and does nothing without focusables', () => {
    expect(trapIndex(3, -1, false)).toBe(0);
    expect(trapIndex(3, -1, true)).toBe(2);
    expect(trapIndex(0, -1, false)).toBeNull();
  });
});
```

Create `site/src/lib/helplines.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { canCall, canText, safeUrl, smsHref, telHref } from './helplines';
import type { HelpLine } from './types';

describe('help lines', () => {
  it('dials only digits', () => {
    expect(telHref('800 911 2000')).toBe('tel:8009112000');
    expect(telHref('1-800-799-7233')).toBe('tel:18007997233');
    expect(telHref('988')).toBe('tel:988');
    expect(telHref('+34 024')).toBe('tel:+34024');
    expect(telHref('call us')).toBeNull();
  });

  it('texts 988 from the same digits when the line names no keyword', () => {
    expect(smsHref('988')).toBe('sms:988');
    expect(smsHref('none')).toBeNull();
    const line = { name: '988', number: '988', channels: ['call', 'sms'], hours: '24/7', topic: 'crisis', purpose: 'p' } as HelpLine;
    expect(canText(line)).toBe(true);
    expect(canText({ ...line, sms: 'START to 88788' })).toBe(false);
    expect(canText({ ...line, channels: ['call'] })).toBe(false);
  });

  it('opens only https addresses', () => {
    expect(safeUrl('https://findahelpline.com')).toBe('https://findahelpline.com/');
    expect(safeUrl('javascript:alert(1)')).toBeNull();
    expect(safeUrl('http://example.com')).toBeNull();
    expect(safeUrl(undefined)).toBeNull();
  });

  it('offers a call only for lines that take calls', () => {
    const line = { name: 'Línea 024', number: '024', channels: ['call'], hours: '24/7', topic: 'crisis', purpose: 'p' } as HelpLine;
    expect(canCall(line)).toBe(true);
    expect(canCall({ ...line, channels: ['web'] })).toBe(false);
    expect(canCall({ ...line, number: undefined })).toBe(false);
  });
});
```

Create `site/src/lib/daily.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { fallbackDailyCard } from './deck';
import { baseUrl, dailyNext, formatDay, localIsoDay, shownFromBase } from './daily';

const DAILY = { day: '2026-11-20', card: { card_id: 'major-19-sun', name: 'El Sol', reversed: true }, text: 'Hoy…', source: 'cache' as const };

describe('dailyNext', () => {
  it('shows the API card with its text', () => {
    const next = dailyNext({ ok: true, status: 200, data: DAILY }, 'es');
    expect(next.type).toBe('shown');
    if (next.type === 'shown') {
      expect(next.shown).toMatchObject({ name: 'El Sol', reversed: true, text: 'Hoy…', day: '2026-11-20', fromBase: false });
      expect(next.shown.card.image).toBe('the-sun');
    }
  });

  it('falls back to the card base on 503 and reports other errors', () => {
    expect(dailyNext({ ok: false, status: 503, error: 'unavailable', body: { reason: 'db' } }, 'en')).toEqual({ type: 'base' });
    expect(dailyNext({ ok: false, status: 429, error: 'busy', body: { reason: 'rate' } }, 'en')).toEqual({ type: 'error', error: 'busy' });
    expect(dailyNext({ ok: true, status: 200, data: { ...DAILY, card: { ...DAILY.card, card_id: 'nope' } } }, 'en').type).toBe('error');
  });
});

describe('the card from the base', () => {
  it('is the day’s card, upright, with its meaning', () => {
    const card = fallbackDailyCard('2026-11-20');
    const shown = shownFromBase('2026-11-20', 'en', [{ card_id: card.card_id, upright: 'Meaning.' }]);
    expect(shown).toMatchObject({ card, name: card.name_en, reversed: false, text: 'Meaning.', fromBase: true });
    expect(shownFromBase('2026-11-20', 'en', [])).toBeNull();
    expect(baseUrl('es')).toBe('/data/daily-es.json');
  });
});

describe('days', () => {
  it('takes the local date in the person’s time zone', () => {
    const late = new Date('2026-11-21T03:30:00Z');
    expect(localIsoDay(late, 'America/Mexico_City')).toBe('2026-11-20');
    expect(localIsoDay(late, 'Europe/Madrid')).toBe('2026-11-21');
  });

  it('writes the day in the page language', () => {
    expect(formatDay('2026-11-13', 'en')).toMatch(/Friday,? 13 November/);
    expect(formatDay('2026-11-13', 'es')).toMatch(/viernes, 13 de noviembre/);
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/panel.test.ts src/lib/turnstile.test.ts src/lib/analytics.test.ts src/lib/focus.test.ts src/lib/helplines.test.ts src/lib/daily.test.ts`
Expected: FAIL — `Error: Cannot find module './panel' imported from /app/src/lib/panel.test.ts` (and the other five modules).

- [ ] **Step 3: Write the modules**

Create `site/src/lib/panel.ts`:

```ts
// The draw panel of each page (spec 4.4a §3): which kind it draws, which choices it offers, the button label and
// the body of POST /api/readings. One place for every page, so the pages only name themselves.
import type { DictKey } from '../i18n';
import type { CreateBody, Kind, Lang, Situation, Tool } from './types';

export type PanelPage = 'home' | 'one_card' | 'yes_no' | 'love' | 'card';

export interface PanelConfig {
  page: PanelPage;
  lang: Lang;
  tool: Tool;
  entry: 'tool' | 'card_page';
  kind: Kind; // the kind drawn when nothing else is chosen
  countToggle: boolean; // Spanish home: "1 carta / 3 cartas"
  situations: boolean; // love: the situation chips
  topic: 'love' | null;
  cardId: string | null; // a card page: the card it is drawn from
  labelKey: DictKey;
  placeholderKey: DictKey;
}

export const ONE_CARD_ANCHOR = '#una-carta';
export const QUESTION_MAX = 500;

export function panelConfig(page: PanelPage, lang: Lang, cardId: string | null = null): PanelConfig {
  const base = { page, lang, entry: 'tool' as const, countToggle: false, situations: false, topic: null, cardId: null,
    labelKey: 'questionLabel' as DictKey };
  switch (page) {
    case 'home':
      return { ...base, tool: 'home', kind: 'three', countToggle: lang === 'es', placeholderKey: 'homePlaceholder' };
    case 'one_card':
      return { ...base, tool: 'one_card', kind: 'one', placeholderKey: 'oneCardPlaceholder' };
    case 'yes_no':
      return { ...base, tool: 'yes_no', kind: 'yes_no', labelKey: 'yesNoLabel', placeholderKey: 'yesNoPlaceholder' };
    case 'love':
      return { ...base, tool: 'love', kind: 'three', situations: true, topic: 'love', placeholderKey: 'lovePlaceholder' };
    case 'card':
      return { ...base, tool: 'one_card', entry: 'card_page', kind: 'card_page', cardId, placeholderKey: 'cardPlaceholder' };
  }
}

/** The kind on load: the Spanish home opened at #una-carta starts with one card. */
export function initialKind(config: PanelConfig, hash: string): Kind {
  return config.countToggle && hash === ONE_CARD_ANCHOR ? 'one' : config.kind;
}

export function drawLabelKey(config: PanelConfig, kind: Kind): DictKey {
  if (config.page === 'card') return 'drawForQuestion';
  if (config.page === 'love') return 'drawLove';
  return kind === 'three' ? 'drawThree' : 'drawOne';
}

/** The tool an event names: one card drawn on the Spanish home counts as one card (plan review M9). */
export function toolFor(config: PanelConfig, kind: Kind): Tool {
  return config.countToggle && kind === 'one' ? 'one_card' : config.tool;
}

export function cardsFor(kind: Kind): 1 | 3 {
  return kind === 'three' ? 3 : 1;
}

export function cleanQuestion(question: string): string {
  return question.trim().slice(0, QUESTION_MAX);
}

export function buildCreateBody(config: PanelConfig, input: { kind: Kind; question: string; situation: Situation | null;
  tz: string | undefined }): CreateBody {
  const body: CreateBody = { lang: config.lang, kind: input.kind };
  const question = cleanQuestion(input.question);
  if (question) body.question = question;
  if (config.topic) body.topic = config.topic;
  if (config.situations && input.situation) body.situation = input.situation;
  if (config.cardId) body.card_id = config.cardId;
  if (input.tz) body.tz = input.tz;
  return body;
}

export function situationKey(situation: Situation): DictKey {
  const keys: Record<Situation, DictKey> = {
    single: 'sitSingle', relationship: 'sitRelationship', after_breakup: 'sitAfterBreakup', complicated: 'sitComplicated',
  };
  return keys[situation];
}
```

Create `site/src/lib/turnstile.ts`:

```ts
// Cloudflare Turnstile, invisible (spec 4.2 §4.2, spec 4.4a §4): the script is loaded only after the API answered
// 403 {"reason": "turnstile", "sitekey": ...}; the site key comes from that answer (TURNSTILE_SITEKEY on the
// server), so the site holds no key of its own.

export const TURNSTILE_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
export const TOKEN_TIMEOUT_MS = 15000;

export interface TurnstileApi {
  render(container: HTMLElement, options: Record<string, unknown>): string | undefined;
  remove(widgetId: string): void;
}

export interface TurnstileHost {
  document: Pick<Document, 'createElement' | 'querySelector' | 'body' | 'head'>;
  window: { turnstile?: TurnstileApi; setTimeout: typeof setTimeout; clearTimeout: typeof clearTimeout };
}

let loading: Promise<TurnstileApi> | null = null;

/** Adds the script once; later calls share the same promise. */
export function loadTurnstile(host: TurnstileHost): Promise<TurnstileApi> {
  if (host.window.turnstile) return Promise.resolve(host.window.turnstile);
  if (loading) return loading;
  loading = new Promise<TurnstileApi>((resolve, reject) => {
    const script = host.document.createElement('script');
    script.src = TURNSTILE_SRC;
    script.async = true;
    script.onload = () => (host.window.turnstile ? resolve(host.window.turnstile) : reject(new Error('turnstile missing')));
    script.onerror = () => {
      loading = null;
      reject(new Error('turnstile script failed'));
    };
    host.document.head.appendChild(script);
  });
  return loading;
}

/** A token from an invisible widget, or null (script blocked, check failed, no answer in time). */
export async function turnstileToken(sitekey: string, host: TurnstileHost): Promise<string | null> {
  let api: TurnstileApi;
  try {
    api = await loadTurnstile(host);
  } catch {
    return null;
  }
  const container = host.document.createElement('div');
  container.className = 'turnstile-slot';
  host.document.body.appendChild(container);
  return new Promise<string | null>((resolve) => {
    let widgetId: string | undefined;
    const finish = (token: string | null) => {
      host.window.clearTimeout(timer);
      if (widgetId) api.remove(widgetId);
      container.remove();
      resolve(token);
    };
    const timer = host.window.setTimeout(() => finish(null), TOKEN_TIMEOUT_MS);
    try {
      widgetId = api.render(container, {
        sitekey,
        callback: (token: string) => finish(token),
        'error-callback': () => finish(null),
        'timeout-callback': () => finish(null),
      });
    } catch {
      finish(null);
    }
  });
}

/** For tests: forget the loaded script. */
export function resetTurnstileForTests(): void {
  loading = null;
}
```

Create `site/src/lib/analytics.ts`:

```ts
// Our own event counter (spec 4.4a §6, docs/design/analytics-events.md): POST /api/events with
// {"name", "tool", "lang", "params"} by navigator.sendBeacon, else fetch with keepalive. No cookie, no id, no
// question text; a failure never reaches the reading.
import type { Lang, Tool } from './types';

export type EventName = 'tool_view' | 'draw_click' | 'night_open' | 'cards_revealed' | 'reading_shown'
  | 'more_about_cards' | 'plus_view';

export type Params = Record<string, string | number | boolean>;

export interface AnalyticsEvent {
  name: EventName;
  tool: Tool | null;
  lang: Lang;
  params: Params;
}

export const EVENTS_URL = '/api/events';

/** plus_view carries no tool (its only parameter is `place`); every other 4.4a event names its tool. */
export function analyticsEvent(name: EventName, tool: Tool, lang: Lang, params: Params = {}): AnalyticsEvent {
  return { name, tool: name === 'plus_view' ? null : tool, lang, params };
}

export interface Transport {
  sendBeacon?: (url: string, data: Blob) => boolean;
  fetch?: (url: string, init: RequestInit) => Promise<unknown>;
}

export function browserTransport(): Transport {
  const nav = typeof navigator === 'undefined' ? undefined : navigator;
  return {
    sendBeacon: nav && typeof nav.sendBeacon === 'function' ? (url, data) => nav.sendBeacon(url, data) : undefined,
    fetch: typeof fetch === 'function' ? (url, init) => fetch(url, init) : undefined,
  };
}

export function sendEvent(event: AnalyticsEvent, transport: Transport = browserTransport()): void {
  const body = JSON.stringify(event);
  try {
    if (transport.sendBeacon?.(EVENTS_URL, new Blob([body], { type: 'application/json' }))) return;
  } catch {
    // fall through to fetch
  }
  try {
    transport.fetch?.(EVENTS_URL, {
      method: 'POST', body, headers: { 'content-type': 'application/json' }, keepalive: true, credentials: 'omit',
    })?.catch(() => {});
  } catch {
    // the counter never breaks the page
  }
}
```

Create `site/src/lib/focus.ts`:

```ts
// Focus kept inside the night room (00-design.md: focus trapped, Escape closes, focus returns to the draw button).

export const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Where Tab must go so that focus stays inside: the index to focus, or null to let the browser move on.
 * `current` is the index of the focused element among `count` focusables (-1: focus is outside). */
export function trapIndex(count: number, current: number, backwards: boolean): number | null {
  if (count === 0) return null;
  if (current < 0) return backwards ? count - 1 : 0;
  if (backwards && current === 0) return count - 1;
  if (!backwards && current === count - 1) return 0;
  return null;
}

/** Keydown inside a dialog: Escape → onEscape; Tab at the edges wraps around. */
export function handleDialogKey(event: KeyboardEvent, container: HTMLElement, onEscape: () => void): void {
  if (event.key === 'Escape') {
    event.preventDefault();
    onEscape();
    return;
  }
  if (event.key !== 'Tab') return;
  const items = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => !el.hasAttribute('inert'));
  const target = trapIndex(items.length, items.indexOf(document.activeElement as HTMLElement), event.shiftKey);
  if (target !== null) {
    event.preventDefault();
    items[target].focus();
  }
}
```

Create `site/src/lib/helplines.ts`:

```ts
// Help lines from the API's crisis answer (spec 4.2 §3.2): links are built only from digits and https addresses.
import type { HelpLine } from './types';

/** "tel:" + the digits (and a leading +) of a number such as "800 911 2000" or "1-800-799-7233". */
export function telHref(number: string): string | null {
  const digits = number.replace(/[^\d+]/g, '').replace(/(?!^)\+/g, '');
  return /\d{3,}/.test(digits) ? `tel:${digits}` : null;
}

/** "sms:" + the same digits, for a line that takes texts but names no SMS keyword (988 in the US). */
export function smsHref(number: string): string | null {
  const tel = telHref(number);
  return tel ? `sms:${tel.slice(4)}` : null;
}

export function canText(line: HelpLine): boolean {
  return Boolean(line.number) && line.channels.includes('sms') && !line.sms;
}

export function safeUrl(url: string | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' ? parsed.href : null;
  } catch {
    return null;
  }
}

export function canCall(line: HelpLine): boolean {
  return Boolean(line.number) && line.channels.includes('call');
}
```

Create `site/src/lib/daily.ts`:

```ts
// Card of the Day (spec 4.4a §5): GET /api/daily → tap the back → the card and its text for today. When the API
// answers 503 (no database), the site shows a card from the card base instead: the same card for everyone that
// local day, upright, with its short meaning (fetched from /data/daily-<lang>.json only at that moment).
import type { ApiResult } from './api';
import { cardById, cardName, fallbackDailyCard, type DeckCard } from './deck';
import type { ErrorKind } from './errors';
import type { DailyCard, Lang } from './types';

export interface DailyShown {
  card: DeckCard;
  name: string;
  reversed: boolean;
  text: string;
  day: string;
  fromBase: boolean; // true: the site's own card from the base (the API was unavailable)
}

export interface BaseMeaning {
  card_id: string;
  upright: string;
}

export type DailyNext = { type: 'shown'; shown: DailyShown } | { type: 'base' } | { type: 'error'; error: ErrorKind };

/** YYYY-MM-DD of `date` in the person's time zone. */
export function localIsoDay(date: Date, timeZone?: string): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)!.value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}

/** "Friday, 20 November" / "viernes, 20 de noviembre". */
export function formatDay(isoDay: string, lang: Lang): string {
  const date = new Date(`${isoDay}T12:00:00Z`);
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-GB' : 'es-MX', {
    weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC',
  }).format(date);
}

export function dailyNext(result: ApiResult<DailyCard>, lang: Lang): DailyNext {
  if (result.ok) {
    const card = cardById(result.data.card.card_id);
    if (!card) return { type: 'error', error: 'other' };
    return { type: 'shown', shown: {
      card, name: result.data.card.name || cardName(card, lang), reversed: result.data.card.reversed,
      text: result.data.text, day: result.data.day, fromBase: false,
    } };
  }
  return result.error === 'unavailable' ? { type: 'base' } : { type: 'error', error: result.error };
}

export function shownFromBase(isoDay: string, lang: Lang, meanings: readonly BaseMeaning[]): DailyShown | null {
  const card = fallbackDailyCard(isoDay);
  const meaning = meanings.find((m) => m.card_id === card.card_id);
  if (!meaning) return null;
  return { card, name: cardName(card, lang), reversed: false, text: meaning.upright, day: isoDay, fromBase: true };
}

export function baseUrl(lang: Lang): string {
  return `/data/daily-${lang}.json`;
}
```

- [ ] **Step 4: Run the tests**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/panel.test.ts src/lib/turnstile.test.ts src/lib/analytics.test.ts src/lib/focus.test.ts src/lib/helplines.test.ts src/lib/daily.test.ts`
Expected: `Test Files  6 passed (6)`, `Tests  28 passed (28)`.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add site/src/lib/panel.ts site/src/lib/turnstile.ts site/src/lib/analytics.ts site/src/lib/focus.ts \
  site/src/lib/helplines.ts site/src/lib/daily.ts site/src/lib/panel.test.ts site/src/lib/turnstile.test.ts \
  site/src/lib/analytics.test.ts site/src/lib/focus.test.ts site/src/lib/helplines.test.ts site/src/lib/daily.test.ts
git commit -m "feat(site): panel settings, Turnstile on demand, event sending, focus trap, Card of the Day logic

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Layout, header and menu, footer, language switch, 404 pages

**Files:**
- Modify: `docs/design/00-design.md` (the focus-ring rule)
- Create: `site/src/styles/global.css`, `site/src/layouts/Base.astro`, `site/src/components/Header.astro`, `site/src/components/Footer.astro`, `site/src/components/LangSwitch.astro`, `site/src/components/MoonMark.astro`, `site/src/components/CardFigure.astro`, `site/src/components/ui/icons.tsx`, `site/src/islands/MenuToggle.tsx`, `site/src/views/NotFoundView.astro`, `site/src/pages/404.astro`, `site/src/pages/es/404.astro`
- Test: `site/src/lib/guards.test.ts`

**Interfaces:**
- Consumes: `t`, `fill`, `DictKey` (Task 4); `NAV_KEYS`, `pagePath`, `switchPath`, `HELP_URL`, `PageKey` (Task 3); `cardImage`, `cardName`, `cardSrcset`, `DeckCard` (Task 3); `site/src/styles/tokens.css` (Task 2).
- Produces:
  - `Base.astro` props `{lang: Lang, title: string, path: string, current?: PageKey}` — `<html lang>`, title, Google Fonts, tokens + global CSS, skip link to `#main`, header, `<main id="main" class="container">`, footer.
  - `CardFigure.astro` props `{card: DeckCard, lang: Lang, sizes: string, eager?: boolean}`.
  - `icons.tsx`: `CloseIcon`, `MenuIcon`, `CheckIcon`, `VerdictIcon({value})` (check / cross / hourglass).
  - Island `MenuToggle` (default export) props `{lang, navId}`; the nav element with id `navId` gets class `is-open`.
  - CSS classes later tasks use: `.night-panel`, `.field`, `.field__label`, `.input`, `.input--day`, `.btn` + `--gold` / `--ink` / `--outline` / `--text` / `--block`, `.chips`, `.chip`, `.backs`, `.panel-hint`, `.card-frame`, `.card-frame__art`, `.card-frame__name`, `.night-room`, `.night`, `.night__top`, `.night__question`, `.night__title`, `.night__status`, `.close-button`, `.spread`, `.spread--one`, `.spread__slot`, `.spread__pos`, `.flip`, `.flip.is-turned`, `.flip__inner`, `.flip__side`, `.flip__side--face`, `.deck-shuffle`, `.night__body`, `.night__cards`, `.night__text`, `.spread--small`, `.answer__headline`, `.answer__soft`, `.answer__label`, `.answer__text`, `.answer__synthesis`, `.verdict`, `.verdict__word`, `.more-cards`, `.night__actions`, `.night__foot`, `.followups`, `.followup__q`, `.followup__a`, `.followup-form`, `.notice`, `.crisis`, `.helplines`, `.plus-slot`, `.plus`, `.plus__card`, `.plus__row`, `.plus__daily`, `.help-line`, `.daily`, `.daily__back`, `.daily__text`, `.card-page`, `.card-page__art`, `.card-page__text`, `.keywords`, `.card-nav`, `.page-hero`, `.page-section`, `.tool-layout`, `.eyebrow`, `.display`, `.display--home`, `.lead`, `.h2`, `.small`, `.muted`, `.link-list`, `.card-row`, `.steps`, `.tile`, `.visually-hidden`, `body.is-locked`, `.turnstile-slot` (z-index 40, above the room). Focus ring: `currentColor`, but `--color-night-text` inside `.night-panel`, `.night`, `.daily` and `--color-day-text` inside `.plus-slot`, `.plus__card`.
  - `guards.test.ts` scans `site/src` (no `innerHTML`/`set:html`, no colour literals outside `tokens.css`, no secrets, no `EventSource`, Turnstile only in `turnstile.ts`) — it covers the files of Tasks 9–10 too.

- [ ] **Step 1: Write the failing test**

Create `site/src/lib/guards.test.ts`:

```ts
// Rules for every source file of the site (00-design.md "Правила для кода", spec 4.4a §4, §7).
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

const SOURCES = files('src').filter((p) => /\.(ts|tsx|astro|css|mjs)$/.test(p) && !p.endsWith('.test.ts') && !p.includes('/testing/'));
const read = (p: string) => readFileSync(p, 'utf-8');

describe('site sources', () => {
  it('never put text in as markup', () => {
    for (const path of SOURCES) expect(read(path), path).not.toMatch(/innerHTML|dangerouslySetInnerHTML|set:html|insertAdjacentHTML|outerHTML/);
  });

  it('take colours only from the tokens', () => {
    for (const path of SOURCES.filter((p) => !p.endsWith('tokens.css'))) {
      expect(read(path), path).not.toMatch(/#[0-9a-fA-F]{3,8}\b(?![\w-])|rgba?\(|hsla?\(/);
    }
  });

  it('hold no secrets and no key of their own', () => {
    for (const path of [...SOURCES, 'astro.config.mjs', 'package.json']) {
      expect(read(path), path).not.toMatch(/sk-ant|TURNSTILE_SECRET|SUPABASE_SERVICE|service_role|0x4AAAA|ANTHROPIC_API_KEY/);
    }
  });

  it('read streams with fetch, never EventSource', () => {
    for (const path of SOURCES) expect(read(path), path).not.toMatch(/new EventSource/);
  });

  it('load the Turnstile script only from src/lib/turnstile.ts', () => {
    const users = SOURCES.filter((p) => read(p).includes('challenges.cloudflare.com'));
    expect(users).toEqual([join('src', 'lib', 'turnstile.ts')]);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run src/lib/guards.test.ts`
Expected: `Tests  5 passed (5)` — a guard, not a feature test: the sources so far already keep the rules, and from now on it fails for any file of this task or of Tasks 9–10 that writes markup from text, uses a colour outside the tokens, holds a secret, uses `EventSource` or loads Turnstile elsewhere.

- [ ] **Step 3: Write the styles, the layout and its parts**

Create `site/src/styles/global.css`:

```css
/* Arcana Diary, stage 4.4a. Colours, type, spacing, radii and motion come only from tokens.css
   (docs/design/tokens.json); overlays mix token colours with transparency. Phone first; desktop from 900px. */

*, *::before, *::after { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  background: var(--color-day-bg);
  color: var(--color-day-text);
  font-family: var(--font-text);
  font-size: var(--font-size-body);
  line-height: 1.5;
}

body.is-locked { overflow: hidden; }

img { max-width: 100%; display: block; }

a { color: var(--color-day-accent); }

:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
/* The ring takes the text colour of the surface it sits on, not of the control: a gold button or a pressed chip has
   night-blue text, the ink button white text, and currentColor would vanish there (plan review I2). */
.night-panel :focus-visible, .night :focus-visible, .daily :focus-visible { outline-color: var(--color-night-text); }
.plus-slot :focus-visible, .plus__card :focus-visible { outline-color: var(--color-day-text); }

.visually-hidden {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

.skip-link {
  position: absolute; left: var(--space-4); top: calc(-1 * var(--space-8)); z-index: 30;
  padding: var(--space-3) var(--space-4); background: var(--color-day-surface); color: var(--color-day-text);
  border-radius: var(--radius-field);
}
.skip-link:focus { top: var(--space-2); }

.container { width: 100%; max-width: 1200px; margin: 0 auto; padding: 0 var(--space-4); }

/* Header, menu, language switch (screens 11c, 11d; desktop 13a) */
.site-header { border-bottom: 1px solid var(--color-day-line); background: var(--color-day-bg); }
.site-header__bar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); min-height: 60px; }
.brand {
  display: inline-flex; align-items: center; gap: var(--space-2); min-height: 44px; color: var(--color-day-text);
  font-family: var(--font-display); font-size: var(--font-size-h-2); font-weight: 600; text-decoration: none;
}
.brand svg { color: var(--color-day-accent); }
.menu-button {
  display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; padding: 0;
  border: 0; background: transparent; color: var(--color-day-text); cursor: pointer; border-radius: var(--radius-pill);
}
.site-nav { display: none; padding: var(--space-2) 0 var(--space-5); }
.site-nav.is-open { display: block; }
.site-nav ul { list-style: none; margin: 0; padding: 0; }
.site-nav a {
  display: flex; align-items: center; min-height: 52px; border-bottom: 1px solid var(--color-day-line);
  color: var(--color-day-text); font-family: var(--font-display); font-size: var(--font-size-h-2); text-decoration: none;
}
.site-nav a[aria-current='page'] { color: var(--color-day-accent); }
.site-nav .lang-switch { margin-top: var(--space-4); }
.lang-switch { display: flex; align-items: center; gap: var(--space-2); font-size: var(--font-size-small); color: var(--color-day-text-muted); }
.lang-switch a, .lang-switch span[aria-current] {
  display: inline-flex; align-items: center; min-height: 44px; min-width: 44px; justify-content: center;
}
.lang-switch a { color: var(--color-day-text-muted); }
.lang-switch span[aria-current] { color: var(--color-day-text); font-weight: 700; }
.site-header__desktop { display: none; }

@media (min-width: 900px) {
  .menu-button, .site-nav { display: none !important; }
  .site-header__desktop { display: flex; align-items: center; gap: var(--space-6); }
  .site-header__desktop ul { display: flex; gap: var(--space-5); list-style: none; margin: 0; padding: 0; }
  .site-header__desktop a {
    display: inline-flex; align-items: center; min-height: 44px; color: var(--color-day-text); text-decoration: none;
    border-bottom: 2px solid transparent; font-weight: 500;
  }
  .site-header__desktop a[aria-current='page'] { border-bottom-color: var(--color-day-accent); }
  .container { padding: 0 var(--space-6); }
}

/* Type */
.eyebrow {
  margin: 0; font-size: var(--font-size-caption); font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--color-day-accent);
}
.display { margin: 0; font-family: var(--font-display); font-weight: 500; line-height: 1.04; font-size: var(--font-size-display-2); }
.display--home { font-size: var(--font-size-display-1); }
.lead { margin: 0; color: var(--color-day-text-muted); }
.h2 { margin: 0; font-family: var(--font-display); font-weight: 500; font-size: var(--font-size-h-1); line-height: 1.1; }
.small { font-size: var(--font-size-small); }
.muted { color: var(--color-day-text-muted); }
@media (min-width: 900px) {
  .display--home { font-size: var(--font-size-display-l); }
  .display { font-size: var(--font-size-display-1); }
}

.page-hero { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-6) 0 0; }
.page-section { display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-7) 0 0; }
.tool-layout { display: grid; gap: var(--space-5); }
@media (min-width: 900px) {
  .tool-layout { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: start; gap: var(--space-7); padding-top: var(--space-5); }
}

/* Buttons and chips (design system: Button, Chips) */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--space-2); min-height: 52px;
  padding: 0 var(--space-5); border-radius: var(--radius-pill); border: 1px solid transparent; cursor: pointer;
  font-family: var(--font-text); font-size: var(--font-size-body); font-weight: 700; text-decoration: none; text-align: center;
}
.btn--block { width: 100%; }
.btn--gold { background: var(--color-night-accent); color: var(--color-night-on-accent); }
.btn--ink { background: var(--color-brand-ink-button); color: var(--color-day-on-accent); }
.btn--outline { background: transparent; color: inherit; border-color: var(--color-day-control-border); font-weight: 600; }
.night .btn--outline, .night-panel .btn--outline { border-color: var(--color-night-control-border); }
.btn--text { background: transparent; color: var(--color-day-accent); font-weight: 600; }
.night .btn--text, .night-panel .btn--text { color: var(--color-night-accent); }
.btn[disabled] { cursor: default; opacity: 0.6; }

.chips { display: flex; flex-wrap: wrap; gap: var(--space-2); margin: 0; padding: 0; border: 0; }
.chip {
  display: inline-flex; align-items: center; gap: var(--space-2); min-height: 44px; padding: 0 var(--space-4);
  border-radius: var(--radius-pill); border: 1px solid var(--color-night-control-border); background: transparent;
  color: var(--color-night-text); font-family: var(--font-text); font-size: var(--font-size-body); font-weight: 600; cursor: pointer;
}
.chip[aria-pressed='true'] { background: var(--color-night-accent); color: var(--color-night-on-accent); }
.chip svg { display: none; }
.chip[aria-pressed='true'] svg { display: block; }

/* The night panel on day pages (screens 1, 5a, 6, 12a) */
.night-panel {
  display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-5) var(--space-5) var(--space-5);
  border-radius: var(--radius-panel-large); background: var(--color-night-bg); color: var(--color-night-text);
  margin: var(--space-5) calc(-1 * var(--space-1)) 0;
}
.night-panel a { color: var(--color-night-accent); }
.field { display: flex; flex-direction: column; gap: var(--space-2); }
.field label, .field__label { font-size: var(--font-size-small); color: var(--color-night-text-muted); }
.input {
  width: 100%; min-height: 52px; padding: 0 var(--space-4); border-radius: var(--radius-field);
  border: 1px solid var(--color-night-control-border); background: var(--color-night-surface); color: var(--color-night-text);
  font-family: var(--font-text); font-size: var(--font-size-body);
}
.input::placeholder { color: var(--color-night-text-muted); }
.input--day { border-color: var(--color-day-control-border); background: var(--color-day-surface); color: var(--color-day-text); }
.input--day::placeholder { color: var(--color-day-text-muted); }
.panel-hint { margin: 0; text-align: center; font-size: var(--font-size-small); color: var(--color-night-text-muted); }
.backs { display: flex; justify-content: center; gap: var(--space-4); padding: var(--space-3) 0; }
.backs img { width: 92px; aspect-ratio: var(--card-ratio); border-radius: var(--radius-card); }
.backs img:nth-child(1) { transform: rotate(-6deg) translateY(6px); }
.backs img:nth-child(3) { transform: rotate(6deg) translateY(6px); }

/* Cards (design system: TarotCard) */
.card-frame {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2); margin: 0;
}
.card-frame__art {
  width: 100%; aspect-ratio: var(--card-ratio); padding: var(--space-1); border-radius: var(--radius-card);
  border: 1px solid var(--color-night-accent); background: var(--color-night-bg);
}
.card-frame__art img { width: 100%; height: 100%; object-fit: cover; border-radius: calc(var(--radius-card) - var(--space-1)); }
.card-frame__art img.is-reversed { transform: rotate(180deg); }
.card-frame__name { font-family: var(--font-display); font-weight: 600; font-size: var(--font-size-small); text-align: center; }
.card-frame__name b { color: var(--color-night-accent); font-weight: 600; }
.card-frame--day .card-frame__name b { color: var(--color-day-accent); }

/* Lists of formats, cards and steps on day pages */
.link-list { list-style: none; margin: 0; padding: 0; }
.link-list a {
  display: flex; align-items: center; gap: var(--space-4); min-height: 64px; padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-day-line); color: var(--color-day-text); text-decoration: none;
}
.link-list__text { display: flex; flex-direction: column; gap: var(--space-1); flex: 1; }
.link-list__name { font-weight: 600; }
.link-list__hint { font-size: var(--font-size-small); color: var(--color-day-text-muted); }
.link-list svg { color: var(--color-day-accent); flex-shrink: 0; }
.card-row { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.card-row a { width: 100px; color: var(--color-day-text); text-decoration: none; }
.steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-4); }
.steps li { display: flex; gap: var(--space-4); align-items: flex-start; }
.steps__n {
  display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; flex-shrink: 0;
  border-radius: var(--radius-pill); border: 1px solid var(--color-day-accent); color: var(--color-day-accent);
  font-size: var(--font-size-small); font-weight: 700;
}
.tile {
  display: flex; gap: var(--space-4); align-items: center; padding: var(--space-5); margin-top: var(--space-6);
  border-radius: var(--radius-panel); background: var(--color-day-surface);
}
.tile img { width: 56px; aspect-ratio: var(--card-ratio); border-radius: calc(var(--radius-card) - var(--space-1)); flex-shrink: 0; }
.tile__body { display: flex; flex-direction: column; gap: var(--space-2); }
.tile__body a { font-weight: 600; min-height: 44px; display: inline-flex; align-items: center; }

/* The night room (screens 2a–2e, 5b, 8b, 13d) */
.night-room {
  position: fixed; inset: 0; z-index: 20; display: flex; align-items: stretch; justify-content: center;
  background: color-mix(in srgb, var(--color-night-bg) 62%, transparent);
}
.night {
  position: relative; width: 100%; max-width: 960px; overflow-y: auto; padding: var(--space-5) var(--space-4) var(--space-7);
  background: var(--color-night-bg); color: var(--color-night-text);
  animation: night-open var(--motion-night-open) var(--motion-easing);
}
@media (min-width: 900px) {
  .night-room { align-items: center; padding: var(--space-6); }
  .night { max-height: 100%; border-radius: var(--radius-panel-large); padding: var(--space-6) var(--space-7) var(--space-7); }
}
.night a { color: var(--color-night-accent); }
.night__top { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
.night__question { margin: 0; font-size: var(--font-size-small); color: var(--color-night-text-muted); }
.night__title { margin: var(--space-5) 0 0; font-family: var(--font-display); font-weight: 500; font-size: var(--font-size-h-1); line-height: 1.15; text-align: center; }
.close-button {
  display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex-shrink: 0;
  border-radius: var(--radius-pill); border: 1px solid var(--color-night-control-border); background: transparent;
  color: var(--color-night-text); cursor: pointer;
}
.night__status { margin: var(--space-6) 0 0; text-align: center; color: var(--color-night-text-muted); }
.spread { display: flex; justify-content: center; gap: var(--space-3); margin-top: var(--space-6); }
.spread__slot { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); width: 106px; }
.spread--one .spread__slot { width: 150px; }
.spread__pos { font-size: var(--font-size-caption); font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--color-night-text-muted); }
.flip { position: relative; width: 100%; aspect-ratio: var(--card-ratio); perspective: 800px; }
.flip__inner {
  position: absolute; inset: 0; transform-style: preserve-3d;
  transition: transform var(--motion-card-flip) var(--motion-easing);
}
.flip.is-turned .flip__inner { transform: rotateY(180deg); }
.flip__side { position: absolute; inset: 0; backface-visibility: hidden; }
.flip__side--face { transform: rotateY(180deg); }
.flip__side img.back { width: 100%; height: 100%; border-radius: var(--radius-card); }
.deck-shuffle { display: flex; justify-content: center; margin-top: var(--space-8); }
.deck-shuffle img { width: 100px; aspect-ratio: var(--card-ratio); border-radius: var(--radius-card); }

/* With the answer (2e, 5b, 13d): cards and text side by side when there is room (desktop), cards above on a phone */
.night__body { display: flex; flex-wrap: wrap; gap: var(--space-5) var(--space-7); align-items: flex-start; margin-top: var(--space-5); }
.night__cards { flex: 0 1 420px; min-width: 0; }
.night__text { flex: 999 1 360px; min-width: 0; display: flex; flex-direction: column; gap: var(--space-5); }
.night__text > .night__actions, .night__text > .followups { margin-top: 0; }
.spread--small { margin-top: 0; }
.spread--small .spread__slot { width: 78px; }
.spread--small .card-frame__name { font-size: var(--font-size-caption); }
.answer__headline { margin: 0; font-family: var(--font-display); font-weight: 500; font-size: var(--font-size-h-1); line-height: 1.1; }
@media (min-width: 900px) {
  .night__question { font-size: var(--font-size-body); }
  .spread--small .spread__slot { width: 128px; }
  .spread--small .card-frame__name { font-size: var(--font-size-small); }
  .answer__headline { font-size: var(--font-size-display-2); }
}
.answer__soft { margin: 0; padding: var(--space-3) var(--space-4); border-radius: var(--radius-field); border: 1px solid var(--color-night-line); color: var(--color-night-text-muted); }
.answer__label { display: block; font-size: var(--font-size-caption); font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--color-night-accent); }
.answer__text { margin: var(--space-1) 0 0; white-space: pre-line; }
.answer__synthesis { margin: 0; padding: var(--space-4); border-radius: var(--radius-field); background: var(--color-night-surface); white-space: pre-line; }
.verdict { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); text-align: center; }
.verdict__word { display: flex; align-items: center; gap: var(--space-4); font-family: var(--font-display); font-weight: 500; font-size: var(--font-size-display-1); line-height: 1; }
.verdict__word svg { color: var(--color-night-accent); }
.more-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); gap: var(--space-2); }
.more-cards .btn { font-size: var(--font-size-small); padding: 0 var(--space-2); }
.night__actions { display: flex; flex-direction: column; gap: var(--space-3); margin-top: var(--space-6); }
.night__foot { margin: var(--space-6) 0 0; text-align: center; font-size: var(--font-size-small); color: var(--color-night-text-muted); }
.followups { display: flex; flex-direction: column; gap: var(--space-4); margin-top: var(--space-6); padding-top: var(--space-5); border-top: 1px solid var(--color-night-line); }
.followup__q { margin: 0; font-size: var(--font-size-small); color: var(--color-night-text-muted); }
.followup__a { margin: var(--space-1) 0 0; white-space: pre-line; }
.followup-form { display: flex; flex-direction: column; gap: var(--space-3); }
.notice { margin: 0; padding: var(--space-3) var(--space-4); border-radius: var(--radius-field); border: 1px solid var(--color-night-control-border); }
.notice--day { border-color: var(--color-day-control-border); background: var(--color-day-surface); }

/* Crisis answer: warm words and help lines, nothing else */
.crisis { display: flex; flex-direction: column; gap: var(--space-4); margin-top: var(--space-5); }
.crisis h2 { margin: 0; font-family: var(--font-display); font-weight: 500; font-size: var(--font-size-h-1); }
.crisis p { margin: 0; }
.helplines { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-3); }
.helplines li { padding: var(--space-4); border-radius: var(--radius-field); background: var(--color-night-surface); display: flex; flex-direction: column; gap: var(--space-1); }
.helplines a { min-height: 44px; display: inline-flex; align-items: center; font-weight: 700; }

/* Plus at the free limit (screen 11a) */
.plus-slot { margin-top: var(--space-5); }
.plus { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-2) 0; }
.plus .display { font-size: var(--font-size-display-2); }
.plus__card {
  display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-5); border-radius: var(--radius-panel);
  background: var(--color-day-surface); color: var(--color-day-text); border-top: 2px solid var(--color-brand-gold);
}
.plus__card h3 { margin: 0; font-size: var(--font-size-h-3); }
.plus__card ul { margin: 0; padding-left: var(--space-5); display: flex; flex-direction: column; gap: var(--space-1); }
.plus__card label { font-size: var(--font-size-small); color: var(--color-day-text-muted); }
.plus__card a { color: var(--color-day-accent); }
.plus__card form { gap: var(--space-3); }
.plus__row { display: flex; flex-wrap: wrap; gap: var(--space-4); align-items: center; }
.plus__row a, .plus__daily { min-height: 44px; display: inline-flex; align-items: center; font-weight: 600; }
.plus__card { margin-top: var(--space-3); }
/* the same card after the free follow-ups inside the night room (402 plus) */
.night .plus .lead { color: var(--color-night-text-muted); }

.help-line { margin: 0; font-size: var(--font-size-small); }
.help-line a { min-height: 44px; display: inline-flex; align-items: center; }

/* Card of the Day (screens 7a, 7b) */
.daily { display: flex; flex-direction: column; align-items: center; gap: var(--space-4); padding: var(--space-6) var(--space-5); margin-top: var(--space-5); border-radius: var(--radius-panel-large); background: var(--color-night-bg); color: var(--color-night-text); text-align: center; }
.daily a { color: var(--color-night-accent); min-height: 44px; display: inline-flex; align-items: center; }
.daily__back { padding: 0; border: 0; background: transparent; cursor: pointer; border-radius: var(--radius-card); color: var(--color-night-text); display: flex; flex-direction: column; align-items: center; gap: var(--space-3); font-family: var(--font-text); font-size: var(--font-size-body); }
.daily__back img { width: 160px; aspect-ratio: var(--card-ratio); border-radius: var(--radius-card); }
.daily .card-frame { width: 180px; }
.daily__text { margin: 0; max-width: 560px; text-align: left; white-space: pre-line; }

/* Simple card page */
.card-page { display: grid; gap: var(--space-6); padding-top: var(--space-6); }
.card-page__art { max-width: 280px; }
.card-page__text { display: flex; flex-direction: column; gap: var(--space-4); }
.card-page__text p { margin: 0; }
.keywords { margin: 0; color: var(--color-day-text-muted); }
.card-nav { display: flex; justify-content: space-between; gap: var(--space-4); padding: var(--space-7) 0 0; }
.card-nav a { display: flex; flex-direction: column; min-height: 44px; text-decoration: none; color: var(--color-day-text); }
.card-nav small { color: var(--color-day-text-muted); }
@media (min-width: 900px) {
  .card-page { grid-template-columns: 280px minmax(0, 1fr) minmax(0, 380px); align-items: start; }
}

/* Footer */
.site-footer { margin-top: var(--space-8); padding: var(--space-5) 0 var(--space-6); border-top: 1px solid var(--color-day-line); }
.site-footer__inner { display: flex; flex-direction: column; gap: var(--space-4); }
.site-footer ul { display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-5); list-style: none; margin: 0; padding: 0; }
.site-footer ul a { min-height: 44px; display: inline-flex; align-items: center; }
.site-footer p { margin: 0; font-size: var(--font-size-small); color: var(--color-day-text-muted); }

.turnstile-slot { position: fixed; bottom: 0; right: 0; z-index: 40; } /* above the night room (z 20) */

@keyframes night-open { from { opacity: 0; transform: scale(0.96); } to { opacity: 1; transform: none; } }
@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

/* Without motion: the room and the cards fade in, cards already turned (00-design.md) */
@media (prefers-reduced-motion: reduce) {
  .night { animation: fade-in var(--motion-night-open) linear; }
  .flip__inner { transition: none; }
  .night__body, .daily .card-frame { animation: fade-in var(--motion-night-open) linear; }
  .backs img:nth-child(1), .backs img:nth-child(3) { transform: none; }
}
```

Create `site/src/layouts/Base.astro`:

```astro
---
// Every page: language, title, fonts (Google Fonts: Cormorant Garamond 500/600, Manrope 400–700), tokens, the
// header with the menu and the language switch, the footer. The stage is closed by Caddy (password, X-Robots-Tag).
import '../styles/tokens.css';
import '../styles/global.css';
import Header from '../components/Header.astro';
import Footer from '../components/Footer.astro';
import { t } from '../i18n';
import type { PageKey } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
  title: string;
  path: string;
  current?: PageKey;
}

const { lang, title, path, current } = Astro.props;
const d = t(lang);
---
<!doctype html>
<html lang={lang}>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Manrope:wght@400;500;600;700&display=swap"
    />
  </head>
  <body>
    <a class="skip-link" href="#main">{d.skipToContent}</a>
    <Header lang={lang} path={path} current={current} />
    <main id="main" class="container" tabindex="-1">
      <slot />
    </main>
    <Footer lang={lang} path={path} />
  </body>
</html>
```

Create `site/src/components/MoonMark.astro`:

```astro
---
// The brand mark: a crescent in a thin ring, in currentColor (design system: Logo).
interface Props {
  size?: number;
}
const { size = 24 } = Astro.props;
---
<svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
  <circle cx="32" cy="32" r="30" stroke="currentColor" stroke-width="2.5"></circle>
  <path d="M39 14a19 19 0 1 0 0 36A15 15 0 1 1 39 14Z" stroke="currentColor" stroke-width="3"></path>
</svg>
```

Create `site/src/components/LangSwitch.astro`:

```astro
---
// EN | ES (pairs from hreflang.csv through src/lib/routes.ts). The current language is not a link.
import { t } from '../i18n';
import { switchPath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
  path: string;
}

const { lang, path } = Astro.props;
const other = switchPath(path);
const d = t(lang);
---
<nav class="lang-switch" aria-label={d.langLabel}>
  {lang === 'en' ? <span aria-current="true" lang="en">EN</span> : <a href={other} lang="en" hreflang="en">EN</a>}
  <span aria-hidden="true">|</span>
  {lang === 'es' ? <span aria-current="true" lang="es">ES</span> : <a href={other} lang="es" hreflang="es">ES</a>}
</nav>
```

Create `site/src/components/Header.astro`:

```astro
---
// Header (design system: Header): wordmark; on a phone the menu button opens the menu (screens 11c, 11d);
// on a desktop the menu items and EN | ES sit in the header (screen 13a).
import MenuToggle from '../islands/MenuToggle';
import LangSwitch from './LangSwitch.astro';
import MoonMark from './MoonMark.astro';
import { t, type DictKey } from '../i18n';
import { NAV_KEYS, pagePath, type PageKey } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
  path: string;
  current?: PageKey;
}

const { lang, path, current } = Astro.props;
const d = t(lang);
const LABELS: Record<string, DictKey> = { home: 'navHome', yes_no: 'navYesNo', love: 'navLove', daily: 'navDaily' };
const items = NAV_KEYS.map((key) => ({ key, href: pagePath(key, lang), label: d[LABELS[key]] }));
---
<header class="site-header">
  <div class="container">
    <div class="site-header__bar">
      <a class="brand" href={pagePath('home', lang)}><MoonMark />{d.siteName}</a>
      <div class="site-header__desktop">
        <nav aria-label={d.navLabel}>
          <ul>
            {items.map((item) => (
              <li><a href={item.href} aria-current={item.key === current ? 'page' : undefined}>{item.label}</a></li>
            ))}
          </ul>
        </nav>
        <LangSwitch lang={lang} path={path} />
      </div>
      <MenuToggle client:load lang={lang} navId="site-menu" />
    </div>
    <nav id="site-menu" class="site-nav" aria-label={d.navLabel}>
      <ul>
        {items.map((item) => (
          <li><a href={item.href} aria-current={item.key === current ? 'page' : undefined}>{item.label}</a></li>
        ))}
      </ul>
      <LangSwitch lang={lang} path={path} />
    </nav>
  </div>
</header>
```

Create `site/src/components/Footer.astro`:

```astro
---
// Footer (screens 1, 12a): the tools, "not a guarantee", the card art credit, the help link and EN | ES.
// Card meanings, About and Privacy arrive with stages 6–7.
import LangSwitch from './LangSwitch.astro';
import { t } from '../i18n';
import { HELP_URL, pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
  path: string;
}

const { lang, path } = Astro.props;
const d = t(lang);
const links = [
  { href: pagePath('one_card', lang), label: d.footerOneCard },
  { href: pagePath('yes_no', lang), label: d.navYesNo },
  { href: pagePath('love', lang), label: d.navLove },
  { href: pagePath('daily', lang), label: d.navDaily },
];
---
<footer class="site-footer">
  <div class="container site-footer__inner">
    <nav aria-label={d.footerLabel}>
      <ul>
        {links.map((link) => <li><a href={link.href}>{link.label}</a></li>)}
      </ul>
    </nav>
    <p>{d.disclaimer}</p>
    <p>{d.cardArtCredit}</p>
    <p class="help-line">{d.helpLead} <a href={HELP_URL} rel="noopener noreferrer">{d.helpLink}</a></p>
    <LangSwitch lang={lang} path={path} />
  </div>
</footer>
```

Create `site/src/components/CardFigure.astro`:

```astro
---
// A card face on a day page: the printed card in a gold frame (three sizes, srcset) and its name as text.
import { fill, t } from '../i18n';
import { cardImage, cardName, cardSrcset, type DeckCard } from '../lib/deck';
import type { Lang } from '../lib/types';

interface Props {
  card: DeckCard;
  lang: Lang;
  sizes: string;
  eager?: boolean;
}

const { card, lang, sizes, eager = false } = Astro.props;
const name = cardName(card, lang);
---
<figure class="card-frame card-frame--day">
  <div class="card-frame__art">
    <img src={cardImage(card, 350)} srcset={cardSrcset(card)} sizes={sizes} width="350" height="600"
      alt={fill(t(lang).cardAlt, { name })} loading={eager ? 'eager' : 'lazy'} />
  </div>
  <figcaption class="card-frame__name"><b>{card.numeral}</b> {name}</figcaption>
</figure>
```

Create `site/src/components/ui/icons.tsx`:

```tsx
// Thin line icons in currentColor (design system: Iconography). Decorative: hidden from screen readers.

export function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <path d="M3 3l10 10M13 3L3 13" />
    </svg>
  );
}

export function MenuIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <path d="M3 7h16M3 15h16" />
    </svg>
  );
}

export function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
      <path d="M2 7.5l3 3 7-7" />
    </svg>
  );
}

/** Yes, No and Not yet differ by shape (check, cross, hourglass), never by colour alone. */
export function VerdictIcon({ value }: { value: 'yes' | 'no' | 'unclear' }) {
  const paths = {
    yes: 'M7.5 13.5l3.5 3.5 7.5-8',
    no: 'M8.5 8.5l9 9M17.5 8.5l-9 9',
    unclear: 'M9 7h8M9 19h8M10 7c0 3.5 6 4.5 6 6s-6 2.5-6 6M16 7c0 3.5-6 4.5-6 6s6 2.5 6 6',
  };
  return (
    <svg width="40" height="40" viewBox="0 0 26 26" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <circle cx="13" cy="13" r="12" />
      <path d={paths[value]} />
    </svg>
  );
}
```

Create `site/src/islands/MenuToggle.tsx`:

```tsx
// The phone menu button (screens 11c, 11d): opens the menu below the header; Escape or the button closes it and
// focus returns to the button. On a desktop the menu is always in the header and this button is hidden.
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../i18n';
import type { Lang } from '../lib/types';
import { CloseIcon, MenuIcon } from '../components/ui/icons';

export default function MenuToggle({ lang, navId }: { lang: Lang; navId: string }) {
  const d = t(lang);
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    document.getElementById(navId)?.classList.toggle('is-open', open);
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <button type="button" class="menu-button" ref={button} aria-expanded={open} aria-controls={navId}
      aria-label={open ? d.menuClose : d.menuOpen} onClick={() => setOpen(!open)}>
      {open ? <CloseIcon /> : <MenuIcon />}
    </button>
  );
}
```

In `docs/design/00-design.md`, replace:

```markdown
- Касание ≥ 44 px; рамка фокуса 2 px цветом текста (`currentColor`), отступ 2 px; настоящие `<button>`, `<a>`, `<label>`.
```

with:

```markdown
- Касание ≥ 44 px; рамка фокуса 2 px цветом текста (`currentColor`), отступ 2 px; настоящие `<button>`, `<a>`, `<label>`.
  Рамка берёт цвет текста поверхности, на которой стоит элемент, а не цвет его надписи: ночью — `--color-night-text`,
  на белой карточке и днём — `--color-day-text` (у золотой кнопки и выбранного чипа надпись цвета фона ночи, у
  чернильной — белая, и `currentColor` там не виден; проверка плана 4.4а, I2).
```

- [ ] **Step 4: Write the 404 pages**

Create `site/src/views/NotFoundView.astro`:

```astro
---
// 404 EN / ES (screen 11b). Caddy serves it for unknown addresses (deploy/Caddyfile, handle_errors 404).
import Base from '../layouts/Base.astro';
import { t } from '../i18n';
import { pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
const links = [
  { href: pagePath('home', lang), label: d.notFoundReading },
  { href: pagePath('yes_no', lang), label: d.navYesNo },
  { href: pagePath('daily', lang), label: d.navDaily },
];
---
<Base lang={lang} title={d.notFoundTitle} path={pagePath('not_found', lang)}>
  <section class="page-hero">
    <p class="eyebrow">{d.notFoundEyebrow}</p>
    <h1 class="display">{d.notFoundH1}</h1>
    <p class="lead">{d.notFoundLead}</p>
  </section>
  <nav class="page-section" aria-label={d.notFoundNav}>
    <ul class="link-list">
      {links.map((link) => <li><a href={link.href}><span class="link-list__name">{link.label}</span></a></li>)}
    </ul>
  </nav>
</Base>
```

Create `site/src/pages/404.astro`:

```astro
---
import NotFoundView from '../views/NotFoundView.astro';
---
<NotFoundView lang="en" />
```

Create `site/src/pages/es/404.astro`:

```astro
---
import NotFoundView from '../../views/NotFoundView.astro';
---
<NotFoundView lang="es" />
```

- [ ] **Step 5: Run all Vitest tests and build**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run`
Expected: `Test Files  17 passed (17)`, `Tests  122 passed (122)`.

Run: `cd ~/arcana-diary && deploy/build-site.sh 2>&1 | tail -3 && ls site/dist site/dist/es`
Expected: `3 page(s) built`, `Complete!`; `site/dist` holds `404.html`, `_astro`, `cards`, `es`, `index.html`, `robots.txt`; `site/dist/es` holds `404.html`.

- [ ] **Step 6: Commit**

```bash
cd ~/arcana-diary
git add site/src/styles/global.css site/src/layouts site/src/components site/src/islands/MenuToggle.tsx \
  site/src/views/NotFoundView.astro site/src/pages/404.astro site/src/pages/es/404.astro site/src/lib/guards.test.ts \
  docs/design/00-design.md
git commit -m "feat(site): layout from tokens, menu, footer, language switch, 404 pages, source guards

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: The reading island and the tool and card pages

> **Amendment after the Fable re-check (R3), required:** when `402 confirm` arrives and the form unmounts, move focus to the confirm button (and give the notice `role="alert"`), so the "this will use 1 reading" notice is announced and focus never falls to `<body>`.

**Files:**
- Create: `site/src/components/ui/CardFace.tsx`, `site/src/components/ui/HelpLine.tsx`, `site/src/components/ui/CrisisView.tsx`, `site/src/components/ui/PlusCard.tsx`, `site/src/components/ui/NightRoom.tsx`, `site/src/islands/ReadingIsland.tsx`
- Create: `site/src/views/HomeView.astro`, `site/src/views/ToolView.astro`, `site/src/views/CardView.astro`
- Create: `site/src/pages/one-card.astro`, `site/src/pages/yes-no.astro`, `site/src/pages/love.astro`, `site/src/pages/es/index.astro`, `site/src/pages/es/si-o-no.astro`, `site/src/pages/es/amor.astro`, `site/src/pages/cards/[slug].astro`, `site/src/pages/es/cartas/[slug].astro`
- Modify: `site/src/pages/index.astro` (whole file)

**Interfaces:**
- Consumes: everything of Tasks 3–8: `panelConfig`, `initialKind`, `drawLabelKey`, `buildCreateBody`, `cardsFor`, `situationKey` (panel); `nightReducer`, `CLOSED`, `DEAL_MS`, `FLIP_INTERVAL_MS`, `followupNow`, `transitionEvents`, `allRevealed`, `answerVisible`, `readingShown`, `statusKey` (nightRoom); `startReading`, `streamReading`, `restoreReading`, `askFollowup`, `FlowDeps` (readingFlow); `createApi`, `browserFetch` (api); `turnstileToken` (turnstile); `analyticsEvent`, `sendEvent` (analytics); `handleDialogKey` (focus); `canCall`, `telHref`, `safeUrl` (helplines); `answerBlocks`; `errorMessageKey`, `needsHelpLink`; `cardById`, `cardImage`, `cardSrcset`, `CARD_BACK`, `DECK`, `neighbors`, `cardName`; `cardPath`, `pagePath`, `HELP_URL`; `Base.astro`, `CardFigure.astro`, icons; CSS classes of Task 8.
- Produces:
  - Island `ReadingIsland` (default export) props `{lang: Lang, page: PanelPage, cardId?: string, cardName?: string, showBacks?: boolean}` — the night panel form and the night room; at the limit the Plus card replaces the dark panel (`.plus-slot`, screen 11a); on the Spanish home the panel (or slot) has `id="una-carta"`. It pushes one history entry `{arcanaNight: true}` (same address) when the room opens; `popstate` closes the room; ×, Escape, "Back to …" and "Ask another question" step back over the entry. Follow-ups always go first without `use_reading`. On a crisis the question field is emptied. Events name `toolFor(config, kind)`.
  - `NightRoom` props `NightRoomProps {state, lang, config, question, sourceName, onClose, onRetry, onRestore, onFollowup(question), onConfirmFollowup, onCancelFollowup, onMoreAbout, onAskAnother}`; `CardArt`, `CardName`, `CardFace` props `{cardId, name, reversed, lang, sizes?}`; `HelpLine({lang})`; `CrisisView({payload, lang})` (call, `sms:` for lines like 988, `HelpLine` under the fallback sentence); `PlusCard({lang, tool, focusOnShow?})` (11a: title, lead, help link, white card with benefits, the e-mail form, "Not now", then "Open your free Card of the Day"). `NightRoom` listens for keys on the document (Escape, Tab trap) and moves focus to `#night-title` on open, on every phase change, when the answer layout replaces the title, and after Try again / Use 1 reading / Not now.
  - `HomeView({lang})`, `ToolView({lang, page: 'one_card' | 'yes_no' | 'love'})`, `CardView({lang, card, meaning})` and its exported type `Meaning {card_id, keywords, upright, reversed}`.

- [ ] **Step 1: Write the Preact pieces of the night room**

Create `site/src/components/ui/CardFace.tsx`:

```tsx
// A tarot card face (design system: TarotCard): the whole printed card in a gold frame, the name as text next to
// it; a reversed card turns only the picture.
import { fill, t } from '../../i18n';
import { cardById, cardImage, cardSrcset } from '../../lib/deck';
import type { Lang } from '../../lib/types';

interface ArtProps {
  cardId: string;
  name: string;
  reversed: boolean;
  lang: Lang;
  sizes?: string;
}

export function CardArt({ cardId, name, reversed, lang, sizes = '(min-width: 900px) 180px, 150px' }: ArtProps) {
  const card = cardById(cardId);
  if (!card) return null;
  const d = t(lang);
  return (
    <div class="card-frame__art">
      <img
        src={cardImage(card, 350)}
        srcset={cardSrcset(card)}
        sizes={sizes}
        width={350}
        height={600}
        alt={fill(reversed ? d.cardAltReversed : d.cardAlt, { name })}
        class={reversed ? 'is-reversed' : undefined}
      />
    </div>
  );
}

export function CardName({ cardId, name }: { cardId: string; name: string }) {
  const card = cardById(cardId);
  return (
    <span class="card-frame__name">
      {card ? <b>{card.numeral}</b> : null} {name}
    </span>
  );
}

export function CardFace(props: ArtProps) {
  return (
    <figure class="card-frame">
      <CardArt {...props} />
      <figcaption>
        <CardName cardId={props.cardId} name={props.name} />
      </figcaption>
    </figure>
  );
}
```

Create `site/src/components/ui/HelpLine.tsx`:

```tsx
// The help link added to the 429, 403 and 503 messages (spec 4.2 §10.8): findahelpline.com lists free,
// confidential lines for every country.
import { t } from '../../i18n';
import { HELP_URL } from '../../lib/routes';
import type { Lang } from '../../lib/types';

export function HelpLine({ lang }: { lang: Lang }) {
  const d = t(lang);
  return (
    <p class="help-line">
      {d.helpLead}{' '}
      <a href={HELP_URL} rel="noopener noreferrer" target="_blank">{d.helpLink}</a>
    </p>
  );
}
```

Create `site/src/components/ui/CrisisView.tsx`:

```tsx
// The crisis answer (spec 4.2 §3.2): warm words and help lines from the API, no cards, no reading. A line that
// takes texts without a keyword (988) gets an sms: link; findahelpline.com is a link under the fallback sentence.
import { fill, t } from '../../i18n';
import { canCall, canText, safeUrl, smsHref, telHref } from '../../lib/helplines';
import type { CrisisPayload, Lang } from '../../lib/types';
import { HelpLine } from './HelpLine';

export function CrisisView({ payload, lang }: { payload: CrisisPayload; lang: Lang }) {
  const d = t(lang);
  const c = payload.crisis;
  return (
    <div class="crisis">
      <p>{c.body}</p>
      <p>{c.not_saved}</p>
      <p>{c.contacts_intro}</p>
      <ul class="helplines">
        {payload.helplines.lines.map((line) => {
          const tel = canCall(line) ? telHref(line.number!) : null;
          const sms = canText(line) ? smsHref(line.number!) : null;
          const url = safeUrl(line.url);
          return (
            <li key={line.name}>
              <strong>{line.name}</strong>
              <span>{line.purpose}</span>
              {tel ? <a href={tel}>{fill(d.crisisCall, { number: line.number! })}</a> : null}
              {sms ? <a href={sms}>{fill(d.crisisText, { sms: line.number! })}</a> : null}
              {line.sms ? <span>{fill(d.crisisText, { sms: line.sms })}</span> : null}
              {url ? <a href={url} rel="noopener noreferrer" target="_blank">{fill(d.crisisWeb, { name: line.name })}</a> : null}
              {line.note ? <span>{line.note}</span> : null}
              {line.hours ? <span>{fill(d.crisisHours, { hours: line.hours })}</span> : null}
            </li>
          );
        })}
      </ul>
      <p>{c.fallback_contacts}</p>
      <HelpLine lang={lang} />
      <p>{c.emergency_line}</p>
      <p>{c.closing}</p>
    </div>
  );
}
```

Create `site/src/components/ui/PlusCard.tsx`:

```tsx
// Today's free readings are used (screen 11a, spec 4.4a §4): a day page block — the title, the lead, the help link,
// a white card with a gold rule ("What Plus gives you", the benefits, "tell me when it opens" by e-mail through
// POST /api/plus/waitlist, "Not now"), then the free Card of the Day. No price on the closed stage (owner,
// 19.11.2026); never inside the answer text.
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import { browserFetch, createApi } from '../../lib/api';
import { errorMessageKey, type ErrorKind } from '../../lib/errors';
import { pagePath } from '../../lib/routes';
import type { Lang, Tool } from '../../lib/types';
import { HelpLine } from './HelpLine';

interface Props {
  lang: Lang;
  tool: Tool;
  focusOnShow?: boolean;
}

export function PlusCard({ lang, tool, focusOnShow = false }: Props) {
  const d = t(lang);
  const heading = useRef<HTMLHeadingElement>(null);
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'done' | 'invalid' | ErrorKind>('idle');
  const id = `plus-${tool}`;

  useEffect(() => {
    sendEvent(analyticsEvent('plus_view', tool, lang, { place: 'limit' }));
    if (focusOnShow) heading.current?.focus();
  }, []);

  const submit = async (event: Event) => {
    event.preventDefault();
    setStatus('sending');
    const result = await createApi(browserFetch()).joinWaitlist(email.trim(), lang);
    if (result.ok) setStatus('done');
    else setStatus(result.status === 422 ? 'invalid' : result.error);
  };

  const error = status === 'invalid' ? d.plusEmailError
    : status !== 'idle' && status !== 'sending' && status !== 'done' ? d[errorMessageKey(status)] : null;
  const daily = pagePath('daily', lang);

  return (
    <div class="plus">
      <h2 class="display" tabIndex={-1} ref={heading}>{d.plusTitle}</h2>
      <p class="lead">{d.plusLead}</p>
      <HelpLine lang={lang} />
      <section class="plus__card" aria-labelledby={`${id}-title`}>
        <h3 id={`${id}-title`}>{d.plusGives}</h3>
        <ul>
          <li>{d.plusBenefit1}</li>
          <li>{d.plusBenefit2}</li>
          <li>{d.plusBenefit3}</li>
        </ul>
        {status === 'done' ? (
          <p role="status">{d.plusDone}</p>
        ) : (
          <form class="field" onSubmit={submit}>
            <label for={`${id}-email`}>{d.plusEmailLabel}</label>
            <input
              id={`${id}-email`}
              class="input input--day"
              type="email"
              autocomplete="email"
              required
              maxLength={254}
              placeholder={d.plusEmailPlaceholder}
              value={email}
              onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
            />
            <div class="plus__row">
              <button type="submit" class="btn btn--ink" disabled={status === 'sending'}>{d.plusNotify}</button>
              <a href={daily}>{d.plusNotNow}</a>
            </div>
            {error ? <p role="alert">{error}</p> : null}
          </form>
        )}
      </section>
      <a class="plus__daily" href={daily}>{d.plusDaily}</a>
    </div>
  );
}
```

Create `site/src/components/ui/NightRoom.tsx`:

```tsx
// The night room (screens 2a–2e, 5b, 8b, 13d): a full-screen layer over the page with no address of its own.
// It only draws NightState (src/lib/nightRoom.ts) and calls back; requests and timers live in ReadingIsland.
// While cards are dealt: the positions on top, the question as the large title, the cards. With the answer (2e, 5b):
// the question small at top left, the headline as the large title; on a desktop cards left, text right (13d).
// Close: × and Escape (listened on the document, so it works wherever focus is); Tab stays inside; after an action
// whose button disappears, and on every change of phase, focus goes to the title.
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t, type DictKey } from '../../i18n';
import { answerBlocks } from '../../lib/answer';
import { CARD_BACK, cardById } from '../../lib/deck';
import { errorMessageKey, needsHelpLink } from '../../lib/errors';
import { handleDialogKey } from '../../lib/focus';
import { answerVisible, followupNow, readingShown, statusKey, type NightState } from '../../lib/nightRoom';
import type { PanelConfig } from '../../lib/panel';
import { cardPath } from '../../lib/routes';
import type { DrawnCard, Lang, Position } from '../../lib/types';
import { CardArt, CardName } from './CardFace';
import { CrisisView } from './CrisisView';
import { HelpLine } from './HelpLine';
import { CloseIcon, VerdictIcon } from './icons';
import { PlusCard } from './PlusCard';

export interface NightRoomProps {
  state: NightState;
  lang: Lang;
  config: PanelConfig;
  question: string;
  sourceName: string | null; // the card page's card, for "Back to The Moon"
  onClose: () => void;
  onRetry: () => void;
  onRestore: () => void;
  onFollowup: (question: string) => void;
  onConfirmFollowup: () => void;
  onCancelFollowup: () => void;
  onMoreAbout: () => void;
  onAskAnother: () => void;
}

const POSITION_KEYS: Record<Position, DictKey | null> = { past: 'posPast', present: 'posPresent', path: 'posPath', card: null };

function cardHref(card: DrawnCard, lang: Lang): string | null {
  const deckCard = cardById(card.card_id);
  return deckCard ? cardPath(deckCard, lang) : null;
}

function cardLabel(card: DrawnCard, lang: Lang): string {
  const d = t(lang);
  const position = POSITION_KEYS[card.position];
  const name = card.reversed ? `${card.name}, ${d.reversedTag.toLowerCase()}` : card.name;
  return position ? `${d[position]} · ${name}` : name;
}

export function NightRoom(props: NightRoomProps) {
  const { state, lang, config } = props;
  const d = t(lang);
  const dialog = useRef<HTMLElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const onClose = useRef(props.onClose);
  onClose.current = props.onClose;
  const [followupText, setFollowupText] = useState('');
  const lastPhase = useRef<string | null>(null);

  const reading = state.reading;
  const cards = reading?.cards ?? [];
  const three = cards.length === 3;
  const withAnswer = state.phase === 'reading' && answerVisible(state);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => dialog.current && handleDialogKey(event, dialog.current, () => onClose.current());
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  // the title takes focus on open, on every change of phase (a crisis answer is announced) and when the title
  // moves under the cards with the answer (the old element is gone)
  useEffect(() => {
    const active = document.activeElement;
    const lost = !active || active === document.body || !dialog.current?.contains(active);
    if (lastPhase.current !== state.phase || lost) title.current?.focus();
    lastPhase.current = state.phase;
  }, [state.phase, withAnswer]);

  const then = (action: () => void) => () => {
    action();
    title.current?.focus(); // the button that was pressed disappears
  };

  const status = statusKey(state);
  const quoted = props.question ? `“${props.question}”` : config.kind === 'three' ? d.noQuestionThree : d.noQuestionOne;
  const closeLabel = props.sourceName ? fill(d.closeBackTo, { name: props.sourceName }) : d.close;
  const top = withAnswer ? quoted : state.phase === 'reading' && three ? [d.posPast, d.posPresent, d.posPath].join(' · ') : '';
  const heading = state.phase === 'crisis' && state.crisis ? state.crisis.crisis.title : quoted;
  const headline = state.answer.sections.headline?.trim();

  const submitFollowup = (event: Event) => {
    event.preventDefault();
    const text = followupText.trim();
    if (!text) return;
    props.onFollowup(text);
    setFollowupText('');
  };

  const spread = (small: boolean) => (
    <div class={`spread${three ? '' : ' spread--one'}${small ? ' spread--small' : ''}`}>
      {cards.map((card, i) => (
        <div class="spread__slot" key={card.card_id}>
          <div class={i < state.revealed ? 'flip is-turned' : 'flip'}>
            <div class="flip__inner">
              <div class="flip__side" aria-hidden="true"><img class="back" src={CARD_BACK} alt="" /></div>
              <div class="flip__side flip__side--face">
                {i < state.revealed ? (
                  <CardArt cardId={card.card_id} name={card.name} reversed={card.reversed} lang={lang}
                    sizes={small ? '(min-width: 900px) 128px, 78px' : three ? '106px' : '150px'} />
                ) : null}
              </div>
            </div>
          </div>
          {i < state.revealed ? <CardName cardId={card.card_id} name={card.name} /> : null}
          {three ? <span class="spread__pos">{d[POSITION_KEYS[card.position]!]}</span> : null}
        </div>
      ))}
    </div>
  );

  return (
    <div class="night-room">
      <section class="night" role="dialog" aria-modal="true" aria-labelledby="night-title" tabIndex={-1} ref={dialog}>
        <div class="night__top">
          <p class="night__question">{top}</p>
          <button type="button" class="close-button" aria-label={closeLabel} onClick={props.onClose}>
            <CloseIcon />
          </button>
        </div>
        {withAnswer ? null : <h2 id="night-title" class="night__title" tabIndex={-1} ref={title}>{heading}</h2>}
        <p class={status === 'readingReady' || status === 'followupReady' ? 'visually-hidden' : 'night__status'}
          role="status" aria-live="polite">
          {status ? d[status] : ''}
        </p>

        {state.phase === 'opening' ? (
          <div class="deck-shuffle" aria-hidden="true"><img src={CARD_BACK} alt="" /></div>
        ) : null}

        {state.phase === 'reading' && reading && !withAnswer ? spread(false) : null}

        {withAnswer && reading ? (
          <div class="night__body">
            <div class="night__cards">{spread(true)}</div>
            <div class="night__text">
              <h2 id="night-title" class="answer__headline" tabIndex={-1} ref={title}>{headline || quoted}</h2>
              {state.softLine ? <p class="answer__soft">{state.softLine}</p> : null}
              {reading.verdict ? (
                <div class="verdict">
                  <p class="verdict__word"><VerdictIcon value={reading.verdict.value} />{reading.verdict.label}</p>
                  {state.answer.sections.why ? <p>{d.whyPrefix} {state.answer.sections.why.trim()}</p> : null}
                </div>
              ) : null}
              {answerBlocks(state.answer, cards).map((block, i) => {
                if (block.kind === 'card') {
                  return (
                    <div key={i}>
                      <span class="answer__label">{cardLabel(block.card, lang)}</span>
                      <p class="answer__text">{block.text}</p>
                    </div>
                  );
                }
                if (block.kind === 'synthesis') return <p key={i} class="answer__synthesis">{block.text}</p>;
                if (block.kind === 'step') {
                  return (
                    <div key={i}>
                      <span class="answer__label">{d.stepLabel}</span>
                      <p class="answer__text">{block.text}</p>
                    </div>
                  );
                }
                return null; // the headline is the title; `why` is shown under the verdict
              })}
              {state.answer.replaced === 'fallback' && state.answer.retry && state.stream === 'done' ? (
                <button type="button" class="btn btn--outline" onClick={then(props.onRetry)}>{d.retry}</button>
              ) : null}
              {state.stream === 'lost' ? (
                <div class="night__actions">
                  <HelpLine lang={lang} />
                  <button type="button" class="btn btn--outline" onClick={then(props.onRestore)}>{d.retry}</button>
                </div>
              ) : null}
              {readingShown(state) ? (
                <Followups {...props} text={followupText} setText={setFollowupText} onSubmit={submitFollowup}
                  onConfirm={then(props.onConfirmFollowup)} onCancel={then(props.onCancelFollowup)} />
              ) : null}
              {readingShown(state) ? (
                <div class="night__actions">
                  {three ? (
                    <>
                      <span class="answer__label">{d.moreAbout}</span>
                      <div class="more-cards">
                        {cards.map((card) => {
                          const href = cardHref(card, lang);
                          return href ? <a class="btn btn--outline" href={href} onClick={props.onMoreAbout}>{card.name}</a> : null;
                        })}
                      </div>
                    </>
                  ) : (
                    cards.map((card) => {
                      const href = cardHref(card, lang);
                      return href ? (
                        <a class="btn btn--outline" href={href} onClick={props.onMoreAbout}>{fill(d.fullMeaning, { name: card.name })}</a>
                      ) : null;
                    })
                  )}
                  {props.sourceName ? (
                    <button type="button" class="btn btn--gold" onClick={props.onClose}>{fill(d.backTo, { name: props.sourceName })}</button>
                  ) : null}
                  <button type="button" class="btn btn--text" onClick={props.onAskAnother}>{d.askAnother}</button>
                </div>
              ) : null}
              <p class="night__foot">{d.notGuarantee}</p>
            </div>
          </div>
        ) : null}

        {state.phase === 'reading' && !withAnswer && state.stream === 'lost' ? (
          <div class="night__actions">
            <HelpLine lang={lang} />
            <button type="button" class="btn btn--outline" onClick={then(props.onRestore)}>{d.retry}</button>
          </div>
        ) : null}

        {state.phase === 'crisis' && state.crisis ? <CrisisView payload={state.crisis} lang={lang} /> : null}

        {state.phase === 'error' && state.error ? (
          <div class="night__actions">
            <p role="alert">{d[errorMessageKey(state.error)]}</p>
            {needsHelpLink(state.error) ? <HelpLine lang={lang} /> : null}
            {state.error === 'stage' ? (
              <button type="button" class="btn btn--gold" onClick={() => location.reload()}>{d.retry}</button>
            ) : (
              <button type="button" class="btn btn--outline" onClick={props.onClose}>{d.close}</button>
            )}
          </div>
        ) : null}
      </section>
    </div>
  );
}

interface FollowupProps extends NightRoomProps {
  text: string;
  setText: (text: string) => void;
  onSubmit: (event: Event) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

function Followups(props: FollowupProps) {
  const { state, lang, config } = props;
  const d = t(lang);
  const offer = followupNow(state);
  const counts = state.counts;
  const streaming = state.followups.some((f) => f.status === 'streaming');
  // the form stays mounted while an answer streams (its button is disabled), so focus never falls out of the room
  const formShown = !state.confirm && !state.followupPlus && state.answer.shown === 'model'
    && counts !== null && counts.followup_attempts_left > 0;
  return (
    <section class="followups" aria-label={d.followupLabel}>
      {state.followups.map((f, i) => (
        <div key={i}>
          <p class="followup__q">{d.followupYouAsked}: {f.question}</p>
          {f.softLine ? <p class="answer__soft">{f.softLine}</p> : null}
          <p class="followup__a">{f.text}</p>
          {f.usedReading ? <p class="small">{d.followupUsedReading}</p> : null}
        </div>
      ))}
      {state.followupError ? (
        <>
          <p role="alert">{d[errorMessageKey(state.followupError)]}</p>
          {needsHelpLink(state.followupError) ? <HelpLine lang={lang} /> : null}
        </>
      ) : null}
      {state.followupPlus ? <PlusCard lang={lang} tool={config.tool} /> : null}
      {state.confirm ? (
        <div class="notice">
          <p>{fill(d.followupPaidWarning, { n: state.confirm.remaining })}</p>
          <div class="night__actions">
            <button type="button" class="btn btn--gold" onClick={props.onConfirm}>{d.followupConfirm}</button>
            <button type="button" class="btn btn--text" onClick={props.onCancel}>{d.followupCancel}</button>
          </div>
        </div>
      ) : null}
      {formShown ? (
        <form class="followup-form" onSubmit={props.onSubmit}>
          <label for="followup-input" class="field__label">{d.followupLabel}</label>
          <input id="followup-input" class="input" maxLength={500} autocomplete="off" value={props.text}
            placeholder={d.followupPlaceholder} onInput={(e) => props.setText((e.target as HTMLInputElement).value)} />
          {offer === 'free' && counts ? <p class="small">{fill(d.followupFreeLeft, { n: counts.followups_left })}</p> : null}
          <button type="submit" class="btn btn--outline" disabled={streaming}>{d.followupSend}</button>
        </form>
      ) : counts && counts.followup_attempts_left <= 0 ? (
        <p class="small">{d.followupNone}</p>
      ) : null}
    </section>
  );
}
```

- [ ] **Step 2: Write the island**

Create `site/src/islands/ReadingIsland.tsx`:

```tsx
// The draw panel and its night room (spec 4.4a §4). Thin: state lives in src/lib/nightRoom.ts, requests in
// src/lib/readingFlow.ts, the page's choices in src/lib/panel.ts; here are only the DOM, timers, focus and history.
// History: the open room adds one entry with the same address (still no address of its own), so the phone's Back
// closes the room instead of leaving the page; × and Escape step back over that entry.
import { useEffect, useMemo, useReducer, useRef, useState } from 'preact/hooks';
import { t } from '../i18n';
import { analyticsEvent, sendEvent } from '../lib/analytics';
import { browserFetch, createApi } from '../lib/api';
import { CARD_BACK } from '../lib/deck';
import { CLOSED, DEAL_MS, FLIP_INTERVAL_MS, nightReducer, transitionEvents, type NightAction, type NightState } from '../lib/nightRoom';
import {
  buildCreateBody, cardsFor, drawLabelKey, initialKind, panelConfig, situationKey, toolFor, type PanelPage,
} from '../lib/panel';
import { askFollowup, restoreReading, startReading, streamReading, type FlowDeps } from '../lib/readingFlow';
import { turnstileToken } from '../lib/turnstile';
import { SITUATIONS, type Kind, type Lang, type Situation, type Tool } from '../lib/types';
import { NightRoom } from '../components/ui/NightRoom';
import { PlusCard } from '../components/ui/PlusCard';
import { CheckIcon } from '../components/ui/icons';

interface Props {
  lang: Lang;
  page: PanelPage;
  cardId?: string;
  cardName?: string;
  showBacks?: boolean;
}

function timeZone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}

function prefersReducedMotion(): boolean {
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export default function ReadingIsland({ lang, page, cardId, cardName, showBacks = false }: Props) {
  const d = t(lang);
  const config = useMemo(() => panelConfig(page, lang, cardId ?? null), [page, lang, cardId]);
  const [kind, setKind] = useState<Kind>(config.kind);
  const [situation, setSituation] = useState<Situation | null>(null);
  const [question, setQuestion] = useState('');
  const [state, rawDispatch] = useReducer<NightState, NightAction>(nightReducer, CLOSED);
  const drawButton = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const run = useRef(0); // each draw is a run; a closed room ignores the late answers of its run
  const drawn = useRef({ at: 0, tz: undefined as string | undefined, question: '', id: '', tool: config.tool as Tool });
  const previous = useRef<NightState>(CLOSED);
  const inHistory = useRef(false); // the room's history entry is on top
  const roomIsOpen = useRef(false);
  const focusQuestion = useRef(false); // "Ask another question": focus the question field once the room is closed
  const api = useMemo(() => createApi(browserFetch()), []);
  const inputId = `question-${page}`;

  useEffect(() => {
    const fromHash = () => setKind(initialKind(config, location.hash));
    fromHash();
    if (page !== 'card') sendEvent(analyticsEvent('tool_view', config.tool, lang));
    const onPop = () => {
      if (!inHistory.current) return;
      inHistory.current = false;
      if (roomIsOpen.current) closeNow();
    };
    window.addEventListener('popstate', onPop);
    if (config.countToggle) window.addEventListener('hashchange', fromHash); // the footer link "Una carta" on this page
    return () => {
      window.removeEventListener('popstate', onPop);
      window.removeEventListener('hashchange', fromHash);
    };
  }, []);

  const deps = (): FlowDeps => {
    const mine = run.current;
    return {
      api,
      dispatch: (action) => {
        if (run.current !== mine) return;
        if (action.type === 'created') drawn.current.id = action.reading.id;
        rawDispatch(action);
      },
      turnstileToken: (sitekey) => turnstileToken(sitekey, { document, window }),
      sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
      reducedMotion: prefersReducedMotion(),
    };
  };

  // analytics on transitions: night_open, cards_revealed, reading_shown
  useEffect(() => {
    for (const name of transitionEvents(previous.current, state)) {
      const params = name === 'cards_revealed' ? { cards_count: state.reading?.cards.length ?? 1 }
        : name === 'reading_shown' ? { ms_from_draw: Math.min(Math.max(Date.now() - drawn.current.at, 0), 600000) } : {};
      sendEvent(analyticsEvent(name, drawn.current.tool, lang, params));
    }
    const wasOpen = previous.current.phase !== 'closed' && previous.current.phase !== 'limit';
    const isOpen = state.phase !== 'closed' && state.phase !== 'limit';
    roomIsOpen.current = isOpen;
    if (wasOpen && !isOpen && state.phase === 'closed') {
      (focusQuestion.current ? input.current : drawButton.current)?.focus();
      focusQuestion.current = false;
    }
    if (wasOpen && !isOpen && inHistory.current) { // closed by the limit: drop the room's history entry
      inHistory.current = false;
      history.back();
    }
    if (state.phase === 'crisis' && previous.current.phase !== 'crisis') setQuestion(''); // "we haven't saved it"
    document.body.classList.toggle('is-locked', isOpen);
    previous.current = state;
  }, [state]);

  // the cards turn one after another (none of this with reduced motion: they arrive turned)
  useEffect(() => {
    if (state.phase !== 'reading' || !state.reading || state.revealed >= state.reading.cards.length) return;
    const timer = setTimeout(() => rawDispatch({ type: 'flip' }), state.revealed === 0 ? DEAL_MS : FLIP_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [state.phase, state.reading, state.revealed]);

  const draw = (event: Event) => {
    event.preventDefault();
    run.current += 1;
    const tz = timeZone();
    const body = buildCreateBody(config, { kind, question, situation, tz });
    drawn.current = { at: Date.now(), tz, question: body.question ?? '', id: '', tool: toolFor(config, kind) };
    sendEvent(analyticsEvent('draw_click', drawn.current.tool, lang, { has_question: Boolean(body.question), entry: config.entry }));
    if (!inHistory.current) {
      history.pushState({ arcanaNight: true }, '');
      inHistory.current = true;
    }
    rawDispatch({ type: 'open' });
    void startReading(deps(), body);
  };

  function closeNow() {
    run.current += 1;
    rawDispatch({ type: 'close' });
  }

  const close = () => {
    if (inHistory.current) history.back(); // popstate closes the room
    else closeNow();
  };

  const askAnother = () => {
    focusQuestion.current = true;
    setQuestion('');
    close();
  };

  // always first without use_reading: after the free ones the API answers 402 confirm with the readings left (the
  // warning) or 402 plus, and only the confirmation sends use_reading: true
  const onFollowup = (text: string) => void askFollowup(deps(), drawn.current.id, text, drawn.current.tz, false);

  const roomOpen = state.phase !== 'closed' && state.phase !== 'limit';

  if (state.phase === 'limit') { // screen 11a: a day block, not the dark panel
    return (
      <div class="plus-slot" id={config.countToggle ? 'una-carta' : undefined}>
        <PlusCard lang={lang} tool={drawn.current.tool} focusOnShow />
      </div>
    );
  }

  return (
    <div class="night-panel" id={config.countToggle ? 'una-carta' : undefined}>
      <form class="field" onSubmit={draw}>
        {config.countToggle ? (
          <div class="chips" role="group" aria-label={d.countGroupLabel}>
            {(['one', 'three'] as const).map((k) => (
              <button type="button" class="chip" aria-pressed={kind === k} onClick={() => setKind(k)}>
                <CheckIcon />{k === 'one' ? d.oneCardChip : d.threeCardsChip}
              </button>
            ))}
          </div>
        ) : null}
        {config.situations ? (
          <div class="field">
            <span id={`situation-${page}`} class="field__label">{d.situationLabel}</span>
            <div class="chips" role="group" aria-labelledby={`situation-${page}`}>
              {SITUATIONS.map((s) => (
                <button type="button" class="chip" aria-pressed={situation === s}
                  onClick={() => setSituation(situation === s ? null : s)}>
                  <CheckIcon />{d[situationKey(s)]}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <label for={inputId}>{d[config.labelKey]}</label>
        <input id={inputId} ref={input} class="input" type="text" maxLength={500} autocomplete="off"
          placeholder={d[config.placeholderKey]} value={question}
          onInput={(e) => setQuestion((e.target as HTMLInputElement).value)} />
        {showBacks ? (
          <div class="backs" aria-hidden="true">
            {Array.from({ length: cardsFor(kind) }, () => <img src={CARD_BACK} alt="" />)}
          </div>
        ) : null}
        <button type="submit" class="btn btn--gold btn--block" ref={drawButton}>{d[drawLabelKey(config, kind)]}</button>
        <p class="panel-hint">{d.freeNoSignup}</p>
      </form>
      {roomOpen ? (
        <NightRoom
          state={state}
          lang={lang}
          config={config}
          question={drawn.current.question}
          sourceName={cardName ?? null}
          onClose={close}
          onRetry={() => void streamReading(deps(), drawn.current.id, drawn.current.tz, 'retry')}
          onRestore={() => void restoreReading(deps(), drawn.current.id, drawn.current.tz)}
          onFollowup={onFollowup}
          onConfirmFollowup={() => state.confirm && void askFollowup(deps(), drawn.current.id, state.confirm.question, drawn.current.tz, true)}
          onCancelFollowup={() => rawDispatch({ type: 'followupCancel' })}
          onMoreAbout={() => sendEvent(analyticsEvent('more_about_cards', drawn.current.tool, lang))}
          onAskAnother={askAnother}
        />
      ) : null}
    </div>
  );
}
```

- [ ] **Step 3: Write the page templates and the pages**

Create `site/src/views/HomeView.astro`:

```astro
---
// Home EN / ES (screens 1, 12a, 13a): the question and three cards in the night panel; ES adds "1 carta / 3 cartas"
// and is the one-card page at #una-carta. Hub links and diary steps wait for stages 6 and 4.4b.
import Base from '../layouts/Base.astro';
import CardFigure from '../components/CardFigure.astro';
import ReadingIsland from '../islands/ReadingIsland';
import { t } from '../i18n';
import { CARD_BACK, cardById } from '../lib/deck';
import { cardPath, pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
const formats = [
  ...(lang === 'en' ? [{ href: pagePath('one_card', lang), name: d.fmtOneCard, hint: d.fmtOneCardHint }] : []),
  { href: pagePath('yes_no', lang), name: d.fmtYesNo, hint: d.fmtYesNoHint },
  { href: pagePath('love', lang), name: d.fmtLove, hint: d.fmtLoveHint },
  { href: pagePath('daily', lang), name: d.fmtDaily, hint: d.fmtDailyHint },
];
const faces = ['major-18-moon', 'major-19-sun', 'major-16-tower'].map((id) => cardById(id)!);
const steps = [d.howStep1, d.howStep2, d.howStep3];
---
<Base lang={lang} title={d.homeTitle} path={pagePath('home', lang)} current="home">
  <div class="tool-layout">
    <section class="page-hero">
      <p class="eyebrow">{d.homeEyebrow}</p>
      <h1 class="display display--home">{d.homeH1}</h1>
      <p class="lead">{d.homeLead}</p>
    </section>
    <ReadingIsland client:load lang={lang} page="home" showBacks />
  </div>

  <section class="page-section" aria-labelledby="other-ways">
    <h2 class="h2" id="other-ways">{d.otherWays}</h2>
    <ul class="link-list">
      {formats.map((f) => (
        <li>
          <a href={f.href}>
            <span class="link-list__text"><span class="link-list__name">{f.name}</span><span class="link-list__hint">{f.hint}</span></span>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M7 4l5 5-5 5"></path></svg>
          </a>
        </li>
      ))}
    </ul>
  </section>

  <section class="tile" aria-labelledby="daily-tile">
    <img src={CARD_BACK} alt="" />
    <div class="tile__body">
      <p class="eyebrow" id="daily-tile">{d.dailyTileEyebrow}</p>
      <p>{d.dailyTileText}</p>
      <a href={pagePath('daily', lang)}>{d.dailyTileLink}</a>
    </div>
  </section>

  <section class="page-section" aria-labelledby="learn">
    <h2 class="h2" id="learn">{d.learnTitle}</h2>
    <p class="lead">{d.learnLead}</p>
    <div class="card-row">
      {faces.map((card) => (
        <a href={cardPath(card, lang)}><CardFigure card={card} lang={lang} sizes="100px" /></a>
      ))}
    </div>
  </section>

  <section class="page-section" aria-labelledby="how">
    <h2 class="h2" id="how">{d.howTitle}</h2>
    <ol class="steps">
      {steps.map((text, i) => <li><span class="steps__n" aria-hidden="true">{i + 1}</span><span>{text}</span></li>)}
    </ol>
    <p class="small muted">{d.disclaimer}</p>
  </section>
</Base>
```

Create `site/src/views/ToolView.astro`:

```astro
---
// A tool page (screens 5a, 6, one card): eyebrow, title, lead and the night panel; love adds a note under it.
import Base from '../layouts/Base.astro';
import ReadingIsland from '../islands/ReadingIsland';
import { t, type DictKey } from '../i18n';
import { pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

type ToolPage = 'one_card' | 'yes_no' | 'love';

interface Props {
  lang: Lang;
  page: ToolPage;
}

const { lang, page } = Astro.props;
const d = t(lang);
const COPY: Record<ToolPage, { title: DictKey; eyebrow: DictKey; h1: DictKey; lead: DictKey; note?: DictKey }> = {
  one_card: { title: 'oneCardTitle', eyebrow: 'oneCardEyebrow', h1: 'oneCardH1', lead: 'oneCardLead' },
  yes_no: { title: 'yesNoTitle', eyebrow: 'yesNoEyebrow', h1: 'yesNoH1', lead: 'yesNoLead' },
  love: { title: 'loveTitle', eyebrow: 'loveEyebrow', h1: 'loveH1', lead: 'loveLead', note: 'loveNote' },
};
const copy = COPY[page];
---
<Base lang={lang} title={d[copy.title]} path={pagePath(page, lang)} current={page === 'one_card' ? undefined : page}>
  <div class="tool-layout">
    <section class="page-hero">
      <p class="eyebrow">{d[copy.eyebrow]}</p>
      <h1 class="display">{d[copy.h1]}</h1>
      <p class="lead">{d[copy.lead]}</p>
    </section>
    <div>
      <ReadingIsland client:load lang={lang} page={page} />
      {copy.note ? <p class="small muted">{d[copy.note]}</p> : null}
    </div>
  </div>
</Base>
```

Create `site/src/views/CardView.astro`:

```astro
---
// The simple card page (spec 4.4a §2.2, §3) until the stage 6 template takes the same address: the picture, the
// keywords, the upright and the reversed meaning from content/cards, the draw panel of path П2 and the
// neighbouring cards.
import Base from '../layouts/Base.astro';
import CardFigure from '../components/CardFigure.astro';
import ReadingIsland from '../islands/ReadingIsland';
import { fill, t } from '../i18n';
import { cardName, neighbors, type DeckCard } from '../lib/deck';
import { cardPath } from '../lib/routes';
import type { Lang } from '../lib/types';

export interface Meaning {
  card_id: string;
  keywords: string[];
  upright: string;
  reversed: string;
}

interface Props {
  lang: Lang;
  card: DeckCard;
  meaning: Meaning;
}

const { lang, card, meaning } = Astro.props;
const d = t(lang);
const name = cardName(card, lang);
const { prev, next } = neighbors(card);
const eyebrow = card.arcana === 'major' ? fill(d.cardEyebrowMajor, { numeral: card.numeral }) : d.cardEyebrowMinor;
---
<Base lang={lang} title={fill(d.cardTitle, { name })} path={cardPath(card, lang)}>
  <div class="card-page">
    <div class="card-page__art">
      <CardFigure card={card} lang={lang} sizes="(min-width: 900px) 280px, 70vw" eager />
    </div>
    <div class="card-page__text">
      <p class="eyebrow">{eyebrow}</p>
      <h1 class="display">{name}</h1>
      <p class="keywords">{meaning.keywords.join(' · ')}</p>
      <section aria-labelledby="upright">
        <h2 class="h2" id="upright">{d.uprightTitle}</h2>
        <p>{meaning.upright}</p>
      </section>
      <section aria-labelledby="reversed">
        <h2 class="h2" id="reversed">{fill(d.reversedTitle, { name })}</h2>
        <p>{meaning.reversed}</p>
      </section>
    </div>
    <section aria-labelledby="draw-heading">
      <h2 class="h2" id="draw-heading">{d.cardDrawHeading}</h2>
      <p class="muted">{d.cardDrawLead}</p>
      <ReadingIsland client:visible lang={lang} page="card" cardId={card.card_id} cardName={name} />
    </section>
  </div>
  <nav class="card-nav" aria-label={d.cardNav}>
    <a href={cardPath(prev, lang)}><small>{d.prevCard}</small>{prev.numeral} {cardName(prev, lang)}</a>
    <a href={cardPath(next, lang)}><small>{d.nextCard}</small>{next.numeral} {cardName(next, lang)}</a>
  </nav>
</Base>
```

Replace the whole of `site/src/pages/index.astro` with:

```astro
---
import HomeView from '../views/HomeView.astro';
---
<HomeView lang="en" />
```

Create `site/src/pages/one-card.astro`:

```astro
---
import ToolView from '../views/ToolView.astro';
---
<ToolView lang="en" page="one_card" />
```

Create `site/src/pages/yes-no.astro`:

```astro
---
import ToolView from '../views/ToolView.astro';
---
<ToolView lang="en" page="yes_no" />
```

Create `site/src/pages/love.astro`:

```astro
---
import ToolView from '../views/ToolView.astro';
---
<ToolView lang="en" page="love" />
```

Create `site/src/pages/es/index.astro`:

```astro
---
import HomeView from '../../views/HomeView.astro';
---
<HomeView lang="es" />
```

Create `site/src/pages/es/si-o-no.astro`:

```astro
---
import ToolView from '../../views/ToolView.astro';
---
<ToolView lang="es" page="yes_no" />
```

Create `site/src/pages/es/amor.astro`:

```astro
---
import ToolView from '../../views/ToolView.astro';
---
<ToolView lang="es" page="love" />
```

Create `site/src/pages/cards/[slug].astro`:

```astro
---
import CardView from '../../views/CardView.astro';
import meanings from '../../data/meanings.en.json';
import { DECK } from '../../lib/deck';

export function getStaticPaths() {
  return DECK.map((card) => ({
    params: { slug: card.slug_en },
    props: { card, meaning: meanings.find((m) => m.card_id === card.card_id)! },
  }));
}

const { card, meaning } = Astro.props;
---
<CardView lang="en" card={card} meaning={meaning} />
```

Create `site/src/pages/es/cartas/[slug].astro`:

```astro
---
import CardView from '../../../views/CardView.astro';
import meanings from '../../../data/meanings.es.json';
import { DECK } from '../../../lib/deck';

export function getStaticPaths() {
  return DECK.map((card) => ({
    params: { slug: card.slug_es },
    props: { card, meaning: meanings.find((m) => m.card_id === card.card_id)! },
  }));
}

const { card, meaning } = Astro.props;
---
<CardView lang="es" card={card} meaning={meaning} />
```

- [ ] **Step 4: Run all Vitest tests and build**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run`
Expected: `Test Files  17 passed (17)`, `Tests  122 passed (122)` (the source guards now also cover the new files).

Run: `cd ~/arcana-diary && deploy/build-site.sh 2>&1 | tail -3 && find site/dist -name '*.html' | wc -l && ls site/dist/_astro | grep -c ReadingIsland`
Expected: `165 page(s) built`, `Complete!`, `165`, `1`.

- [ ] **Step 5: Check the built pages by eye in the HTML**

Run: `cd ~/arcana-diary && grep -o '<html lang="[a-z]*"' site/dist/es.html site/dist/es/cartas/la-luna.html site/dist/yes-no.html && grep -c 'Saca una carta para tu pregunta' site/dist/es/cartas/la-luna.html && grep -o 'id="una-carta"' site/dist/es.html | head -1`
Expected: three lines (grep may print them in another order) — `site/dist/es.html:<html lang="es"`, `site/dist/es/cartas/la-luna.html:<html lang="es"`, `site/dist/yes-no.html:<html lang="en"`; then `1` and `id="una-carta"`.

- [ ] **Step 6: Commit**

```bash
cd ~/arcana-diary
git add site/src/components/ui site/src/islands/ReadingIsland.tsx site/src/views site/src/pages
git commit -m "feat(site): the night room and the tool and card pages, EN and ES

Home (ES with 1 carta / 3 cartas and #una-carta), one card, yes or no, love, 78 simple card pages per
language with the draw panel of path П2; crisis answer, Plus card at the limit, follow-ups.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Card of the Day

**Files:**
- Create: `site/src/islands/DailyIsland.tsx`, `site/src/views/DailyView.astro`, `site/src/pages/daily.astro`, `site/src/pages/es/carta-del-dia.astro`, `site/src/pages/data/daily-[lang].json.ts`

**Interfaces:**
- Consumes: `dailyNext`, `shownFromBase`, `localIsoDay`, `formatDay`, `baseUrl`, `BaseMeaning`, `DailyShown` (Task 7); `createApi`, `browserFetch` (Task 5); `CARD_BACK` (Task 3); `cardPath` (Task 3); `errorMessageKey`, `needsHelpLink`, `ErrorKind` (Task 5); `CardFace`, `HelpLine` (Task 9); `analyticsEvent`, `sendEvent` (Task 7); `Base.astro` (Task 8); `site/src/data/meanings.<lang>.json` (Task 2).
- Produces: island `DailyIsland` (default export) props `{lang}`; `DailyView({lang})`; static files `/data/daily-en.json`, `/data/daily-es.json` — arrays of `{card_id, upright}` (78).

- [ ] **Step 1: Write the island, the view, the pages and the base file**

Create `site/src/islands/DailyIsland.tsx`:

```tsx
// Card of the Day (screens 7a, 7b; spec 4.4a §5): tap the back → GET /api/daily → the card and its text. On 503
// the card comes from the card base (src/lib/daily.ts). "Remind me tomorrow" and "Save to diary" are stage 4.4b.
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t } from '../i18n';
import { analyticsEvent, sendEvent } from '../lib/analytics';
import { browserFetch, createApi } from '../lib/api';
import { baseUrl, dailyNext, formatDay, localIsoDay, shownFromBase, type BaseMeaning, type DailyShown } from '../lib/daily';
import { CARD_BACK } from '../lib/deck';
import { errorMessageKey, needsHelpLink, type ErrorKind } from '../lib/errors';
import { cardPath } from '../lib/routes';
import type { Lang } from '../lib/types';
import { CardFace } from '../components/ui/CardFace';
import { HelpLine } from '../components/ui/HelpLine';

type View = { type: 'back' } | { type: 'loading' } | { type: 'shown'; shown: DailyShown } | { type: 'error'; error: ErrorKind };

function timeZone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}

async function fromBase(lang: Lang, tz: string | undefined): Promise<DailyShown | null> {
  try {
    const response = await fetch(baseUrl(lang));
    if (!response.ok) return null;
    return shownFromBase(localIsoDay(new Date(), tz), lang, (await response.json()) as BaseMeaning[]);
  } catch {
    return null;
  }
}

export default function DailyIsland({ lang }: { lang: Lang }) {
  const d = t(lang);
  const [view, setView] = useState<View>({ type: 'back' });
  const heading = useRef<HTMLHeadingElement>(null);
  const tappedAt = useRef(0);

  useEffect(() => sendEvent(analyticsEvent('tool_view', 'daily', lang)), []);

  useEffect(() => {
    if (view.type !== 'shown') return;
    sendEvent(analyticsEvent('cards_revealed', 'daily', lang, { cards_count: 1 }));
    sendEvent(analyticsEvent('reading_shown', 'daily', lang, { ms_from_draw: Math.min(Date.now() - tappedAt.current, 600000) }));
    heading.current?.focus();
  }, [view.type]);

  const turn = async () => {
    tappedAt.current = Date.now();
    sendEvent(analyticsEvent('draw_click', 'daily', lang, { has_question: false, entry: 'tool' }));
    setView({ type: 'loading' });
    const tz = timeZone();
    const next = dailyNext(await createApi(browserFetch()).getDaily(lang, tz), lang);
    if (next.type === 'shown') return setView({ type: 'shown', shown: next.shown });
    if (next.type === 'error') return setView({ type: 'error', error: next.error });
    const shown = await fromBase(lang, tz);
    setView(shown ? { type: 'shown', shown } : { type: 'error', error: 'unavailable' });
  };

  if (view.type === 'shown') {
    const { shown } = view;
    return (
      <section class="daily" aria-labelledby="daily-card">
        <p class="eyebrow">{formatDay(shown.day, lang)}</p>
        <CardFace cardId={shown.card.card_id} name={shown.name} reversed={shown.reversed} lang={lang} />
        <h2 id="daily-card" class="h2" tabIndex={-1} ref={heading}>
          {shown.name}{shown.reversed ? ` · ${d.reversedTag}` : ''}
        </h2>
        {shown.fromBase ? <p class="small">{d.dailyFallbackNote}</p> : null}
        <p class="daily__text">{shown.text}</p>
        <a href={cardPath(shown.card, lang)} onClick={() => sendEvent(analyticsEvent('more_about_cards', 'daily', lang))}>
          {fill(d.fullMeaning, { name: shown.name })}
        </a>
      </section>
    );
  }

  return (
    <section class="daily" aria-label={d.dailyEyebrow}>
      <button type="button" class="daily__back" onClick={turn} disabled={view.type === 'loading'}>
        <img src={CARD_BACK} alt="" />
        <span>{view.type === 'loading' ? d.dailyLoading : d.dailyTap}</span>
      </button>
      <p class="small" role="status" aria-live="polite">{view.type === 'loading' ? d.dailyLoading : ''}</p>
      {view.type === 'error' ? (
        <>
          <p role="alert">{view.error === 'unavailable' ? d.dailyError : d[errorMessageKey(view.error)]}</p>
          {needsHelpLink(view.error) ? <HelpLine lang={lang} /> : null}
        </>
      ) : null}
      <p class="small">{d.dailyNote}</p>
    </section>
  );
}
```

Create `site/src/views/DailyView.astro`:

```astro
---
// Card of the Day (screens 7a, 7b).
import Base from '../layouts/Base.astro';
import DailyIsland from '../islands/DailyIsland';
import { t } from '../i18n';
import { pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
---
<Base lang={lang} title={d.dailyTitle} path={pagePath('daily', lang)} current="daily">
  <section class="page-hero">
    <p class="eyebrow">{d.dailyEyebrow}</p>
    <h1 class="display">{d.dailyH1}</h1>
  </section>
  <DailyIsland client:load lang={lang} />
</Base>
```

Create `site/src/pages/daily.astro`:

```astro
---
import DailyView from '../views/DailyView.astro';
---
<DailyView lang="en" />
```

Create `site/src/pages/es/carta-del-dia.astro`:

```astro
---
import DailyView from '../../views/DailyView.astro';
---
<DailyView lang="es" />
```

Create `site/src/pages/data/daily-[lang].json.ts`:

```ts
// /data/daily-en.json, /data/daily-es.json: upright meanings of the 78 cards, fetched by the Card of the Day only
// when GET /api/daily answers 503 (src/lib/daily.ts).
import en from '../../data/meanings.en.json';
import es from '../../data/meanings.es.json';

export function getStaticPaths() {
  return [{ params: { lang: 'en' } }, { params: { lang: 'es' } }];
}

export function GET({ params }: { params: { lang: 'en' | 'es' } }) {
  const meanings = params.lang === 'es' ? es : en;
  return new Response(JSON.stringify(meanings.map((m) => ({ card_id: m.card_id, upright: m.upright }))), {
    headers: { 'content-type': 'application/json' },
  });
}
```

- [ ] **Step 2: Run all Vitest tests, build and check every page of spec §3**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run`
Expected: `Test Files  17 passed (17)`, `Tests  122 passed (122)`.

Run: `cd ~/arcana-diary && deploy/build-site.sh 2>&1 | tail -3 && python3 tools/site/check_dist.py && python3 -c "import json; d=json.load(open('site/dist/data/daily-es.json')); print(len(d), sorted(d[0]))"`
Expected: `167 page(s) built`, `Complete!`, `OK: 167 pages`, `78 ['card_id', 'upright']`.

- [ ] **Step 3: Commit**

```bash
cd ~/arcana-diary
git add site/src/islands/DailyIsland.tsx site/src/views/DailyView.astro site/src/pages/daily.astro \
  site/src/pages/es/carta-del-dia.astro site/src/pages/data
git commit -m "feat(site): Card of the Day, EN and ES, with the card base when the API answers 503

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Caddy serves the pages and the 404 page of each language

> **Amendments after the Fable re-check, required.** **R1 (open redirect):** restrict both redirect patterns to the site's own address characters — `^(/[a-z0-9][a-z0-9/-]*)/$` and `^(/[a-z0-9][a-z0-9/-]*)\.html$` (keep the `/index.html` rule equally strict). Add to `deploy/test-site-routes.sh`: `/%5Cexample.com/` and `/%5Cexample.com/x.html` answer 404 and neither response has a `Location` header; run it on throwaway containers and report. **R4:** keep the query string in these redirects (`/es/?utm_source=x` → `/es?utm_source=x`), with one test line.

**Files:**
- Modify: `deploy/Caddyfile`, `deploy/check-indexing.sh`
- Create: `deploy/test-site-routes.sh`

**Interfaces:**
- Consumes: `site/dist` from Task 10 (`one-card.html`, `es.html`, `es/404.html`, `404.html`, …); `caddy:2.8.4`; `deploy/caddy/*.caddy` parts (never `stage_auth.caddy`).
- Produces: `handle` blocks that redirect `/index.html` → `/`, `/x/` → `/x` and `/x.html` → `/x` (308; `/api/*` keeps its own block first); in the `handle` block `try_files {path} {path}.html` before `file_server`; a `handle_errors 404` block that serves `/es/404.html` for `/es` and `/es/*`, otherwise `/404.html`, with status 404 and the noindex part; `deploy/test-site-routes.sh` (throwaway container `arcana-routetest-<pid>`, removed on exit; prints `OK: адреса страниц и 404`).

- [ ] **Step 1: Write the failing check**

Create `deploy/test-site-routes.sh`:

```bash
#!/usr/bin/env bash
# Проверяет адреса страниц 4.4а на временном контейнере caddy:2.8.4 (тот же образ, что в бою) с этим Caddyfile и
# собранным site/dist: страницы открываются без .html и без слэша в конце, неизвестный адрес получает 404 на своём
# языке. LAUNCHED=true — без пароля стенда (его проверяет deploy/test-stage-auth.sh). Боевые контейнеры,
# deploy/.env и deploy/caddy/stage_auth.caddy не трогает; контейнер проверки удаляется в конце.
# Сначала собрать сайт: deploy/build-site.sh.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
DIST="$(cd "${DIST:-$DIR/../site/dist}" && pwd)"
[ -f "$DIST/index.html" ] || { echo "нет $DIST/index.html: сначала deploy/build-site.sh"; exit 2; }
TMP="$(mktemp -d)"
NAME="arcana-routetest-$$"
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; rm -rf "$TMP"; }
trap cleanup EXIT

mkdir -p "$TMP/parts"
cp "$DIR/Caddyfile" "$TMP/Caddyfile"
for f in "$DIR"/caddy/*.caddy; do
  [ "$(basename "$f")" = stage_auth.caddy ] || cp "$f" "$TMP/parts/"
done
chmod -R a+rX "$TMP"

docker run -d --rm --name "$NAME" -e SITE_DOMAIN=arcana.test -e TLS_MODE=local -e LAUNCHED=true \
  -e TRUST_CLOUDFLARE=false -v "$TMP/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$TMP/parts:/etc/caddy/parts:ro" \
  -v "$DIST:/srv/site:ro" -p 127.0.0.1::443 caddy:2.8.4 >/dev/null
PORT="$(docker port "$NAME" 443/tcp | head -1 | sed 's/.*://')"
URL="https://arcana.test:$PORT"
CURL=(curl -sS -k --max-time 10 --resolve "arcana.test:$PORT:127.0.0.1")
for _ in $(seq 1 50); do "${CURL[@]}" -o /dev/null "$URL/" 2>/dev/null && break; sleep 0.2; done

fails=0
expect() { if [ "$2" = "$3" ]; then echo "PASS $1 ($2)"; else echo "FAIL $1: ожидалось '$3', получено '$2'"; fails=$((fails + 1)); fi; }
status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$URL$1"; }
html_lang() { "${CURL[@]}" "$URL$1" | grep -o '<html lang="[a-z]*"' | head -1; }
moved_to() { "${CURL[@]}" -o /dev/null -w '%{http_code} %{redirect_url}' "$URL$1"; }

for path in / /one-card /yes-no /love /daily /cards/the-moon /cards/ace-of-cups /es /es/si-o-no /es/amor \
  /es/carta-del-dia /es/cartas/la-luna /404 /es/404 /data/daily-en.json /data/daily-es.json /cards/back.svg; do
  expect "$path" "$(status "$path")" 200
done
expect "/es — испанская главная" "$(html_lang /es)" '<html lang="es"'
expect "/nope" "$(status /nope)" 404
expect "/nope — страница 404 EN" "$(html_lang /nope)" '<html lang="en"'
expect "/es/nope" "$(status /es/nope)" 404
expect "/es/nope — страница 404 ES" "$(html_lang /es/nope)" '<html lang="es"'
expect "/cards/no-such-card" "$(status /cards/no-such-card)" 404
expect "/es/ → /es" "$(moved_to /es/)" "308 $URL/es"
expect "/one-card/ → /one-card" "$(moved_to /one-card/)" "308 $URL/one-card"
expect "/one-card.html → /one-card" "$(moved_to /one-card.html)" "308 $URL/one-card"
expect "/index.html → /" "$(moved_to /index.html)" "308 $URL/"
expect "/api/ не перенаправляется" "$(status /api/limits/)" 502

if [ "$fails" -eq 0 ]; then echo "OK: адреса страниц и 404"; else echo "ПРОВАЛ: $fails"; exit 1; fi
```

Run: `cd ~/arcana-diary && chmod +x deploy/test-site-routes.sh && deploy/test-site-routes.sh | grep -E '^FAIL /one-card:|ПРОВАЛ'`
Expected: `FAIL /one-card: ожидалось '200', получено '404'` and `ПРОВАЛ: 20` (every address without `.html`, both 404 pages and the four redirects fail; the container is removed on exit).

- [ ] **Step 2: Serve the page files, the redirects and the 404 pages**

In `deploy/Caddyfile`, replace:

```
	}
	handle {
		# LAUNCHED=false: the stage cookie, so /api/* requests with Authorization: Bearer pass the password (4.3)
```

with:

```
	}
	# stage 4.4a: one address per page — a trailing slash or .html goes to the clean address (308)
	handle /index.html {
		redir * / 308
	}
	@slash path_regexp slash ^(/.+)/$
	handle @slash {
		redir {re.slash.1} 308
	}
	@html path_regexp html ^(/.+)\.html$
	handle @html {
		redir {re.html.1} 308
	}
	handle {
		# LAUNCHED=false: the stage cookie, so /api/* requests with Authorization: Bearer pass the password (4.3)
```

In `deploy/Caddyfile`, replace:

```
		root * /srv/site
		file_server
	}
	handle_errors {
```

with:

```
		root * /srv/site
		# stage 4.4a: one HTML file per page (Astro build.format "file"): /one-card → /one-card.html, /es → /es.html
		try_files {path} {path}.html
		file_server
	}
	# stage 4.4a: an unknown address gets the 404 page of its language with status 404 (/es/... → /es/404.html)
	handle_errors 404 {
		import /etc/caddy/parts/noindex-{$LAUNCHED}.caddy
		root * /srv/site
		# a map, not `handle @es`: in Caddy 2.8 `handle_errors 404` replaces the matchers of the blocks inside it
		map {path} {not_found_page} {
			~^/es(/|$) /es/404.html
			default /404.html
		}
		rewrite * {not_found_page}
		file_server
	}
	handle_errors {
```

`deploy/check-indexing.sh` runs after the owner's deploy and reads `deploy/.env`, so here it is only syntax-checked.

In `deploy/check-indexing.sh`, replace:

```bash
  expect "сайт с паролем" "$(status "${AUTH[@]}" "https://$D/")" 200
```

with:

```bash
  expect "сайт с паролем" "$(status "${AUTH[@]}" "https://$D/")" 200
  # stage 4.4a: the new Caddyfile is live — a page without .html opens, an unknown address is a 404 page
  expect "страница без .html с паролем" "$(status "${AUTH[@]}" "https://$D/one-card")" 200
  expect "неизвестный адрес с паролем" "$(status "${AUTH[@]}" "https://$D/no-such-page")" 404
```

Run: `cd ~/arcana-diary && bash -n deploy/check-indexing.sh && echo syntax ok`
Expected: `syntax ok`.

- [ ] **Step 3: Run the route check and the stage-password check**

Run: `cd ~/arcana-diary && deploy/test-site-routes.sh | tail -1 && deploy/test-stage-auth.sh | tail -1 && docker ps -a --format '{{.Names}}'`
Expected: `OK: адреса страниц и 404`, `OK: пароль и кука стенда работают`, and only `arcana-caddy-1`, `arcana-api-1` (both checks use throwaway containers and a dummy password; the running Caddy is not touched — it picks the new Caddyfile up only when the owner deploys).

- [ ] **Step 4: Final run of every suite**

Run: `cd ~/arcana-diary && docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm -v "$PWD/site:/app" -w /app node:22 npx vitest run 2>&1 | grep -E 'Test Files|Tests ' && api/.venv/bin/pytest -q tools/site | tail -1 && python3 tools/site/sync_site_data.py --check && python3 tools/site/check_dist.py && (cd api && .venv/bin/pytest -q | tail -1)`
Expected: `Test Files  17 passed (17)`, `Tests  122 passed (122)`, `7 passed`, `OK: 167 pages`, `1083 passed`.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add deploy/Caddyfile deploy/test-site-routes.sh deploy/check-indexing.sh
git commit -m "feat(deploy): pages without .html, one address per page, a 404 page per language; their checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

After this task the owner deploys (`deploy/deploy.sh`, spec §9; `deploy/check-indexing.sh` then confirms the new Caddyfile is live) and makes the first real reading. Before Turnstile can ever be needed, the owner creates the widget in Cloudflare with the mode **Invisible** (the site renders it into a corner slot above the room and shows no challenge UI); then Fable 5.2 walks paths П1–П5 on the closed site by the stage 3 checklist (phone and desktop, EN and ES, errors, reduced motion, keyboard).

---

## Spec coverage

| Spec | Where |
|---|---|
| §3 pages, menu, footer, language switch, phone and desktop | Tasks 2–3 (routes, pairs), 8 (layout, menu, footer, 404), 9 (tools, cards), 10 (daily), 11 (addresses, redirects and 404 on the server) |
| §3 yes/no — one card, no toggle (owner, 19.11.2026) | Task 7 (`panelConfig('yes_no')`), Task 9 (`ToolView`) |
| §4 night room: layer, ×/Escape/Back, focus trap and return, 960 px stage with cards left and text right, states, layout of 2b–2e / 5b / 13d, reduced motion | Task 6 (`nightRoom.ts`), Task 7 (`focus.ts`), Task 8 (CSS), Task 9 (`NightRoom.tsx`, `ReadingIsland.tsx`) |
| §4 API: create → stream via fetch → restore via GET; `/retry` only after a fallback; follow-ups: free, then `402 confirm` warning → `use_reading: true`, `402 plus`, `used_reading`, a broken follow-up read back, crisis clears text | Tasks 5–6 (`sse.ts`, `api.ts`, `followups.ts`, `readingFlow.ts`, `nightRoom.ts`) |
| §4 crisis (call / SMS / help link, question cleared), 429 / 403 / 502–504 with help link, Turnstile on demand, Plus card (11a) with the waitlist and no price, textContent only | Tasks 5–7, 9 (`CrisisView`, `HelpLine`, `PlusCard`), guard test in Task 8 |
| §5 Card of the Day; one base card for everyone on 503 / 502 / 504 | Tasks 5, 7, 10 |
| §6 events endpoint, migration 004, whitelist, no person data, per-address and global limits, funnel SQL from the launch day; the seven 4.4a events, one card on the ES home as `one_card` | Task 1; Tasks 7, 9, 10 (`analytics.ts`, `toolFor`, islands) |
| §7 Astro + Preact islands, tokens, fonts, 44 px, focus ring in the surface's text colour, real controls, dictionaries with drafts, srcset, logic in tested modules | Tasks 2–10 |
| §8 Vitest for states, SSE, sections, follow-ups, errors, crisis, dictionaries, routes and pairs; API tests; build of every page | Tasks 1, 3–8, 10 (`check_dist.py`), 11 (`test-site-routes.sh`) |
| §11 restore list (hidden until 4.4b and stages 6–7) | nothing is drawn for those items in 4.4a; the list is in the spec |

## Owner decisions applied (19.11.2026, after the Fable review)

- **Yes or No is one card in 4.4a**, without the "1 / 3 cards" toggle and its hint line: the API draws one card for `kind: "yes_no"` (`api/app/draw.py`). "Yes/no with three cards" is its own small sub-stage before launch 14.12.2026 (API, reader prompt, paid eval run with the owner's "yes", site) — spec §3.
- **Prototype fidelity:** with the answer the question is small at top left and the headline is the large title (2e, 5b); the desktop room has cards left and text right (13d); the Plus card is a day block in place of the night panel (11a, with "Not now" and "Open your free Card of the Day").
- **Plus without a price** on the closed stage; the owner names the price before launch (spec §4). "Your reader remembers your past readings" stays out (decision of 14.11.2026, item 2).
- **Card of the Day on 503 / 502 / 504:** the personal card comes from the HttpOnly guest cookie, which the page cannot read; the site shows one card for everyone that local day, upright, from the card base, with a note (`dailyFallbackNote`).
- **Hidden links** ("Save to diary", "Remind me tomorrow", the Card Meanings menu item, "All 78 card meanings", the yes/no reference, About, Privacy, "Your diary") and the rewritten lines ("Free · no sign-up", step 3 of "How a reading works", the Plus lead without the diary sentence): accepted; the restore list is spec §11.
- **Fonts** stay on Google Fonts in 4.4a; self-hosting is a stage 7 item (spec §11).
