# Stage 6: Page Templates for the Stage 5 Texts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the reviewed stage 5 texts (78 × 2 card pages, tool, hub and service pages) on the site with full SEO
heads, JSON-LD, breadcrumbs, a sitemap, hidden service pages and checked internal links — in five parts, each one
deployable to the stage on the owner's word.

**Architecture:** `tools/site/sync_site_data.py` copies the texts and a `facts.json` (limits from `api/app/config.py`,
yes/no counts from the deck) into `site/src/data/`; pure TypeScript modules in `site/src/lib/` (facts, text and card
page loaders, routes, SEO, breadcrumbs, JSON-LD, card page assembly, card lists, sitemap) do all the logic and are
tested with vitest; Astro views only compose them. Python checkers on the built `site/dist` (`check_dist.py`,
new `check_links.py`) and `deploy/test-site-routes.sh` prove the result.

**Tech Stack:** Astro 5 (static, `build.format: 'file'`), Preact islands, vitest 5 + happy-dom, Python 3 stdlib
(pytest from `api/.venv`), Caddy 2.8.4 (route test only).

**Spec:** `docs/superpowers/specs/2026-11-23-stage6-page-templates-design.md` (owner decisions 34–36).

## Global Constraints

Every task's requirements include this section.

- **Working directory:** every command runs from the repository root `~/arcana-diary` (branch `stage6-templates`).
- **No new packages:** no new npm or pip packages, nothing added to `site/package.json`; the sitemap, the HTML checks
  and the link check are our own code (Python: stdlib only).
- **Node only in Docker `node:22`, never `npm install`.** The exact commands:
  - all site tests: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run'`
  - one test file: the same command with `'npx vitest run src/lib/<file>.test.ts'`
  - types: the same command with `'npx astro check'` — expected `0 errors`
  - build: `deploy/build-site.sh` (runs `npm ci` from the lock file inside `node:22`, then `astro build`; from Task 7
    it also runs `tools/site/sync_site_data.py --check` before and `tools/site/check_dist.py` after the build)
- **Python tests:** `api/.venv/bin/pytest -q tools/site` (Task 13 also `api/.venv/bin/pytest -q tools/research`).
- **Generated data:** files under `site/src/data/` are written only by `python3 tools/site/sync_site_data.py`, never
  by hand; after a sync, `python3 tools/site/sync_site_data.py --check` exits 0.
- **Design tokens only:** colours, fonts, sizes, spacing, radii and motion come only from `site/src/styles/tokens.css`
  through `var(--…)`; no hex, `rgb()`, `hsl()` or `color()` in sources (`src/lib/guards.test.ts` enforces it).
- **Touch and focus:** every standalone link, button, chip and `<summary>` is at least 44 px high; links inside running
  text keep the line height (WCAG 2.5.8 inline exception). Focus keeps the existing `:focus-visible` ring (2 px,
  offset 2 px); never `outline: none` on a control. Real `<a>`, `<button>`, `<details>/<summary>`, `<table>` with
  `<th scope>`; one `<h1>` per page.
- **Copy:** every visible word comes from `content/` (through `site/src/data/`) or from the dictionaries
  `site/src/i18n/{en,es}.ts`; new dictionary keys exactly as the tasks list them, the same keys in both files.
  `content/` is owner-reviewed: tasks do not edit it.
- **No element or astrology lines:** the prototypes' suit themes ("Fire: energy…", "Water: feelings…") and
  "Siguiente paso" are not carried over (owner decision 10); prototypes give layout and style only.
- **Waite quotes:** `<blockquote lang="en">` with its citation on EN and ES pages; the ES translation is labelled
  "Traducción nuestra" (from `template-strings.json`).
- **Islands:** `ReadingIsland` logic does not change; the only island edits are the `three_cards` panel config
  (Task 11) and an optional privacy link prop (Task 15).
- **API:** unchanged; `api/app/config.py` is only read as text by the sync script.
- **Secrets and production:** never open, print, copy or edit `deploy/.env` or `deploy/caddy/stage_auth.caddy*`;
  never start, stop, restart or recreate the production containers (no `docker compose up/restart/down`, no
  `deploy/deploy.sh`). `deploy/test-site-routes.sh` runs its own temporary containers and is allowed.
- **Deploy:** only on the owner's word. Each part ends with a *Deploy checkpoint* — a stop for the owner, not a
  command to run.
- **Commits:** one commit per task (more if a task says so) on `stage6-templates`; every message ends with a blank
  line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No push, no merge without the owner.

## Decisions taken in this plan (spec gaps)

These resolve gaps or contradictions found while reading the spec against the code; the report to the owner lists
them too.

1. **Order inside the parts.** So that every part deploys without broken links, Part 1 already builds the six new
   addresses (`/cards`, `/cards/major-arcana`, `/yes-no/cards`, `/es/cartas`, `/es/cartas/arcanos-mayores`,
   `/es/tiradas/3-cartas`) as plain text pages, and the menu item "Card Meanings" arrives with them. The ten service
   pages, their `hreflang.csv` rows and the footer links come in Part 4, together with the pages themselves.
2. **`hreflang.csv` rows need page-map rows.** `tools/research/validate_structure.py` refuses a `hreflang.csv` row
   without a row in `docs/research/stage1/page-map-{en,es}.csv`, so Task 13 adds five rows per language (new
   `page_type` `service`), regenerates `hreflang.csv` with `tools/research/build_hreflang.py` and raises
   `LAUNCH_CLUSTERS` from 84 to 89.
3. **hreflang only for mutual pairs.** `pairs.json` holds the language-switch target, which is not always mutual
   (`/one-card` → `/es`, `/yes-no/cards` → `/es/si-o-no`, `/es/tiradas/3-cartas` → `/`). A page gets `en`, `es` and
   `x-default` alternates only when its pair points back at it; otherwise it gets only its own `hreflang`.
4. **`reviewedBy` is a WebPage property.** schema.org has no `reviewedBy` on `Article`, so the card page emits an
   `Article` (author and publisher: the Organization, `editor`: the Person) whose `mainEntityOfPage` is a `WebPage`
   carrying `reviewedBy` and `lastReviewed`.
5. **JSON-LD needs `set:html`.** `src/lib/guards.test.ts` forbids `set:html`; Astro cannot print JSON-LD without it.
   One component, `src/components/JsonLd.astro`, may use exactly `set:html={ldScript(data)}`, and `ldScript` escapes
   `<`, `>`, `&`, U+2028 and U+2029.
6. **`cta.button` is unused.** The card page's draw panel is the existing `ReadingIsland`, whose own button says
   "Draw a card for your question" / "Saca una carta para tu pregunta" — exactly the anchor of links L-EN-07 and
   L-ES-05. The heading and text of the CTA come from `template-strings.json`; `cta.button` stays unrendered.
7. **`facts.also_called` has no template string.** The names are appended to the facts line: "Arcanos mayores ·
   carta VI · Los Amantes".
8. **Links drawn by islands are not in `site/dist`.** Rows to `@drawn` and `@diary` (L-EN-01, -02, -03, -15, -16,
   -31; L-ES-01, -02, -03, -04, -15, -16, -23) appear only after a reading, so `check_links.py` lists them instead of
   checking them. Several differ from today's islands (three-card readings show names only; the Card of the Day shows
   "{name} — full meaning", not "Today's card: {name}", and has no "Save to diary"; no "#amor" / "Por qué … dice …"
   links) — an owner decision, outside this plan.
9. **Default share image.** No 1200 × 630 share picture exists; pages without their own card use
   `/cards/the-moon.webp` until one is made.
10. **The Spanish home has no `#una-carta` text block;** the island already carries `id="una-carta"`. The section
    rows of the page maps that are not linked at launch (`/#ai-reader`, `/yes-no#one-or-three`, `/love#situation`,
    `/cards#download`) get no anchors in this stage.
11. **Hub lists go under the capsule** (spec §5 and prototypes Hub/DeskHub). Three EN sentences say "the list below"
    (`content/pages/en/cards.json` blocks `card-pages` and FAQ, `major-arcana.json` block `names-and-numbers`); they
    are shown to the owner at the Part 3 checkpoint for a wording decision — the plan does not edit content.
12. **The old home "How a reading works" steps** are removed: the stage 5 block "How the reading works" replaces them.
    Dictionary keys that fall out of use (`homeLead`, `howTitle`, `howStep1–3`, `cardTitle`, `uprightTitle`, …) stay,
    because `i18n.test.ts` pins several of them.
13. **The yes/no lists** of `/yes-no/cards` sit inside the blocks that describe them (`lean-yes`, `lean-no`,
    `not-clear-yet`), after the capsule and the rule block — the spec's order "capsule, rule, lists, blocks, FAQ".
14. **Launch guard.** `deploy/build-site.sh` passes `--launched` to `check_dist.py` when `deploy/.env` has the line
    `LAUNCHED=true` (checked with `grep -qx`, which prints nothing); with it, a hidden service page fails the build.

## File map

Created:

| File | Responsibility |
|---|---|
| `site/src/lib/facts.ts` | `FACTS` from `facts.json`; fill and list missing `{placeholders}` |
| `site/src/lib/textPages.ts` | stage 5 tool/hub/service texts: types, lookup by address, filling, hidden service pages |
| `site/src/lib/cardPages.ts` | card page texts (schema 2) and template strings: types, lookup |
| `site/src/lib/seo.ts` | absolute URLs, canonical, hreflang alternates, default image |
| `site/src/lib/breadcrumbs.ts` | breadcrumb trails of every page kind |
| `site/src/lib/jsonld.ts` | BreadcrumbList, FAQPage, WebPage, CollectionPage, card Article; safe script text |
| `site/src/lib/sitemap.ts` | indexable addresses and the `sitemap.xml` text |
| `site/src/lib/cardPage.ts` | what the card template adds: facts line, captions, yes/no lines, pairs, mention links, About lines |
| `site/src/lib/cardLists.ts` | card lists of the hubs: majors, suits, verdicts, first keyword |
| `site/src/components/{JsonLd,Breadcrumbs,TextBlocks,Faq,Segments}.astro` | small render pieces |
| `site/src/views/{TextPageView,CardPageView,HubView,MajorView,YesNoCardsView}.astro` | page templates |
| `site/src/pages/sitemap.xml.ts` | the sitemap endpoint |
| `site/src/pages/cards/index.astro`, `cards/major-arcana.astro`, `yes-no/cards.astro`, `es/cartas/index.astro`, `es/cartas/arcanos-mayores.astro`, `es/tiradas/3-cartas.astro` | new addresses (Task 6) |
| `site/src/pages/{about,contact,how-readings-work,privacy,terms}.astro`, `site/src/pages/es/{sobre-nosotros,contacto,como-funcionan-las-lecturas,privacidad,terminos}.astro` | service pages (Task 14) |
| `site/src/data/facts.json`, `site/src/data/pages/**`, `site/src/data/cardpages/**` | generated by the sync |
| `tools/site/check_links.py`, `tools/site/test_check_links.py` | link matrix check on `site/dist` |
| `docs/research/stage6/semantic-audit.md` | audit findings (Task 18) |

Modified: `tools/site/sync_site_data.py` (+ test), `tools/site/check_dist.py` (+ test), `deploy/build-site.sh`,
`deploy/test-site-routes.sh`, `site/src/lib/routes.ts` (+ test), `site/src/lib/deck.ts`, `site/src/lib/panel.ts`
(+ test), `site/src/lib/types.ts`, `site/src/lib/guards.test.ts`, `site/src/layouts/Base.astro`,
`site/src/components/{Header,Footer,CardFigure}.astro`, `site/src/views/{HomeView,ToolView,DailyView,AccountView}.astro`,
`site/src/pages/{cards,es/cartas}/[slug].astro`, `site/src/i18n/{en,es}.ts` (+ test),
`site/src/islands/{ReadingIsland,AccountIsland}.tsx`, `site/src/components/ui/{useSaveToDiary,SaveSheet}.tsx`,
`site/src/styles/global.css`, `site/public/robots.txt`, `docs/research/stage1/page-map-{en,es}.csv`,
`docs/research/stage2/hreflang.csv`, `docs/research/stage2/99-changelog.md`, `tools/research/validate_page_map.py`,
`tools/research/structure_hreflang.py`. Deleted: `site/src/views/CardView.astro` (Task 9).

New dictionary keys by task (count in `i18n.test.ts`): Task 3 → 232, Task 8 → 239, Task 11 → 240, Task 12 → 242,
Task 14 → 247, Task 15 → 248, Task 16 → 255. They are new interface copy: the owner reads them at the checkpoints.

---

# Part 1 — Foundation (all pages)

Ends deployable: every existing page has its SEO head and JSON-LD; the six new addresses exist as text pages; the
menu has "Card Meanings"; `sitemap.xml` and `robots.txt` are served; the build checks itself.

### Task 1: Site data — facts, texts, card pages, verdicts, all launch pairs

**Files:**
- Modify: `tools/site/sync_site_data.py`
- Test: `tools/site/test_sync_site_data.py`
- Generated (by running the script): `site/src/data/facts.json`, `site/src/data/pages/{en,es}/*.json` (25 files),
  `site/src/data/cardpages/{en,es}/*.json` (156 files), `site/src/data/cardpages/template-strings.json`,
  `site/src/data/deck.json`, `site/src/data/meanings.{en,es}.json`, `site/src/data/pairs.json`

**Interfaces:**
- Consumes: `content/pages/{en,es}/*.json`, `content/cards/pages/{en,es}/*.json`,
  `content/cards/pages/template-strings.json`, `content/cards/deck.json` (`yes_no`), `content/cards/meanings.*.json`
  (`yes_no_why`), `api/app/config.py` constants `DAILY_LIMIT`, `USER_DAILY_LIMIT`, `FOLLOWUP_LIMIT`,
  `FREE_DIARY_VISIBLE`, `docs/research/stage2/hreflang.csv`.
- Produces (later tasks rely on these shapes):
  - `site/src/data/facts.json`: `{"guest_limit": int, "user_limit": int, "followups": int, "diary_free": int,
    "yes_count": int, "no_count": int, "unclear_count": int, "editor_name": "Adrian Solenne"}`
  - `site/src/data/pages/<lang>/<name>.json`: the stage 5 file as is (`page_id`, `lang`, `url`, `title`,
    `description`, `h1`, `lead`, `capsule`, `blocks[{id, heading, paragraphs}]`, `faq[{q, a}]`, `intents`)
  - `site/src/data/cardpages/<lang>/<card_id>.json`: the schema 2 file without `citations`
  - `site/src/data/cardpages/template-strings.json`: a copy
  - `deck.json` entries gain `"yes_no": "yes" | "no" | "unclear"`; `meanings.<lang>.json` entries gain `"yes_no_why"`
  - `pairs.json`: every `запуск` row of `hreflang.csv` (171 entries)
  - Python: `config_constant(text: str, name: str) -> int`, `facts() -> dict`, `text_pages() -> dict[Path, str]`,
    `card_pages() -> dict[Path, str]`, `API_CONFIG: Path`

- [ ] **Step 1: Write the failing tests**

Replace `tools/site/test_sync_site_data.py` with:

