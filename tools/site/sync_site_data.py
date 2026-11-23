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


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _load(name: str):
    return json.loads((CARDS / name).read_text(encoding="utf-8"))


def deck() -> list[dict]:
    names = {lang: {m["card_id"]: m["name"] for m in _load(f"meanings.{lang}.json")} for lang in ("en", "es")}
    cards = sorted(_load("deck.json"), key=lambda c: c["order"])
    return [{"card_id": c["card_id"], "numeral": c["numeral"], "arcana": c["arcana"], "suit": c["suit"],
             "yes_no": c["yes_no"], "image": c["image"], "slug_en": c["slug_en"], "slug_es": c["slug_es"],
             "name_en": names["en"][c["card_id"]], "name_es": names["es"][c["card_id"]]} for c in cards]


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
