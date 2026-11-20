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