```python
import json

import pytest

from check_dist import dist_file, expected_pages
from sync_site_data import (API_CONFIG, ROOT, SITE, build, card_pages, config_constant, deck, facts, meanings, pairs,
                            stale, text_pages)


def test_committed_site_data_matches_its_sources():
    assert stale(build()) == []


def test_deck_has_78_cards_in_deck_order_with_both_names():
    cards = deck()
    assert len(cards) == 78
    assert cards[0]["card_id"] == "major-00-fool" and cards[0]["name_es"] == "El Loco"
    assert cards[18]["slug_en"] == "the-moon" and cards[18]["slug_es"] == "la-luna" and cards[18]["numeral"] == "XVIII"
    assert all(c["name_en"] and c["name_es"] for c in cards)


def test_deck_carries_the_yes_no_verdict_of_the_card_base():
    cards = deck()
    assert {c["yes_no"] for c in cards} == {"yes", "no", "unclear"}
    assert cards[18]["yes_no"] == "unclear"  # The Moon
    assert next(c for c in cards if c["card_id"] == "swords-03-three")["yes_no"] == "no"


def test_every_card_has_its_three_image_sizes():
    for card in deck():
        for suffix in ("", "@350", "@160"):
            assert (SITE / "public/cards" / f"{card['image']}{suffix}.webp").exists(), card["image"]


def test_meanings_cover_the_deck_in_both_languages():
    ids = {c["card_id"] for c in deck()}
    for lang in ("en", "es"):
        records = meanings(lang)
        assert {m["card_id"] for m in records} == ids
        assert all(m["upright"] and m["reversed"] and m["keywords"] and m["yes_no_why"] for m in records)


def test_config_constant_reads_a_number_and_refuses_a_missing_name():
    text = "DAILY_LIMIT = 2            # a guest\nUSER_DAILY_LIMIT = 3\n"
    assert config_constant(text, "DAILY_LIMIT") == 2
    assert config_constant(text, "USER_DAILY_LIMIT") == 3
    with pytest.raises(ValueError, match="FOLLOWUP_LIMIT"):
        config_constant(text, "FOLLOWUP_LIMIT")


def test_facts_come_from_the_api_constants_and_the_deck():
    f = facts()
    text = API_CONFIG.read_text(encoding="utf-8")
    assert f["guest_limit"] == config_constant(text, "DAILY_LIMIT")
    assert f["user_limit"] == config_constant(text, "USER_DAILY_LIMIT")
    assert f["followups"] == config_constant(text, "FOLLOWUP_LIMIT")
    assert f["diary_free"] == config_constant(text, "FREE_DIARY_VISIBLE")
    assert f["yes_count"] + f["no_count"] + f["unclear_count"] == 78
    assert f["editor_name"] == "Adrian Solenne"
    # spec §2: operator placeholders ({operator_name}, …) stay out until the operator's data exists
    assert set(f) == {"guest_limit", "user_limit", "followups", "diary_free", "yes_count", "no_count", "unclear_count",
                      "editor_name"}


def test_text_pages_are_copied_for_both_languages():
    files = text_pages()
    assert len(files) == 25
    home = json.loads(files[SITE / "src/data/pages/en/home.json"])
    assert home["url"] == "/" and home["h1"] == "Free tarot reading: ask the cards"
    three = json.loads(files[SITE / "src/data/pages/es/tres-cartas.json"])
    assert three["url"] == "/es/tiradas/3-cartas"


def test_card_pages_are_copied_without_the_reviewers_excerpts():
    files = card_pages()
    assert len(files) == 78 * 2 + 1
    moon = json.loads(files[SITE / "src/data/cardpages/es/major-18-moon.json"])
    assert moon["name_forms"]["name"] == "La Luna" and "citations" not in moon
    strings = json.loads(files[SITE / "src/data/cardpages/template-strings.json"])
    assert strings["es"]["waite"]["translation_label"] == "Traducción nuestra"


def test_pairs_are_every_launch_page_of_hreflang_csv():
    table = pairs()
    assert len(table) == 15 + 78 * 2
    assert table["/"] == "/es" and table["/es"] == "/"
    assert table["/one-card"] == "/es"
    assert table["/yes-no"] == "/es/si-o-no" and table["/es/si-o-no"] == "/yes-no"
    assert table["/love"] == "/es/amor" and table["/daily"] == "/es/carta-del-dia"
    assert table["/cards"] == "/es/cartas" and table["/es/cartas"] == "/cards"
    assert table["/cards/major-arcana"] == "/es/cartas/arcanos-mayores"
    assert table["/yes-no/cards"] == "/es/si-o-no" and table["/es/tiradas/3-cartas"] == "/"
    for card in deck():
        en, es = f"/cards/{card['slug_en']}", f"/es/cartas/{card['slug_es']}"
        assert table[en] == es and table[es] == en


def test_tokens_css_is_the_design_copy():
    assert (SITE / "src/styles/tokens.css").read_text() == (ROOT / "docs/design/tokens.css").read_text()


def test_the_build_check_expects_177_pages_with_their_files():
    pages = expected_pages()
    assert len(pages) == 177  # stage 6 part 1: + /cards, /cards/major-arcana, /yes-no/cards and three ES pages
    assert {"/", "/es", "/404", "/es/404", "/one-card", "/es/cartas/la-luna", "/diary", "/es/cuenta", "/cards",
            "/es/tiradas/3-cartas"} <= set(pages)
    assert [dist_file(p) for p in ("/", "/es", "/es/404", "/cards/the-moon", "/cards")] == [
        "index.html", "es.html", "es/404.html", "cards/the-moon.html", "cards.html"]
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `api/.venv/bin/pytest -q tools/site/test_sync_site_data.py`
Expected: FAIL — `ImportError: cannot import name 'API_CONFIG' from 'sync_site_data'`.

- [ ] **Step 3: Implement**

In `tools/site/sync_site_data.py`:

Replace the module docstring and the constants block (from the first line down to and including the
`PAGE_ENTITIES = …` line) with:

```python
"""Data the site build needs from outside site/ (stage 4.4a, stage 6 §2). The site is built in a node:22 container
that sees only site/ (deploy/build-site.sh), so these files are generated into site/ and committed:

  site/src/styles/tokens.css        — a copy of docs/design/tokens.css (made by tools/design/tokens.py)
  site/src/data/deck.json           — 78 cards in deck order: id, numeral, arcana, suit, yes/no verdict, image,
                                      slugs, EN/ES names
  site/src/data/meanings.en.json    — short meanings (keywords, upright, reversed, yes/no reason)
  site/src/data/meanings.es.json
  site/src/data/pairs.json          — language pairs of every launch page (url → switch_to) from hreflang.csv
  site/src/data/facts.json          — the numbers and names the texts leave as {placeholders} (owner decision 36):
                                      limits from api/app/config.py (read as text, never imported), yes/no counts
                                      from the deck, the editor's name
  site/src/data/pages/<lang>/*.json — the stage 5 tool, hub and service texts (content/pages)
  site/src/data/cardpages/…         — the stage 5 card pages without `citations` (the reviewer's excerpts) and
                                      template-strings.json

Run from the repository root:
  python3 tools/site/sync_site_data.py          — write the files
  python3 tools/site/sync_site_data.py --check  — exit 1 if a file is missing or differs from its sources
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS = ROOT / "content/cards"
CARD_PAGES = CARDS / "pages"
PAGES = ROOT / "content/pages"
API_CONFIG = ROOT / "api/app/config.py"
HREFLANG = ROOT / "docs/research/stage2/hreflang.csv"
TOKENS_CSS = ROOT / "docs/design/tokens.css"
SITE = ROOT / "site"
LAUNCH = "запуск"
# placeholder in the texts → constant of api/app/config.py (spec stage 6 §2)
LIMITS = {"guest_limit": "DAILY_LIMIT", "user_limit": "USER_DAILY_LIMIT", "followups": "FOLLOWUP_LIMIT",
          "diary_free": "FREE_DIARY_VISIBLE"}
EDITOR_NAME = "Adrian Solenne"  # spec stage 6 §2: the editor who reads and signs the card pages
```

In `deck()`, add the verdict after `"suit": c["suit"],`:

```python
    return [{"card_id": c["card_id"], "numeral": c["numeral"], "arcana": c["arcana"], "suit": c["suit"],
             "yes_no": c["yes_no"], "image": c["image"], "slug_en": c["slug_en"], "slug_es": c["slug_es"],
             "name_en": names["en"][c["card_id"]], "name_es": names["es"][c["card_id"]]} for c in cards]
```

Replace `meanings()` and `pairs()` with:

```python
def meanings(lang: str) -> list[dict]:
    return [{"card_id": m["card_id"], "keywords": m["keywords"], "upright": m["upright"], "reversed": m["reversed"],
             "yes_no_why": m["yes_no_why"]} for m in _load(f"meanings.{lang}.json")]


def pairs() -> dict[str, str]:
    with open(HREFLANG, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["url"]: r["switch_to"] for r in rows if r["wave"] == LAUNCH}


def config_constant(text: str, name: str) -> int:
    """`NAME = 2  # comment` at the start of a line of api/app/config.py."""
    match = re.search(rf"^{name}\s*=\s*(\d+)\b", text, re.M)
    if not match:
        raise ValueError(f"{name} not found in api/app/config.py")
    return int(match.group(1))


def facts() -> dict:
    text = API_CONFIG.read_text(encoding="utf-8")
    out: dict = {key: config_constant(text, name) for key, name in LIMITS.items()}
    verdicts = [c["yes_no"] for c in _load("deck.json")]
    out.update(yes_count=verdicts.count("yes"), no_count=verdicts.count("no"), unclear_count=verdicts.count("unclear"))
    out["editor_name"] = EDITOR_NAME
    return out


def text_pages() -> dict[Path, str]:
    return {SITE / "src/data/pages" / f.parent.name / f.name: _json(json.loads(f.read_text(encoding="utf-8")))
            for f in sorted(PAGES.glob("*/*.json"))}


def card_pages() -> dict[Path, str]:
    files: dict[Path, str] = {}
    for f in sorted(CARD_PAGES.glob("*/*.json")):
        page = json.loads(f.read_text(encoding="utf-8"))
        page.pop("citations", None)  # the reviewer's excerpts (rules §1), never shown on the page
        files[SITE / "src/data/cardpages" / f.parent.name / f.name] = _json(page)
    strings = json.loads((CARD_PAGES / "template-strings.json").read_text(encoding="utf-8"))
    files[SITE / "src/data/cardpages/template-strings.json"] = _json(strings)
    return files
```

Replace `build()` with:

```python
def build() -> dict[Path, str]:
    return {
        SITE / "src/styles/tokens.css": TOKENS_CSS.read_text(encoding="utf-8"),
        SITE / "src/data/deck.json": _json(deck()),
        SITE / "src/data/meanings.en.json": _json(meanings("en")),
        SITE / "src/data/meanings.es.json": _json(meanings("es")),
        SITE / "src/data/pairs.json": _json(pairs()),
        SITE / "src/data/facts.json": _json(facts()),
        **text_pages(),
        **card_pages(),
    }
```

- [ ] **Step 4: Write the data and run the tests**

Run: `python3 tools/site/sync_site_data.py && python3 tools/site/sync_site_data.py --check && api/.venv/bin/pytest -q tools/site`
Expected: `wrote …` lines (188 files), the check prints nothing, pytest: all passed. (`tools/site/check_dist.py` on an
old `site/dist` would now miss six pages — that is expected until Task 6.)

- [ ] **Step 5: Run the site tests (the deck and meanings changed shape)**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run'`
Expected: all test files pass.

- [ ] **Step 6: Commit**

```bash
git add tools/site/sync_site_data.py tools/site/test_sync_site_data.py site/src/data
git commit -m "site data (stage 6): facts from the API constants, stage 5 texts and card pages, verdicts, all launch pairs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Facts, text pages and card pages in the site

**Files:**
- Create: `site/src/lib/facts.ts`, `site/src/lib/textPages.ts`, `site/src/lib/cardPages.ts`
- Test: `site/src/lib/facts.test.ts`, `site/src/lib/textPages.test.ts`, `site/src/lib/cardPages.test.ts`

**Interfaces:**
- Consumes: Task 1 data; `fill`, `placeholders` from `site/src/i18n/index.ts`; `DeckCard`, `DECK`, `cardById` from
  `site/src/lib/deck.ts`.
- Produces:
  - `facts.ts`: `type Facts = Readonly<Record<string, string | number>>`, `FACTS: Facts`,
    `fillFacts(text: string, facts?: Facts): string`, `missingFacts(texts: readonly string[], facts?: Facts): string[]`
  - `textPages.ts`: `interface TextBlock { id: string; heading: string; paragraphs: string[] }`,
    `interface FaqItem { q: string; a: string }`, `interface TextPage { page_id; lang: Lang; url; title; description;
    h1; lead; capsule: string | null; blocks: TextBlock[]; faq: FaqItem[] }`, `TEXT_PAGES: readonly TextPage[]`,
    `SERVICE_PAGE_IDS: ReadonlySet<string>`, `textPage(path: string): TextPage`, `pageTexts(page): string[]`,
    `isHidden(page, facts?): boolean`, `filledPage(page, facts?): TextPage`, `hiddenPaths(facts?): Set<string>`
  - `cardPages.ts`: `type CardBlockId`, `CARD_BLOCK_IDS`, `interface CardPair`, `interface CardBlock`,
    `interface CardSource`, `interface CardPageData`, `interface TemplateStrings`,
    `TEMPLATE_STRINGS: Readonly<Record<Lang, TemplateStrings>>`, `CARD_PAGES: readonly CardPageData[]`,
    `cardPage(card: DeckCard, lang: Lang): CardPageData`

- [ ] **Step 1: Write the failing tests**

`site/src/lib/facts.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { FACTS, fillFacts, missingFacts } from './facts';

describe('facts (spec stage 6 §2, owner decision 36)', () => {
  it('hold the limits, the yes/no counts and the editor, nothing about the operator yet', () => {
    expect(Object.keys(FACTS).sort()).toEqual(['diary_free', 'editor_name', 'followups', 'guest_limit', 'no_count',
      'unclear_count', 'user_limit', 'yes_count']);
    expect(Number(FACTS.yes_count) + Number(FACTS.no_count) + Number(FACTS.unclear_count)).toBe(78);
    expect(FACTS.editor_name).toBe('Adrian Solenne');
  });

  it('fill the placeholders they know and leave the others', () => {
    expect(fillFacts('{guest_limit} a day, {operator_name}', { guest_limit: 2 })).toBe('2 a day, {operator_name}');
    expect(fillFacts(`{user_limit}`)).toBe(String(FACTS.user_limit));
  });

  it('list the placeholders without a value, once each, sorted', () => {
    expect(missingFacts(['{b} {guest_limit}', '{a} {b}'], { guest_limit: 2 })).toEqual(['a', 'b']);
    expect(missingFacts(['no placeholder'])).toEqual([]);
  });
});
```

`site/src/lib/textPages.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { FACTS } from './facts';
import { SERVICE_PAGE_IDS, TEXT_PAGES, filledPage, hiddenPaths, isHidden, pageTexts, textPage } from './textPages';

describe('stage 5 text pages', () => {
  it('are the 25 files of content/pages, one per address', () => {
    expect(TEXT_PAGES).toHaveLength(25);
    expect(new Set(TEXT_PAGES.map((p) => p.url)).size).toBe(25);
    expect(textPage('/cards').h1).toBe('Tarot card meanings: the whole deck, card by card');
    expect(textPage('/es/tiradas/3-cartas').lang).toBe('es');
    expect(() => textPage('/nope')).toThrow('/nope');
  });

  it('fill every placeholder of a page with the facts', () => {
    const home = filledPage(textPage('/'));
    expect(home.faq[0].a).toContain(`draw ${FACTS.guest_limit} readings a day`);
    expect(pageTexts(home).join(' ')).not.toMatch(/\{\w+\}/);
  });

  it('hide a service page while an operator placeholder has no value (owner decision 35)', () => {
    expect(isHidden(textPage('/about'))).toBe(true);
    expect(isHidden(textPage('/es/privacidad'))).toBe(true);
    expect(isHidden(textPage('/how-readings-work'))).toBe(false);
    expect(isHidden(textPage('/'))).toBe(false);
    expect(isHidden(textPage('/about'), { ...FACTS, operator_name: 'X', operator_address: 'Y', contact_email: 'Z' }))
      .toBe(false);
  });

  it('refuse a page that is not a service page and has a placeholder without a value', () => {
    const page = { ...textPage('/'), capsule: 'Up to {nope} cards' };
    expect(() => isHidden(page)).toThrow('{nope}');
  });

  it('know the ten service pages and which of them are hidden now', () => {
    expect(SERVICE_PAGE_IDS.size).toBe(10);
    expect([...hiddenPaths()].sort()).toEqual(['/about', '/contact', '/es/contacto', '/es/privacidad',
      '/es/sobre-nosotros', '/es/terminos', '/privacy', '/terms']);
  });
});
```

`site/src/lib/cardPages.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { CARD_BLOCK_IDS, CARD_PAGES, TEMPLATE_STRINGS, cardPage } from './cardPages';
import { DECK, cardById } from './deck';

describe('card pages (schema 2)', () => {
  it('cover the deck in both languages with the 12 blocks in order', () => {
    expect(CARD_PAGES).toHaveLength(156);
    for (const lang of ['en', 'es'] as const) {
      for (const card of DECK) expect(cardPage(card, lang).blocks.map((b) => b.id)).toEqual(CARD_BLOCK_IDS);
    }
  });

  it('find a page by card and language', () => {
    const moon = cardById('major-18-moon')!;
    expect(cardPage(moon, 'en').h1).toBe('The Moon Tarot Card Meaning');
    expect(cardPage(moon, 'es').name_forms.de).toBe('de La Luna');
    expect(cardPage(moon, 'es').waite.translation).toMatch(/^Enemigos ocultos/);
  });

  it('carry the template strings of both languages with the same keys', () => {
    expect(TEMPLATE_STRINGS.en.waite.translation_label).toBeNull();
    expect(TEMPLATE_STRINGS.es.waite.translation_label).toBe('Traducción nuestra');
    expect(Object.keys(TEMPLATE_STRINGS.es).sort()).toEqual(Object.keys(TEMPLATE_STRINGS.en).sort());
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/facts.test.ts src/lib/textPages.test.ts src/lib/cardPages.test.ts'`
Expected: FAIL — `Failed to resolve import "./facts"` (and the same for the other two).

- [ ] **Step 3: Implement**

`site/src/lib/facts.ts`:

```ts
// The numbers and names the stage 5 texts leave as {placeholders} (spec stage 6 §2, owner decision 36): the limits
// from api/app/config.py, the yes/no counts from the deck and the editor's name, written to src/data/facts.json by
// tools/site/sync_site_data.py. The operator's data is not there yet: pages that need it stay hidden.
import factsData from '../data/facts.json';
import { fill, placeholders } from '../i18n';

export type Facts = Readonly<Record<string, string | number>>;

export const FACTS: Facts = factsData;

export function fillFacts(text: string, facts: Facts = FACTS): string {
  return fill(text, facts);
}

/** The placeholders of these texts that have no value in the facts, once each, sorted. */
export function missingFacts(texts: readonly string[], facts: Facts = FACTS): string[] {
  return [...new Set(texts.flatMap((text) => placeholders(text)))].filter((key) => !(key in facts)).sort();
}
```

`site/src/lib/textPages.ts`:

```ts
// The stage 5 texts of the tool, hub and service pages (content/pages, copied to src/data/pages by
// tools/site/sync_site_data.py). A service page with a placeholder that has no value in the facts is built but
// hidden — noindex, outside the menu, the footer and the sitemap (owner decision 35); any other page with such a
// placeholder stops the build.
import { FACTS, fillFacts, missingFacts, type Facts } from './facts';
import type { Lang } from './types';

export interface TextBlock {
  id: string;
  heading: string;
  paragraphs: string[];
}

export interface FaqItem {
  q: string;
  a: string;
}

export interface TextPage {
  page_id: string;
  lang: Lang;
  url: string;
  title: string;
  description: string;
  h1: string;
  lead: string;
  capsule: string | null;
  blocks: TextBlock[];
  faq: FaqItem[];
}

const FILES = import.meta.glob<TextPage>('../data/pages/*/*.json', { eager: true, import: 'default' });

export const TEXT_PAGES: readonly TextPage[] = Object.values(FILES);

const BY_URL = new Map(TEXT_PAGES.map((page) => [page.url, page]));

/** The ten service pages of spec stage 6 §6 (their `page_id`s). */
export const SERVICE_PAGE_IDS: ReadonlySet<string> = new Set([
  'about', 'contact', 'how-readings-work', 'privacy', 'terms',
  'sobre-nosotros', 'contacto', 'como-funcionan-las-lecturas', 'privacidad', 'terminos',
]);

export function textPage(path: string): TextPage {
  const page = BY_URL.get(path);
  if (!page) throw new Error(`no text page for ${path} in src/data/pages`);
  return page;
}

/** Every string of a page the reader sees. */
export function pageTexts(page: TextPage): string[] {
  return [page.title, page.description, page.h1, page.lead, page.capsule ?? '',
    ...page.blocks.flatMap((b) => [b.heading, ...b.paragraphs]), ...page.faq.flatMap((f) => [f.q, f.a])];
}

export function isHidden(page: TextPage, facts: Facts = FACTS): boolean {
  const missing = missingFacts(pageTexts(page), facts);
  if (missing.length === 0) return false;
  if (SERVICE_PAGE_IDS.has(page.page_id)) return true;
  throw new Error(`${page.url}: no value for {${missing.join('}, {')}} in src/data/facts.json`);
}

export function filledPage(page: TextPage, facts: Facts = FACTS): TextPage {
  const f = (text: string) => fillFacts(text, facts);
  return {
    ...page,
    title: f(page.title), description: f(page.description), h1: f(page.h1), lead: f(page.lead),
    capsule: page.capsule === null ? null : f(page.capsule),
    blocks: page.blocks.map((b) => ({ ...b, heading: f(b.heading), paragraphs: b.paragraphs.map(f) })),
    faq: page.faq.map((item) => ({ q: f(item.q), a: f(item.a) })),
  };
}

export function hiddenPaths(facts: Facts = FACTS): Set<string> {
  return new Set(TEXT_PAGES.filter((page) => isHidden(page, facts)).map((page) => page.url));
}
```

`site/src/lib/cardPages.ts`:

```ts
// The stage 5 card pages (content/cards/pages, schema 2; rules docs/research/stage5/30-card-page-rules.md §1, §12)
// and the strings the template adds to every one of them (template-strings.json), copied to src/data/cardpages by
// tools/site/sync_site_data.py without `citations` (the reviewer's excerpts).
import templateData from '../data/cardpages/template-strings.json';
import type { DeckCard } from './deck';
import type { FaqItem } from './textPages';
import type { Lang } from './types';

export type CardBlockId = 'on_the_card' | 'waite' | 'upright' | 'reversed' | 'love' | 'work_money' | 'advice' | 'yes_no'
  | 'in_a_reading' | 'combinations' | 'not_to_confuse' | 'ask_yourself';

export const CARD_BLOCK_IDS: readonly CardBlockId[] = ['on_the_card', 'waite', 'upright', 'reversed', 'love',
  'work_money', 'advice', 'yes_no', 'in_a_reading', 'combinations', 'not_to_confuse', 'ask_yourself'];

export interface CardPair {
  card_id: string;
  text: string;
}

export interface CardBlock {
  id: CardBlockId;
  heading: string;
  paragraphs?: string[]; // every block but combinations
  pairs?: CardPair[]; // combinations only
}

export interface CardSource {
  kind: 'image' | 'waite' | 'project';
  what: string;
  where: string;
  pages?: number[];
  url: string | null;
}

export interface CardPageData {
  schema: 2;
  card_id: string;
  lang: Lang;
  status: string;
  editor: string;
  reviewed_at: string | null;
  name_forms: { name: string; in_sentence: string; de?: string };
  title: string;
  description: string;
  h1: string;
  image_alt: string;
  facts: { arcana: 'major' | 'minor'; suit: 'wands' | 'cups' | 'swords' | 'pentacles' | null; number: number;
    numeral: string | null; also_called: string[] };
  capsule: string;
  keywords: { upright: string[]; reversed: string[] };
  blocks: CardBlock[];
  faq: FaqItem[];
  related: string[];
  mentions: { card_id: string; text: string }[];
  waite: { quote: string; quote_lang: 'en'; pages: number[]; translation: string | null; harsh: boolean };
  sources: CardSource[];
}

export interface TemplateStrings {
  facts: { major: string; minor: string; suits: Record<'wands' | 'cups' | 'swords' | 'pentacles', string>;
    ranks: Record<string, string> };
  image_caption: string;
  keywords: { caption: string; upright: string; reversed: string };
  waite: { cite: string; translation_label: string | null; harsh_context: string; boundary: string };
  work_money: { money_line: string };
  yes_no: { upright: string; reversed: string; rule: string };
  in_a_reading: { note: string };
  combinations: { intro: string; pair: string; col_pair: string; col_reading: string };
  ask_yourself: { diary_button: string };
  cta: { heading: string; text: string; button: string };
  faq: { heading: string };
  related: { heading: string };
  about: { heading: string; sources_label: string; page_one: string; page_many: string; page_numbers: string;
    method: string; deck_note: string };
}

export const TEMPLATE_STRINGS: Readonly<Record<Lang, TemplateStrings>> = {
  en: templateData.en as TemplateStrings,
  es: templateData.es as TemplateStrings,
};

const FILES = import.meta.glob<CardPageData>('../data/cardpages/*/*.json', { eager: true, import: 'default' });

export const CARD_PAGES: readonly CardPageData[] = Object.values(FILES);

const BY_KEY = new Map(CARD_PAGES.map((page) => [`${page.lang}/${page.card_id}`, page]));

export function cardPage(card: DeckCard, lang: Lang): CardPageData {
  const page = BY_KEY.get(`${lang}/${card.card_id}`);
  if (!page) throw new Error(`no card page ${lang}/${card.card_id} in src/data/cardpages`);
  return page;
}
```

- [ ] **Step 4: Run the tests and the type check**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check'`
Expected: all tests pass; `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/facts.ts site/src/lib/facts.test.ts site/src/lib/textPages.ts site/src/lib/textPages.test.ts site/src/lib/cardPages.ts site/src/lib/cardPages.test.ts
git commit -m "site (stage 6): facts, stage 5 text pages with hidden service pages, card pages and template strings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Addresses, hreflang pairs, canonical and breadcrumbs

**Files:**
- Modify: `site/src/lib/routes.ts`, `site/src/i18n/en.ts`, `site/src/i18n/es.ts`
- Create: `site/src/lib/seo.ts`, `site/src/lib/breadcrumbs.ts`
- Test: `site/src/lib/routes.test.ts`, `site/src/lib/seo.test.ts`, `site/src/lib/breadcrumbs.test.ts`,
  `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `pairs.json` (Task 1), `cardName`, `DeckCard` (deck.ts), `t` (i18n).
- Produces:
  - `routes.ts`: `PageKey` gains `'cards' | 'major_arcana' | 'yes_no_cards' | 'three_cards'`;
    `hreflangPair(path: string): string | null`; `allPagePaths()` returns 177 unique addresses.
  - `seo.ts`: `SITE_URL = 'https://arcanadiary.com'`, `DEFAULT_IMAGE = '/cards/the-moon.webp'`,
    `absoluteUrl(path: string): string`, `interface Alternate { hreflang: 'en' | 'es' | 'x-default'; href: string }`,
    `alternates(path: string): Alternate[]`
  - `breadcrumbs.ts`: `interface Crumb { name: string; path: string }`, `crumbsFor(key: PageKey, lang: Lang): Crumb[]`,
    `cardCrumbs(card: DeckCard, lang: Lang): Crumb[]`
  - dictionary keys: `navCards`, `breadcrumbLabel`, `crumbHome`, `crumbCards`, `crumbMajor`, `crumbYesNoCards`,
    `faqTitle` (232 keys)

- [ ] **Step 1: Write the failing tests**

In `site/src/lib/routes.test.ts` change the import line to

```ts
import { NAV_KEYS, PRIVATE_PAIRS, allPagePaths, cardPath, distFile, hreflangPair, langOf, pagePath, switchPath } from './routes';
```

replace the first test (`'lists every page of spec §3 for both languages'`) with

```ts
  it('lists every page of the site for both languages (stage 6 part 1)', () => {
    const paths = allPagePaths();
    expect(paths).toHaveLength(11 + 78 + 10 + 78);
    for (const p of ['/', '/one-card', '/yes-no', '/love', '/daily', '/diary', '/account', '/404', '/es', '/es/si-o-no',
      '/es/amor', '/es/carta-del-dia', '/es/diario', '/es/cuenta', '/es/404', '/cards/the-moon', '/es/cartas/la-luna',
      '/cards', '/cards/major-arcana', '/yes-no/cards', '/es/cartas', '/es/cartas/arcanos-mayores',
      '/es/tiradas/3-cartas']) {
      expect(paths).toContain(p);
    }
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('maps the pages that exist in one language only onto the nearest page of the other', () => {
    expect(pagePath('three_cards', 'es')).toBe('/es/tiradas/3-cartas');
    expect(pagePath('three_cards', 'en')).toBe('/'); // the English home is the three-card reading
    expect(pagePath('yes_no_cards', 'en')).toBe('/yes-no/cards');
    expect(pagePath('yes_no_cards', 'es')).toBe('/es/si-o-no'); // no Spanish card list: the yes/no tool
  });

  it('pairs a page for hreflang only when its pair points back at it', () => {
    expect(hreflangPair('/yes-no')).toBe('/es/si-o-no');
    expect(hreflangPair('/es/si-o-no')).toBe('/yes-no');
    expect(hreflangPair('/cards')).toBe('/es/cartas');
    expect(hreflangPair('/cards/the-moon')).toBe('/es/cartas/la-luna');
    expect(hreflangPair('/one-card')).toBeNull();
    expect(hreflangPair('/yes-no/cards')).toBeNull();
    expect(hreflangPair('/es/tiradas/3-cartas')).toBeNull();
    expect(hreflangPair('/diary')).toBeNull();
  });
```

and add to `'switches language by the pairs of hreflang.csv'`:

```ts
    expect(switchPath('/cards')).toBe('/es/cartas');
    expect(switchPath('/yes-no/cards')).toBe('/es/si-o-no');
    expect(switchPath('/es/tiradas/3-cartas')).toBe('/');
```

`site/src/lib/seo.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { DEFAULT_IMAGE, SITE_URL, absoluteUrl, alternates } from './seo';

describe('canonical and hreflang (spec stage 6 §3)', () => {
  it('builds absolute addresses on the production domain', () => {
    expect(SITE_URL).toBe('https://arcanadiary.com');
    expect(absoluteUrl('/')).toBe('https://arcanadiary.com/');
    expect(absoluteUrl('/es')).toBe('https://arcanadiary.com/es');
    expect(absoluteUrl('/cards/the-moon.webp')).toBe('https://arcanadiary.com/cards/the-moon.webp');
    expect(DEFAULT_IMAGE).toBe('/cards/the-moon.webp');
  });

  it('gives a paired page en, es and x-default = EN, from either side', () => {
    const both = [
      { hreflang: 'en', href: 'https://arcanadiary.com/yes-no' },
      { hreflang: 'es', href: 'https://arcanadiary.com/es/si-o-no' },
      { hreflang: 'x-default', href: 'https://arcanadiary.com/yes-no' },
    ];
    expect(alternates('/yes-no')).toEqual(both);
    expect(alternates('/es/si-o-no')).toEqual(both);
    expect(alternates('/')[1]).toEqual({ hreflang: 'es', href: 'https://arcanadiary.com/es' });
  });

  it('gives a page without a mutual pair only its own link', () => {
    expect(alternates('/one-card')).toEqual([{ hreflang: 'en', href: 'https://arcanadiary.com/one-card' }]);
    expect(alternates('/es/tiradas/3-cartas')).toEqual([
      { hreflang: 'es', href: 'https://arcanadiary.com/es/tiradas/3-cartas' }]);
  });
});
```

`site/src/lib/breadcrumbs.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { cardCrumbs, crumbsFor } from './breadcrumbs';
import { cardById } from './deck';

describe('breadcrumbs (spec stage 6 §3)', () => {
  it('start with Home / Inicio and follow the stage 2 trails', () => {
    expect(crumbsFor('cards', 'en')).toEqual([{ name: 'Home', path: '/' }, { name: 'Cards', path: '/cards' }]);
    expect(crumbsFor('major_arcana', 'es')).toEqual([{ name: 'Inicio', path: '/es' }, { name: 'Cartas', path: '/es/cartas' },
      { name: 'Arcanos mayores', path: '/es/cartas/arcanos-mayores' }]);
    expect(crumbsFor('yes_no_cards', 'en')).toEqual([{ name: 'Home', path: '/' }, { name: 'Yes or No', path: '/yes-no' },
      { name: 'Card list', path: '/yes-no/cards' }]);
    expect(crumbsFor('three_cards', 'es')).toEqual([{ name: 'Inicio', path: '/es' },
      { name: '3 cartas', path: '/es/tiradas/3-cartas' }]);
  });

  it('give the tools on the home level no breadcrumbs', () => {
    for (const key of ['home', 'one_card', 'yes_no', 'love', 'daily'] as const) expect(crumbsFor(key, 'en')).toEqual([]);
  });

  it('put a major card under Major Arcana and a minor card under Cards', () => {
    expect(cardCrumbs(cardById('major-18-moon')!, 'en')).toEqual([{ name: 'Home', path: '/' },
      { name: 'Cards', path: '/cards' }, { name: 'Major Arcana', path: '/cards/major-arcana' },
      { name: 'The Moon', path: '/cards/the-moon' }]);
    expect(cardCrumbs(cardById('swords-03-three')!, 'es')).toEqual([{ name: 'Inicio', path: '/es' },
      { name: 'Cartas', path: '/es/cartas' }, { name: 'Tres de Espadas', path: '/es/cartas/tres-de-espadas' }]);
  });
});
```

In `site/src/i18n/i18n.test.ts` change `expect(keys('en').length).toBe(225);` to `expect(keys('en').length).toBe(232);`
and add inside `describe('dictionaries', …)`:

```ts
  it('keep the stage 6 menu and breadcrumb words (stage 2 menu table, prototypes)', () => {
    expect([t('en').navCards, t('es').navCards]).toEqual(['Card Meanings', 'Significados']);
    expect([t('en').crumbHome, t('es').crumbHome, t('en').crumbCards, t('es').crumbCards]).toEqual(['Home', 'Inicio',
      'Cards', 'Cartas']);
    expect([t('en').crumbMajor, t('es').crumbMajor]).toEqual(['Major Arcana', 'Arcanos mayores']);
    expect([t('en').breadcrumbLabel, t('es').breadcrumbLabel]).toEqual(['Breadcrumb', 'Ruta']);
  });
```

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/routes.test.ts src/lib/seo.test.ts src/lib/breadcrumbs.test.ts src/i18n/i18n.test.ts'`
Expected: FAIL — `hreflangPair` is not exported; `./seo` and `./breadcrumbs` do not resolve; 225 keys instead of 232.

- [ ] **Step 3: Implement**

In `site/src/lib/routes.ts` replace the `PageKey` line, the `PAGE_PATHS` constant and `allPagePaths()` with:

```ts
export type PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'diary' | 'account' | 'not_found'
  | 'cards' | 'major_arcana' | 'yes_no_cards' | 'three_cards';
```

```ts
const PAGE_PATHS: Record<Lang, Record<PageKey, string>> = {
  en: {
    home: '/', one_card: '/one-card', yes_no: '/yes-no', love: '/love', daily: '/daily', diary: '/diary',
    account: '/account', not_found: '/404', cards: '/cards', major_arcana: '/cards/major-arcana',
    yes_no_cards: '/yes-no/cards',
    three_cards: '/', // English has no three-card page: the home page is the three-card reading
  },
  // Spanish has no one-card page: the one-card mode is the #una-carta section of the home page (stage 2 map)
  es: {
    home: '/es', one_card: '/es#una-carta', yes_no: '/es/si-o-no', love: '/es/amor', daily: '/es/carta-del-dia',
    diary: '/es/diario', account: '/es/cuenta', not_found: '/es/404', cards: '/es/cartas',
    major_arcana: '/es/cartas/arcanos-mayores',
    yes_no_cards: '/es/si-o-no', // no Spanish card list: the yes/no tool
    three_cards: '/es/tiradas/3-cartas',
  },
};
```

```ts
/** The pair for hreflang (spec stage 6 §3): only a pair that points back — /one-card → /es is a switch, not a pair. */
export function hreflangPair(path: string): string | null {
  const pair = PAIRS[path];
  return pair !== undefined && PAIRS[pair] === path ? pair : null;
}

/** Every page the build must produce, both languages: tools, hubs, the diary and the account, 78 card pages each,
 * 404. A key that points at another page of its language (three_cards in English) is listed once. */
export function allPagePaths(): string[] {
  const tools = (lang: Lang) => [...new Set((Object.keys(PAGE_PATHS[lang]) as PageKey[])
    .map((key) => PAGE_PATHS[lang][key]).filter((p) => !p.includes('#')))];
  return [...tools('en'), ...DECK.map((c) => cardPath(c, 'en')), ...tools('es'), ...DECK.map((c) => cardPath(c, 'es'))];
}
```

Change the first comment line of `routes.ts` to
`// Addresses of the site's pages (spec 4.4a §3, stage 6 §3) and their language pairs`.

`site/src/lib/seo.ts`:

```ts
// Canonical address and hreflang of a page (spec stage 6 §3): canonical https://arcanadiary.com{path}; en, es and
// x-default = EN for a page whose pair in pairs.json points back at it; a page without such a pair gets only its own
// link.
import { hreflangPair, langOf } from './routes';

export const SITE_URL = 'https://arcanadiary.com';
/** Share picture of a page without its own card scan (no 1200 × 630 picture exists yet). */
export const DEFAULT_IMAGE = '/cards/the-moon.webp';

export interface Alternate {
  hreflang: 'en' | 'es' | 'x-default';
  href: string;
}

export function absoluteUrl(path: string): string {
  return path === '/' ? `${SITE_URL}/` : `${SITE_URL}${path}`;
}

export function alternates(path: string): Alternate[] {
  const lang = langOf(path);
  const pair = hreflangPair(path);
  if (pair === null) return [{ hreflang: lang, href: absoluteUrl(path) }];
  const en = lang === 'en' ? path : pair;
  const es = lang === 'es' ? path : pair;
  return [
    { hreflang: 'en', href: absoluteUrl(en) },
    { hreflang: 'es', href: absoluteUrl(es) },
    { hreflang: 'x-default', href: absoluteUrl(en) },
  ];
}
```

`site/src/lib/breadcrumbs.ts`:

```ts
// Breadcrumbs (spec stage 6 §3; stage 2 `breadcrumb` columns): first Home / Inicio; a major card — Home › Cards ›
// Major Arcana › card; a minor card — Home › Cards › card; the hub — Home › Cards; Major Arcana — Home › Cards › Major
// Arcana; the yes/no card list — Home › Yes or No › Card list; "3 cartas" — Inicio › 3 cartas; the tools on the home
// level have none.
import { t } from '../i18n';
import { cardName, type DeckCard } from './deck';
import { cardPath, pagePath, type PageKey } from './routes';
import type { Lang } from './types';

export interface Crumb {
  name: string;
  path: string;
}

function base(lang: Lang): { home: Crumb; cards: Crumb; major: Crumb } {
  const d = t(lang);
  return {
    home: { name: d.crumbHome, path: pagePath('home', lang) },
    cards: { name: d.crumbCards, path: pagePath('cards', lang) },
    major: { name: d.crumbMajor, path: pagePath('major_arcana', lang) },
  };
}

export function crumbsFor(key: PageKey, lang: Lang): Crumb[] {
  const d = t(lang);
  const { home, cards, major } = base(lang);
  switch (key) {
    case 'cards':
      return [home, cards];
    case 'major_arcana':
      return [home, cards, major];
    case 'yes_no_cards':
      return [home, { name: d.navYesNo, path: pagePath('yes_no', lang) },
        { name: d.crumbYesNoCards, path: pagePath('yes_no_cards', lang) }];
    case 'three_cards':
      return [home, { name: d.threeCardsChip, path: pagePath('three_cards', lang) }];
    default:
      return [];
  }
}

export function cardCrumbs(card: DeckCard, lang: Lang): Crumb[] {
  const { home, cards, major } = base(lang);
  const self = { name: cardName(card, lang), path: cardPath(card, lang) };
  return card.arcana === 'major' ? [home, cards, major, self] : [home, cards, self];
}
```

In `site/src/i18n/en.ts` replace

```ts
  diaryReminderOnLink: 'your account',
};
```

with

```ts
  diaryReminderOnLink: 'your account',
  // stage 6: menu (stage 2 menu table), breadcrumbs (prototypes CardMoon, Major, YesNoList), FAQ heading
  navCards: 'Card Meanings',
  breadcrumbLabel: 'Breadcrumb',
  crumbHome: 'Home',
  crumbCards: 'Cards',
  crumbMajor: 'Major Arcana',
  crumbYesNoCards: 'Card list',
  faqTitle: 'Frequently asked questions',
};
```

In `site/src/i18n/es.ts` replace

```ts
  diaryReminderOnLink: 'tu cuenta',
};
```

with

```ts
  diaryReminderOnLink: 'tu cuenta',
  // etapa 6: menú (tabla del menú de la etapa 2), migas (prototipos LaLuna, TresCartas), título de las preguntas
  navCards: 'Significados',
  breadcrumbLabel: 'Ruta',
  crumbHome: 'Inicio',
  crumbCards: 'Cartas',
  crumbMajor: 'Arcanos mayores',
  crumbYesNoCards: 'Lista de cartas',
  faqTitle: 'Preguntas frecuentes',
};
```

- [ ] **Step 4: Run all site tests**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check'`
Expected: all pass, `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/routes.ts site/src/lib/routes.test.ts site/src/lib/seo.ts site/src/lib/seo.test.ts site/src/lib/breadcrumbs.ts site/src/lib/breadcrumbs.test.ts site/src/i18n
git commit -m "site (stage 6): new addresses, mutual hreflang pairs, canonical URLs, breadcrumb trails

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: JSON-LD

**Files:**
- Create: `site/src/lib/jsonld.ts`, `site/src/components/JsonLd.astro`
- Modify: `site/src/lib/guards.test.ts` (one allowed `set:html`)
- Test: `site/src/lib/jsonld.test.ts`

**Interfaces:**
- Consumes: `Crumb` (breadcrumbs.ts), `absoluteUrl` (seo.ts), `FaqItem` (textPages.ts).
- Produces: `type JsonLd = Readonly<Record<string, unknown>>`, `interface LdItem { name: string; path: string }`,
  `ORGANIZATION`, `WAITE_BOOK`, `breadcrumbLd(crumbs): JsonLd | null`, `faqLd(items): JsonLd | null`,
  `webPageLd({ name, description, path, lang }): JsonLd`, `collectionLd({ name, description, path, lang, items }): JsonLd`,
  `cardLd({ headline, description, path, lang, image, reviewedAt, editorName }): JsonLd`, `ldScript(data): string`;
  component `<JsonLd data={…} />`.

- [ ] **Step 1: Write the failing tests**

`site/src/lib/jsonld.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { breadcrumbLd, cardLd, collectionLd, faqLd, ldScript, webPageLd } from './jsonld';

describe('JSON-LD (spec stage 6 §3)', () => {
  it('lists the breadcrumbs with absolute addresses, nothing for a page without them', () => {
    expect(breadcrumbLd([{ name: 'Home', path: '/' }, { name: 'Cards', path: '/cards' }])).toEqual({
      '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://arcanadiary.com/' },
        { '@type': 'ListItem', position: 2, name: 'Cards', item: 'https://arcanadiary.com/cards' }],
    });
    expect(breadcrumbLd([])).toBeNull();
  });

  it('turns the FAQ into FAQPage, nothing for a page without questions', () => {
    expect(faqLd([{ q: 'Is it free?', a: 'Yes.' }])).toEqual({ '@context': 'https://schema.org', '@type': 'FAQPage',
      mainEntity: [{ '@type': 'Question', name: 'Is it free?', acceptedAnswer: { '@type': 'Answer', text: 'Yes.' } }] });
    expect(faqLd([])).toBeNull();
  });

  it('describes a tool as a WebPage and a hub as a CollectionPage with its list', () => {
    expect(webPageLd({ name: 'Yes or no tarot', description: 'D', path: '/yes-no', lang: 'en' })).toEqual({
      '@context': 'https://schema.org', '@type': 'WebPage', name: 'Yes or no tarot', description: 'D',
      url: 'https://arcanadiary.com/yes-no', inLanguage: 'en',
      isPartOf: { '@type': 'WebSite', name: 'Arcana Diary', url: 'https://arcanadiary.com/' } });
    const hub = collectionLd({ name: 'Cartas', description: 'D', path: '/es/cartas', lang: 'es',
      items: [{ name: 'El Loco', path: '/es/cartas/el-loco' }] });
    expect(hub['@type']).toBe('CollectionPage');
    expect(hub.mainEntity).toEqual({ '@type': 'ItemList', numberOfItems: 1, itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'El Loco', url: 'https://arcanadiary.com/es/cartas/el-loco' }] });
  });

  it('describes a card page as an Article by the Organization, edited and reviewed by the editor', () => {
    const ld = cardLd({ headline: 'The Moon Tarot Card Meaning', description: 'D', path: '/cards/the-moon', lang: 'en',
      image: '/cards/the-moon.webp', reviewedAt: '2026-11-23', editorName: 'Adrian Solenne' });
    const editor = { '@type': 'Person', name: 'Adrian Solenne', jobTitle: 'Editor' };
    const org = { '@type': 'Organization', name: 'Arcana Diary', url: 'https://arcanadiary.com/' };
    expect(ld).toMatchObject({ '@type': 'Article', headline: 'The Moon Tarot Card Meaning', inLanguage: 'en',
      image: 'https://arcanadiary.com/cards/the-moon.webp', author: org, publisher: org, dateModified: '2026-11-23',
      editor, isBasedOn: { '@type': 'Book', name: 'The Pictorial Key to the Tarot', datePublished: '1911',
        url: 'https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot' } });
    expect(ld.mainEntityOfPage).toEqual({ '@type': 'WebPage', '@id': 'https://arcanadiary.com/cards/the-moon',
      url: 'https://arcanadiary.com/cards/the-moon', reviewedBy: editor, lastReviewed: '2026-11-23' });
  });

  it('writes script text that cannot close the script or start markup', () => {
    const text = ldScript({ name: '</script><b>&\u2028' });
    expect(text).toBe('{"name":"\\u003c/script\\u003e\\u003cb\\u003e\\u0026\\u2028"}');
    expect(JSON.parse(text)).toEqual({ name: '</script><b>&\u2028' });
  });
});
```

In `site/src/lib/guards.test.ts` replace the test `'never put text in as markup'` with:

```ts
  it('never put text in as markup (one exception: the JSON-LD script, escaped by ldScript)', () => {
    const sink = /innerHTML|dangerouslySetInnerHTML|set:html|insertAdjacentHTML|outerHTML\s*=|document\.write|createContextualFragment|srcdoc|new Function\(|\beval\(/;
    const allowed = (path: string) => (rel(path) === 'components/JsonLd.astro'
      ? read(path).replace('set:html={ldScript(data)}', '') : read(path));
    for (const path of SOURCES) expect(allowed(path), rel(path)).not.toMatch(sink);
    expect(read(join(SRC, 'components/JsonLd.astro'))).toContain('set:html={ldScript(data)}');
  });
```

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/jsonld.test.ts src/lib/guards.test.ts'`
Expected: FAIL — `./jsonld` does not resolve; `ENOENT … components/JsonLd.astro`.

- [ ] **Step 3: Implement**

`site/src/lib/jsonld.ts`:

```ts
// JSON-LD of the pages (spec stage 6 §3): BreadcrumbList wherever there are breadcrumbs; FAQPage from the FAQ; the
// card page an Article (author and publisher: the Organization "Arcana Diary"; dateModified = reviewed_at; the
// editor a Person; isBasedOn: Waite's book on Wikisource) whose WebPage carries reviewedBy — schema.org defines
// reviewedBy on WebPage, not on Article; hubs a CollectionPage with an ItemList; tools and text pages a WebPage.
import type { Crumb } from './breadcrumbs';
import { absoluteUrl } from './seo';
import type { FaqItem } from './textPages';
import type { Lang } from './types';

export type JsonLd = Readonly<Record<string, unknown>>;

export interface LdItem {
  name: string;
  path: string;
}

interface PageInfo {
  name: string;
  description: string;
  path: string;
  lang: Lang;
}

const CONTEXT = 'https://schema.org';

export const ORGANIZATION = { '@type': 'Organization', name: 'Arcana Diary', url: absoluteUrl('/') } as const;

export const WAITE_BOOK = {
  '@type': 'Book', name: 'The Pictorial Key to the Tarot', author: { '@type': 'Person', name: 'Arthur Edward Waite' },
  datePublished: '1911', url: 'https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot',
} as const;

const WEBSITE = { '@type': 'WebSite', name: 'Arcana Diary', url: absoluteUrl('/') } as const;

export function breadcrumbLd(crumbs: readonly Crumb[]): JsonLd | null {
  if (crumbs.length === 0) return null;
  return {
    '@context': CONTEXT, '@type': 'BreadcrumbList',
    itemListElement: crumbs.map((c, i) => ({ '@type': 'ListItem', position: i + 1, name: c.name, item: absoluteUrl(c.path) })),
  };
}

export function faqLd(items: readonly FaqItem[]): JsonLd | null {
  if (items.length === 0) return null;
  return {
    '@context': CONTEXT, '@type': 'FAQPage',
    mainEntity: items.map((f) => ({ '@type': 'Question', name: f.q, acceptedAnswer: { '@type': 'Answer', text: f.a } })),
  };
}

export function webPageLd(p: PageInfo): JsonLd {
  return { '@context': CONTEXT, '@type': 'WebPage', name: p.name, description: p.description, url: absoluteUrl(p.path),
    inLanguage: p.lang, isPartOf: WEBSITE };
}

export function collectionLd(p: PageInfo & { items: readonly LdItem[] }): JsonLd {
  return {
    '@context': CONTEXT, '@type': 'CollectionPage', name: p.name, description: p.description, url: absoluteUrl(p.path),
    inLanguage: p.lang, isPartOf: WEBSITE,
    mainEntity: { '@type': 'ItemList', numberOfItems: p.items.length,
      itemListElement: p.items.map((it, i) => ({ '@type': 'ListItem', position: i + 1, name: it.name, url: absoluteUrl(it.path) })) },
  };
}

export function cardLd(p: { headline: string; description: string; path: string; lang: Lang; image: string;
  reviewedAt: string; editorName: string }): JsonLd {
  const editor = { '@type': 'Person', name: p.editorName, jobTitle: 'Editor' };
  return {
    '@context': CONTEXT, '@type': 'Article', headline: p.headline, description: p.description, inLanguage: p.lang,
    image: absoluteUrl(p.image), author: ORGANIZATION, publisher: ORGANIZATION, dateModified: p.reviewedAt, editor,
    isBasedOn: WAITE_BOOK,
    mainEntityOfPage: { '@type': 'WebPage', '@id': absoluteUrl(p.path), url: absoluteUrl(p.path), reviewedBy: editor,
      lastReviewed: p.reviewedAt },
  };
}

/** The text of a <script type="application/ld+json">: no "<", ">" or "&" that could close it or start markup. */
export function ldScript(data: JsonLd): string {
  return JSON.stringify(data).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
}
```

`site/src/components/JsonLd.astro`:

```astro
---
// One JSON-LD script. The only set:html of the site (guards.test.ts allows exactly this line): Astro prints script
// text only this way, and ldScript escapes every character that could close the script.
import { ldScript, type JsonLd } from '../lib/jsonld';

interface Props {
  data: JsonLd;
}

const { data } = Astro.props;
---
<script type="application/ld+json" is:inline set:html={ldScript(data)} />
```

- [ ] **Step 4: Run all site tests and the type check**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check'`
Expected: all pass, `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/jsonld.ts site/src/lib/jsonld.test.ts site/src/components/JsonLd.astro site/src/lib/guards.test.ts
git commit -m "site (stage 6): JSON-LD builders and the one escaped JSON-LD script

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The head of every page

**Files:**
- Modify: `site/src/layouts/Base.astro`, `site/src/views/HomeView.astro`, `site/src/views/ToolView.astro`,
  `site/src/views/DailyView.astro`, `site/src/views/CardView.astro`, `site/src/styles/global.css`
- Create: `site/src/components/Breadcrumbs.astro`

**Interfaces:**
- Consumes: `absoluteUrl`, `alternates`, `DEFAULT_IMAGE` (seo.ts); `JsonLd`, `webPageLd`, `breadcrumbLd` (jsonld.ts);
  `JsonLd.astro`; `textPage`, `filledPage` (textPages.ts); `cardPage` (cardPages.ts); `cardCrumbs`, `Crumb`
  (breadcrumbs.ts).
- Produces:
  - `Base.astro` props: `lang`, `title`, `path`, `current?`, `noindex?`, `description?: string`, `image?: string`
    (site path, default `DEFAULT_IMAGE`), `ogType?: 'website' | 'article'`, `jsonLd?: readonly (JsonLd | null)[]`.
    Rule: a page is *indexable* when it has a `description` and no `noindex`; only then does it get canonical,
    hreflang, Open Graph, Twitter and JSON-LD.
  - `<Breadcrumbs lang crumbs />` — renders nothing for an empty list.

- [ ] **Step 1: Write the layout**

Replace `site/src/layouts/Base.astro` with:

```astro
---
// Every page: language, title, description, fonts (our own, /fonts: Cormorant Garamond 500/600, Manrope 400–700;
// @font-face in global.css), tokens, the header with the menu and the language switch, the footer. Stage 6 (spec §3):
// an indexable page — one with a description and without noindex — also gets its canonical address, hreflang by its
// language pair (src/lib/seo.ts), Open Graph and Twitter tags and its JSON-LD. The stage is closed by Caddy
// (password, X-Robots-Tag). `noindex`: the diary and the account (spec 4.4b §5, §6) — never indexed, also after the
// launch — and the hidden service pages (stage 6 decision 35).
import '../styles/tokens.css';
import '../styles/global.css';
import Header from '../components/Header.astro';
import Footer from '../components/Footer.astro';
import JsonLdScript from '../components/JsonLd.astro';
import { t } from '../i18n';
import type { JsonLd } from '../lib/jsonld';
import type { PageKey } from '../lib/routes';
import { DEFAULT_IMAGE, absoluteUrl, alternates } from '../lib/seo';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
  title: string;
  path: string;
  current?: PageKey;
  noindex?: boolean;
  description?: string;
  image?: string;
  ogType?: 'website' | 'article';
  jsonLd?: readonly (JsonLd | null)[];
}

const { lang, title, path, current, noindex = false, description, image = DEFAULT_IMAGE, ogType = 'website',
  jsonLd = [] } = Astro.props;
const d = t(lang);
const indexable = !noindex && description !== undefined;
const url = absoluteUrl(path);
const imageUrl = absoluteUrl(image);
const ld = jsonLd.filter((item): item is JsonLd => item !== null);
---
<!doctype html>
<html lang={lang}>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    {description !== undefined ? <meta name="description" content={description} /> : null}
    {noindex ? <meta name="robots" content="noindex, nofollow" /> : null}
    {indexable ? (
      <>
        <link rel="canonical" href={url} />
        {alternates(path).map((a) => <link rel="alternate" hreflang={a.hreflang} href={a.href} />)}
        <meta property="og:type" content={ogType} />
        <meta property="og:site_name" content={d.siteName} />
        <meta property="og:title" content={title} />
        <meta property="og:description" content={description} />
        <meta property="og:url" content={url} />
        <meta property="og:image" content={imageUrl} />
        <meta property="og:locale" content={lang === 'en' ? 'en_US' : 'es_MX'} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={title} />
        <meta name="twitter:description" content={description} />
        <meta name="twitter:image" content={imageUrl} />
        {ld.map((data) => <JsonLdScript data={data} />)}
      </>
    ) : null}
    <noscript><style>@media (max-width: 899px) { .site-nav { display: block; } .menu-button { display: none; } }</style></noscript>
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

- [ ] **Step 2: Write the breadcrumbs component and its style**

`site/src/components/Breadcrumbs.astro`:

```astro
---
// Breadcrumbs (spec stage 6 §3; prototypes CardMoon, Major, YesNoList, TresCartas): links, the last item is the page
// itself. The same trail goes to BreadcrumbList JSON-LD (src/lib/jsonld.ts).
import { t } from '../i18n';
import type { Crumb } from '../lib/breadcrumbs';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
  crumbs: readonly Crumb[];
}

const { lang, crumbs } = Astro.props;
---
{crumbs.length > 0 ? (
  <nav class="breadcrumbs" aria-label={t(lang).breadcrumbLabel}>
    <ol>
      {crumbs.map((crumb, i) => (
        <li>{i === crumbs.length - 1 ? <span aria-current="page">{crumb.name}</span> : <a href={crumb.path}>{crumb.name}</a>}</li>
      ))}
    </ol>
  </nav>
) : null}
```

Append to `site/src/styles/global.css`:

```css

/* Breadcrumbs (stage 6; prototypes CardMoon, Major, YesNoList, TresCartas) */
.breadcrumbs { padding-top: var(--space-3); font-size: var(--font-size-small); color: var(--color-day-text-muted); }
.breadcrumbs ol { display: flex; flex-wrap: wrap; align-items: center; gap: 0 var(--space-2); list-style: none; margin: 0; padding: 0; }
.breadcrumbs li { display: inline-flex; align-items: center; gap: var(--space-2); }
.breadcrumbs li + li::before { content: '›'; content: '›' / ''; }
.breadcrumbs a { display: inline-flex; align-items: center; min-height: 44px; color: var(--color-day-text-muted); }
.breadcrumbs [aria-current='page'] { color: var(--color-day-text); }
```

- [ ] **Step 3: Give the existing views their titles, descriptions and JSON-LD**

`site/src/views/HomeView.astro`: add these imports after `import { cardPath, pagePath } from '../lib/routes';`:

```ts
import { webPageLd } from '../lib/jsonld';
import { filledPage, textPage } from '../lib/textPages';
```

add after `const d = t(lang);`:

```ts
const path = pagePath('home', lang);
const text = filledPage(textPage(path)); // title and description of the stage 5 text (spec stage 6 §5)
```

and replace the opening `<Base …>` line with:

```astro
<Base lang={lang} title={text.title} description={text.description} path={path} current="home"
  jsonLd={[webPageLd({ name: text.h1, description: text.description, path, lang })]}>
```

`site/src/views/ToolView.astro`: add the same two imports after `import { pagePath } from '../lib/routes';`, add after
`const copy = COPY[page];`:

```ts
const path = pagePath(page, lang);
const text = filledPage(textPage(path)); // title and description of the stage 5 text (spec stage 6 §5)
```

and replace the opening `<Base …>` line with:

```astro
<Base lang={lang} title={text.title} description={text.description} path={path}
  current={page === 'one_card' ? undefined : page}
  jsonLd={[webPageLd({ name: text.h1, description: text.description, path, lang })]}>
```

`site/src/views/DailyView.astro`: add the two imports after `import { pagePath } from '../lib/routes';`, add after
`const d = t(lang);`:

```ts
const path = pagePath('daily', lang);
const text = filledPage(textPage(path)); // title and description of the stage 5 text (spec stage 6 §5)
```

and replace the opening `<Base …>` line with:

```astro
<Base lang={lang} title={text.title} description={text.description} path={path} current="daily"
  jsonLd={[webPageLd({ name: text.h1, description: text.description, path, lang })]}>
```

`site/src/views/CardView.astro` (temporary until Task 9): add after `import ReadingIsland from '../islands/ReadingIsland';`:

```ts
import Breadcrumbs from '../components/Breadcrumbs.astro';
import { cardCrumbs } from '../lib/breadcrumbs';
import { cardPage } from '../lib/cardPages';
import { breadcrumbLd } from '../lib/jsonld';
```

change `import { cardName, neighbors, type DeckCard } from '../lib/deck';` to
`import { cardImage, cardName, neighbors, type DeckCard } from '../lib/deck';`, add after the `eyebrow` constant:

```ts
const text = cardPage(card, lang); // title and description of the stage 5 card page
const crumbs = cardCrumbs(card, lang);
```

and replace the opening `<Base …>` line with:

```astro
<Base lang={lang} title={text.title} description={text.description} path={cardPath(card, lang)} current="cards"
  image={cardImage(card, 700)} jsonLd={[breadcrumbLd(crumbs)]}>
  <Breadcrumbs lang={lang} crumbs={crumbs} />
```

- [ ] **Step 4: Build and look at the heads**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx astro check' && deploy/build-site.sh`
Expected: `0 errors`; the build ends with `Complete!`.

Run: `grep -o '<link rel="canonical"[^>]*>\|<link rel="alternate"[^>]*>' site/dist/yes-no.html site/dist/one-card.html site/dist/cards/the-moon.html`
Expected:

```
site/dist/yes-no.html:<link rel="canonical" href="https://arcanadiary.com/yes-no">
site/dist/yes-no.html:<link rel="alternate" hreflang="en" href="https://arcanadiary.com/yes-no">
site/dist/yes-no.html:<link rel="alternate" hreflang="es" href="https://arcanadiary.com/es/si-o-no">
site/dist/yes-no.html:<link rel="alternate" hreflang="x-default" href="https://arcanadiary.com/yes-no">
site/dist/one-card.html:<link rel="canonical" href="https://arcanadiary.com/one-card">
site/dist/one-card.html:<link rel="alternate" hreflang="en" href="https://arcanadiary.com/one-card">
site/dist/cards/the-moon.html:<link rel="canonical" href="https://arcanadiary.com/cards/the-moon">
site/dist/cards/the-moon.html:<link rel="alternate" hreflang="en" href="https://arcanadiary.com/cards/the-moon">
site/dist/cards/the-moon.html:<link rel="alternate" hreflang="es" href="https://arcanadiary.com/es/cartas/la-luna">
site/dist/cards/the-moon.html:<link rel="alternate" hreflang="x-default" href="https://arcanadiary.com/cards/the-moon">
```

Run: `for f in index cards/the-moon diary 404; do echo "$f $(grep -o 'application/ld+json' site/dist/$f.html | wc -l) $(grep -o 'rel="canonical"' site/dist/$f.html | wc -l)"; done`
Expected: `index 1 1`, `cards/the-moon 1 1`, `diary 0 0`, `404 0 0`.

- [ ] **Step 5: Run the tests**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run'`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add site/src/layouts/Base.astro site/src/components/Breadcrumbs.astro site/src/views site/src/styles/global.css
git commit -m "site (stage 6): description, canonical, hreflang, Open Graph and JSON-LD on every indexable page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: The six new addresses as text pages, and "Card Meanings" in the menu

**Files:**
- Create: `site/src/views/TextPageView.astro`, `site/src/components/TextBlocks.astro`, `site/src/components/Faq.astro`,
  `site/src/pages/cards/index.astro`, `site/src/pages/cards/major-arcana.astro`, `site/src/pages/yes-no/cards.astro`,
  `site/src/pages/es/cartas/index.astro`, `site/src/pages/es/cartas/arcanos-mayores.astro`,
  `site/src/pages/es/tiradas/3-cartas.astro`
- Modify: `site/src/lib/routes.ts` (`NAV_KEYS`), `site/src/components/Header.astro`, `site/src/styles/global.css`
- Test: `site/src/lib/routes.test.ts`

**Interfaces:**
- Consumes: everything of Tasks 2–5.
- Produces:
  - `<TextPageView lang pageKey current? items? />` — breadcrumbs, H1, lead, capsule, default slot (lists, Part 3),
    blocks, FAQ; `items: readonly LdItem[]` switches its JSON-LD from WebPage to CollectionPage; a hidden page
    (`isHidden`) is rendered with `noindex`.
  - `<TextBlocks blocks />` — one `<section class="page-section prose" id={block.id}>` per block with an `<h2>`.
  - `<Faq heading items id />` — `<details>` per question, the first open; nothing when `items` is empty.
  - `NAV_KEYS = ['home', 'yes_no', 'love', 'daily', 'cards', 'diary']`.

- [ ] **Step 1: Write the failing test**

In `site/src/lib/routes.test.ts` replace the test `'has the menu items of 4.4b in both languages'` with:

```ts
  it('has the menu items of stage 6 in both languages (stage 2 menu table)', () => {
    expect(NAV_KEYS).toEqual(['home', 'yes_no', 'love', 'daily', 'cards', 'diary']);
    expect(NAV_KEYS.map((k) => pagePath(k, 'es'))).toEqual(['/es', '/es/si-o-no', '/es/amor', '/es/carta-del-dia',
      '/es/cartas', '/es/diario']);
  });
```

- [ ] **Step 2: Run it to see it fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/routes.test.ts'`
Expected: FAIL — the menu has 5 items, not 6.

- [ ] **Step 3: Menu**

In `site/src/lib/routes.ts` replace

```ts
/** The menu (stage 2 structure, design screens 11c/11d, 13a): the diary since 4.4b; "Card Meanings" arrives with
 * stage 6. */
export const NAV_KEYS: readonly PageKey[] = ['home', 'yes_no', 'love', 'daily', 'diary'];
```

with

```ts
/** The menu (stage 2 structure, design screens 11c/11d, 13a): the diary since 4.4b, "Card Meanings" since stage 6. */
export const NAV_KEYS: readonly PageKey[] = ['home', 'yes_no', 'love', 'daily', 'cards', 'diary'];
```

In `site/src/components/Header.astro` replace

```ts
const LABELS: Record<string, DictKey> = {
  home: 'navHome', yes_no: 'navYesNo', love: 'navLove', daily: 'navDaily', diary: 'navDiary',
};
```

with

```ts
const LABELS: Record<string, DictKey> = {
  home: 'navHome', yes_no: 'navYesNo', love: 'navLove', daily: 'navDaily', cards: 'navCards', diary: 'navDiary',
};
```

- [ ] **Step 4: Text blocks, FAQ and the text page view**

`site/src/components/TextBlocks.astro`:

```astro
---
// The blocks of a stage 5 text (content/pages): a section per block, its id the block id, an H2 and the paragraphs.
import type { TextBlock } from '../lib/textPages';

interface Props {
  blocks: readonly TextBlock[];
}

const { blocks } = Astro.props;
---
{blocks.map((block) => (
  <section class="page-section prose" id={block.id} aria-labelledby={`${block.id}-title`}>
    <h2 class="h2" id={`${block.id}-title`}>{block.heading}</h2>
    {block.paragraphs.map((paragraph) => <p>{paragraph}</p>)}
  </section>
))}
```

`site/src/components/Faq.astro`:

```astro
---
// FAQ of a page (spec stage 6 §4–§5): one <details> per question, the first one open. The same questions go to the
// FAQPage JSON-LD (src/lib/jsonld.ts).
import type { FaqItem } from '../lib/textPages';

interface Props {
  heading: string;
  items: readonly FaqItem[];
  id: string;
}

const { heading, items, id } = Astro.props;
---
{items.length > 0 ? (
  <section class="page-section faq" id={id} aria-labelledby={`${id}-title`}>
    <h2 class="h2" id={`${id}-title`}>{heading}</h2>
    {items.map((item, i) => (
      <details open={i === 0}>
        <summary>{item.q}</summary>
        <p>{item.a}</p>
      </details>
    ))}
  </section>
) : null}
```

`site/src/views/TextPageView.astro`:

```astro
---
// A page of stage 5 text without a tool (spec stage 6 §3, §5, §6): breadcrumbs, H1, lead, capsule, then the default
// slot (the card lists of the hubs, part 3), the blocks and the FAQ of content/pages. A service page whose text still
// has an operator placeholder is built but hidden: noindex, and the footer and the sitemap leave it out (decision 35).
import Base from '../layouts/Base.astro';
import Breadcrumbs from '../components/Breadcrumbs.astro';
import Faq from '../components/Faq.astro';
import TextBlocks from '../components/TextBlocks.astro';
import { t } from '../i18n';
import { crumbsFor } from '../lib/breadcrumbs';
import { breadcrumbLd, collectionLd, faqLd, webPageLd, type LdItem } from '../lib/jsonld';
import { pagePath, type PageKey } from '../lib/routes';
import { filledPage, isHidden, textPage } from '../lib/textPages';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
  pageKey: PageKey;
  current?: PageKey;
  items?: readonly LdItem[];
}

const { lang, pageKey, current, items } = Astro.props;
const d = t(lang);
const path = pagePath(pageKey, lang);
const source = textPage(path);
const hidden = isHidden(source);
const page = filledPage(source);
const crumbs = crumbsFor(pageKey, lang);
const info = { name: page.h1, description: page.description, path, lang };
const main = items ? collectionLd({ ...info, items }) : webPageLd(info);
---
<Base lang={lang} title={page.title} description={page.description} path={path} current={current} noindex={hidden}
  jsonLd={[breadcrumbLd(crumbs), main, faqLd(page.faq)]}>
  <Breadcrumbs lang={lang} crumbs={crumbs} />
  <section class="page-hero">
    <h1 class="display">{page.h1}</h1>
    <p class="lead">{page.lead}</p>
    {page.capsule ? <p class="capsule">{page.capsule}</p> : null}
  </section>
  <slot />
  <TextBlocks blocks={page.blocks} />
  <Faq heading={d.faqTitle} items={page.faq} id="faq" />
</Base>
```

- [ ] **Step 5: The six addresses**

`site/src/pages/cards/index.astro` (Astro with `build.format: 'file'` writes `cards.html` next to the `cards/` folder):

```astro
---
import TextPageView from '../../views/TextPageView.astro';
---
<TextPageView lang="en" pageKey="cards" current="cards" />
```

`site/src/pages/cards/major-arcana.astro` (a static route wins over `cards/[slug].astro`; no card has this slug —
`RESERVED` in `tools/research/structure_map.py`):

```astro
---
import TextPageView from '../../views/TextPageView.astro';
---
<TextPageView lang="en" pageKey="major_arcana" current="cards" />
```

`site/src/pages/yes-no/cards.astro`:

```astro
---
import TextPageView from '../../views/TextPageView.astro';
---
<TextPageView lang="en" pageKey="yes_no_cards" current="yes_no" />
```

`site/src/pages/es/cartas/index.astro`:

```astro
---
import TextPageView from '../../../views/TextPageView.astro';
---
<TextPageView lang="es" pageKey="cards" current="cards" />
```

`site/src/pages/es/cartas/arcanos-mayores.astro`:

```astro
---
import TextPageView from '../../../views/TextPageView.astro';
---
<TextPageView lang="es" pageKey="major_arcana" current="cards" />
```

`site/src/pages/es/tiradas/3-cartas.astro` (text only until Task 11 puts the tool on it):

```astro
---
import TextPageView from '../../../views/TextPageView.astro';
---
<TextPageView lang="es" pageKey="three_cards" current="home" />
```

- [ ] **Step 6: Style of the text pages**

Append to `site/src/styles/global.css`:

```css

/* Stage 5 text: capsule, blocks, FAQ (stage 6) */
.capsule { margin: 0; font-size: var(--font-size-h-3); line-height: 1.45; max-width: 68ch; }
.prose { max-width: 72ch; }
.prose p { margin: 0; }
.h3 { margin: 0; font-family: var(--font-display); font-weight: 600; font-size: var(--font-size-h-3); line-height: 1.2; }
.faq details { max-width: 72ch; border-bottom: 1px solid var(--color-day-line); }
.faq summary { display: flex; align-items: center; min-height: 44px; padding: var(--space-3) 0; cursor: pointer; font-weight: 600; }
.faq details p { margin: 0 0 var(--space-4); }
.block-link { margin: 0; }
.block-link a { display: inline-flex; align-items: center; min-height: 44px; font-weight: 600; }
```

- [ ] **Step 7: Run the tests, the type check and the build**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && deploy/build-site.sh`
Expected: all tests pass, `0 errors`, build `Complete!`.

Run: `ls site/dist/cards.html site/dist/cards/major-arcana.html site/dist/yes-no/cards.html site/dist/es/cartas.html site/dist/es/cartas/arcanos-mayores.html site/dist/es/tiradas/3-cartas.html && grep -o '<h1[^>]*>[^<]*</h1>' site/dist/cards.html && grep -o 'aria-current="page">Card Meanings<' site/dist/cards.html | wc -l`
Expected: the six files listed; `<h1 class="display">Tarot card meanings: the whole deck, card by card</h1>`; `2`
(desktop and phone menu).

Run: `python3 tools/site/check_dist.py`
Expected: `OK: 177 pages`.

- [ ] **Step 8: Commit**

```bash
git add site/src/views/TextPageView.astro site/src/components/TextBlocks.astro site/src/components/Faq.astro site/src/pages site/src/lib/routes.ts site/src/lib/routes.test.ts site/src/components/Header.astro site/src/styles/global.css
git commit -m "site (stage 6): hubs, Major Arcana, yes/no card list and 3 cartas as stage 5 text pages; Card Meanings in the menu

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Sitemap, robots.txt and the checks of the built site

**Files:**
- Create: `site/src/lib/sitemap.ts`, `site/src/pages/sitemap.xml.ts`
- Modify: `site/public/robots.txt`, `tools/site/check_dist.py`, `deploy/build-site.sh`, `deploy/test-site-routes.sh`
- Test: `site/src/lib/sitemap.test.ts`, `tools/site/test_check_dist.py`

**Interfaces:**
- Consumes: `allPagePaths`, `PRIVATE_PAIRS` (routes.ts), `absoluteUrl`, `alternates` (seo.ts), `hiddenPaths`
  (textPages.ts).
- Produces:
  - `sitemap.ts`: `indexablePaths(): string[]`, `sitemapXml(paths: readonly string[]): string`; `site/dist/sitemap.xml`
  - `check_dist.py`: `SITE_URL`, `SERVICE_PAGE_IDS`, `canonical(path) -> str`, `expected_alternates(path) -> set[tuple[str, str]]`,
    `hidden_pages() -> set[str]`, `noindex_pages() -> set[str]`, `indexable_pages() -> list[str]`,
    `head_problems(dist)`, `placeholder_problems(dist)`, `sitemap_problems(dist)`, `robots_txt_problems(dist)`,
    `launched_problems() -> list[str]`, `main(dist=None, launched=False) -> int`; command line flag `--launched`
  - `deploy/build-site.sh` runs the data check before and `check_dist.py` after the build.

- [ ] **Step 1: Write the failing site test**

`site/src/lib/sitemap.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { indexablePaths, sitemapXml } from './sitemap';

describe('sitemap (spec stage 6 §3)', () => {
  it('lists the indexable pages: no diary, no account, no 404, no hidden service page', () => {
    const paths = indexablePaths();
    expect(paths).toHaveLength(177 - 4 - 2);
    expect(paths).toContain('/cards');
    expect(paths).toContain('/es/tiradas/3-cartas');
    for (const p of ['/diary', '/es/diario', '/account', '/es/cuenta', '/404', '/es/404', '/about']) {
      expect(paths).not.toContain(p);
    }
  });

  it('writes each address with its hreflang links when it has a mutual pair', () => {
    expect(sitemapXml(['/', '/one-card'])).toBe('<?xml version="1.0" encoding="UTF-8"?>\n'
      + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
      + '<url><loc>https://arcanadiary.com/</loc>'
      + '<xhtml:link rel="alternate" hreflang="en" href="https://arcanadiary.com/"/>'
      + '<xhtml:link rel="alternate" hreflang="es" href="https://arcanadiary.com/es"/>'
      + '<xhtml:link rel="alternate" hreflang="x-default" href="https://arcanadiary.com/"/></url>\n'
      + '<url><loc>https://arcanadiary.com/one-card</loc></url>\n'
      + '</urlset>\n');
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/sitemap.test.ts'`
Expected: FAIL — `./sitemap` does not resolve.

- [ ] **Step 3: Implement the sitemap**

`site/src/lib/sitemap.ts`:

```ts
// sitemap.xml by our own code at build time (spec stage 6 §3, no new packages): every indexable page with its
// xhtml:link hreflang alternates; the diary, the account, the 404 pages and the hidden service pages stay out.
import { PRIVATE_PAIRS, allPagePaths } from './routes';
import { absoluteUrl, alternates } from './seo';
import { hiddenPaths } from './textPages';

export function indexablePaths(): string[] {
  const hidden = hiddenPaths();
  return allPagePaths().filter((p) => !(p in PRIVATE_PAIRS) && !p.endsWith('/404') && !hidden.has(p));
}

const escape = (text: string) => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export function sitemapXml(paths: readonly string[]): string {
  const urls = paths.map((path) => {
    const links = alternates(path);
    const xhtml = links.length > 1
      ? links.map((a) => `<xhtml:link rel="alternate" hreflang="${a.hreflang}" href="${escape(a.href)}"/>`).join('') : '';
    return `<url><loc>${escape(absoluteUrl(path))}</loc>${xhtml}</url>`;
  });
  return '<?xml version="1.0" encoding="UTF-8"?>\n'
    + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    + `${urls.join('\n')}\n</urlset>\n`;
}
```

`site/src/pages/sitemap.xml.ts`:

```ts
// /sitemap.xml (spec stage 6 §3): written once at build time.
import { indexablePaths, sitemapXml } from '../lib/sitemap';

export function GET() {
  return new Response(sitemapXml(indexablePaths()), { headers: { 'content-type': 'application/xml; charset=utf-8' } });
}
```

Replace `site/public/robots.txt` with:

```
User-agent: *
Disallow:
Sitemap: https://arcanadiary.com/sitemap.xml
```

- [ ] **Step 4: Run the site test**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run'`
Expected: all pass.

- [ ] **Step 5: Write the failing checker tests**

Replace `tools/site/test_check_dist.py` with:

```python
"""tools/site/check_dist.py on small hand-made builds (spec 4.4b §5, §6, §11; stage 6 §8): every page exists, an
indexable page has its head and JSON-LD, no placeholder is left, private and hidden pages are noindex and out of the
sitemap, and the sign-in library is never loaded at start by a reading page."""
import check_dist
from check_dist import (EXTRA, READING_PAGES, auth_problems, canonical, dist_file, expected_alternates, expected_pages,
                        head_problems, hidden_pages, indexable_pages, launched_problems, noindex_pages,
                        placeholder_problems, robots_problems, robots_txt_problems, sitemap_problems, static_chunks)

ISLAND = '<astro-island component-url="/_astro/ReadingIsland.a1.js" renderer-url="/_astro/client.b2.js"></astro-island>'
NOINDEX = '<meta name="robots" content="noindex, nofollow">'
LD = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>'
ROBOTS_TXT = "User-agent: *\nDisallow:\nSitemap: https://arcanadiary.com/sitemap.xml\n"


def write(dist, name, text):
    file = dist / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def head(path):
    if path in noindex_pages():
        return NOINDEX
    if path in EXTRA:
        return "<title>Not found</title>"
    links = "".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in sorted(expected_alternates(path)))
    return (f'<title>Title</title><meta name="description" content="About this page">'
            f'<link rel="canonical" href="{canonical(path)}">{links}{LD}')


def sitemap(paths):
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset>'
            + "".join(f"<url><loc>{canonical(p)}</loc></url>" for p in paths) + "</urlset>")


def site(tmp_path, reading_island='import{x}from"./api.d4.js";'):
    dist = tmp_path / "dist"
    for path in expected_pages():
        write(dist, dist_file(path), head(path) + ISLAND)
    write(dist, "_astro/client.b2.js", 'import{h}from"./preact.c3.js";')
    write(dist, "_astro/preact.c3.js", "export const h=1;")
    write(dist, "_astro/ReadingIsland.a1.js", reading_island)
    write(dist, "_astro/api.d4.js", 'const l=()=>import("./supabaseClient.e5.js");export{l};')
    write(dist, "_astro/supabaseClient.e5.js", 'class GoTrueClient{};export{GoTrueClient as A};')
    write(dist, "data/daily-en.json", "[]")
    write(dist, "data/daily-es.json", "[]")
    write(dist, "sitemap.xml", sitemap(indexable_pages()))
    write(dist, "robots.txt", ROBOTS_TXT)
    return dist


def test_every_page_of_stage_6_part_1_is_expected():
    pages = expected_pages()
    assert len(pages) == 177
    assert {"/diary", "/es/diario", "/account", "/es/cuenta", "/cards", "/yes-no/cards", "/es/tiradas/3-cartas"} <= set(pages)


def test_hreflang_follows_mutual_pairs_only():
    assert expected_alternates("/yes-no") == {("en", "https://arcanadiary.com/yes-no"),
                                              ("es", "https://arcanadiary.com/es/si-o-no"),
                                              ("x-default", "https://arcanadiary.com/yes-no")}
    assert expected_alternates("/one-card") == {("en", "https://arcanadiary.com/one-card")}
    assert expected_alternates("/es/tiradas/3-cartas") == {("es", "https://arcanadiary.com/es/tiradas/3-cartas")}
    assert canonical("/") == "https://arcanadiary.com/"


def test_hidden_pages_are_the_service_pages_with_an_operator_placeholder():
    assert hidden_pages() == {"/about", "/contact", "/privacy", "/terms", "/es/sobre-nosotros", "/es/contacto",
                              "/es/privacidad", "/es/terminos"}


def test_only_the_private_and_hidden_pages_say_noindex(tmp_path):
    dist = site(tmp_path)
    assert robots_problems(dist) == []
    write(dist, "diary.html", ISLAND)
    write(dist, "yes-no.html", NOINDEX + ISLAND)
    assert robots_problems(dist) == ["no noindex meta: site/dist/diary.html", "unexpected noindex meta: site/dist/yes-no.html"]


def test_a_good_build_has_every_head_part(tmp_path):
    assert head_problems(site(tmp_path)) == []


def test_each_missing_or_wrong_head_part_is_named(tmp_path):
    dist = site(tmp_path)
    links = "".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in sorted(expected_alternates("/cards")))
    write(dist, "cards.html", '<title>T</title><link rel="canonical" href="https://arcanadiary.com/cards/">'
          + links + '<script type="application/ld+json">{oops</script>')
    write(dist, "love.html", "<title> </title>")
    assert head_problems(dist) == [
        "no description: site/dist/cards.html",
        "canonical https://arcanadiary.com/cards/ instead of https://arcanadiary.com/cards: site/dist/cards.html",
        "JSON-LD does not parse: site/dist/cards.html",
        "no title: site/dist/love.html",
        "no description: site/dist/love.html",
        "canonical None instead of https://arcanadiary.com/love: site/dist/love.html",
        "hreflang [] instead of [('en', 'https://arcanadiary.com/love'), ('es', 'https://arcanadiary.com/es/amor'), "
        "('x-default', 'https://arcanadiary.com/love')]: site/dist/love.html",
        "no JSON-LD: site/dist/love.html",
    ]


def test_a_placeholder_left_in_the_text_is_reported_but_not_one_inside_a_script(tmp_path):
    dist = site(tmp_path)
    assert placeholder_problems(dist) == []
    write(dist, "love.html", head("/love") + "<p>Draw {guest_limit} a day</p><script>const a = {x};</script>")
    assert placeholder_problems(dist) == ["placeholder {guest_limit} left: site/dist/love.html"]


def test_the_sitemap_lists_exactly_the_indexable_pages(tmp_path):
    dist = site(tmp_path)
    assert sitemap_problems(dist) == []
    write(dist, "sitemap.xml", sitemap([p for p in indexable_pages() if p != "/cards"] + ["/diary"]))
    assert sitemap_problems(dist) == ["sitemap.xml lacks https://arcanadiary.com/cards",
                                      "sitemap.xml lists https://arcanadiary.com/diary, not an indexable page"]


def test_robots_txt_names_the_sitemap(tmp_path):
    dist = site(tmp_path)
    assert robots_txt_problems(dist) == []
    write(dist, "robots.txt", "User-agent: *\nDisallow:\n")
    assert robots_txt_problems(dist) == ["robots.txt does not name the sitemap"]


def test_the_open_site_refuses_a_hidden_page(monkeypatch):
    monkeypatch.setattr(check_dist, "expected_pages", lambda: ["/", "/about"])
    assert launched_problems() == ["hidden page on the open site: /about (an operator placeholder has no value)"]


def test_a_dynamic_import_of_the_library_is_fine(tmp_path):
    dist = site(tmp_path)
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
    out = capsys.readouterr().out
    assert "missing: site/dist/diary.html" in out and "missing: site/dist/sitemap.xml" in out
    assert check_dist.main(site(tmp_path)) == 0
    assert capsys.readouterr().out == "OK: 177 pages\n"
```

- [ ] **Step 6: Run them to see them fail**

Run: `api/.venv/bin/pytest -q tools/site/test_check_dist.py`
Expected: FAIL — `ImportError: cannot import name 'canonical' from 'check_dist'`.

- [ ] **Step 7: Implement the checker**

Replace `tools/site/check_dist.py` with:

```python
"""After the site build (spec 4.4a §3, 4.4b §5–§6, stage 6 §8): every page exists in site/dist for EN and ES; each
indexable page has a title, a description, its canonical address, hreflang by its language pair (en, es and
x-default only for a mutual pair) and JSON-LD that parses; no page that is not hidden shows a {placeholder}; the
diary, the account and the hidden service pages say noindex and stay out of sitemap.xml, which lists every indexable
page; robots.txt names the sitemap; no page that draws a reading loads the sign-in library at start (spec 4.4b §3).

