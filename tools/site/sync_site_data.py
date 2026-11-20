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
