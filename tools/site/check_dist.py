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