The pages are the language pairs of site/src/data/pairs.json, the two 404 pages and the four private pages; Astro
writes one file per page (build.format "file"): / → index.html, /es → es.html, /cards/x → cards/x.html. A service
page is hidden while its text has a placeholder without a value in site/src/data/facts.json (owner decision 35; the
same rule as site/src/lib/textPages.ts).

  python3 tools/site/check_dist.py             — prints "OK: N pages" or the problems (exit 1)
  python3 tools/site/check_dist.py --launched  — the same for the open site: a hidden page is a problem too
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
SITE_URL = "https://arcanadiary.com"
EXTRA = ("/404", "/es/404")
PRIVATE = ("/diary", "/es/diario", "/account", "/es/cuenta")  # noindex, outside hreflang.csv
DATA_FILES = ("data/daily-en.json", "data/daily-es.json", "sitemap.xml", "robots.txt")
# = SERVICE_PAGE_IDS of site/src/lib/textPages.ts
SERVICE_PAGE_IDS = frozenset({"about", "contact", "how-readings-work", "privacy", "terms", "sobre-nosotros", "contacto",
                              "como-funcionan-las-lecturas", "privacidad", "terminos"})
# the pages with a night room or the Card of the Day: a guest there never downloads the sign-in library
READING_PAGES = ("/", "/one-card", "/yes-no", "/love", "/daily", "/cards/the-moon", "/es", "/es/si-o-no", "/es/amor",
                 "/es/carta-del-dia", "/es/cartas/la-luna")
AUTH_MARKERS = ("GoTrueClient", "supabase.auth.token")  # strings found only in @supabase/auth-js
ROBOTS = re.compile(r'<meta name="robots" content="noindex, nofollow"\s*/?>')
ENTRY = re.compile(r'(?:component-url|renderer-url|src)="(/_astro/[^"]+\.js)"')
# static imports and re-exports only: import("…") (a chunk loaded later) is not followed
STATIC_IMPORT = re.compile(r'\b(?:import|export)\s*(?:[\w$*\s{},]*?\bfrom\s*)?["\'](\.{1,2}/[^"\']+|/_astro/[^"\']+)["\']')
PLACEHOLDER = re.compile(r"\{(\w+)\}")
LEFT_PLACEHOLDER = re.compile(r"\{[A-Za-z_]+\}")
SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)


def pairs() -> dict[str, str]:
    return json.loads((SITE / "src/data/pairs.json").read_text(encoding="utf-8"))


def expected_pages() -> list[str]:
    return sorted(set(pairs()) | set(EXTRA) | set(PRIVATE))


def dist_file(path: str) -> str:
    return "index.html" if path == "/" else f"{path[1:]}.html"


def canonical(path: str) -> str:
    return f"{SITE_URL}/" if path == "/" else f"{SITE_URL}{path}"


def lang_of(path: str) -> str:
    return "es" if path == "/es" or path.startswith("/es/") else "en"


def expected_alternates(path: str) -> set[tuple[str, str]]:
    table = pairs()
    pair = table.get(path)
    if pair is None or table.get(pair) != path:
        return {(lang_of(path), canonical(path))}
    en, es = (path, pair) if lang_of(path) == "en" else (pair, path)
    return {("en", canonical(en)), ("es", canonical(es)), ("x-default", canonical(en))}


def page_texts(page: dict) -> list[str]:
    return [page["title"], page["description"], page["h1"], page["lead"], page["capsule"] or "",
            *[t for b in page["blocks"] for t in (b["heading"], *b["paragraphs"])],
            *[t for f in page["faq"] for t in (f["q"], f["a"])]]


def hidden_pages() -> set[str]:
    known = set(json.loads((SITE / "src/data/facts.json").read_text(encoding="utf-8")))
    hidden = set()
    for file in sorted((SITE / "src/data/pages").glob("*/*.json")):
        page = json.loads(file.read_text(encoding="utf-8"))
        names = {name for text in page_texts(page) for name in PLACEHOLDER.findall(text)}
        if page["page_id"] in SERVICE_PAGE_IDS and names - known:
            hidden.add(page["url"])
    return hidden


def noindex_pages() -> set[str]:
    return set(PRIVATE) | hidden_pages()


def indexable_pages() -> list[str]:
    noindex = noindex_pages()
    return [p for p in expected_pages() if p not in EXTRA and p not in noindex]


def missing(dist: Path) -> list[str]:
    files = [dist_file(p) for p in expected_pages()] + list(DATA_FILES)
    return [f for f in files if not (dist / f).is_file()]


def robots_problems(dist: Path) -> list[str]:
    """The private and the hidden pages carry the noindex meta; no other page does."""
    problems = []
    noindex = noindex_pages()
    for path in expected_pages():
        file = dist / dist_file(path)
        if not file.is_file():
            continue  # missing() reports it
        has = bool(ROBOTS.search(file.read_text(encoding="utf-8")))
        if has != (path in noindex):
            problems.append(f"{'no' if path in noindex else 'unexpected'} noindex meta: site/dist/{dist_file(path)}")
    return problems


class Head(HTMLParser):
    """Title, description, canonical, hreflang links and JSON-LD texts of a page."""

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description: str | None = None
        self.canonical: str | None = None
        self.alternates: set[tuple[str, str]] = set()
        self.ld: list[str] = []
        self._in_title = False
        self._ld: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name") == "description":
            self.description = a.get("content") or ""
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        elif tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
            self.alternates.add((a["hreflang"], a.get("href") or ""))
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._ld = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._ld is not None:
            self.ld.append("".join(self._ld))
            self._ld = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._ld is not None:
            self._ld.append(data)


def head_problems(dist: Path) -> list[str]:
    problems = []
    for path in indexable_pages():
        file = dist / dist_file(path)
        if not file.is_file():
            continue
        head = Head()
        head.feed(file.read_text(encoding="utf-8"))
        name = f"site/dist/{dist_file(path)}"
        want = expected_alternates(path)
        if not head.title.strip():
            problems.append(f"no title: {name}")
        if not (head.description or "").strip():
            problems.append(f"no description: {name}")
        if head.canonical != canonical(path):
            problems.append(f"canonical {head.canonical} instead of {canonical(path)}: {name}")
        if head.alternates != want:
            problems.append(f"hreflang {sorted(head.alternates)} instead of {sorted(want)}: {name}")
        if not head.ld:
            problems.append(f"no JSON-LD: {name}")
        for text in head.ld:
            try:
                json.loads(text)
            except ValueError:
                problems.append(f"JSON-LD does not parse: {name}")
    return problems


def placeholder_problems(dist: Path) -> list[str]:
    """A {placeholder} left in the text of a page that is not hidden (scripts and styles are not text)."""
    problems = []
    hidden = hidden_pages()
    for path in expected_pages():
        file = dist / dist_file(path)
        if path in hidden or not file.is_file():
            continue
        text = SCRIPT_STYLE.sub("", file.read_text(encoding="utf-8"))
        problems += [f"placeholder {mark} left: site/dist/{dist_file(path)}" for mark in sorted(set(LEFT_PLACEHOLDER.findall(text)))]
    return problems


def sitemap_problems(dist: Path) -> list[str]:
    file = dist / "sitemap.xml"
    if not file.is_file():
        return []  # missing() reports it
    locs = set(re.findall(r"<loc>([^<]+)</loc>", file.read_text(encoding="utf-8")))
    want = {canonical(p) for p in indexable_pages()}
    return ([f"sitemap.xml lacks {url}" for url in sorted(want - locs)]
            + [f"sitemap.xml lists {url}, not an indexable page" for url in sorted(locs - want)])


def robots_txt_problems(dist: Path) -> list[str]:
    file = dist / "robots.txt"
    if file.is_file() and f"Sitemap: {SITE_URL}/sitemap.xml" not in file.read_text(encoding="utf-8").splitlines():
        return ["robots.txt does not name the sitemap"]
    return []


def launched_problems() -> list[str]:
    return [f"hidden page on the open site: {path} (an operator placeholder has no value)"
            for path in sorted(hidden_pages() & set(expected_pages()))]


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


def main(dist: Path | None = None, launched: bool = False) -> int:
    dist = dist or SITE / "dist"
    problems = ([f"missing: site/dist/{name}" for name in missing(dist)] + robots_problems(dist) + head_problems(dist)
                + placeholder_problems(dist) + sitemap_problems(dist) + robots_txt_problems(dist) + auth_problems(dist)
                + (launched_problems() if launched else []))
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"OK: {len(expected_pages())} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main(launched="--launched" in sys.argv[1:]))
```

- [ ] **Step 8: Run the checker tests**

Run: `api/.venv/bin/pytest -q tools/site`
Expected: all passed.

- [ ] **Step 9: Make the build check itself**

Replace `deploy/build-site.sh` with:

```bash
#!/usr/bin/env bash
# Собирает site/dist в контейнере node:22; Node на хост не ставится. До сборки — данные сайта совпадают с
# источниками (tools/site/sync_site_data.py --check: тексты, факты из api/app/config.py), после — проверка
# собранного сайта (tools/site/check_dist.py: страницы, head, JSON-LD, метки, sitemap.xml, robots.txt).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/tools/site/sync_site_data.py" --check
docker run --rm -u "$(id -u):$(id -g)" \
  -e npm_config_cache=/tmp/.npm -e ASTRO_TELEMETRY_DISABLED=1 \
  -v "$ROOT/site:/app" -w /app node:22 \
  sh -c 'if [ -f package-lock.json ]; then npm ci; else npm install; fi && npm run build'
python3 "$ROOT/tools/site/check_dist.py"
```

- [ ] **Step 10: Test the new addresses and the file/folder pairs on Caddy**

In `deploy/test-site-routes.sh`, after the line `expect "/es — испанская главная" "$(html_lang /es)" '<html lang="es"'` insert:

```bash
# stage 6: новые адреса, sitemap.xml и robots.txt
for path in /cards /cards/major-arcana /yes-no/cards /es/cartas /es/cartas/arcanos-mayores /es/tiradas/3-cartas \
  /sitemap.xml /robots.txt; do
  expect "$path" "$(status "$path")" 200
done
canonical() { "${CURL[@]}" "$URL$1" | grep -o '<link rel="canonical" href="[^"]*"' | head -1 | sed 's/.*href="\([^"]*\)"/\1/'; }
# файл и папка с одним именем (cards.html и cards/, yes-no.html и yes-no/, es/cartas.html и es/cartas/): Caddy
# отдаёт файл, адреса внутри папки — свои страницы, слэш в конце уводит на адрес без слэша
expect "/cards — хаб, не папка" "$(canonical /cards)" "https://arcanadiary.com/cards"
expect "/cards/the-moon — страница карты" "$(canonical /cards/the-moon)" "https://arcanadiary.com/cards/the-moon"
expect "/cards/major-arcana — старшие арканы" "$(canonical /cards/major-arcana)" "https://arcanadiary.com/cards/major-arcana"
expect "/yes-no — инструмент" "$(canonical /yes-no)" "https://arcanadiary.com/yes-no"
expect "/yes-no/cards — справочник" "$(canonical /yes-no/cards)" "https://arcanadiary.com/yes-no/cards"
expect "/es/cartas — хаб ES" "$(canonical /es/cartas)" "https://arcanadiary.com/es/cartas"
expect "/es/cartas/la-luna — карта ES" "$(canonical /es/cartas/la-luna)" "https://arcanadiary.com/es/cartas/la-luna"
expect "/cards/ → /cards" "$(moved_to /cards/)" "308 $URL/cards"
expect "/yes-no/cards/ → /yes-no/cards" "$(moved_to /yes-no/cards/)" "308 $URL/yes-no/cards"
expect "/es/cartas/ → /es/cartas" "$(moved_to /es/cartas/)" "308 $URL/es/cartas"
expect "/es/tiradas/3-cartas.html → без .html" "$(moved_to /es/tiradas/3-cartas.html)" "308 $URL/es/tiradas/3-cartas"
# папка без своей страницы — 404 на своём языке, без перенаправления
expect "/es/tiradas — только папка" "$(status /es/tiradas)" 404
expect "/es/tiradas — страница 404 ES" "$(html_lang /es/tiradas)" '<html lang="es"'
expect "robots.txt называет sitemap" "$("${CURL[@]}" "$URL/robots.txt" | grep -c '^Sitemap: https://arcanadiary.com/sitemap.xml$')" 1
expect "sitemap.xml без дневника" "$("${CURL[@]}" "$URL/sitemap.xml" | grep -c '/diary<')" 0
```

- [ ] **Step 11: Build and run every check**

Run: `deploy/build-site.sh && deploy/test-site-routes.sh`
Expected: the build ends with `OK: 177 pages`; the route test ends with `OK: адреса страниц и 404`.

- [ ] **Step 12: Commit**

```bash
git add site/src/lib/sitemap.ts site/src/lib/sitemap.test.ts site/src/pages/sitemap.xml.ts site/public/robots.txt tools/site/check_dist.py tools/site/test_check_dist.py deploy/build-site.sh deploy/test-site-routes.sh
git commit -m "site (stage 6): sitemap.xml by our own code, robots.txt Sitemap line, head/JSON-LD/placeholder/sitemap checks of the build, file/folder route tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Deploy checkpoint — Part 1

Stop here. Before asking the owner: all site tests, `api/.venv/bin/pytest -q tools/site`, `deploy/build-site.sh`
(`OK: 177 pages`) and `deploy/test-site-routes.sh` pass; the branch review (Sonnet) has no open blocking finding.
Check the desktop header at 900 px: six menu items and EN | ES must fit on one line (if they do not, change the gap of
`.site-header__desktop ul` from `var(--space-5)` to `var(--space-4)` and commit). Tell the owner what to look at on
the stage: the menu item "Card Meanings", the six new text pages with breadcrumbs,
`/sitemap.xml`, and the page source of `/yes-no` (canonical, hreflang, JSON-LD). The owner deploys with
`deploy/deploy.sh` himself or gives the word; the agent never runs it.

---

# Part 2 — The card page (78 × 2)

Ends deployable: all 156 card pages use the stage 5 text in the CardMoon / DeskCard layout; `CardView.astro` is gone.

### Task 8: What the card template adds to the text

**Files:**
- Create: `site/src/lib/cardPage.ts`
- Modify: `site/src/lib/deck.ts` (`yes_no` on `DeckCard`), `site/src/lib/routes.ts` (suits), `site/src/i18n/en.ts`,
  `site/src/i18n/es.ts`
- Test: `site/src/lib/cardPage.test.ts`, `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `CardPageData`, `TemplateStrings`, `CARD_PAGES`, `TEMPLATE_STRINGS`, `cardPage` (Task 2); `cardById`,
  `cardName`, `DeckCard` (deck.ts); `cardPath`, `pagePath` (routes.ts); `fill`, `t` (i18n); `Lang`, `Vote` (types.ts).
- Produces:
  - `deck.ts`: `DeckCard.yes_no: Vote`
  - `routes.ts`: `type Suit = 'wands' | 'cups' | 'swords' | 'pentacles'`, `SUIT_IDS: Record<Lang, Record<Suit, string>>`
    (EN `wands`…, ES `bastos`, `copas`, `espadas`, `oros`), `suitPath(suit: Suit, lang: Lang): string` (`/cards#swords`)
  - `cardPage.ts`: `type Segment = string | { text: string; href: string }`,
    `interface LinkSlot { before: string; link: { text: string; href: string } | null; after: string }`,
    `SECTION_IDS: Record<Lang, Record<CardBlockId | 'draw' | 'faq' | 'related' | 'about', string>>`,
    `formatPages(pages, s): string`, `formatDate(iso, lang): string`, `factsLine(page, s, lang): LinkSlot`,
    `imageCaption(page, s): string`, `keywordCaption(page, s): string`, `keywordRows(page): [string, string][]`,
    `waiteCite(page, s): string`, `yesNoReason(card, lang): string`,
    `yesNoLines(card, reason, s, lang): { upright: string; reversed: string; rule: string }`,
    `interface PairRow extends LinkSlot { reading: string }`, `pairRows(page, s, lang): PairRow[]`,
    `mentionSegments(page, lang): Map<string, Segment[]>` (keys `capsule`, `<blockId>:<j>`, `faq:<i>`),
    `segmentsOf(map, key, text): Segment[]`, `ctaText(page, s): { heading: string; text: string }`,
    `faqHeading(page, s): string`, `relatedCards(page): DeckCard[]`,
    `tocLinks(lang): { href: string; label: string }[]`,
    `aboutLines(page, s, lang, editorName): { sources: { what; where; pages: string | null; url: string | null }[];
    pageNumbers; method; deckNote }`
  - dictionary keys: `tocLabel`, `tocUpright`, `tocReversed`, `tocLove`, `tocWorkMoney`, `tocYesNo`, `tocFaq` (239)

- [ ] **Step 1: Write the failing tests**

`site/src/lib/cardPage.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  SECTION_IDS, aboutLines, ctaText, factsLine, faqHeading, formatDate, formatPages, imageCaption, keywordCaption,
  keywordRows, mentionSegments, pairRows, relatedCards, segmentsOf, tocLinks, waiteCite, yesNoLines, yesNoReason,
} from './cardPage';
import { CARD_PAGES, TEMPLATE_STRINGS, cardPage } from './cardPages';
import { cardById } from './deck';

const EN = TEMPLATE_STRINGS.en;
const ES = TEMPLATE_STRINGS.es;
const moon = cardById('major-18-moon')!;
const swords3 = cardById('swords-03-three')!;
const lovers = cardById('major-06-lovers')!;
const fool = cardById('major-00-fool')!;

describe('the card template (spec stage 6 §4, rules §12)', () => {
  it('writes the facts line, linking the suit of a minor card to its block on the hub', () => {
    expect(factsLine(cardPage(moon, 'en'), EN, 'en')).toEqual({ before: 'Major Arcana · card XVIII', link: null, after: '' });
    expect(factsLine(cardPage(swords3, 'en'), EN, 'en')).toEqual({ before: 'Minor Arcana · ',
      link: { text: 'Swords', href: '/cards#swords' }, after: ' · Three' });
    expect(factsLine(cardPage(swords3, 'es'), ES, 'es')).toEqual({ before: 'Arcanos menores · ',
      link: { text: 'Espadas', href: '/es/cartas#espadas' }, after: ' · Tres' });
    expect(factsLine(cardPage(lovers, 'es'), ES, 'es').after).toBe(' · Los Amantes'); // facts.also_called
  });

  it('captions the scan and the keyword table and pairs the keyword columns', () => {
    expect(imageCaption(cardPage(moon, 'en'), EN)).toBe('The Moon, 1909 Rider–Waite–Smith deck ("Roses & Lilies" '
      + 'printing), drawn by Pamela Colman Smith. Public-domain scan, Wikimedia Commons.');
    expect(keywordCaption(cardPage(moon, 'es'), ES)).toBe('La Luna: palabras clave');
    expect(keywordRows(cardPage(moon, 'en'))).toEqual([['uncertainty', 'confusion lifting'], ['intuition', 'worry'],
      ['dreams', 'clearer sight'], ['hidden feelings', '']]);
  });

  it('cites Waite with the page list of the edition', () => {
    expect(formatPages([286], EN)).toBe('p. 286');
    expect(formatPages([140, 143], ES)).toBe('pp. 140, 143');
    expect(waiteCite(cardPage(moon, 'en'), EN)).toBe('A. E. Waite, The Pictorial Key to the Tarot (1911), p. 286');
  });

  it('builds the yes/no lines from the deck verdict and the reason of the card base', () => {
    expect(yesNoLines(moon, yesNoReason(moon, 'en'), EN, 'en')).toEqual({
      upright: "Upright: Not clear yet. Under the Moon's light the path is only half visible, and shapes are hard to read.",
      reversed: 'Reversed: Not clear yet.', rule: EN.yes_no.rule });
    expect(yesNoLines(swords3, yesNoReason(swords3, 'en'), EN, 'en').upright)
      .toBe('Upright: No. Three swords pierce the heart under a rainy sky, a picture of hurt rather than ease.');
    expect(yesNoLines(moon, yesNoReason(moon, 'es'), ES, 'es').reversed).toBe('Al revés: Todavía no está claro.');
  });

  it('names both cards of a pair and links the other one', () => {
    expect(pairRows(cardPage(moon, 'en'), EN, 'en')[0]).toEqual({ before: 'The Moon + ',
      link: { text: 'The Sun', href: '/cards/the-sun' }, after: '',
      reading: 'Uncertainty giving way to clarity. Wait for daylight before you decide.' });
    expect(pairRows(cardPage(moon, 'es'), ES, 'es')[0].link).toEqual({ text: 'El Sol', href: '/es/cartas/el-sol' });
  });

  it('links the first mention of another card, in the blocks or in the FAQ answers', () => {
    const segments = mentionSegments(cardPage(moon, 'en'), 'en').get('not_to_confuse:0')!;
    expect(segments[1]).toEqual({ text: 'High Priestess', href: '/cards/the-high-priestess' });
    expect((segments[0] as string).endsWith("In Waite's description of the ")).toBe(true);
    const foolFaq = mentionSegments(cardPage(fool, 'en'), 'en').get('faq:3')!;
    expect(foolFaq).toContainEqual({ text: 'The Magician', href: '/cards/the-magician' });
    expect(segmentsOf(new Map(), 'capsule', 'plain')).toEqual(['plain']);
  });

  it('finds every mention and every pair of all 156 pages, each page reviewed with a date', () => {
    for (const page of CARD_PAGES) {
      const s = TEMPLATE_STRINGS[page.lang];
      const links = [...mentionSegments(page, page.lang).values()].flat().filter((seg) => typeof seg !== 'string');
      expect(links, `${page.lang}/${page.card_id}`).toHaveLength(page.mentions.length);
      expect(pairRows(page, s, page.lang).length).toBeGreaterThanOrEqual(3);
      expect(relatedCards(page).length).toBe(page.related.length);
      expect(page.reviewed_at).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });

  it('heads the CTA and the FAQ with the name in the sentence', () => {
    expect(ctaText(cardPage(swords3, 'en'), EN).heading).toBe('Draw the Three of Swords for your question');
    expect(ctaText(cardPage(moon, 'es'), ES).heading).toBe('¿Qué dice La Luna de tu pregunta?');
    expect(faqHeading(cardPage(moon, 'en'), EN)).toBe('Questions about The Moon');
  });

  it('signs the page with the editor and the date of the review', () => {
    expect(formatDate('2026-11-23', 'en')).toBe('November 23, 2026');
    expect(formatDate('2026-11-23', 'es')).toBe('23 de noviembre de 2026');
    const about = aboutLines(cardPage(moon, 'en'), EN, 'en', 'Adrian Solenne');
    expect(about.method).toBe("Written with AI from Waite's book and Arcana Diary's card meanings. Reviewed by "
      + 'Adrian Solenne on November 23, 2026.');
    expect(about.sources[1]).toEqual({ what: 'Description of the picture, traditional meanings and quotes',
      where: 'A. E. Waite, The Pictorial Key to the Tarot (1911)', pages: 'pp. 27, 76, 140, 143, 286',
      url: 'https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot' });
    expect(about.sources[2].url).toBeNull();
  });

  it('gives the sections the anchors of the page maps (EN #reversed; ES #invertida, #amor, #si-o-no)', () => {
    expect([SECTION_IDS.en.reversed, SECTION_IDS.en.love]).toEqual(['reversed', 'love']);
    expect([SECTION_IDS.es.reversed, SECTION_IDS.es.love, SECTION_IDS.es.yes_no]).toEqual(['invertida', 'amor', 'si-o-no']);
    expect(tocLinks('es')).toEqual([{ href: '#al-derecho', label: 'Al derecho' }, { href: '#invertida', label: 'Al revés' },
      { href: '#amor', label: 'Amor' }, { href: '#trabajo-y-dinero', label: 'Trabajo y dinero' },
      { href: '#si-o-no', label: 'Sí o no' }, { href: '#preguntas', label: 'Preguntas' }]);
  });
});
```

In `site/src/i18n/i18n.test.ts` change `toBe(232)` to `toBe(239)`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/cardPage.test.ts src/i18n/i18n.test.ts'`
Expected: FAIL — `./cardPage` does not resolve; 232 keys instead of 239.

- [ ] **Step 3: Implement**

In `site/src/lib/deck.ts` change the import line to `import type { Lang, Vote } from './types';` and add to
`interface DeckCard` after `suit: string | null;`:

```ts
  yes_no: Vote; // base yes/no verdict of the card upright (content/cards/deck.json)
```

In `site/src/lib/routes.ts` add after `cardPath()`:

```ts
export type Suit = 'wands' | 'cups' | 'swords' | 'pentacles';

/** The suit blocks of the hub (/cards#wands, /es/cartas#bastos): links L-EN-10, L-ES-10 of the stage 2 matrix. */
export const SUIT_IDS: Readonly<Record<Lang, Readonly<Record<Suit, string>>>> = {
  en: { wands: 'wands', cups: 'cups', swords: 'swords', pentacles: 'pentacles' },
  es: { wands: 'bastos', cups: 'copas', swords: 'espadas', pentacles: 'oros' },
};

export function suitPath(suit: Suit, lang: Lang): string {
  return `${pagePath('cards', lang)}#${SUIT_IDS[lang][suit]}`;
}
```

`site/src/lib/cardPage.ts`:

```ts
// What the card template adds to the stage 5 text (spec stage 6 §4, rules 30-card-page-rules.md §12): the facts
// line, the captions, the keyword rows, the Waite citation, the yes/no lines from the deck, the pairs, links on the
// first mention of another card, the CTA and FAQ headings and the "About this page" lines. Strings come only from
// template-strings.json and the dictionaries.
import { fill, t, type DictKey } from '../i18n';
import meaningsEn from '../data/meanings.en.json';
import meaningsEs from '../data/meanings.es.json';
import type { CardBlockId, CardPageData, TemplateStrings } from './cardPages';
import { cardById, cardName, type DeckCard } from './deck';
import { cardPath, suitPath } from './routes';
import type { Lang, Vote } from './types';

export type Segment = string | { text: string; href: string };

export interface LinkSlot {
  before: string;
  link: { text: string; href: string } | null;
  after: string;
}

export interface PairRow extends LinkSlot {
  reading: string;
}

type SectionKey = CardBlockId | 'draw' | 'faq' | 'related' | 'about';

/** Section anchors; EN #reversed, ES #invertida, #amor, #si-o-no are rows EN-095, ES-092…094 of the page maps. */
export const SECTION_IDS: Readonly<Record<Lang, Readonly<Record<SectionKey, string>>>> = {
  en: {
    on_the_card: 'on-the-card', waite: 'waite', upright: 'upright', reversed: 'reversed', love: 'love',
    work_money: 'work-and-money', advice: 'advice', yes_no: 'yes-or-no', in_a_reading: 'as-a-person',
    combinations: 'combinations', not_to_confuse: 'not-to-confuse', ask_yourself: 'ask-yourself',
    draw: 'draw', faq: 'faq', related: 'related', about: 'about',
  },
  es: {
    on_the_card: 'en-la-carta', waite: 'waite', upright: 'al-derecho', reversed: 'invertida', love: 'amor',
    work_money: 'trabajo-y-dinero', advice: 'consejo', yes_no: 'si-o-no', in_a_reading: 'como-persona',
    combinations: 'combinaciones', not_to_confuse: 'no-confundir', ask_yourself: 'preguntas-para-ti',
    draw: 'tu-pregunta', faq: 'preguntas', related: 'relacionadas', about: 'sobre-esta-pagina',
  },
};

const TOC: readonly [SectionKey, DictKey][] = [['upright', 'tocUpright'], ['reversed', 'tocReversed'], ['love', 'tocLove'],
  ['work_money', 'tocWorkMoney'], ['yes_no', 'tocYesNo'], ['faq', 'tocFaq']];

const VOTE_KEYS: Readonly<Record<Vote, DictKey>> = { yes: 'voteYes', no: 'voteNo', unclear: 'voteUnclear' };

const REASONS: Readonly<Record<Lang, ReadonlyMap<string, string>>> = {
  en: new Map(meaningsEn.map((m) => [m.card_id, m.yes_no_why])),
  es: new Map(meaningsEs.map((m) => [m.card_id, m.yes_no_why])),
};

const names = (page: CardPageData) => ({ Card: page.name_forms.name, card: page.name_forms.in_sentence });

/** The parts of a template around one placeholder, each filled with the other values. */
function around(template: string, key: string, vars: Readonly<Record<string, string>>): [string, string] {
  const [before, after = ''] = template.split(`{${key}}`);
  return [fill(before, vars), fill(after, vars)];
}

function card(cardId: string, page: CardPageData): DeckCard {
  const found = cardById(cardId);
  if (!found) throw new Error(`${page.lang}/${page.card_id}: unknown card ${cardId}`);
  return found;
}

export function formatPages(pages: readonly number[], s: TemplateStrings): string {
  return fill(pages.length === 1 ? s.about.page_one : s.about.page_many, { pages: pages.join(', ') });
}

export function formatDate(iso: string, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-US' : 'es-MX', { dateStyle: 'long', timeZone: 'UTC' })
    .format(new Date(`${iso}T00:00:00Z`));
}

export function factsLine(page: CardPageData, s: TemplateStrings, lang: Lang): LinkSlot {
  const alsoCalled = page.facts.also_called.map((name) => ` · ${name}`).join('');
  if (page.facts.arcana === 'major' || page.facts.suit === null) {
    return { before: fill(s.facts.major, { numeral: page.facts.numeral ?? '' }), link: null, after: alsoCalled };
  }
  const [before, after] = around(s.facts.minor, 'suit', { rank: s.facts.ranks[String(page.facts.number)] });
  return { before, link: { text: s.facts.suits[page.facts.suit], href: suitPath(page.facts.suit, lang) },
    after: after + alsoCalled };
}

export function imageCaption(page: CardPageData, s: TemplateStrings): string {
  return fill(s.image_caption, names(page));
}

export function keywordCaption(page: CardPageData, s: TemplateStrings): string {
  return fill(s.keywords.caption, names(page));
}

export function keywordRows(page: CardPageData): [string, string][] {
  const { upright, reversed } = page.keywords;
  return Array.from({ length: Math.max(upright.length, reversed.length) }, (_, i) => [upright[i] ?? '', reversed[i] ?? '']);
}

export function waiteCite(page: CardPageData, s: TemplateStrings): string {
  return fill(s.waite.cite, { pages: formatPages(page.waite.pages, s) });
}

export function yesNoReason(c: DeckCard, lang: Lang): string {
  return REASONS[lang].get(c.card_id) ?? '';
}

/** Upright: the base verdict and its reason; reversed: always "Not clear yet" (yes-no-rules.json reversed_shift). */
export function yesNoLines(c: DeckCard, reason: string, s: TemplateStrings, lang: Lang) {
  const d = t(lang);
  return {
    upright: fill(s.yes_no.upright, { label: d[VOTE_KEYS[c.yes_no]], reason }),
    reversed: fill(s.yes_no.reversed, { label_reversed: d.voteUnclear }),
    rule: s.yes_no.rule,
  };
}

export function pairRows(page: CardPageData, s: TemplateStrings, lang: Lang): PairRow[] {
  const pairs = page.blocks.find((b) => b.id === 'combinations')?.pairs ?? [];
  return pairs.map((pair) => {
    const other = card(pair.card_id, page);
    const [before, after] = around(s.combinations.pair, 'Other', names(page));
    return { before, link: { text: cardName(other, lang), href: cardPath(other, lang) }, after, reading: pair.text };
  });
}

/** The page's running texts in reading order: capsule, block paragraphs, FAQ answers. */
function runningTexts(page: CardPageData): [string, string][] {
  return [
    ['capsule', page.capsule],
    ...page.blocks.flatMap((b) => (b.paragraphs ?? []).map((p, j): [string, string] => [`${b.id}:${j}`, p])),
    ...page.faq.map((f, i): [string, string] => [`faq:${i}`, f.a]),
  ];
}

/** `mentions`: the first place each mention's text appears (and is not taken by another mention) becomes a link. */
export function mentionSegments(page: CardPageData, lang: Lang): Map<string, Segment[]> {
  const texts = runningTexts(page);
  const claimed = new Map<string, { start: number; end: number; href: string }[]>();
  for (const mention of page.mentions) {
    const href = cardPath(card(mention.card_id, page), lang);
    let placed = false;
    for (const [key, text] of texts) {
      const taken = claimed.get(key) ?? [];
      for (let at = text.indexOf(mention.text); at >= 0 && !placed; at = text.indexOf(mention.text, at + 1)) {
        const end = at + mention.text.length;
        if (taken.every((r) => end <= r.start || at >= r.end)) {
          claimed.set(key, [...taken, { start: at, end, href }]);
          placed = true;
        }
      }
      if (placed) break;
    }
    if (!placed) throw new Error(`${page.lang}/${page.card_id}: mention "${mention.text}" is not in the text`);
  }
  const out = new Map<string, Segment[]>();
  for (const [key, text] of texts) {
    const ranges = [...(claimed.get(key) ?? [])].sort((a, b) => a.start - b.start);
    if (ranges.length === 0) continue;
    const segments: Segment[] = [];
    let at = 0;
    for (const r of ranges) {
      if (r.start > at) segments.push(text.slice(at, r.start));
      segments.push({ text: text.slice(r.start, r.end), href: r.href });
      at = r.end;
    }
    if (at < text.length) segments.push(text.slice(at));
    out.set(key, segments);
  }
  return out;
}

export function segmentsOf(map: ReadonlyMap<string, Segment[]>, key: string, text: string): Segment[] {
  return map.get(key) ?? [text];
}

export function ctaText(page: CardPageData, s: TemplateStrings): { heading: string; text: string } {
  return { heading: fill(s.cta.heading, names(page)), text: fill(s.cta.text, names(page)) };
}

export function faqHeading(page: CardPageData, s: TemplateStrings): string {
  return fill(s.faq.heading, names(page));
}

export function relatedCards(page: CardPageData): DeckCard[] {
  return page.related.map((id) => card(id, page));
}

export function tocLinks(lang: Lang): { href: string; label: string }[] {
  const d = t(lang);
  return TOC.map(([key, label]) => ({ href: `#${SECTION_IDS[lang][key]}`, label: d[label] }));
}

export function aboutLines(page: CardPageData, s: TemplateStrings, lang: Lang, editorName: string) {
  if (!page.reviewed_at) throw new Error(`${page.lang}/${page.card_id}: not reviewed`);
  return {
    sources: page.sources.map((src) => ({ what: src.what, where: src.where,
      pages: src.pages ? formatPages(src.pages, s) : null, url: src.url })),
    pageNumbers: s.about.page_numbers,
    method: fill(s.about.method, { editor_name: editorName, reviewed_at: formatDate(page.reviewed_at, lang) }),
    deckNote: s.about.deck_note,
  };
}
```

In `site/src/i18n/en.ts` replace

```ts
  faqTitle: 'Frequently asked questions',
};
```

with

```ts
  faqTitle: 'Frequently asked questions',
  // stage 6: the "on this page" chips of the card page (prototype DeskCard)
  tocLabel: 'On this page',
  tocUpright: 'Upright',
  tocReversed: 'Reversed',
  tocLove: 'Love',
  tocWorkMoney: 'Work and money',
  tocYesNo: 'Yes or no',
  tocFaq: 'FAQ',
};
```

In `site/src/i18n/es.ts` replace

```ts
  faqTitle: 'Preguntas frecuentes',
};
```

with

```ts
  faqTitle: 'Preguntas frecuentes',
  // etapa 6: accesos «en esta página» de la página de carta (prototipo DeskCard)
  tocLabel: 'En esta página',
  tocUpright: 'Al derecho',
  tocReversed: 'Al revés',
  tocLove: 'Amor',
  tocWorkMoney: 'Trabajo y dinero',
  tocYesNo: 'Sí o no',
  tocFaq: 'Preguntas',
};
```

- [ ] **Step 4: Run all site tests and the type check**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check'`
Expected: all pass, `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/cardPage.ts site/src/lib/cardPage.test.ts site/src/lib/deck.ts site/src/lib/routes.ts site/src/i18n
git commit -m "site (stage 6): card template pieces — facts line, captions, Waite citation, yes/no lines, pairs, first-mention links, About lines

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: The card page template

**Files:**
- Create: `site/src/views/CardPageView.astro`, `site/src/components/Segments.astro`
- Modify: `site/src/components/CardFigure.astro`, `site/src/pages/cards/[slug].astro`,
  `site/src/pages/es/cartas/[slug].astro`, `site/src/styles/global.css`
- Delete: `site/src/views/CardView.astro`

**Interfaces:**
- Consumes: everything of Task 8; `cardLd`, `breadcrumbLd`, `faqLd` (jsonld.ts); `cardCrumbs`; `FACTS`;
  `ReadingIsland` (unchanged: `lang`, `page="card"`, `cardId`, `cardName`).
- Produces: `<CardPageView lang card />`; `<CardFigure … alt? caption? />` (optional `alt` overrides the dictionary alt,
  optional `caption` replaces "numeral + name" under the picture); `<Segments segments />`.

- [ ] **Step 1: CardFigure takes the page's alt and caption**

Replace `site/src/components/CardFigure.astro` with:

```astro
---
// A card face on a day page: the printed card in a gold frame (three sizes, srcset) and its name as text. The card
// page gives its own alt (image_alt of the stage 5 text) and the scan's caption (template-strings.json).
import { fill, t } from '../i18n';
import { cardImage, cardName, cardSrcset, type DeckCard } from '../lib/deck';
import type { Lang } from '../lib/types';

interface Props {
  card: DeckCard;
  lang: Lang;
  sizes: string;
  eager?: boolean;
  alt?: string;
  caption?: string;
}

const { card, lang, sizes, eager = false, alt, caption } = Astro.props;
const name = cardName(card, lang);
---
<figure class="card-frame card-frame--day">
  <div class="card-frame__art">
    <img src={cardImage(card, 350)} srcset={cardSrcset(card)} sizes={sizes} width="350" height="600"
      alt={alt ?? fill(t(lang).cardAlt, { name })} loading={eager ? 'eager' : 'lazy'} />
  </div>
  {caption
    ? <figcaption class="card-frame__caption">{caption}</figcaption>
    : <figcaption class="card-frame__name"><b>{card.numeral}</b> {name}</figcaption>}
</figure>
```

- [ ] **Step 2: Segments**

`site/src/components/Segments.astro`:

```astro
---
// Running text with links on the first mention of another card (src/lib/cardPage.ts mentionSegments).
import type { Segment } from '../lib/cardPage';

interface Props {
  segments: readonly Segment[];
}

const { segments } = Astro.props;
---
{segments.map((seg) => (typeof seg === 'string' ? seg : <a href={seg.href}>{seg.text}</a>))}
```

- [ ] **Step 3: The view**

`site/src/views/CardPageView.astro`:

```astro
---
// The card page (spec stage 6 §4; prototypes CardMoon — phone, DeskCard — desktop: the scan and the draw panel on
// the left, the text on the right). Order: breadcrumbs → 1909 scan with its caption → facts line, H1, capsule,
// keyword table → "on this page" chips → the 12 blocks → the draw panel (ReadingIsland, unchanged) → FAQ (first
// open) → related cards → previous and next card → About this page. Text: content/cards/pages (stage 5); template
// strings: template-strings.json; nothing about elements or astrology (owner decision 10).
import Base from '../layouts/Base.astro';
import Breadcrumbs from '../components/Breadcrumbs.astro';
import CardFigure from '../components/CardFigure.astro';
import Segments from '../components/Segments.astro';
import ReadingIsland from '../islands/ReadingIsland';
import { t } from '../i18n';
import { cardCrumbs } from '../lib/breadcrumbs';
import {
  SECTION_IDS, aboutLines, ctaText, factsLine, faqHeading, imageCaption, keywordCaption, keywordRows, mentionSegments,
  pairRows, relatedCards, segmentsOf, tocLinks, waiteCite, yesNoLines, yesNoReason,
} from '../lib/cardPage';
import { TEMPLATE_STRINGS, cardPage } from '../lib/cardPages';
import { cardImage, cardName, neighbors, type DeckCard } from '../lib/deck';
import { FACTS } from '../lib/facts';
import { breadcrumbLd, cardLd, faqLd } from '../lib/jsonld';
import { cardPath, pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
  card: DeckCard;
}

const { lang, card } = Astro.props;
const d = t(lang);
const s = TEMPLATE_STRINGS[lang];
const page = cardPage(card, lang);
const path = cardPath(card, lang);
const ids = SECTION_IDS[lang];
const crumbs = cardCrumbs(card, lang);
const editorName = String(FACTS.editor_name);
const facts = factsLine(page, s, lang);
const mentions = mentionSegments(page, lang);
const yesNo = yesNoLines(card, yesNoReason(card, lang), s, lang);
const pairs = pairRows(page, s, lang);
const cta = ctaText(page, s);
const about = aboutLines(page, s, lang, editorName);
const { prev, next } = neighbors(card);
const ld = cardLd({ headline: page.h1, description: page.description, path, lang, image: cardImage(card, 700),
  reviewedAt: page.reviewed_at ?? '', editorName });
---
<Base lang={lang} title={page.title} description={page.description} path={path} current="cards"
  image={cardImage(card, 700)} ogType="article" jsonLd={[breadcrumbLd(crumbs), ld, faqLd(page.faq)]}>
  <Breadcrumbs lang={lang} crumbs={crumbs} />
  <div class="card-page">
    <div class="card-page__art">
      <CardFigure card={card} lang={lang} sizes="(min-width: 900px) 320px, 70vw" eager alt={page.image_alt}
        caption={imageCaption(page, s)} />
    </div>

    <article class="card-page__main" aria-labelledby="card-title">
      <p class="eyebrow">{facts.before}{facts.link ? <a href={facts.link.href}>{facts.link.text}</a> : null}{facts.after}</p>
      <h1 class="display" id="card-title">{page.h1}</h1>
      <p class="capsule"><Segments segments={segmentsOf(mentions, 'capsule', page.capsule)} /></p>
      <table class="data-table">
        <caption>{keywordCaption(page, s)}</caption>
        <thead><tr><th scope="col">{s.keywords.upright}</th><th scope="col">{s.keywords.reversed}</th></tr></thead>
        <tbody>{keywordRows(page).map(([up, rev]) => <tr><td>{up}</td><td>{rev}</td></tr>)}</tbody>
      </table>
      <nav class="toc" aria-label={d.tocLabel}>
        <ul>{tocLinks(lang).map((link) => <li><a href={link.href}>{link.label}</a></li>)}</ul>
      </nav>

      {page.blocks.map((block) => (
        <section class="card-block" id={ids[block.id]} aria-labelledby={`${ids[block.id]}-title`}>
          <h2 class="h2" id={`${ids[block.id]}-title`}>{block.heading}</h2>
          {block.id === 'waite' ? (
            <>
              <figure class="waite-quote">
                <blockquote lang="en"><p>{page.waite.quote}</p></blockquote>
                <figcaption><cite>{waiteCite(page, s)}</cite></figcaption>
              </figure>
              {page.waite.translation && s.waite.translation_label ? (
                <p><span class="waite-translation__label">{s.waite.translation_label}:</span> {page.waite.translation}</p>
              ) : null}
              {page.waite.harsh ? <p class="block-note">{s.waite.harsh_context}</p> : null}
            </>
          ) : null}
          {block.id === 'yes_no' ? (
            <>
              <p>{yesNo.upright}</p>
              <p>{yesNo.reversed}</p>
              <p class="block-note">{yesNo.rule}</p>
            </>
          ) : null}
          {block.id === 'combinations' ? (
            <>
              <p>{s.combinations.intro}</p>
              <table class="data-table">
                <thead><tr><th scope="col">{s.combinations.col_pair}</th><th scope="col">{s.combinations.col_reading}</th></tr></thead>
                <tbody>
                  {pairs.map((row) => (
                    <tr>
                      <th scope="row">{row.before}{row.link ? <a href={row.link.href}>{row.link.text}</a> : null}{row.after}</th>
                      <td>{row.reading}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
          {block.id === 'ask_yourself' ? (
            <ul class="ask-list">
              {(block.paragraphs ?? []).map((p, j) => <li><Segments segments={segmentsOf(mentions, `${block.id}:${j}`, p)} /></li>)}
            </ul>
          ) : (
            (block.paragraphs ?? []).map((p, j) => <p><Segments segments={segmentsOf(mentions, `${block.id}:${j}`, p)} /></p>)
          )}
          {block.id === 'waite' ? <p class="waite-boundary">{s.waite.boundary}</p> : null}
          {block.id === 'work_money' ? <p class="block-note">{s.work_money.money_line}</p> : null}
          {block.id === 'in_a_reading' ? <p class="block-note">{s.in_a_reading.note}</p> : null}
          {block.id === 'ask_yourself' ? (
            <p><a class="btn btn--outline" href={pagePath('diary', lang)}>{s.ask_yourself.diary_button}</a></p>
          ) : null}
        </section>
      ))}
    </article>

    <section class="card-page__cta" id={ids.draw} aria-labelledby={`${ids.draw}-title`}>
      <h2 class="h2" id={`${ids.draw}-title`}>{cta.heading}</h2>
      <p class="muted">{cta.text}</p>
      <ReadingIsland client:visible lang={lang} page="card" cardId={card.card_id} cardName={cardName(card, lang)} />
    </section>

    <div class="card-page__more">
      <section class="page-section faq" id={ids.faq} aria-labelledby={`${ids.faq}-title`}>
        <h2 class="h2" id={`${ids.faq}-title`}>{faqHeading(page, s)}</h2>
        {page.faq.map((item, i) => (
          <details open={i === 0}>
            <summary>{item.q}</summary>
            <p><Segments segments={segmentsOf(mentions, `faq:${i}`, item.a)} /></p>
          </details>
        ))}
      </section>

      <section class="page-section" id={ids.related} aria-labelledby={`${ids.related}-title`}>
        <h2 class="h2" id={`${ids.related}-title`}>{s.related.heading}</h2>
        <ul class="card-row">
          {relatedCards(page).map((other) => (
            <li><a href={cardPath(other, lang)}><CardFigure card={other} lang={lang} sizes="100px" /></a></li>
          ))}
        </ul>
      </section>

      <nav class="card-nav" aria-label={d.cardNav}>
        <a href={cardPath(prev, lang)}><small>{d.prevCard}</small>{prev.numeral} {cardName(prev, lang)}</a>
        <a href={cardPath(next, lang)}><small>{d.nextCard}</small>{next.numeral} {cardName(next, lang)}</a>
      </nav>

      <section class="page-section about-page" id={ids.about} aria-labelledby={`${ids.about}-title`}>
        <h2 class="h2" id={`${ids.about}-title`}>{s.about.heading}</h2>
        <h3 class="h3">{s.about.sources_label}</h3>
        <ul class="sources">
          {about.sources.map((src) => (
            <li>
              <span class="sources__what">{src.what}:</span> {src.url ? <a href={src.url} rel="noopener">{src.where}</a> : src.where}{src.pages ? `, ${src.pages}` : ''}
            </li>
          ))}
        </ul>
        <p class="small muted">{about.pageNumbers}</p>
        <p class="small">{about.method}</p>
        <p class="small muted">{about.deckNote}</p>
      </section>
    </div>
  </div>
</Base>
```

- [ ] **Step 4: Point the card addresses at the new view and remove the old one**

Replace `site/src/pages/cards/[slug].astro` with:

```astro
---
import CardPageView from '../../views/CardPageView.astro';
import { DECK } from '../../lib/deck';

export function getStaticPaths() {
  return DECK.map((card) => ({ params: { slug: card.slug_en }, props: { card } }));
}

const { card } = Astro.props;
---
<CardPageView lang="en" card={card} />
```

Replace `site/src/pages/es/cartas/[slug].astro` with:

```astro
---
import CardPageView from '../../../views/CardPageView.astro';
import { DECK } from '../../../lib/deck';

export function getStaticPaths() {
  return DECK.map((card) => ({ params: { slug: card.slug_es }, props: { card } }));
}

const { card } = Astro.props;
---
<CardPageView lang="es" card={card} />
```

Run: `git rm site/src/views/CardView.astro`

- [ ] **Step 5: Style**

In `site/src/styles/global.css` replace the whole block from `/* Simple card page */` down to and including the
`@media (min-width: 900px) { .card-page { grid-template-columns: 280px minmax(0, 1fr) minmax(0, 380px); align-items: start; } }`
block (the line before `/* Footer */`) with:

```css
/* The card page (stage 6; prototypes CardMoon — phone, DeskCard — desktop) */
.card-page { display: grid; gap: var(--space-6); padding-top: var(--space-5); }
.card-page__art { max-width: 280px; }
.card-page__main { display: flex; flex-direction: column; gap: var(--space-4); min-width: 0; }
.card-page__main p { margin: 0; }
.card-page__cta { display: flex; flex-direction: column; gap: var(--space-3); min-width: 0; }
.card-page__cta p { margin: 0; }
.card-page__more { min-width: 0; }
.card-frame__caption { font-size: var(--font-size-caption); color: var(--color-day-text-muted); text-align: center; }
.eyebrow a { display: inline-flex; align-items: center; min-height: 44px; color: inherit; }
.data-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-small); }
.data-table caption { text-align: left; font-weight: 600; padding-bottom: var(--space-2); }
.data-table th, .data-table td {
  text-align: left; vertical-align: top; padding: var(--space-2) var(--space-3) var(--space-2) 0;
  border-bottom: 1px solid var(--color-day-line);
}
.data-table thead th { color: var(--color-day-text-muted); font-weight: 600; }
.data-table tbody th { font-weight: 600; }
.toc ul { display: flex; flex-wrap: wrap; gap: var(--space-2); list-style: none; margin: 0; padding: 0; }
.toc a {
  display: inline-flex; align-items: center; min-height: 44px; padding: 0 var(--space-4); border-radius: var(--radius-pill);
  border: 1px solid var(--color-day-control-border); background: var(--color-day-surface); color: var(--color-day-text);
  font-size: var(--font-size-small); font-weight: 600; text-decoration: none;
}
.card-block { display: flex; flex-direction: column; gap: var(--space-4); padding-top: var(--space-6); scroll-margin-top: var(--space-4); }
.waite-quote {
  margin: 0; padding: var(--space-4) var(--space-5); border-left: 2px solid var(--color-day-accent);
  border-radius: var(--radius-field); background: var(--color-day-surface);
}
.waite-quote blockquote { margin: 0; font-family: var(--font-display); font-size: var(--font-size-h-3); line-height: 1.4; }
.waite-quote figcaption { margin-top: var(--space-2); font-size: var(--font-size-small); color: var(--color-day-text-muted); }
.waite-translation__label { font-weight: 700; }
.block-note { font-size: var(--font-size-small); color: var(--color-day-text-muted); }
.waite-boundary {
  padding-top: var(--space-3); border-top: 1px solid var(--color-day-line); font-size: var(--font-size-small);
  color: var(--color-day-text-muted);
}
.ask-list { margin: 0; padding-left: var(--space-5); display: flex; flex-direction: column; gap: var(--space-2); }
.card-row { list-style: none; margin: 0; padding: 0; }
.sources { margin: 0; padding-left: var(--space-5); display: flex; flex-direction: column; gap: var(--space-2); font-size: var(--font-size-small); }
.sources__what { font-weight: 600; }
.card-nav { display: flex; justify-content: space-between; gap: var(--space-4); padding: var(--space-7) 0 0; }
.card-nav a { display: flex; flex-direction: column; min-height: 44px; text-decoration: none; color: var(--color-day-text); }
.card-nav small { color: var(--color-day-text-muted); }
@media (min-width: 900px) {
  .card-page { grid-template-columns: 320px minmax(0, 1fr); column-gap: var(--space-7); row-gap: 0; align-items: start; }
  .card-page__art { grid-column: 1; grid-row: 1; max-width: none; }
  .card-page__cta { grid-column: 1; grid-row: 2; position: sticky; top: var(--space-5); padding-top: var(--space-5); }
  .card-page__main { grid-column: 2; grid-row: 1 / span 2; }
  .card-page__more { grid-column: 2; grid-row: 3; }
}
```

- [ ] **Step 6: Tests, types, build**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && deploy/build-site.sh`
Expected: all tests pass, `0 errors`, build ends with `OK: 177 pages`.

- [ ] **Step 7: Look at two built pages**

Run:

```bash
f=site/dist/es/cartas/la-luna.html
grep -c '<blockquote lang="en">' $f
grep -o 'Traducción nuestra:\|Así se leían las cartas en 1911[^<]*\|id="invertida"\|id="amor"\|id="si-o-no"\|Al derecho: Todavía no está claro\.' $f | sort -u
grep -o '"@type":"Article"\|"reviewedBy":{[^}]*}' site/dist/cards/the-moon.html
grep -o 'href="/cards#swords">Swords<\|href="/cards/four-of-swords">Four of Swords<\|Upright: No\.' site/dist/cards/three-of-swords.html | sort -u
grep -c 'astro-island' site/dist/cards/the-moon.html
grep -o '<h1[^>]*>' site/dist/cards/the-moon.html | wc -l
```

Expected: `1`; the six ES strings (`Al derecho: Todavía no está claro.`, `Así se leían las cartas en 1911; hoy no la
leemos así.`, `Traducción nuestra:`, `id="amor"`, `id="invertida"`, `id="si-o-no"`); `"@type":"Article"` and
`"reviewedBy":{"@type":"Person","name":"Adrian Solenne","jobTitle":"Editor"}`; `Upright: No.`, the Swords link of the
facts line and the Four of Swords link of the first pair; `1`; `1`.

- [ ] **Step 8: Check the layout by eye**

Run: `deploy/test-site-routes.sh` (must end `OK: адреса страниц и 404`). Then open the built pages in a browser at
390 px and 1440 px width (for example `python3 -m http.server -d site/dist 8099` on the server, an SSH tunnel and the `.html` file names, or
the stage after the owner's deploy) and compare with `docs/design/prototypes/CardMoon.dc.html` and `DeskCard.dc.html`:
scan + CTA on the left at 1440 px, text on the right; every chip, button, `<summary>` and breadcrumb link ≥ 44 px;
the Tab key shows the focus ring on each.

- [ ] **Step 9: Commit**

```bash
git add site/src/views/CardPageView.astro site/src/components/Segments.astro site/src/components/CardFigure.astro site/src/pages/cards site/src/pages/es/cartas site/src/styles/global.css
git commit -m "site (stage 6): card page template — 1909 scan, facts, capsule, keywords, 12 blocks with Waite quote, yes/no, pairs, CTA, FAQ, related, About

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Deploy checkpoint — Part 2

Stop here. Before asking the owner: all tests, `deploy/build-site.sh` (`OK: 177 pages`), `deploy/test-site-routes.sh`
pass; branch review (Sonnet) done. Tell the owner what to look at: `/cards/the-moon`, `/es/cartas/la-luna`,
`/cards/three-of-swords`, `/es/cartas/los-enamorados` on a phone and a desktop; the new chip labels (Task 8 keys).
Deploy only on the owner's word.

---

# Part 3 — Tools and hubs

Ends deployable: the tool pages carry their stage 5 text under the tool; `/es/tiradas/3-cartas` draws three cards;
the hubs, Major Arcana and the yes/no card list show their card lists from the data.

### Task 10: Stage 5 text under the tools

**Files:**
- Modify: `site/src/views/HomeView.astro`, `site/src/views/ToolView.astro`, `site/src/views/DailyView.astro`

**Interfaces:**
- Consumes: `TextBlocks.astro`, `Faq.astro` (Task 6); `textPage`, `filledPage`; `webPageLd`, `faqLd`.
- Produces: tool pages with eyebrow (dictionary), H1 and lead (stage 5 text), blocks and FAQ under the tool, JSON-LD
  WebPage + FAQPage. `ToolView` props unchanged (`lang`, `page: 'one_card' | 'yes_no' | 'love'`).

- [ ] **Step 1: Home**

Replace `site/src/views/HomeView.astro` with:

```astro
---
// Home EN / ES (screens 1, 12a, 13a; spec stage 6 §5): the eyebrow from the dictionary, H1 and lead from the stage 5
// text, the night panel (ES adds "1 carta / 3 cartas" and is the one-card page at #una-carta); under it the other
// formats, the Card of the Day tile, the text blocks, the cards to learn and the FAQ of content/pages. The old
// "How a reading works" steps gave way to the stage 5 block "How the reading works". A line after the account was
// deleted (HomeNotice).
import Base from '../layouts/Base.astro';
import CardFigure from '../components/CardFigure.astro';
import Faq from '../components/Faq.astro';
import TextBlocks from '../components/TextBlocks.astro';
import HomeNotice from '../islands/HomeNotice';
import ReadingIsland from '../islands/ReadingIsland';
import { t } from '../i18n';
import { CARD_BACK, cardById } from '../lib/deck';
import { faqLd, webPageLd } from '../lib/jsonld';
import { cardPath, pagePath } from '../lib/routes';
import { filledPage, textPage } from '../lib/textPages';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
const path = pagePath('home', lang);
const text = filledPage(textPage(path));
const formats = [
  ...(lang === 'en' ? [{ href: pagePath('one_card', lang), name: d.fmtOneCard, hint: d.fmtOneCardHint }] : []),
  { href: pagePath('yes_no', lang), name: d.fmtYesNo, hint: d.fmtYesNoHint },
  { href: pagePath('love', lang), name: d.fmtLove, hint: d.fmtLoveHint },
  { href: pagePath('daily', lang), name: d.fmtDaily, hint: d.fmtDailyHint },
];
const faces = ['major-18-moon', 'major-19-sun', 'major-16-tower'].map((id) => cardById(id)!);
---
<Base lang={lang} title={text.title} description={text.description} path={path} current="home"
  jsonLd={[webPageLd({ name: text.h1, description: text.description, path, lang }), faqLd(text.faq)]}>
  <HomeNotice client:load lang={lang} />
  <div class="tool-layout">
    <section class="page-hero">
      <p class="eyebrow">{d.homeEyebrow}</p>
      <h1 class="display display--home">{text.h1}</h1>
      <p class="lead">{text.lead}</p>
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

  <TextBlocks blocks={text.blocks} />

  <section class="page-section" aria-labelledby="learn">
    <h2 class="h2" id="learn">{d.learnTitle}</h2>
    <p class="lead">{d.learnLead}</p>
    <div class="card-row">
      {faces.map((card) => (
        <a href={cardPath(card, lang)}><CardFigure card={card} lang={lang} sizes="100px" /></a>
      ))}
    </div>
  </section>

  <Faq heading={d.faqTitle} items={text.faq} id="faq" />
</Base>
```

- [ ] **Step 2: One card, yes or no, love**

Replace `site/src/views/ToolView.astro` with:

```astro
---
// A tool page (screens 5a, 6, one card; spec stage 6 §5): the eyebrow from the dictionary, H1 and lead from the stage
// 5 text, the night panel (love adds a note under it); under the tool the text blocks and the FAQ of content/pages.
import Base from '../layouts/Base.astro';
import Faq from '../components/Faq.astro';
import TextBlocks from '../components/TextBlocks.astro';
import ReadingIsland from '../islands/ReadingIsland';
import { t, type DictKey } from '../i18n';
import { faqLd, webPageLd } from '../lib/jsonld';
import { pagePath, type PageKey } from '../lib/routes';
import { filledPage, textPage } from '../lib/textPages';
import type { Lang } from '../lib/types';

type ToolPage = 'one_card' | 'yes_no' | 'love';

interface Props {
  lang: Lang;
  page: ToolPage;
}

const { lang, page } = Astro.props;
const d = t(lang);
const EYEBROW: Record<ToolPage, DictKey> = { one_card: 'oneCardEyebrow', yes_no: 'yesNoEyebrow', love: 'loveEyebrow' };
const CURRENT: Record<ToolPage, PageKey | undefined> = { one_card: undefined, yes_no: 'yes_no', love: 'love' };
const path = pagePath(page, lang);
const text = filledPage(textPage(path));
---
<Base lang={lang} title={text.title} description={text.description} path={path} current={CURRENT[page]}
  jsonLd={[webPageLd({ name: text.h1, description: text.description, path, lang }), faqLd(text.faq)]}>
  <div class="tool-layout">
    <section class="page-hero">
      <p class="eyebrow">{d[EYEBROW[page]]}</p>
      <h1 class="display">{text.h1}</h1>
      <p class="lead">{text.lead}</p>
    </section>
    <div>
      <ReadingIsland client:load lang={lang} page={page} />
      {page === 'love' ? <p class="small muted">{d.loveNote}</p> : null}
    </div>
  </div>
  <TextBlocks blocks={text.blocks} />
  <Faq heading={d.faqTitle} items={text.faq} id="faq" />
</Base>
```

- [ ] **Step 3: Card of the Day**

Replace `site/src/views/DailyView.astro` with:

```astro
---
// Card of the Day (screens 7a, 7b; spec stage 6 §5): the eyebrow from the dictionary, H1 and lead from the stage 5
// text, the card; under it the text blocks and the FAQ of content/pages.
import Base from '../layouts/Base.astro';
import Faq from '../components/Faq.astro';
import TextBlocks from '../components/TextBlocks.astro';
import DailyIsland from '../islands/DailyIsland';
import { t } from '../i18n';
import { faqLd, webPageLd } from '../lib/jsonld';
import { pagePath } from '../lib/routes';
import { filledPage, textPage } from '../lib/textPages';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
const path = pagePath('daily', lang);
const text = filledPage(textPage(path));
---
<Base lang={lang} title={text.title} description={text.description} path={path} current="daily"
  jsonLd={[webPageLd({ name: text.h1, description: text.description, path, lang }), faqLd(text.faq)]}>
  <section class="page-hero">
    <p class="eyebrow">{d.dailyEyebrow}</p>
    <h1 class="display">{text.h1}</h1>
    <p class="lead">{text.lead}</p>
  </section>
  <DailyIsland client:load lang={lang} />
  <TextBlocks blocks={text.blocks} />
  <Faq heading={d.faqTitle} items={text.faq} id="faq" />
</Base>
```

- [ ] **Step 4: Tests, types, build, look**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && deploy/build-site.sh`
Expected: all pass, `0 errors`, `OK: 177 pages`.

Run: `grep -o '<h2 class="h2" id="[a-z-]*-title">[^<]*' site/dist/index.html site/dist/es/si-o-no.html | head -12; grep -o '"@type":"FAQPage"' site/dist/index.html site/dist/daily.html site/dist/es/amor.html; grep -o '{guest_limit}' site/dist/index.html | wc -l`
Expected: the stage 5 headings (`How the reading works`, `How to ask a good question`, … / `¿Cómo funciona el sí o no?`, …);
three `"@type":"FAQPage"` lines; `0` (the facts are filled).

- [ ] **Step 5: Commit**

```bash
git add site/src/views/HomeView.astro site/src/views/ToolView.astro site/src/views/DailyView.astro
git commit -m "site (stage 6): stage 5 H1, lead, blocks and FAQ on the home, one-card, yes/no, love and Card of the Day pages

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: The three-card tool at /es/tiradas/3-cartas

**Files:**
- Modify: `site/src/lib/types.ts` (`Tool`), `site/src/lib/panel.ts`, `site/src/views/ToolView.astro`,
  `site/src/pages/es/tiradas/3-cartas.astro`, `site/src/i18n/en.ts`, `site/src/i18n/es.ts`, `tools/site/check_dist.py`
- Test: `site/src/lib/panel.test.ts`, `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `ReadingIsland` (unchanged), `crumbsFor('three_cards', lang)`, `breadcrumbLd`.
- Produces: `Tool` gains `'three_cards'` (already accepted by `api/app/events.py` `TOOLS`); `PanelPage` gains
  `'three_cards'` — kind `three`, tool `three_cards`, placeholder `homePlaceholder`; `ToolView` `page` gains
  `'three_cards'` with breadcrumbs Inicio › 3 cartas; dictionary key `threeCardsEyebrow` (240).

- [ ] **Step 1: Write the failing tests**

In `site/src/lib/panel.test.ts`, inside `describe('panelConfig', …)`, add:

```ts
  it('draws three cards on the Spanish 3 cartas page, counted as the three_cards tool (spec stage 6 §5)', () => {
    const config = panelConfig('three_cards', 'es');
    expect([config.tool, config.kind, config.countToggle, config.entry, config.placeholderKey]).toEqual([
      'three_cards', 'three', false, 'tool', 'homePlaceholder']);
    expect(drawLabelKey(config, 'three')).toBe('drawThree');
    expect(toolFor(config, 'three')).toBe('three_cards');
    expect(buildCreateBody(config, { kind: 'three', question: '', situation: null, tz: undefined })).toEqual({
      lang: 'es', kind: 'three' });
  });
```

In `site/src/i18n/i18n.test.ts` change `toBe(239)` to `toBe(240)`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/panel.test.ts src/i18n/i18n.test.ts'`
Expected: FAIL — `panelConfig('three_cards', …)` returns `undefined` (TypeError reading `tool`); 239 keys.

- [ ] **Step 3: Implement**

In `site/src/lib/types.ts` replace

```ts
/** The `tool` of docs/design/analytics-events.md that the 4.4a pages use. */
export type Tool = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily';
```

with

```ts
/** The `tool` of docs/design/analytics-events.md that the pages use (three_cards: /es/tiradas/3-cartas, stage 6). */
export type Tool = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'three_cards';
```

In `site/src/lib/panel.ts` change the `PanelPage` line to

```ts
export type PanelPage = 'home' | 'one_card' | 'yes_no' | 'love' | 'card' | 'three_cards';
```

and add before `case 'card':`:

```ts
    case 'three_cards': // /es/tiradas/3-cartas (spec stage 6 §5): past, present, where it's heading
      return { ...base, tool: 'three_cards', kind: 'three', placeholderKey: 'homePlaceholder' };
```

Replace `site/src/views/ToolView.astro` with:

```astro
---
// A tool page (screens 5a, 6, 12d, one card; spec stage 6 §5): the eyebrow from the dictionary, H1 and lead from the
// stage 5 text, the night panel (love adds a note under it); under the tool the text blocks and the FAQ of
// content/pages. "3 cartas" (Spanish only) has breadcrumbs Inicio › 3 cartas (prototype TresCartas).
import Base from '../layouts/Base.astro';
import Breadcrumbs from '../components/Breadcrumbs.astro';
import Faq from '../components/Faq.astro';
import TextBlocks from '../components/TextBlocks.astro';
import ReadingIsland from '../islands/ReadingIsland';
import { t, type DictKey } from '../i18n';
import { crumbsFor } from '../lib/breadcrumbs';
import { breadcrumbLd, faqLd, webPageLd } from '../lib/jsonld';
import { pagePath, type PageKey } from '../lib/routes';
import { filledPage, textPage } from '../lib/textPages';
import type { Lang } from '../lib/types';

type ToolPage = 'one_card' | 'yes_no' | 'love' | 'three_cards';

interface Props {
  lang: Lang;
  page: ToolPage;
}

const { lang, page } = Astro.props;
const d = t(lang);
const EYEBROW: Record<ToolPage, DictKey> = {
  one_card: 'oneCardEyebrow', yes_no: 'yesNoEyebrow', love: 'loveEyebrow', three_cards: 'threeCardsEyebrow',
};
const CURRENT: Record<ToolPage, PageKey | undefined> = {
  one_card: undefined, yes_no: 'yes_no', love: 'love', three_cards: 'home',
};
const path = pagePath(page, lang);
const text = filledPage(textPage(path));
const crumbs = crumbsFor(page, lang);
---
<Base lang={lang} title={text.title} description={text.description} path={path} current={CURRENT[page]}
  jsonLd={[breadcrumbLd(crumbs), webPageLd({ name: text.h1, description: text.description, path, lang }), faqLd(text.faq)]}>
  <Breadcrumbs lang={lang} crumbs={crumbs} />
  <div class="tool-layout">
    <section class="page-hero">
      <p class="eyebrow">{d[EYEBROW[page]]}</p>
      <h1 class="display">{text.h1}</h1>
      <p class="lead">{text.lead}</p>
    </section>
    <div>
      <ReadingIsland client:load lang={lang} page={page} />
      {page === 'love' ? <p class="small muted">{d.loveNote}</p> : null}
    </div>
  </div>
  <TextBlocks blocks={text.blocks} />
  <Faq heading={d.faqTitle} items={text.faq} id="faq" />
</Base>
```

Replace `site/src/pages/es/tiradas/3-cartas.astro` with:

```astro
---
import ToolView from '../../../views/ToolView.astro';
---
<ToolView lang="es" page="three_cards" />
```

In `site/src/i18n/en.ts` replace

```ts
  tocFaq: 'FAQ',
};
```

with

```ts
  tocFaq: 'FAQ',
  // stage 6: the Spanish three-card page (query · fact); English has no such page, the key keeps both files equal
  threeCardsEyebrow: 'Three-card tarot · Free, no sign-up',
};
```

In `site/src/i18n/es.ts` replace

```ts
  tocFaq: 'Preguntas',
};
```

with

```ts
  tocFaq: 'Preguntas',
  // etapa 6: la página de 3 cartas (consulta · dato)
  threeCardsEyebrow: 'Tarot de 3 cartas · Gratis, sin registro',
};
```

In `tools/site/check_dist.py` change `READING_PAGES` to:

```python
READING_PAGES = ("/", "/one-card", "/yes-no", "/love", "/daily", "/cards/the-moon", "/es", "/es/si-o-no", "/es/amor",
                 "/es/carta-del-dia", "/es/cartas/la-luna", "/es/tiradas/3-cartas")
```

- [ ] **Step 4: Tests, types, build, look**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && api/.venv/bin/pytest -q tools/site && deploy/build-site.sh`
Expected: all pass, `0 errors`, `OK: 177 pages`.

Run: `grep -o 'Saca tres cartas\|aria-label="Ruta"\|Tarot de 3 cartas · Gratis, sin registro' site/dist/es/tiradas/3-cartas.html | sort -u`
Expected: the three strings.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/types.ts site/src/lib/panel.ts site/src/lib/panel.test.ts site/src/views/ToolView.astro site/src/pages/es/tiradas site/src/i18n tools/site/check_dist.py
git commit -m "site (stage 6): three-card tool on /es/tiradas/3-cartas (tool three_cards), breadcrumbs Inicio › 3 cartas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Card lists of the hubs, Major Arcana and the yes/no card list

**Files:**
- Create: `site/src/lib/cardLists.ts`, `site/src/views/HubView.astro`, `site/src/views/MajorView.astro`,
  `site/src/views/YesNoCardsView.astro`
- Modify: `site/src/pages/cards/index.astro`, `site/src/pages/cards/major-arcana.astro`,
  `site/src/pages/yes-no/cards.astro`, `site/src/pages/es/cartas/index.astro`,
  `site/src/pages/es/cartas/arcanos-mayores.astro`, `site/src/styles/global.css`, `site/src/i18n/en.ts`,
  `site/src/i18n/es.ts`
- Test: `site/src/lib/cardLists.test.ts`, `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `DECK`, `cardName`, `DeckCard.yes_no` (deck.ts); `cardPath`, `pagePath`, `Suit`, `SUIT_IDS` (routes.ts);
  `TEMPLATE_STRINGS` (suit names); `TextPageView` default slot and `items` prop; `LdItem`.
- Produces:
  - `cardLists.ts`: `interface ListedCard { card: DeckCard; name: string; href: string }`, `SUITS: readonly Suit[]`,
    `majorCards(lang): ListedCard[]`, `suitCards(suit, lang): ListedCard[]`, `verdictCards(verdict: Vote, lang):
    ListedCard[]`, `firstKeyword(card, lang): string`, `ldItems(cards): LdItem[]`
  - views `<HubView lang />`, `<MajorView lang />`, `<YesNoCardsView />` (English only)
  - dictionary keys `allCardsLink`, `yesNoListAsk` (242)

- [ ] **Step 1: Write the failing tests**

`site/src/lib/cardLists.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { SUITS, firstKeyword, ldItems, majorCards, suitCards, verdictCards } from './cardLists';
import { cardById } from './deck';
import { FACTS } from './facts';

describe('card lists of the hubs (spec stage 6 §5: from the data, not from the text)', () => {
  it('list the 22 Major Arcana in deck order with their addresses', () => {
    const majors = majorCards('en');
    expect(majors).toHaveLength(22);
    expect(majors[0]).toMatchObject({ name: 'The Fool', href: '/cards/the-fool' });
    expect(majorCards('es')[21]).toMatchObject({ name: 'El Mundo', href: '/es/cartas/el-mundo' });
  });

  it('list 14 cards in each of the four suits', () => {
    expect(SUITS).toEqual(['wands', 'cups', 'swords', 'pentacles']);
    for (const suit of SUITS) expect(suitCards(suit, 'en')).toHaveLength(14);
    expect(suitCards('swords', 'es')[2]).toMatchObject({ name: 'Tres de Espadas', href: '/es/cartas/tres-de-espadas' });
  });

  it('sort the deck by its yes/no verdict, as many as the facts say', () => {
    expect(verdictCards('yes', 'en')).toHaveLength(Number(FACTS.yes_count));
    expect(verdictCards('no', 'en')).toHaveLength(Number(FACTS.no_count));
    expect(verdictCards('unclear', 'en').map((c) => c.name)).toContain('The Moon');
  });

  it('give each card its first keyword and the JSON-LD items', () => {
    expect(firstKeyword(cardById('major-18-moon')!, 'en')).toBe('uncertainty');
    expect(firstKeyword(cardById('major-00-fool')!, 'es')).toBe('comienzo');
    expect(ldItems(majorCards('en')).slice(0, 1)).toEqual([{ name: 'The Fool', path: '/cards/the-fool' }]);
  });
});
```

In `site/src/i18n/i18n.test.ts` change `toBe(240)` to `toBe(242)`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/cardLists.test.ts src/i18n/i18n.test.ts'`
Expected: FAIL — `./cardLists` does not resolve; 240 keys.

- [ ] **Step 3: Implement the lists**

`site/src/lib/cardLists.ts`:

```ts
// Card lists of the hubs (spec stage 6 §5): the 22 Major Arcana, the four suits, the yes/no verdicts — from the
// deck, never from the text. No suit themes or elements (owner decision 10).
import meaningsEn from '../data/meanings.en.json';
import meaningsEs from '../data/meanings.es.json';
import { DECK, cardName, type DeckCard } from './deck';
import type { LdItem } from './jsonld';
import { cardPath, type Suit } from './routes';
import type { Lang, Vote } from './types';

export interface ListedCard {
  card: DeckCard;
  name: string;
  href: string;
}

export const SUITS: readonly Suit[] = ['wands', 'cups', 'swords', 'pentacles'];

const KEYWORDS: Readonly<Record<Lang, ReadonlyMap<string, string>>> = {
  en: new Map(meaningsEn.map((m) => [m.card_id, m.keywords[0]])),
  es: new Map(meaningsEs.map((m) => [m.card_id, m.keywords[0]])),
};

const listed = (card: DeckCard, lang: Lang): ListedCard => ({ card, name: cardName(card, lang), href: cardPath(card, lang) });

export function majorCards(lang: Lang): ListedCard[] {
  return DECK.filter((c) => c.arcana === 'major').map((c) => listed(c, lang));
}

export function suitCards(suit: Suit, lang: Lang): ListedCard[] {
  return DECK.filter((c) => c.suit === suit).map((c) => listed(c, lang));
}

export function verdictCards(verdict: Vote, lang: Lang): ListedCard[] {
  return DECK.filter((c) => c.yes_no === verdict).map((c) => listed(c, lang));
}

export function firstKeyword(card: DeckCard, lang: Lang): string {
  return KEYWORDS[lang].get(card.card_id) ?? '';
}

export function ldItems(cards: readonly ListedCard[]): LdItem[] {
  return cards.map((c) => ({ name: c.name, path: c.href }));
}
```

- [ ] **Step 4: Dictionary**

In `site/src/i18n/en.ts` replace

```ts
  threeCardsEyebrow: 'Three-card tarot · Free, no sign-up',
};
```

with

```ts
  threeCardsEyebrow: 'Three-card tarot · Free, no sign-up',
  // stage 6: links of the card lists (stage 2 matrix L-EN-14 "All 78 cards", L-EN-06 "Ask your question")
  allCardsLink: 'All 78 cards',
  yesNoListAsk: 'Ask your question',
};
```

In `site/src/i18n/es.ts` replace

```ts
  threeCardsEyebrow: 'Tarot de 3 cartas · Gratis, sin registro',
};
```

with

```ts
  threeCardsEyebrow: 'Tarot de 3 cartas · Gratis, sin registro',
  // etapa 6: enlaces de las listas (matriz de la etapa 2, L-ES-14 «Las 78 cartas»)
  allCardsLink: 'Las 78 cartas',
  yesNoListAsk: 'Haz tu pregunta',
};
```

- [ ] **Step 5: The three views**

`site/src/views/HubView.astro`:

```astro
---
// The hub of 78 cards (spec stage 6 §5; prototypes Hub, DeskHub — without the suit elements, owner decision 10):
// capsule, the 22 Major Arcana as pictures under a link to their page, the four suits as name lists with anchors
// (#wands… / #bastos…, links L-EN-10, L-ES-10), the draw button, then the stage 5 blocks and FAQ.
import CardFigure from '../components/CardFigure.astro';
import TextPageView from './TextPageView.astro';
import { t } from '../i18n';
import { SUITS, ldItems, majorCards, suitCards } from '../lib/cardLists';
import { TEMPLATE_STRINGS } from '../lib/cardPages';
import { SUIT_IDS, pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
const suitNames = TEMPLATE_STRINGS[lang].facts.suits;
const majors = majorCards(lang);
const suits = SUITS.map((suit) => ({ suit, id: SUIT_IDS[lang][suit], name: suitNames[suit], cards: suitCards(suit, lang) }));
---
<TextPageView lang={lang} pageKey="cards" current="cards" items={ldItems([...majors, ...suits.flatMap((s) => s.cards)])}>
  <section class="page-section" aria-labelledby="major-list">
    <h2 class="h2" id="major-list"><a href={pagePath('major_arcana', lang)}>{d.crumbMajor}</a></h2>
    <ul class="major-grid">
      {majors.map((c) => <li><a href={c.href}><CardFigure card={c.card} lang={lang} sizes="100px" /></a></li>)}
    </ul>
  </section>
  <section class="page-section" aria-labelledby="minor-list">
    <h2 class="h2" id="minor-list">{d.cardEyebrowMinor}</h2>
    {suits.map((s) => (
      <div class="suit" id={s.id}>
        <h3 class="h3"><span class={`suit-dot suit-dot--${s.suit}`} aria-hidden="true"></span>{s.name}</h3>
        <ul class="name-list">{s.cards.map((c) => <li><a href={c.href}>{c.name}</a></li>)}</ul>
      </div>
    ))}
    <p><a class="btn btn--ink" href={pagePath('home', lang)}>{d.drawForQuestion}</a></p>
  </section>
</TextPageView>
```

`site/src/views/MajorView.astro`:

```astro
---
// The 22 Major Arcana (spec stage 6 §5; prototype Major): capsule, the list with numeral, name and the first keyword
// of the card base, a link to all 78 cards (L-EN-14, L-ES-14), the draw button, then the stage 5 blocks and FAQ.
import TextPageView from './TextPageView.astro';
import { t } from '../i18n';
import { firstKeyword, ldItems, majorCards } from '../lib/cardLists';
import { pagePath } from '../lib/routes';
import type { Lang } from '../lib/types';

interface Props {
  lang: Lang;
}

const { lang } = Astro.props;
const d = t(lang);
const majors = majorCards(lang);
---
<TextPageView lang={lang} pageKey="major_arcana" current="cards" items={ldItems(majors)}>
  <section class="page-section" aria-label={d.crumbMajor}>
    <ol class="link-list major-list">
      {majors.map((c) => (
        <li>
          <a href={c.href}>
            <span class="major-list__n">{c.card.numeral}</span>
            <span class="link-list__text"><span class="link-list__name">{c.name}</span><span class="link-list__hint">{firstKeyword(c.card, lang)}</span></span>
          </a>
        </li>
      ))}
    </ol>
    <p class="block-link"><a href={pagePath('cards', lang)}>{d.allCardsLink}</a></p>
    <p><a class="btn btn--ink" href={pagePath('home', lang)}>{d.drawForQuestion}</a></p>
  </section>
</TextPageView>
```

`site/src/views/YesNoCardsView.astro`:

```astro
---
// Yes or no card list, English only (spec stage 6 §5; prototype YesNoList): capsule, the rule block, then the blocks
// "Cards that lean yes / no / Not clear yet" each with its list from deck.json (links to the cards, L-EN-05), the
// other blocks, "Ask your question" (L-EN-06) and the FAQ.
import Base from '../layouts/Base.astro';
import Breadcrumbs from '../components/Breadcrumbs.astro';
import Faq from '../components/Faq.astro';
import { t } from '../i18n';
import { crumbsFor } from '../lib/breadcrumbs';
import { ldItems, verdictCards } from '../lib/cardLists';
import { breadcrumbLd, collectionLd, faqLd } from '../lib/jsonld';
import { pagePath } from '../lib/routes';
import { filledPage, textPage } from '../lib/textPages';
import type { Vote } from '../lib/types';

const lang = 'en';
const d = t(lang);
const path = pagePath('yes_no_cards', lang);
const page = filledPage(textPage(path));
const crumbs = crumbsFor('yes_no_cards', lang);
// the blocks of content/pages/en/yes-no-cards.json that describe one verdict
const VERDICT_OF: Readonly<Record<string, Vote>> = { 'lean-yes': 'yes', 'lean-no': 'no', 'not-clear-yet': 'unclear' };
const all = (['yes', 'no', 'unclear'] as const).flatMap((v) => verdictCards(v, lang));
---
<Base lang={lang} title={page.title} description={page.description} path={path} current="yes_no"
  jsonLd={[breadcrumbLd(crumbs), collectionLd({ name: page.h1, description: page.description, path, lang, items: ldItems(all) }),
    faqLd(page.faq)]}>
  <Breadcrumbs lang={lang} crumbs={crumbs} />
  <section class="page-hero">
    <h1 class="display">{page.h1}</h1>
    <p class="lead">{page.lead}</p>
    {page.capsule ? <p class="capsule">{page.capsule}</p> : null}
  </section>
  {page.blocks.map((block) => (
    <section class="page-section prose" id={block.id} aria-labelledby={`${block.id}-title`}>
      <h2 class="h2" id={`${block.id}-title`}>{block.heading}</h2>
      {block.paragraphs.map((paragraph) => <p>{paragraph}</p>)}
      {VERDICT_OF[block.id] ? (
        <ul class="name-list">
          {verdictCards(VERDICT_OF[block.id], lang).map((c) => <li><a href={c.href}>{c.name}</a></li>)}
        </ul>
      ) : null}
    </section>
  ))}
  <p class="page-section"><a class="btn btn--ink" href={pagePath('yes_no', lang)}>{d.yesNoListAsk}</a></p>
  <Faq heading={d.faqTitle} items={page.faq} id="faq" />
</Base>
```

- [ ] **Step 6: Point the pages at the views**

Replace `site/src/pages/cards/index.astro` with:

```astro
---
import HubView from '../../views/HubView.astro';
---
<HubView lang="en" />
```

Replace `site/src/pages/es/cartas/index.astro` with:

```astro
---
import HubView from '../../../views/HubView.astro';
---
<HubView lang="es" />
```

Replace `site/src/pages/cards/major-arcana.astro` with:

```astro
---
import MajorView from '../../views/MajorView.astro';
---
<MajorView lang="en" />
```

Replace `site/src/pages/es/cartas/arcanos-mayores.astro` with:

```astro
---
import MajorView from '../../../views/MajorView.astro';
---
<MajorView lang="es" />
```

Replace `site/src/pages/yes-no/cards.astro` with:

```astro
---
import YesNoCardsView from '../../views/YesNoCardsView.astro';
---
<YesNoCardsView />
```

- [ ] **Step 7: Style**

Append to `site/src/styles/global.css`:

```css

/* Card lists of the hubs (stage 6; prototypes Hub, DeskHub, Major, YesNoList — no suit elements, decision 10) */
.major-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: var(--space-4) var(--space-3);
  list-style: none; margin: 0; padding: 0;
}
.major-grid a { display: block; color: var(--color-day-text); text-decoration: none; }
.h2 a { display: inline-flex; align-items: center; min-height: 44px; color: inherit; }
.suit { display: flex; flex-direction: column; gap: var(--space-2); scroll-margin-top: var(--space-4); }
.suit .h3 { display: flex; align-items: center; gap: var(--space-2); }
.suit-dot { width: var(--space-3); height: var(--space-3); border-radius: var(--radius-pill); flex-shrink: 0; }
.suit-dot--wands { background: var(--color-suit-day-wands); }
.suit-dot--cups { background: var(--color-suit-day-cups); }
.suit-dot--swords { background: var(--color-suit-day-swords); }
.suit-dot--pentacles { background: var(--color-suit-day-pentacles); }
.name-list { columns: 2; column-gap: var(--space-5); list-style: none; margin: 0; padding: 0; }
.name-list li { break-inside: avoid; }
.name-list a { display: flex; align-items: center; min-height: 44px; color: var(--color-day-text); }
.major-list__n { min-width: var(--space-7); color: var(--color-day-accent); font-family: var(--font-display); font-weight: 600; }
@media (min-width: 900px) {
  .name-list { columns: 3; }
}
```

- [ ] **Step 8: Tests, types, build, look**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && deploy/build-site.sh && deploy/test-site-routes.sh`
Expected: all pass, `0 errors`, `OK: 177 pages`, `OK: адреса страниц и 404`.

Run:

```bash
grep -o 'href="/cards/[a-z-]*"' site/dist/cards.html | grep -v major-arcana | sort -u | wc -l
grep -o 'href="/es/cartas/[a-z-]*"' site/dist/es/cartas/arcanos-mayores.html | sort -u | wc -l
grep -o 'href="/cards/[a-z-]*"' site/dist/yes-no/cards.html | sort -u | wc -l
grep -o 'id="wands"\|id="bastos"\|"numberOfItems":78' site/dist/cards.html site/dist/es/cartas.html | sort -u
grep -ci 'fire\|fuego\|water\|agua' site/dist/cards.html site/dist/es/cartas.html
```

Expected: `78`; `22`; `78`; `site/dist/cards.html:"numberOfItems":78`, `site/dist/cards.html:id="wands"`,
`site/dist/es/cartas.html:"numberOfItems":78`, `site/dist/es/cartas.html:id="bastos"`; the last command prints a
count per file — open any match and confirm it is stage 5 text, not a suit theme line.

- [ ] **Step 9: Commit**

```bash
git add site/src/lib/cardLists.ts site/src/lib/cardLists.test.ts site/src/views/HubView.astro site/src/views/MajorView.astro site/src/views/YesNoCardsView.astro site/src/pages site/src/styles/global.css site/src/i18n
git commit -m "site (stage 6): card lists from the deck — hub grid and suits, 22 Major Arcana with keywords, yes/no lists in their blocks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Deploy checkpoint — Part 3

Stop here. Before asking the owner: all tests, build, route test pass; branch review (Sonnet) done. Show the owner:
the tool pages with their texts (`/`, `/es`, `/yes-no`, `/love`, `/daily`), `/es/tiradas/3-cartas` drawing three
cards, `/cards`, `/es/cartas`, `/cards/major-arcana`, `/yes-no/cards`. Ask the wording question of decision 11: the
three EN sentences "in the list below" (`content/pages/en/cards.json`, `major-arcana.json`) now sit under the list —
change to "in the list above" / "on this page", or keep? Deploy only on the owner's word.

---

# Part 4 — Service pages

Ends deployable: the ten service pages are built from their stage 5 texts; the eight with operator placeholders are
hidden (noindex, outside the footer and the sitemap); "How our readings work" / "Cómo funcionan las lecturas" is open,
paired for hreflang and in the footer; privacy links appear by themselves once the privacy page opens.

### Task 13: Stage 2 rows of the service pages and their hreflang pairs

**Files:**
- Modify: `docs/research/stage1/page-map-en.csv`, `docs/research/stage1/page-map-es.csv` (5 rows each),
  `docs/research/stage2/hreflang.csv` (regenerated), `tools/research/validate_page_map.py` (`PAGE_TYPES`),
  `tools/research/structure_hreflang.py` (`LAUNCH_CLUSTERS`), `docs/research/stage2/00-structure.md`,
  `docs/research/stage2/99-changelog.md`, `site/src/data/pairs.json` (sync)
- Test: `tools/site/test_sync_site_data.py`, `tools/site/test_check_dist.py`

**Interfaces:**
- Consumes: `tools/research/build_hreflang.py`, `validate_page_map.py`, `validate_structure.py`, `sync_site_data.py`.
- Produces: page-map rows EN-125…EN-129 and ES-108…ES-112 (`page_type` `service`, entities `page:about`,
  `page:how-readings-work`, `page:contact`, `page:privacy`, `page:terms`); `hreflang.csv` 359 rows, 89 launch
  clusters; `pairs.json` 181 entries; `check_dist.expected_pages()` 187 addresses (the ten new ones are built in
  Task 14 — until then `check_dist.py` on a build reports them missing).

- [ ] **Step 1: Write the failing tests**

In `tools/site/test_sync_site_data.py` replace `test_pairs_are_every_launch_page_of_hreflang_csv` and
`test_the_build_check_expects_177_pages_with_their_files` with:

```python
def test_pairs_are_every_launch_page_of_hreflang_csv():
    table = pairs()
    assert len(table) == 25 + 78 * 2
    assert table["/"] == "/es" and table["/es"] == "/"
    assert table["/one-card"] == "/es"
    assert table["/yes-no"] == "/es/si-o-no" and table["/es/si-o-no"] == "/yes-no"
    assert table["/love"] == "/es/amor" and table["/daily"] == "/es/carta-del-dia"
    assert table["/cards"] == "/es/cartas" and table["/es/cartas"] == "/cards"
    assert table["/cards/major-arcana"] == "/es/cartas/arcanos-mayores"
    assert table["/yes-no/cards"] == "/es/si-o-no" and table["/es/tiradas/3-cartas"] == "/"
    # stage 6 part 4: the service pages and their Spanish pairs (owner decision 8 of 14.11.2026)
    for en, es in (("/about", "/es/sobre-nosotros"), ("/how-readings-work", "/es/como-funcionan-las-lecturas"),
                   ("/contact", "/es/contacto"), ("/privacy", "/es/privacidad"), ("/terms", "/es/terminos")):
        assert table[en] == es and table[es] == en
    for card in deck():
        en, es = f"/cards/{card['slug_en']}", f"/es/cartas/{card['slug_es']}"
        assert table[en] == es and table[es] == en


def test_the_build_check_expects_187_pages_with_their_files():
    pages = expected_pages()
    assert len(pages) == 187  # stage 6 part 4: + 10 service pages
    assert {"/", "/es", "/404", "/es/404", "/one-card", "/es/cartas/la-luna", "/diary", "/es/cuenta", "/cards",
            "/es/tiradas/3-cartas", "/about", "/es/terminos"} <= set(pages)
    assert [dist_file(p) for p in ("/", "/es", "/es/404", "/cards/the-moon", "/cards")] == [
        "index.html", "es.html", "es/404.html", "cards/the-moon.html", "cards.html"]
```

In `tools/site/test_check_dist.py` replace `test_every_page_of_stage_6_part_1_is_expected` with:

```python
def test_every_page_of_stage_6_is_expected():
    pages = expected_pages()
    assert len(pages) == 187
    assert {"/diary", "/es/diario", "/account", "/es/cuenta", "/cards", "/yes-no/cards", "/es/tiradas/3-cartas",
            "/about", "/how-readings-work", "/es/privacidad"} <= set(pages)


def test_today_the_open_site_would_refuse_the_eight_hidden_service_pages():
    assert launched_problems() == [f"hidden page on the open site: {p} (an operator placeholder has no value)" for p in
                                   ("/about", "/contact", "/es/contacto", "/es/privacidad", "/es/sobre-nosotros",
                                    "/es/terminos", "/privacy", "/terms")]
```

and in `test_main_reports_every_problem_and_passes_a_good_build` change `"OK: 177 pages\n"` to `"OK: 187 pages\n"`.

- [ ] **Step 2: Run them to see them fail**

Run: `api/.venv/bin/pytest -q tools/site`
Expected: FAIL — `KeyError: '/about'`; 177 pages instead of 187.

- [ ] **Step 3: Allow the page type and the five new launch clusters**

In `tools/research/validate_page_map.py` replace

```python
PAGE_TYPES = {"home", "one-card", "yes-no", "love", "cards", "card-context", "spreads",
              "birth-card", "horoscope", "quiz", "pairs", "learn"}
```

with

```python
PAGE_TYPES = {"home", "one-card", "yes-no", "love", "cards", "card-context", "spreads",
              "birth-card", "horoscope", "quiz", "pairs", "learn", "service"}
```

In `tools/research/structure_hreflang.py` replace `LAUNCH_CLUSTERS = 84` with
`LAUNCH_CLUSTERS = 89  # stage 6: + about, how-readings-work, contact, privacy, terms`.

- [ ] **Step 4: Add the ten page-map rows**

Run from the repository root:

```bash
python3 - <<'EOF'
import csv
from pathlib import Path

STAGE1 = Path("docs/research/stage1")
NO = "нет данных"
COMMON = {
    "intent_label": "служебная (доверие и право)", "kd": NO, "data_date": NO,
    "decision": "самостоятельная страница",
    "rationale": "решение владельца 8 (14.11.2026): служебные и правовые страницы с испанскими парами; "
                 "спецификация этапа 6, §6; тексты — этап 5 (content/pages)",
    "priority_value": "служебная — доверие и правовые требования; спрос не изучался",
    "priority_readiness": "текст готов (этап 5); данные оператора — этап 7",
    "priority_constraints": "скрыта (noindex, вне подвала и карты сайта), пока в тексте есть метки оператора (решение 35)",
    "maintenance_cost": "низкий — правки при смене оператора, поставщиков или лимитов",
    "dependencies": "данные оператора (этап 7)", "open_questions": "", "wave": "запуск",
    "menu_item": "", "host_id": "", "pages": "1",
}
ROWS = {
    "en": [
        ("EN-125", "/about", "page:about", "About Arcana Diary", "узнать, кто делает сайт и как пишутся тексты"),
        ("EN-126", "/how-readings-work", "page:how-readings-work", "How our readings work",
         "понять, как устроено чтение: вытягивание, чтец, лимиты, кризисный ответ"),
        ("EN-127", "/contact", "page:contact", "Contact", "написать оператору сайта"),
        ("EN-128", "/privacy", "page:privacy", "Privacy policy", "узнать, какие данные собираются и как удалить их"),
        ("EN-129", "/terms", "page:terms", "Terms of use", "узнать условия пользования сервисом"),
    ],
    "es": [
        ("ES-108", "/es/sobre-nosotros", "page:about", "Sobre nosotros", "узнать, кто делает сайт и как пишутся тексты"),
        ("ES-109", "/es/como-funcionan-las-lecturas", "page:how-readings-work", "Cómo funcionan las lecturas",
         "понять, как устроено чтение: вытягивание, чтец, лимиты, кризисный ответ"),
        ("ES-110", "/es/contacto", "page:contact", "Contacto", "написать оператору сайта"),
        ("ES-111", "/es/privacidad", "page:privacy", "Aviso de privacidad", "узнать, какие данные собираются и как удалить их"),
        ("ES-112", "/es/terminos", "page:terms", "Términos de uso", "узнать условия пользования сервисом"),
    ],
}
for lang, rows in ROWS.items():
    path = STAGE1 / f"page-map-{lang}.csv"
    with open(path, encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    volume = {c: NO for c in header if c.startswith("volume_")}
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        for rid, url, entity, title, task in rows:
            writer.writerow({**COMMON, **volume, "id": rid, "page_type": "service", "working_title": title, "task": task,
                             "top_entities": title, "queries": title.lower(), "url": url, "entity_id": entity,
                             "parent_id": "EN-001" if lang == "en" else "ES-001", "breadcrumb": rid})
print("OK")
EOF
python3 tools/research/validate_page_map.py docs/research/stage1/page-map-en.csv en
python3 tools/research/validate_page_map.py docs/research/stage1/page-map-es.csv es
python3 tools/research/build_hreflang.py
python3 tools/research/validate_structure.py
```

Expected: `OK`, `OK`, `OK`, `OK: hreflang.csv — 359 строк`, `OK`.

Run: `git diff --stat docs/research/stage2/hreflang.csv && grep -c ',service,' docs/research/stage2/hreflang.csv`
Expected: `1 file changed, 10 insertions(+)`; `10`.

- [ ] **Step 5: Update the stage 2 notes**

In `docs/research/stage2/00-structure.md` replace

```
| Страниц запуска | 86 | 85 |
```

with

```
| Страниц запуска | 91 | 90 |
```

and replace `Языковых пар запуска — 84 (главная, карта дня, да/нет, любовь, хаб, старшие арканы, 78 карт)` with
`Языковых пар запуска — 89 (главная, карта дня, да/нет, любовь, хаб, старшие арканы, 78 карт, с этапа 6 — пять
служебных страниц)`.

In `docs/research/stage2/99-changelog.md` insert after the first line (`# Журнал версий …`) and its blank line:

```markdown
## Версия 1.1 — 23.11.2026 (этап 6)

- **Ответственный:** Claude (план этапа 6, задача 13).
- **Изменения:** в карты страниц добавлены служебные страницы с испанскими парами (решение владельца 8 от
  14.11.2026; спецификация этапа 6, §6): EN-125…EN-129 и ES-108…ES-112, `page_type` `service`, сущности
  `page:about`, `page:how-readings-work`, `page:contact`, `page:privacy`, `page:terms`. `hreflang.csv` пересобран
  `tools/research/build_hreflang.py` (359 строк, 89 кластеров запуска; `LAUNCH_CLUSTERS` в
  `tools/research/structure_hreflang.py`). Матрица ссылок не менялась.
- **Состояние утверждения:** по слову владельца на просмотре части 4 этапа 6.

```

- [ ] **Step 6: Sync and run the tests**

Run: `python3 tools/site/sync_site_data.py && api/.venv/bin/pytest -q tools/site tools/research`
Expected: `wrote …`; all passed.

- [ ] **Step 7: Commit**

```bash
git add docs/research/stage1/page-map-en.csv docs/research/stage1/page-map-es.csv docs/research/stage2 tools/research/validate_page_map.py tools/research/structure_hreflang.py site/src/data/pairs.json tools/site/test_sync_site_data.py tools/site/test_check_dist.py
git commit -m "structure (stage 6): service pages in the page maps and hreflang.csv — 5 new EN/ES pairs, 89 launch clusters

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: The ten service pages, hidden while they wait for the operator's data

**Files:**
- Modify: `site/src/lib/routes.ts`, `site/src/lib/breadcrumbs.ts`, `site/src/components/Footer.astro`,
  `site/src/i18n/en.ts`, `site/src/i18n/es.ts`, `deploy/build-site.sh`, `deploy/test-site-routes.sh`,
  `site/src/styles/global.css`
- Create: `site/src/pages/{about,contact,how-readings-work,privacy,terms}.astro`,
  `site/src/pages/es/{sobre-nosotros,contacto,como-funcionan-las-lecturas,privacidad,terminos}.astro`
- Test: `site/src/lib/routes.test.ts`, `site/src/lib/breadcrumbs.test.ts`, `site/src/lib/textPages.test.ts`,
  `site/src/lib/sitemap.test.ts`, `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `TextPageView` (hides a page with `isHidden`), `hiddenPaths`, `hreflangPair`.
- Produces: `type ServiceKey = 'about' | 'how_readings_work' | 'contact' | 'privacy' | 'terms'` (part of `PageKey`),
  `SERVICE_KEYS: readonly ServiceKey[]` (routes.ts); `SERVICE_LABELS: Record<ServiceKey, DictKey>`
  (breadcrumbs.ts); `crumbsFor(serviceKey)` → Home › page; the footer's second list of open service pages;
  dictionary keys `footerAbout`, `footerHowReadings`, `footerContact`, `footerPrivacy`, `footerTerms` (247);
  `deploy/build-site.sh` passes `--launched` when `deploy/.env` has `LAUNCHED=true`.

- [ ] **Step 1: Write the failing tests**

In `site/src/lib/routes.test.ts` change the first test's length to `16 + 78 + 15 + 78`, add to its address list
`'/about', '/how-readings-work', '/contact', '/privacy', '/terms', '/es/sobre-nosotros', '/es/como-funcionan-las-lecturas',
'/es/contacto', '/es/privacidad', '/es/terminos'`, and add to `'switches language by the pairs of hreflang.csv'`:

```ts
    expect(switchPath('/about')).toBe('/es/sobre-nosotros');
    expect(switchPath('/es/terminos')).toBe('/terms');
```

In `site/src/lib/breadcrumbs.test.ts` add:

```ts
  it('put a service page right under Home / Inicio', () => {
    expect(crumbsFor('how_readings_work', 'en')).toEqual([{ name: 'Home', path: '/' },
      { name: 'How our readings work', path: '/how-readings-work' }]);
    expect(crumbsFor('privacy', 'es')).toEqual([{ name: 'Inicio', path: '/es' }, { name: 'Privacidad', path: '/es/privacidad' }]);
  });
```

In `site/src/lib/textPages.test.ts` add the import `import { allPagePaths, hreflangPair } from './routes';` and the test:

```ts
  it('never pair an open page with a hidden one for hreflang', () => {
    const hidden = hiddenPaths();
    for (const path of allPagePaths()) {
      const pair = hreflangPair(path);
      if (!hidden.has(path) && pair !== null) expect(hidden.has(pair), `${path} ↔ ${pair}`).toBe(false);
    }
  });
```

In `site/src/lib/sitemap.test.ts` change `expect(paths).toHaveLength(177 - 4 - 2);` to
`expect(paths).toHaveLength(187 - 4 - 2 - 8); // no diary/account, no 404, no hidden service page` and add
`expect(paths).toContain('/how-readings-work');` after it.

In `site/src/i18n/i18n.test.ts` change `toBe(242)` to `toBe(247)`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run'`
Expected: FAIL — 177 paths instead of 187; `crumbsFor('how_readings_work', …)` is not a `PageKey`; 242 keys.

- [ ] **Step 3: Routes, breadcrumbs, dictionary**

In `site/src/lib/routes.ts` replace the `PageKey` declaration with:

```ts
/** The service pages of spec stage 6 §6 (EN and ES pairs, owner decision 8 of 14.11.2026). */
export type ServiceKey = 'about' | 'how_readings_work' | 'contact' | 'privacy' | 'terms';

export type PageKey = 'home' | 'one_card' | 'yes_no' | 'love' | 'daily' | 'diary' | 'account' | 'not_found'
  | 'cards' | 'major_arcana' | 'yes_no_cards' | 'three_cards' | ServiceKey;

export const SERVICE_KEYS: readonly ServiceKey[] = ['about', 'how_readings_work', 'contact', 'privacy', 'terms'];
```

add to `PAGE_PATHS.en` after `yes_no_cards: '/yes-no/cards',`:

```ts
    about: '/about', how_readings_work: '/how-readings-work', contact: '/contact', privacy: '/privacy', terms: '/terms',
```

and to `PAGE_PATHS.es` after `three_cards: '/es/tiradas/3-cartas',`:

```ts
    about: '/es/sobre-nosotros', how_readings_work: '/es/como-funcionan-las-lecturas', contact: '/es/contacto',
    privacy: '/es/privacidad', terms: '/es/terminos',
```

In `site/src/lib/breadcrumbs.ts` change the imports to

```ts
import { t, type DictKey } from '../i18n';
import { cardName, type DeckCard } from './deck';
import { SERVICE_KEYS, cardPath, pagePath, type PageKey, type ServiceKey } from './routes';
import type { Lang } from './types';
```

add after the `Crumb` interface:

```ts
/** The short names of the service pages: the footer and the last breadcrumb. */
export const SERVICE_LABELS: Readonly<Record<ServiceKey, DictKey>> = {
  about: 'footerAbout', how_readings_work: 'footerHowReadings', contact: 'footerContact', privacy: 'footerPrivacy',
  terms: 'footerTerms',
};

const isService = (key: PageKey): key is ServiceKey => (SERVICE_KEYS as readonly PageKey[]).includes(key);
```

and replace the `default:` branch of `crumbsFor` with:

```ts
    default:
      return isService(key) ? [home, { name: d[SERVICE_LABELS[key]], path: pagePath(key, lang) }] : [];
```

Also extend the comment at the top of `breadcrumbs.ts`: `… "3 cartas" — Inicio › 3 cartas; a service page — Home ›
page; the tools on the home level have none.`

In `site/src/i18n/en.ts` replace

```ts
  yesNoListAsk: 'Ask your question',
};
```

with

```ts
  yesNoListAsk: 'Ask your question',
  // stage 6: the service pages in the footer and their breadcrumbs (spec §3)
  footerAbout: 'About',
  footerHowReadings: 'How our readings work',
  footerContact: 'Contact',
  footerPrivacy: 'Privacy',
  footerTerms: 'Terms',
};
```

In `site/src/i18n/es.ts` replace

```ts
  yesNoListAsk: 'Haz tu pregunta',
};
```

with

```ts
  yesNoListAsk: 'Haz tu pregunta',
  // etapa 6: las páginas de servicio en el pie y en las migas
  footerAbout: 'Sobre nosotros',
  footerHowReadings: 'Cómo funcionan las lecturas',
  footerContact: 'Contacto',
  footerPrivacy: 'Privacidad',
  footerTerms: 'Términos',
};
```

- [ ] **Step 4: The ten pages**

Create each file with exactly these lines (EN files under `site/src/pages/`, ES under `site/src/pages/es/`):

`site/src/pages/about.astro`:

```astro
---
import TextPageView from '../views/TextPageView.astro';
---
<TextPageView lang="en" pageKey="about" />
```

`site/src/pages/how-readings-work.astro`:

```astro
---
import TextPageView from '../views/TextPageView.astro';
---
<TextPageView lang="en" pageKey="how_readings_work" />
```

`site/src/pages/contact.astro`:

```astro
---
import TextPageView from '../views/TextPageView.astro';
---
<TextPageView lang="en" pageKey="contact" />
```

`site/src/pages/privacy.astro`:

```astro
---
import TextPageView from '../views/TextPageView.astro';
---
<TextPageView lang="en" pageKey="privacy" />
```

`site/src/pages/terms.astro`:

```astro
---
import TextPageView from '../views/TextPageView.astro';
---
<TextPageView lang="en" pageKey="terms" />
```

`site/src/pages/es/sobre-nosotros.astro`:

```astro
---
import TextPageView from '../../views/TextPageView.astro';
---
<TextPageView lang="es" pageKey="about" />
```

`site/src/pages/es/como-funcionan-las-lecturas.astro`:

```astro
---
import TextPageView from '../../views/TextPageView.astro';
---
<TextPageView lang="es" pageKey="how_readings_work" />
```

`site/src/pages/es/contacto.astro`:

```astro
---
import TextPageView from '../../views/TextPageView.astro';
---
<TextPageView lang="es" pageKey="contact" />
```

`site/src/pages/es/privacidad.astro`:

```astro
---
import TextPageView from '../../views/TextPageView.astro';
---
<TextPageView lang="es" pageKey="privacy" />
```

`site/src/pages/es/terminos.astro`:

```astro
---
import TextPageView from '../../views/TextPageView.astro';
---
<TextPageView lang="es" pageKey="terms" />
```

- [ ] **Step 5: The footer lists the open service pages**

Replace `site/src/components/Footer.astro` with:

```astro
---
// Footer (screens 1, 12a; spec stage 6 §3): the tools; the service pages that are open (a hidden one — operator
// placeholders without a value, decision 35 — is left out); "not a guarantee", the card art credit, the help link and
// EN | ES.
import LangSwitch from './LangSwitch.astro';
import { t } from '../i18n';
import { SERVICE_LABELS } from '../lib/breadcrumbs';
import { HELP_URL, SERVICE_KEYS, pagePath } from '../lib/routes';
import { hiddenPaths } from '../lib/textPages';
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
const hidden = hiddenPaths();
const service = SERVICE_KEYS.map((key) => ({ href: pagePath(key, lang), label: d[SERVICE_LABELS[key]] }))
  .filter((link) => !hidden.has(link.href));
---
<footer class="site-footer">
  <div class="container site-footer__inner">
    <nav aria-label={d.footerLabel}>
      <ul>
        {links.map((link) => <li><a href={link.href}>{link.label}</a></li>)}
      </ul>
      {service.length > 0 ? (
        <ul class="site-footer__service">
          {service.map((link) => <li><a href={link.href}>{link.label}</a></li>)}
        </ul>
      ) : null}
    </nav>
    <p>{d.disclaimer}</p>
    <p>{d.cardArtCredit}</p>
    <p class="help-line">{d.helpLead} <a href={HELP_URL} rel="noopener noreferrer">{d.helpLink}</a></p>
    <LangSwitch lang={lang} path={path} />
  </div>
</footer>
```

Append to `site/src/styles/global.css`:

```css

.site-footer__service { margin-top: var(--space-2); font-size: var(--font-size-small); }
```

- [ ] **Step 6: The open site refuses a hidden page**

In `deploy/build-site.sh` replace the last line `python3 "$ROOT/tools/site/check_dist.py"` with:

```bash
# открытый сайт (LAUNCHED=true в deploy/.env; grep -qx ничего не печатает): скрытая служебная страница — ошибка
# сборки (решение 35)
LAUNCHED_FLAG=""
if [ -f "$ROOT/deploy/.env" ] && grep -qx 'LAUNCHED=true' "$ROOT/deploy/.env"; then LAUNCHED_FLAG="--launched"; fi
python3 "$ROOT/tools/site/check_dist.py" $LAUNCHED_FLAG
```

- [ ] **Step 7: Route test of the service pages**

In `deploy/test-site-routes.sh`, after the stage 6 block added in Task 7 (after the line
`expect "sitemap.xml без дневника" …`), insert:

```bash
# stage 6, часть 4: служебные страницы; с метками оператора — noindex и вне sitemap.xml
for path in /about /how-readings-work /contact /privacy /terms /es/sobre-nosotros /es/como-funcionan-las-lecturas \
  /es/contacto /es/privacidad /es/terminos; do
  expect "$path" "$(status "$path")" 200
done
expect "/about — скрыта (meta robots)" "$("${CURL[@]}" "$URL/about" | grep -c 'name="robots" content="noindex, nofollow"')" 1
expect "/es/privacidad — скрыта (meta robots)" "$("${CURL[@]}" "$URL/es/privacidad" | grep -c 'name="robots" content="noindex, nofollow"')" 1
expect "/how-readings-work — открыта" "$(canonical /how-readings-work)" "https://arcanadiary.com/how-readings-work"
expect "/es/como-funcionan-las-lecturas — страница ES" "$(html_lang /es/como-funcionan-las-lecturas)" '<html lang="es"'
expect "sitemap.xml без скрытых" "$("${CURL[@]}" "$URL/sitemap.xml" | grep -c '/about<\|/privacy<\|/es/terminos<')" 0
```

- [ ] **Step 8: Tests, types, build, routes, look**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && api/.venv/bin/pytest -q tools/site && deploy/build-site.sh && deploy/test-site-routes.sh`
Expected: all pass, `0 errors`, `OK: 187 pages`, `OK: адреса страниц и 404`.

Run: `python3 tools/site/check_dist.py --launched | tail -3`
Expected: three of the eight lines `hidden page on the open site: … (an operator placeholder has no value)` — the
guard works; the exit code is 1. (The stage build itself runs without `--launched`.)

Run: `grep -o 'site-footer__service"><li><a href="[^"]*">[^<]*</a></li></ul>' site/dist/index.html`
Expected: `site-footer__service"><li><a href="/how-readings-work">How our readings work</a></li></ul>` — one item only.

- [ ] **Step 9: Commit**

```bash
git add site/src/lib/routes.ts site/src/lib/routes.test.ts site/src/lib/breadcrumbs.ts site/src/lib/breadcrumbs.test.ts site/src/lib/textPages.test.ts site/src/lib/sitemap.test.ts site/src/components/Footer.astro site/src/pages site/src/i18n site/src/styles/global.css deploy/build-site.sh deploy/test-site-routes.sh
git commit -m "site (stage 6): ten service pages from the stage 5 texts, hidden while operator placeholders remain; open ones in the footer; launch guard

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Privacy links at the AI provider line and the consents

**Files:**
- Modify: `site/src/lib/textPages.ts`, `site/src/islands/ReadingIsland.tsx`, `site/src/components/ui/useSaveToDiary.tsx`,
  `site/src/components/ui/SaveSheet.tsx`, `site/src/islands/AccountIsland.tsx`, `site/src/views/HomeView.astro`,
  `site/src/views/ToolView.astro`, `site/src/views/CardPageView.astro`, `site/src/views/AccountView.astro`,
  `site/src/i18n/en.ts`, `site/src/i18n/es.ts`
- Test: `site/src/lib/textPages.test.ts`, `site/src/islands/ReadingIsland.test.tsx`,
  `site/src/components/ui/SaveSheet.test.tsx`, `site/src/islands/AccountIsland.test.tsx`, `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `hiddenPaths`, `pagePath`.
- Produces: `openPagePath(key: PageKey, lang: Lang): string | null` (textPages.ts) — the address, or `null` while the
  page is hidden; optional prop `privacyHref?: string` on `ReadingIsland`, `SaveSheet`, `AccountIsland` and option
  `privacyHref?: string` on `useSaveToDiary`; dictionary key `privacyLink` (248). While `/privacy` is hidden the views
  pass `undefined` and nothing changes on the page (spec §6: the links appear together with the page).

- [ ] **Step 1: Write the failing tests**

In `site/src/lib/textPages.test.ts` add `openPagePath` to the import from `./textPages` and add:

```ts
  it('give the address of a page only while it is open', () => {
    expect(openPagePath('privacy', 'en')).toBeNull();
    expect(openPagePath('how_readings_work', 'es')).toBe('/es/como-funcionan-las-lecturas');
  });
```

In `site/src/islands/ReadingIsland.test.tsx` add at the end of the file:

```tsx
describe('ReadingIsland: the privacy link at the AI provider line (spec stage 6 §6)', () => {
  it('links the policy when the page is open', async () => {
    const { root } = await mount(<ReadingIsland lang="en" page="love" privacyHref="/privacy" />);
    expect(byText<HTMLAnchorElement>(root, t('en').privacyLink, 'a').getAttribute('href')).toBe('/privacy');
  });

  it('shows no link while the page is hidden', async () => {
    const { root } = await mount(island());
    expect(queryText(root, t('en').privacyLink, 'a')).toBeNull();
  });
});
```

In `site/src/components/ui/SaveSheet.test.tsx` add at the end of the file:

```tsx
describe('the save sheet: privacy link next to the reminder consent (spec stage 6 §6)', () => {
  it('links the policy only when it is given', async () => {
    const f = fakes();
    const { root } = await mount(
      <SaveSheet lang="en" readingId="r1" auth={f.auth} google={false} accountApi={f.accountApi}
        origin="https://arcana.test" onClose={() => {}} privacyHref="/privacy" />,
    );
    expect(byText<HTMLAnchorElement>(root, 'Privacy policy', 'a').getAttribute('href')).toBe('/privacy');
    cleanup();
    const again = await mount(sheet(fakes()));
    expect(queryText(again.root, 'Privacy policy', 'a')).toBeNull();
  });
});
```

In `site/src/islands/AccountIsland.test.tsx`, inside `describe('the account page (spec 4.4b §6)', …)`, add:

```tsx
  it('links the privacy policy under the consent once the policy page is open (stage 6 §6)', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} privacyHref="/privacy" />);
    expect(byText<HTMLAnchorElement>(root, 'Privacy policy', 'a').getAttribute('href')).toBe('/privacy');
  });
```

In `site/src/i18n/i18n.test.ts` change `toBe(247)` to `toBe(248)`.

- [ ] **Step 2: Run them to see them fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/lib/textPages.test.ts src/islands/ReadingIsland.test.tsx src/components/ui/SaveSheet.test.tsx src/islands/AccountIsland.test.tsx src/i18n/i18n.test.ts'`
Expected: FAIL — `openPagePath` is not exported; `no element with the text "Privacy policy"`; 247 keys.

- [ ] **Step 3: Implement**

In `site/src/lib/textPages.ts` add the import `import { pagePath, type PageKey } from './routes';` and at the end:

```ts
/** The address of a page, or null while it is hidden: links to it appear together with the page (spec stage 6 §6). */
export function openPagePath(key: PageKey, lang: Lang): string | null {
  const path = pagePath(key, lang);
  return hiddenPaths().has(path) ? null : path;
}
```

In `site/src/i18n/en.ts` replace

```ts
  footerTerms: 'Terms',
};
```

with

```ts
  footerTerms: 'Terms',
  // stage 6: next to the AI provider line and the e-mail consents, once the privacy page is open
  privacyLink: 'Privacy policy',
};
```

In `site/src/i18n/es.ts` replace

```ts
  footerTerms: 'Términos',
};
```

with

```ts
  footerTerms: 'Términos',
  // etapa 6: junto a la línea del proveedor de IA y a los consentimientos, cuando la página de privacidad se abre
  privacyLink: 'Aviso de privacidad',
};
```

In `site/src/islands/ReadingIsland.tsx`:
- in `interface Props` add after `showBacks?: boolean;`:

```ts
  /** The privacy page, once it is open (spec stage 6 §6); no link while it is hidden. */
  privacyHref?: string;
```

- change the function signature to
  `export default function ReadingIsland({ lang, page, cardId, cardName, showBacks = false, privacyHref }: Props) {`
- change the `useSaveToDiary(` call to:

```ts
  const saving = useSaveToDiary({ lang, tool: drawn.current.tool, readingId: state.reading?.id ?? null,
    signedIn: drawn.current.signedIn, privacyHref });
```

- replace `<p class="provider-line">{d.providerLine}</p>` with:

```tsx
        <p class="provider-line">{d.providerLine}{privacyHref ? <> <a href={privacyHref}>{d.privacyLink}</a></> : null}</p>
```

In `site/src/components/ui/useSaveToDiary.tsx` add to `interface SaveToDiaryOptions` after `origin?: string;`:

```ts
  /** The privacy page next to the reminder consent, once it is open (spec stage 6 §6). */
  privacyHref?: string;
```

and change the `<SaveSheet …` element to:

```tsx
    <SaveSheet lang={lang} readingId={readingId} auth={auth} google={config.google} accountApi={api}
      origin={options.origin ?? location.origin} onClose={closeSheet} privacyHref={options.privacyHref} />
```

In `site/src/components/ui/SaveSheet.tsx` add to `interface Props` after `onClose: () => void;`:

```ts
  privacyHref?: string; // the privacy page, once it is open (spec stage 6 §6)
```

change the signature to
`export function SaveSheet({ lang, readingId, auth, google, accountApi, origin, onClose, privacyHref }: Props) {`
and insert right after the closing `</label>` of the reminder checkbox:

```tsx
      {privacyHref ? <p class="small"><a href={privacyHref}>{d.privacyLink}</a></p> : null}
```

In `site/src/islands/AccountIsland.tsx` add to `interface Props` after `lang: Lang;`:

```ts
  /** The privacy page under the consent, once it is open (spec stage 6 §6). */
  privacyHref?: string;
```

change the start of the signature `export default function AccountIsland({ lang, api: given,` to
`export default function AccountIsland({ lang, privacyHref, api: given,` (the rest of the line stays), and insert right after
`<p id="account-consent-note" class="small muted">{d.accountConsentNote}</p>`:

```tsx
        {privacyHref ? <p class="small"><a href={privacyHref}>{d.privacyLink}</a></p> : null}
```

In the views pass the prop (it is `undefined` while `/privacy` is hidden):
- `site/src/views/HomeView.astro`: add `openPagePath` to the import from `../lib/textPages`, add
  `const privacyHref = openPagePath('privacy', lang) ?? undefined;` after `const text = …`, and change the island to
  `<ReadingIsland client:load lang={lang} page="home" showBacks privacyHref={privacyHref} />`.
- `site/src/views/ToolView.astro`: the same import and constant; island
  `<ReadingIsland client:load lang={lang} page={page} privacyHref={privacyHref} />`.
- `site/src/views/CardPageView.astro`: add `import { openPagePath } from '../lib/textPages';`, the constant after
  `const about = …`, and add `privacyHref={privacyHref}` to the `<ReadingIsland … />` element.
- `site/src/views/AccountView.astro`: add `import { openPagePath } from '../lib/textPages';`, the constant after
  `const d = t(lang);`, and change the island to `<AccountIsland client:load lang={lang} privacyHref={privacyHref} />`.

- [ ] **Step 4: Tests, types, build**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && deploy/build-site.sh`
Expected: all pass, `0 errors`, `OK: 187 pages`.

Run: `grep -c 'Privacy policy' site/dist/index.html`
Expected: `0` — the privacy page is hidden, so no link yet.

- [ ] **Step 5: Commit**

```bash
git add site/src/lib/textPages.ts site/src/lib/textPages.test.ts site/src/islands site/src/components/ui/useSaveToDiary.tsx site/src/components/ui/SaveSheet.tsx site/src/components/ui/SaveSheet.test.tsx site/src/views site/src/i18n
git commit -m "site (stage 6): privacy links at the AI provider line and the consents, shown once the privacy page opens

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Deploy checkpoint — Part 4

Stop here. Before asking the owner: all tests, build (`OK: 187 pages`), route test pass; branch review (Sonnet) done.
Show the owner: `/how-readings-work` and `/es/como-funcionan-las-lecturas` (open, in the footer), one hidden page
(`/privacy`: noindex, visible placeholders such as `{operator_name}` — expected until stage 7), the footer, the new
footer labels. Remind the owner that `LAUNCHED=true` now refuses the build while any service page is hidden. Deploy
only on the owner's word.

---

# Part 5 — Internal links and the audit

Ends deployable: every static link of the launch wave of the stage 2 matrix is on the built pages and the build
proves it; the semantic markup of six pages is audited and fixed.

### Task 16: The address links of the matrix in the templates

**Files:**
- Modify: `site/src/views/HomeView.astro`, `site/src/views/ToolView.astro`, `site/src/views/CardPageView.astro`,
  `site/src/components/TextBlocks.astro`, `site/src/i18n/en.ts`, `site/src/i18n/es.ts`
- Test: `site/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: `pagePath`, the views of Parts 2–3.
- Produces: `<TextBlocks blocks links? />` — `links: Readonly<Record<blockId, { href: string; text: string }>>` adds a
  `<p class="block-link">` link at the end of that block; dictionary keys `fmtCards`, `fmtCardsHint`, `fmtThree`,
  `fmtThreeHint`, `yesNoMethodLink`, `cardLoveLink`, `cardYesNoLink` (255); `fmtLove` (EN) becomes `Love reading`.
  Template links of the matrix already made by Parts 1–3: breadcrumbs (`@major` → Major Arcana), facts-line suit
  (`@minor` → hub), previous/next (`@neighbors`), hub/Major/yes-no lists (`@cards`, `@major`), "All 78 cards", hub and
  Major draw buttons, yes/no "Ask your question".

| Row | From → to | Anchor | Where |
|---|---|---|---|
| L-EN-04 | `/yes-no` → `/yes-no/cards` | How we read yes and no | end of block `rule` |
| L-EN-19 | `/` → `/love` | Love reading | "Other ways to ask" (`fmtLove`) |
| L-EN-21, L-ES-21 | home → hub | Card meanings / Significados de las cartas | "Other ways to ask" (`fmtCards`) |
| L-ES-20 | `/es` → `/es/tiradas/3-cartas` | Tirada de 3 cartas | "Otras formas de preguntar" (`fmtThree`) |
| L-ES-06 | ES card `#amor` → `/es/amor` | Haz una tirada de amor | end of the love block (both languages) |
| L-ES-07 | ES card `#si-o-no` → `/es/si-o-no` | Pregunta sí o no | end of the yes/no block (both languages) |

- [ ] **Step 1: Write the failing test**

In `site/src/i18n/i18n.test.ts` change `toBe(248)` to `toBe(255)` and add inside `describe('dictionaries', …)`:

```ts
  it('use the anchors of the stage 2 link matrix (docs/research/stage2/links-{en,es}.csv)', () => {
    expect([t('en').fmtLove, t('en').fmtCards, t('en').yesNoMethodLink]).toEqual([
      'Love reading', 'Card meanings', 'How we read yes and no']);
    expect([t('es').fmtThree, t('es').fmtCards, t('es').cardLoveLink, t('es').cardYesNoLink]).toEqual([
      'Tirada de 3 cartas', 'Significados de las cartas', 'Haz una tirada de amor', 'Pregunta sí o no']);
    expect([t('en').drawForQuestion, t('es').drawForQuestion, t('en').allCardsLink, t('es').allCardsLink,
      t('en').yesNoListAsk]).toEqual(['Draw a card for your question', 'Saca una carta para tu pregunta', 'All 78 cards',
      'Las 78 cartas', 'Ask your question']);
  });
```

- [ ] **Step 2: Run it to see it fail**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run src/i18n/i18n.test.ts'`
Expected: FAIL — 248 keys; `fmtLove` is `Love`.

- [ ] **Step 3: Dictionary**

In `site/src/i18n/en.ts` change `fmtLove: 'Love',` to `fmtLove: 'Love reading', // anchor of L-EN-19` and replace

```ts
  privacyLink: 'Privacy policy',
};
```

with

```ts
  privacyLink: 'Privacy policy',
  // stage 6: anchors of the stage 2 link matrix (links-en.csv, links-es.csv, wave "запуск")
  fmtCards: 'Card meanings',
  fmtCardsHint: 'What each of the 78 cards means',
  fmtThree: 'Three cards',
  fmtThreeHint: "Past, present and where it's heading",
  yesNoMethodLink: 'How we read yes and no',
  cardLoveLink: 'Try a love reading',
  cardYesNoLink: 'Ask a yes or no question',
};
```

In `site/src/i18n/es.ts` replace

```ts
  privacyLink: 'Aviso de privacidad',
};
```

with

```ts
  privacyLink: 'Aviso de privacidad',
  // etapa 6: textos de enlace de la matriz de la etapa 2 (links-es.csv, ola «запуск»)
  fmtCards: 'Significados de las cartas',
  fmtCardsHint: 'Qué significa cada una de las 78 cartas',
  fmtThree: 'Tirada de 3 cartas',
  fmtThreeHint: 'Pasado, presente y hacia dónde va',
  yesNoMethodLink: 'Cómo leemos el sí o no',
  cardLoveLink: 'Haz una tirada de amor',
  cardYesNoLink: 'Pregunta sí o no',
};
```

- [ ] **Step 4: Templates**

Replace `site/src/components/TextBlocks.astro` with:

```astro
---
// The blocks of a stage 5 text (content/pages): a section per block, its id the block id, an H2 and the paragraphs;
// `links` puts a link of the stage 2 matrix at the end of a block (spec stage 6 §7: address links sit in the blocks,
// next to the terms of their context).
import type { TextBlock } from '../lib/textPages';

interface Props {
  blocks: readonly TextBlock[];
  links?: Readonly<Record<string, { href: string; text: string }>>;
}

const { blocks, links = {} } = Astro.props;
---
{blocks.map((block) => (
  <section class="page-section prose" id={block.id} aria-labelledby={`${block.id}-title`}>
    <h2 class="h2" id={`${block.id}-title`}>{block.heading}</h2>
    {block.paragraphs.map((paragraph) => <p>{paragraph}</p>)}
    {links[block.id] ? <p class="block-link"><a href={links[block.id].href}>{links[block.id].text}</a></p> : null}
  </section>
))}
```

In `site/src/views/ToolView.astro` add after `const crumbs = crumbsFor(page, lang);`:

```ts
// L-EN-04: the yes/no tool links the card list that explains its rule (Spanish has no such list)
const links = page === 'yes_no' && lang === 'en'
  ? { rule: { href: pagePath('yes_no_cards', lang), text: d.yesNoMethodLink } } : {};
```

and change `<TextBlocks blocks={text.blocks} />` to `<TextBlocks blocks={text.blocks} links={links} />`.

In `site/src/views/HomeView.astro` replace the `formats` constant with:

```ts
// the format switch (stage 2 matrix L-EN-17…21, L-ES-17…21)
const formats = [
  ...(lang === 'en' ? [{ href: pagePath('one_card', lang), name: d.fmtOneCard, hint: d.fmtOneCardHint }] : []),
  { href: pagePath('yes_no', lang), name: d.fmtYesNo, hint: d.fmtYesNoHint },
  { href: pagePath('love', lang), name: d.fmtLove, hint: d.fmtLoveHint },
  { href: pagePath('daily', lang), name: d.fmtDaily, hint: d.fmtDailyHint },
  ...(lang === 'es' ? [{ href: pagePath('three_cards', lang), name: d.fmtThree, hint: d.fmtThreeHint }] : []),
  { href: pagePath('cards', lang), name: d.fmtCards, hint: d.fmtCardsHint },
];
```

In `site/src/views/CardPageView.astro` insert after the line
`{block.id === 'work_money' ? <p class="block-note">{s.work_money.money_line}</p> : null}`:

```astro
          {block.id === 'love' ? <p class="block-link"><a href={pagePath('love', lang)}>{d.cardLoveLink}</a></p> : null}
          {block.id === 'yes_no' ? <p class="block-link"><a href={pagePath('yes_no', lang)}>{d.cardYesNoLink}</a></p> : null}
```

- [ ] **Step 5: Tests, types, build**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && deploy/build-site.sh`
Expected: all pass, `0 errors`, `OK: 187 pages`.

Run: `grep -o '<a href="/yes-no/cards">How we read yes and no</a>' site/dist/yes-no.html; grep -o 'href="/es/tiradas/3-cartas"' site/dist/es.html | head -1; grep -o 'id="amor".\{0,9000\}Haz una tirada de amor' site/dist/es/cartas/la-luna.html | wc -l`
Expected: the link; `href="/es/tiradas/3-cartas"`; `1`.

- [ ] **Step 6: Commit**

```bash
git add site/src/components/TextBlocks.astro site/src/views/HomeView.astro site/src/views/ToolView.astro site/src/views/CardPageView.astro site/src/i18n
git commit -m "site (stage 6): address links of the stage 2 matrix — format switch, yes/no method link, love and yes/no links of the card pages

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: check_links.py — every launch link of the matrix on the built site

**Files:**
- Create: `tools/site/check_links.py`, `tools/site/test_check_links.py`
- Modify: `deploy/build-site.sh`

**Interfaces:**
- Consumes: `docs/research/stage2/links-{en,es}.csv` (wave `запуск`), `docs/research/stage1/page-map-{en,es}.csv`
  (id → url, section anchors), `site/src/data/deck.json`, `site/src/data/cardpages/template-strings.json` (suit
  names), `site/dist`.
- Produces: `parse_links(html) -> list[dict]` (`tag`, `href`, `text`, `ids`), `href_path(href) -> str | None`,
  `class Site(dist=None)` (`deck`, `sources(row, lang)`, `targets(row, lang, card)`, `links(path)`),
  `is_runtime(site, row, lang) -> bool`, `check_row(site, row, lang) -> tuple[list[str], int]`,
  `launch_rows() -> list[tuple[str, dict]]`, `main(dist=None) -> int`; the build runs it after `check_dist.py`.

- [ ] **Step 1: Write the failing tests**

`tools/site/test_check_links.py`:

```python
"""tools/site/check_links.py on hand-made pages (spec stage 6 §7)."""
from check_links import Site, check_row, href_path, is_runtime, launch_rows, main, parse_links

LAUNCH = "запуск"


def write(dist, name, text):
    file = dist / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def test_links_carry_their_text_and_the_ids_around_them():
    html = ('<section id="amor"><p>Text <a href="/es/amor">Haz una <b>tirada</b>\n de amor</a></p><img src="x.webp">'
            '<button type="submit">Saca una carta</button></section>'
            '<a href="https://arcanadiary.com/es#una-carta">Una</a>')
    links = parse_links(html)
    assert [(l["tag"], l["href"], l["text"], sorted(l["ids"])) for l in links] == [
        ("a", "/es/amor", "Haz una tirada de amor", ["amor"]),
        ("button", None, "Saca una carta", ["amor"]),
        ("a", "https://arcanadiary.com/es#una-carta", "Una", []),
    ]
    assert href_path("https://arcanadiary.com/es#una-carta") == "/es"
    assert href_path("/cards#swords") == "/cards"
    assert href_path("https://arcanadiary.com/") == "/"


def test_a_page_to_page_link_is_found_or_reported(tmp_path):
    row = {"link_id": "T-1", "from_id": "EN-093", "to_id": "EN-014", "anchor_pattern": "All 78 cards", "wave": LAUNCH}
    write(tmp_path, "cards/major-arcana.html", '<a href="/cards">All 78 cards</a>')
    assert check_row(Site(tmp_path), row, "en") == ([], 1)
    write(tmp_path, "cards/major-arcana.html", '<a href="/cards/the-fool">All 78 cards</a>')
    assert check_row(Site(tmp_path), row, "en") == (["T-1: /cards/major-arcana has no link to /cards «All 78 cards»"], 1)
    (tmp_path / "cards/major-arcana.html").unlink()
    assert check_row(Site(tmp_path), row, "en") == (["T-1: no page /cards/major-arcana in site/dist"], 0)


def test_a_section_row_needs_its_link_inside_the_section(tmp_path):
    site = Site(tmp_path)
    row = {"link_id": "T-2", "from_id": "ES-093", "to_id": "ES-009", "anchor_pattern": "Haz una tirada de amor",
           "wave": LAUNCH}
    for card in site.deck:
        write(tmp_path, f"es/cartas/{card['slug_es']}.html",
              '<section id="amor"><p><a href="/es/amor">Haz una tirada de amor</a></p></section>')
    assert check_row(site, row, "es") == ([], 78)
    write(tmp_path, "es/cartas/la-luna.html", '<section id="amor"></section><a href="/es/amor">Haz una tirada de amor</a>')
    assert check_row(Site(tmp_path), row, "es") == (
        ["T-2: /es/cartas/la-luna has no link to /es/amor «Haz una tirada de amor» inside #amor"], 78)


def test_card_rows_fill_in_the_card_and_the_suit_names(tmp_path):
    site = Site(tmp_path)
    nav = {"link_id": "T-3", "from_id": "@cards", "to_id": "@neighbors", "anchor_pattern": "{card_name}", "wave": LAUNCH}
    suit = {"link_id": "T-4", "from_id": "@minor", "to_id": "EN-014", "anchor_pattern": "{suit_name}", "wave": LAUNCH}
    deck = site.deck
    for i, card in enumerate(deck):
        before, after = deck[i - 1], deck[(i + 1) % len(deck)]
        suit_link = f'<a href="/cards#{card["suit"]}">{card["suit"].title()}</a>' if card["suit"] else ""
        write(tmp_path, f"cards/{card['slug_en']}.html",
              f'<a href="/cards/{before["slug_en"]}"><small>← Previous</small>{before["name_en"]}</a>'
              f'<a href="/cards/{after["slug_en"]}"><small>Next →</small>{after["name_en"]}</a>{suit_link}')
    assert check_row(site, nav, "en") == ([], 156)
    assert check_row(site, suit, "en") == ([], 56)


def test_the_card_page_draw_button_counts_for_its_own_row_only(tmp_path):
    site = Site(tmp_path)
    row = {"link_id": "L-EN-07", "from_id": "@cards", "to_id": "EN-001", "anchor_pattern": "Draw a card for your question",
           "wave": LAUNCH}
    for card in site.deck:
        write(tmp_path, f"cards/{card['slug_en']}.html", '<button type="submit">Draw a card for your question</button>')
    assert check_row(site, row, "en") == ([], 78)
    problems, checked = check_row(Site(tmp_path), {**row, "link_id": "T-5"}, "en")
    assert len(problems) == 78 and checked == 78


def test_links_drawn_by_islands_are_listed_not_checked(tmp_path, capsys):
    site = Site(tmp_path)
    rows = launch_rows()
    assert len(rows) == 48
    assert [r["link_id"] for lang, r in rows if is_runtime(site, r, lang)] == [
        "L-EN-01", "L-EN-02", "L-EN-03", "L-EN-15", "L-EN-16", "L-EN-31",
        "L-ES-01", "L-ES-02", "L-ES-03", "L-ES-04", "L-ES-15", "L-ES-16", "L-ES-23"]
    assert main(tmp_path) == 1
    assert "L-EN-04: no page /yes-no in site/dist" in capsys.readouterr().out
```

- [ ] **Step 2: Run them to see them fail**

Run: `api/.venv/bin/pytest -q tools/site/test_check_links.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_links'`.

- [ ] **Step 3: Implement**

`tools/site/check_links.py`:

```python
"""Stage 6 part 5 (spec §7): every link of the launch wave of docs/research/stage2/links-{en,es}.csv is on the built
pages in site/dist — the link is there, goes to the right address (the #fragment of the href does not count) and its
text contains the row's anchor_pattern with {card_name} / {suit_name} filled in (case-insensitive). A row that starts
in a section (ES-093: /es/cartas/{slug_es}#amor) needs its link inside the element with that id.

Listed, not checked: rows whose links an island draws after a reading or on the Card of the Day — to "@drawn",
"@diary" or to a section of the drawn card (ES-093, ES-094) — are never in site/dist. L-EN-07 and L-ES-05 ("Draw a
card for your question" from every card page) are the card page's own draw button: the reading panel is on the page,
so a <button> with that text counts for these two rows.

  python3 tools/site/check_links.py   — prints "OK: N rows, M links" and the rows drawn by islands, or the problems
"""
import csv
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
STAGE1 = ROOT / "docs/research/stage1"
STAGE2 = ROOT / "docs/research/stage2"
SITE_URL = "https://arcanadiary.com"
LAUNCH = "запуск"
RUNTIME = {"@drawn", "@diary"}
IN_PLACE = {"L-EN-07", "L-ES-05"}
CARD_SETS = {"@cards", "@major", "@minor"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Links(HTMLParser):
    """Every <a> and <button>: tag, href, text (spaces collapsed) and the ids of the elements around it."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.open: list[dict] = []
        self.found: list[dict] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("a", "button"):
            self.open.append({"tag": tag, "href": a.get("href"), "text": [], "ids": {i for _, i in self.stack if i}})
        if tag not in VOID:
            self.stack.append((tag, a.get("id")))

    def handle_endtag(self, tag):
        if tag in ("a", "button") and self.open and self.open[-1]["tag"] == tag:
            link = self.open.pop()
            link["text"] = " ".join(" ".join(link["text"]).split())
            self.found.append(link)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        for link in self.open:
            link["text"].append(data)


def parse_links(html: str) -> list[dict]:
    parser = Links()
    parser.feed(html)
    parser.close()
    return parser.found


def href_path(href: str | None) -> str | None:
    if href is None:
        return None
    if href.startswith(SITE_URL):
        href = href[len(SITE_URL):] or "/"
    return href.split("#", 1)[0] or None


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def dist_file(path: str) -> str:
    return "index.html" if path == "/" else f"{path[1:]}.html"


class Site:
    def __init__(self, dist: Path | None = None) -> None:
        self.dist = dist or SITE / "dist"
        self.deck: list[dict] = json.loads((SITE / "src/data/deck.json").read_text(encoding="utf-8"))
        self.strings = json.loads((SITE / "src/data/cardpages/template-strings.json").read_text(encoding="utf-8"))
        self.maps = {lang: {r["id"]: r for r in read_csv(STAGE1 / f"page-map-{lang}.csv")} for lang in ("en", "es")}
        self._links: dict[str, list[dict] | None] = {}

    @staticmethod
    def card_url(card: dict, lang: str) -> str:
        return f"/cards/{card['slug_en']}" if lang == "en" else f"/es/cartas/{card['slug_es']}"

    def cards(self, token: str) -> list[dict]:
        if token == "@major":
            return [c for c in self.deck if c["arcana"] == "major"]
        if token == "@minor":
            return [c for c in self.deck if c["arcana"] == "minor"]
        return list(self.deck)

    def neighbors(self, card: dict) -> list[dict]:
        i = self.deck.index(card)
        return [self.deck[(i - 1) % len(self.deck)], self.deck[(i + 1) % len(self.deck)]]

    def url(self, page_id: str, lang: str) -> str:
        return self.maps[lang][page_id]["url"]

    def links(self, path: str) -> list[dict] | None:
        if path not in self._links:
            file = self.dist / dist_file(path)
            self._links[path] = parse_links(file.read_text(encoding="utf-8")) if file.is_file() else None
        return self._links[path]

    def sources(self, row: dict, lang: str) -> list[tuple[str, str | None, dict | None]]:
        """(page, id of the section the link must sit in, the card of that page) for each page the row starts on."""
        src = row["from_id"]
        if src in CARD_SETS:
            return [(self.card_url(c, lang), None, c) for c in self.cards(src)]
        base, _, anchor = self.url(src, lang).partition("#")
        if "{" in base:
            return [(self.card_url(c, lang), anchor or None, c) for c in self.deck]
        return [(base, anchor or None, None)]

    def targets(self, row: dict, lang: str, card: dict | None) -> list[tuple[str, str]]:
        """(address, anchor text) of each link the row asks for on one page."""
        pattern, to = row["anchor_pattern"], row["to_id"]
        if to in ("@cards", "@major"):
            return [(self.card_url(c, lang), pattern.replace("{card_name}", c[f"name_{lang}"])) for c in self.cards(to)]
        if to == "@neighbors" and card is not None:
            return [(self.card_url(c, lang), pattern.replace("{card_name}", c[f"name_{lang}"])) for c in self.neighbors(card)]
        text = pattern
        if card is not None:
            text = text.replace("{card_name}", card[f"name_{lang}"])
            if card["suit"]:
                text = text.replace("{suit_name}", self.strings[lang]["facts"]["suits"][card["suit"]])
        return [(self.url(to, lang).split("#", 1)[0], text)]


def is_runtime(site: Site, row: dict, lang: str) -> bool:
    """A link an island draws: to "@drawn"/"@diary", or to a section of a card page from a page that is not one."""
    to = row["to_id"]
    return to in RUNTIME or (to not in CARD_SETS | {"@neighbors"} and "{" in site.url(to, lang))


def has_link(links: list[dict], url: str, text: str, section: str | None, button: bool) -> bool:
    want = text.casefold()
    for link in links:
        if section is not None and section not in link["ids"]:
            continue
        if want not in link["text"].casefold():
            continue
        if link["tag"] == "a" and href_path(link["href"]) == url:
            return True
        if button and link["tag"] == "button":
            return True
    return False


def check_row(site: Site, row: dict, lang: str) -> tuple[list[str], int]:
    problems: list[str] = []
    checked = 0
    for page, section, card in site.sources(row, lang):
        links = site.links(page)
        if links is None:
            problems.append(f"{row['link_id']}: no page {page} in site/dist")
            continue
        for url, text in site.targets(row, lang, card):
            checked += 1
            if not has_link(links, url, text, section, row["link_id"] in IN_PLACE):
                where = f" inside #{section}" if section else ""
                problems.append(f"{row['link_id']}: {page} has no link to {url} «{text}»{where}")
    return problems, checked


def launch_rows() -> list[tuple[str, dict]]:
    return [(lang, r) for lang in ("en", "es") for r in read_csv(STAGE2 / f"links-{lang}.csv") if r["wave"] == LAUNCH]


def main(dist: Path | None = None) -> int:
    site = Site(dist)
    problems: list[str] = []
    rows = links = 0
    runtime: list[str] = []
    for lang, row in launch_rows():
        if is_runtime(site, row, lang):
            runtime.append(row["link_id"])
            continue
        found, checked = check_row(site, row, lang)
        problems += found
        rows += 1
        links += checked
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"OK: {rows} rows, {links} links")
    print(f"drawn by islands, not in site/dist: {', '.join(runtime)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `api/.venv/bin/pytest -q tools/site`
Expected: all passed.

- [ ] **Step 5: Run it on the real build, then make the build run it**

Run: `python3 tools/site/check_links.py`
Expected:

```
OK: 35 rows, 1078 links
drawn by islands, not in site/dist: L-EN-01, L-EN-02, L-EN-03, L-EN-15, L-EN-16, L-EN-31, L-ES-01, L-ES-02, L-ES-03, L-ES-04, L-ES-15, L-ES-16, L-ES-23
```

If a row fails, fix the template that should carry it (never the CSV) and build again.

In `deploy/build-site.sh` append after the `check_dist.py` line:

```bash
python3 "$ROOT/tools/site/check_links.py"
```

and extend the header comment's last sentence with `; ссылки матрицы этапа 2 (tools/site/check_links.py)`.

Run: `deploy/build-site.sh`
Expected: `OK: 187 pages`, then the two lines above.

- [ ] **Step 6: Commit**

```bash
git add tools/site/check_links.py tools/site/test_check_links.py deploy/build-site.sh
git commit -m "tools (stage 6): check_links.py — every launch link of the stage 2 matrix on the built site; the build runs it

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 18: Semantic markup audit of six pages and template fixes

**Files:**
- Create: `docs/research/stage6/semantic-audit.md`
- Modify: the templates the findings name (`site/src/views/*.astro`, `site/src/components/*.astro`,
  `site/src/styles/global.css`) and, for each fixed finding that a script can see, `tools/site/check_dist.py` +
  `tools/site/test_check_dist.py`

**Interfaces:**
- Consumes: the built `site/dist` of Task 17; skill `anthropic-skills:semanticrank-orchestrator` (named "semanticrank"
  in the spec).
- Produces: the audit file (format below); fixed templates; a regression check per fixed, checkable finding.

The six pages (spec §7): `site/dist/cards/the-moon.html` (card EN), `site/dist/es/cartas/la-luna.html` (card ES),
`site/dist/cards.html` (hub), `site/dist/cards/major-arcana.html` (Major Arcana), `site/dist/yes-no/cards.html`
(yes/no), `site/dist/es.html` (home ES).

- [ ] **Step 1: Build and copy the six pages for the audit**

Run:

```bash
deploy/build-site.sh
mkdir -p /tmp/stage6-audit
for f in cards/the-moon es/cartas/la-luna cards cards/major-arcana yes-no/cards es; do
  cp "site/dist/$f.html" "/tmp/stage6-audit/$(echo "$f" | tr / -).html"
done
ls /tmp/stage6-audit
```

Expected: six files `cards-the-moon.html`, `es-cartas-la-luna.html`, `cards.html`, `cards-major-arcana.html`,
`yes-no-cards.html`, `es.html`.

- [ ] **Step 2: Run the audit**

Invoke the skill `anthropic-skills:semanticrank-orchestrator` once per file of `/tmp/stage6-audit/`, telling it: the
page's address on `https://arcanadiary.com`, its language, its job (card meaning / hub of 78 cards / list of 22 /
yes-no list / Spanish home with the reading tool), and that the text is fixed (owner-reviewed stage 5) — only markup,
headings, landmarks, lists, tables, links and structured data may change.

- [ ] **Step 3: Write the findings**

Create `docs/research/stage6/semantic-audit.md`:

```markdown
# Этап 6. Аудит семантической вёрстки (semanticrank)

Дата: <date of the run>. Страницы: /cards/the-moon, /es/cartas/la-luna, /cards, /cards/major-arcana, /yes-no/cards,
/es (сборка ветки stage6-templates, коммит <short sha>). Текст страниц не меняется (этап 5, прочитан владельцем) —
только разметка.

| № | Страница | Находка | Важность | Шаблон | Решение |
|---|---|---|---|---|---|
| 1 | … | … | обязательно / желательно / можно | `site/src/…` | исправлено (коммит) / отложено: причина |
```

One row per finding of the skill, in its words, translated to Russian; "Важность" — `обязательно` for anything that
breaks one H1 per page, heading order, landmarks, list/table semantics, link text, `lang` of quotes, or JSON-LD
validity; `желательно` for extraction aids; `можно` for the rest.

- [ ] **Step 4: Fix every "обязательно" finding in the templates**

For each such row: change the template it names (never the text in `content/` and never the dictionaries' reviewed
values), keeping the Global Constraints (tokens, 44 px, focus ring). When the finding is visible in HTML (for example
"two H1", "a table without `th`", "heading levels skip H2"), add a check of it to `tools/site/check_dist.py` with a
test in `tools/site/test_check_dist.py` written first (fails on a hand-made page that has the problem, passes on a
good one), following the pattern of `head_problems` / `test_each_missing_or_wrong_head_part_is_named`. Mark the row
`исправлено (<sha>)`. "желательно" rows are fixed when the change is local to one template; otherwise `отложено` with
the reason.

- [ ] **Step 5: Run every check**

Run: `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -e npm_config_cache=/tmp/.npm -e npm_config_update_notifier=false -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run && npx astro check' && api/.venv/bin/pytest -q tools/site && deploy/build-site.sh && deploy/test-site-routes.sh`
Expected: all pass, `0 errors`, `OK: 187 pages`, `OK: 35 rows, 1078 links`, `OK: адреса страниц и 404`.

- [ ] **Step 6: Commit**

```bash
git add docs/research/stage6/semantic-audit.md site/src tools/site
git commit -m "stage 6: semantic markup audit of six pages (semanticrank) and the template fixes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
rm -rf /tmp/stage6-audit
```

### Deploy checkpoint — Part 5 (end of stage 6)

Stop here. Before asking the owner: every check of Step 5 passes; branch review (Sonnet) done; the final review
(Fable) if the owner wants it (spec §8). Show the owner `docs/research/stage6/semantic-audit.md`, the output of
`tools/site/check_links.py` and the 13 island-drawn rows (decision 8) for a decision. Merge of `stage6-templates`
and the deploy happen only on the owner's word.

---

### Task 19: Island links under the matrix (owner decision 38, 23.11.2026)

The owner chose "the screen follows the matrix": the links the islands draw under drawn cards must match the
launch rows of `docs/research/stage2/links-{en,es}.csv` that Task 17 only lists (L-EN-01/02/03/15/16/31,
L-ES-01/02/03/04/15/16/23) — target, anchor text by `anchor_pattern`, and the section anchor where the row names one
(love reading → the card page's love section, `#amor` in ES; yes/no → the card page's yes/no section, `#si-o-no` in ES;
Card of the Day → "Today's card: {card_name}" / the ES pattern, plus "Save to diary" where the row names it).

**Files:**
- Modify: the islands and ui components that render drawn-card links (`site/src/islands/ReadingIsland.tsx`,
  `site/src/islands/DailyIsland.tsx`, `site/src/components/ui/NightRoom.tsx`, `site/src/components/ui/CardFace.tsx`
  or wherever the link is built — grep `fullMeaning` / the current anchor keys), `site/src/i18n/{en,es}.ts` (new or
  changed anchor strings; placeholders tested by `i18n.test.ts`).
- Test: the islands' existing `*.test.tsx` (assert href and text per tool and language).
- Modify: `tools/site/check_links.py` list of island-only rows → each listed row now has a vitest assertion; the
  script prints which test covers it.

- [ ] **Step 1:** For each listed row, write a failing vitest case in the island's test file: render the tool with a
  fixed draw, find the link under each drawn card, assert `href` (card path + section hash from the row) and the
  visible text (the row's `anchor_pattern` with `{card_name}`, `{verdict}` filled).
- [ ] **Step 2:** Run `docker run --rm -u "$(id -u):$(id -g)" -e ASTRO_TELEMETRY_DISABLED=1 -v "$PWD/site:/app" -w /app node:22 sh -c 'npx vitest run'` — the new cases fail.
- [ ] **Step 3:** Change the link building (one helper `drawnCardLink(card, tool, lang)` in `site/src/lib/routes.ts`
  returning `{href, text}` from a small table keyed by tool, mirroring the rows) and use it in every island.
- [ ] **Step 4:** Run vitest and `npx astro check` — all pass.
- [ ] **Step 5:** Commit: `git commit -m "Stage 6: drawn-card links follow the stage 2 matrix (owner decision 38)"` with the
  Co-Authored-By line.

## Self-review

**Spec coverage**

| Spec | Task |
|---|---|
| §1 decision 34 — five parts, deploy after each by the owner's word | checkpoints after Tasks 7, 9, 12, 15, 18 |
| §1 decision 35 — hidden service pages (noindex, out of menu, footer, sitemap; open site refuses them) | 2 (`isHidden`), 6 (`TextPageView` noindex), 7 (sitemap, `check_dist --launched`), 14 (pages, footer, build flag) |
| §1 decision 36 — limits and verdict counts at build from server code and deck | 1 (`facts.json`), 2 (`fillFacts`), 7 (`sync --check` in the build) |
| §2 sync: card pages, template strings, pages, facts (4 constants by text, 3 counts, editor) | 1 |
| §2 `facts.ts` fill; hidden when a placeholder has no value; build check of left placeholders | 2, 7 (`placeholder_problems`) |
| §3 head: description, canonical, hreflang + x-default, unpaired self only, OG/Twitter (card scan or common image), noindex | 3 (`seo.ts`), 5 (`Base.astro`), 9 (card image) |
| §3 JSON-LD: BreadcrumbList, FAQPage, card Article (author/publisher Org, dateModified, reviewedBy Person editor, image, isBasedOn), hubs CollectionPage + ItemList, tools WebPage | 4, 5, 6, 9, 10, 12 |
| §3 breadcrumbs of every page kind | 3, 5, 9, 11, 14 |
| §3 menu "Card Meanings"; footer About, How our readings work, Contact, Privacy, Terms — only not hidden | 6, 14 |
| §3 own sitemap with xhtml:link, robots Sitemap line, hidden/noindex out | 7 |
| §3 routes: new PageKeys, `allPagePaths` grows, service pairs in `hreflang.csv` and `pairs.json`, file/folder conflict test | 3, 6, 7, 13, 14 |
| §4 card page: order of the elements, Waite block (blockquote lang=en, cite, ES translation, harsh line, boundary), money line, yes/no from data, in_a_reading note, pairs table, ask_yourself list, CTA with existing ReadingIsland, FAQ details first open, related, About (sources, method with editor and date, deck note), mentions → first mention link, replaces CardView, ES addresses | 8, 9 |
| §5 tools: eyebrow from dictionary, H1/lead/blocks/FAQ/title/description from the text | 5, 10 |
| §5 3 cartas with ReadingIsland three-card mode, event tool three_cards | 6, 11 |
| §5 hubs, Major (keyword from meanings), yes/no list from deck.json, lists from data, no elements | 12 |
| §6 ten service pages, hidden; privacy links at the provider line and consents appear with the page | 14, 15 |
| §7 template links and address links by anchor_pattern; `check_links.py` on `site/dist` | 6, 9, 12, 16, 17 |
| §7 semanticrank audit of six pages and template fixes | 18 |
| §8 vitest: facts.fill, breadcrumbs, JSON-LD, hreflang/canonical, card blocks (several cards), hiding | 2, 3, 4, 8, 14 |
| §8 `check_dist.py`: pages, title, description, canonical, hreflang, JSON-LD parses, no placeholders, hidden noindex and out of sitemap, page count; `test-site-routes.sh` new addresses and conflict | 7, 13, 14 |
| §8 API unchanged; reviews Sonnet / Fable; merge and deploy by the owner | Global Constraints, checkpoints |

**Placeholder scan:** Task 18 is an audit whose findings are not known in advance; its steps give the exact
commands, the file format, the decision rule and the regression-test pattern instead of code. No other step leaves
code or values open.

**Type consistency:** names used across tasks — `FACTS`, `fillFacts`, `missingFacts` (2); `TextPage`, `FaqItem`,
`textPage`, `filledPage`, `isHidden`, `hiddenPaths`, `openPagePath` (2, 15); `CardPageData`, `TemplateStrings`,
`TEMPLATE_STRINGS`, `CARD_PAGES`, `cardPage` (2); `hreflangPair`, `SUIT_IDS`, `suitPath`, `Suit`, `SERVICE_KEYS`,
`ServiceKey` (3, 8, 14); `absoluteUrl`, `alternates`, `DEFAULT_IMAGE` (3); `Crumb`, `crumbsFor`, `cardCrumbs`,
`SERVICE_LABELS` (3, 14); `JsonLd`, `LdItem`, `breadcrumbLd`, `faqLd`, `webPageLd`, `collectionLd`, `cardLd`,
`ldScript` (4); `indexablePaths`, `sitemapXml` (7); `SECTION_IDS`, `Segment`, `mentionSegments`, `segmentsOf` and the
other card helpers (8); `ListedCard`, `SUITS`, `majorCards`, `suitCards`, `verdictCards`, `firstKeyword`, `ldItems`
(12); Python `canonical`, `expected_alternates`, `hidden_pages`, `noindex_pages`, `indexable_pages`,
`launched_problems` (7), `check_row`, `is_runtime`, `launch_rows`, `Site` (17). Dictionary counts: 225 → 232 (3) →
239 (8) → 240 (11) → 242 (12) → 247 (14) → 248 (15) → 255 (16). Page counts: 171 → 177 (Task 1/6) → 187 (13/14).

## Execution

Plan complete. Two ways to run it: **subagent-driven** (recommended — superpowers:subagent-driven-development, a fresh
subagent per task and a reviewer gate between tasks) or **inline** (superpowers:executing-plans, with the
checkpoints above). In both, stop at every Deploy checkpoint for the owner.
