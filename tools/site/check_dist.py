"""After the site build (spec 4.4a §3, 4.4b §5–§6, stage 6 §8): every page exists in site/dist for EN and ES; each
indexable page has a title, a description, its canonical address, hreflang by its language pair (en, es and
x-default for a mutual pair of two indexable pages, no hreflang at all otherwise) and JSON-LD that parses; no
hreflang link of any page points at a page that is not indexable; no page that is not hidden shows a {placeholder};
the diary, the account and the hidden service pages say noindex and stay out of sitemap.xml, which lists every
indexable page (plain <loc> entries: hreflang lives only in the head); robots.txt names the sitemap; no page that
draws a reading loads the sign-in library at start (spec 4.4b §3); the markup findings of the stage 6 audit that a
script can see (markup_problems: one link per address in <main> outside <nav>, aria-current in the footer, link text
that does not run words together, the review date of a card page in <time datetime>).

The pages are the language pairs of site/src/data/pairs.json, the two 404 pages and the four private pages; Astro
writes one file per page (build.format "file"): / → index.html, /es → es.html, /cards/x → cards/x.html. A service
page is hidden while its text has a placeholder without a value in site/src/data/facts.json (owner decision 35; the
same rule as site/src/lib/textPages.ts).

  python3 tools/site/check_dist.py             — prints "OK: N pages" or the problems (exit 1)
  python3 tools/site/check_dist.py --launched  — the same for the open site (plan decision 13): a hidden page and a
                                               robots.txt with "Disallow: /" are problems too
"""
import functools
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
SITE_URL = "https://arcanadiary.com"
# a robots.txt rule that closes the whole site: "Disallow: /" (or "/*"), any case and spacing
DISALLOW_ALL = re.compile(r"^\s*disallow\s*:\s*/\*?\s*$", re.I | re.M)
EXTRA = ("/404", "/es/404")
PRIVATE = ("/diary", "/es/diario", "/account", "/es/cuenta")  # noindex, outside hreflang.csv
DATA_FILES = ("data/daily-en.json", "data/daily-es.json", "sitemap.xml", "robots.txt")
# = SERVICE_PAGE_IDS of site/src/lib/textPages.ts
SERVICE_PAGE_IDS = frozenset({"about", "contact", "how-readings-work", "privacy", "terms", "sobre-nosotros", "contacto",
                              "como-funcionan-las-lecturas", "privacidad", "terminos"})
# the pages with a night room or the Card of the Day: a guest there never downloads the sign-in library
READING_PAGES = ("/", "/one-card", "/yes-no", "/love", "/daily", "/cards/the-moon", "/es", "/es/si-o-no", "/es/amor",
                 "/es/carta-del-dia", "/es/cartas/la-luna", "/es/tiradas/3-cartas")
AUTH_MARKERS = ("GoTrueClient", "supabase.auth.token")  # strings found only in @supabase/auth-js
ROBOTS = re.compile(r'<meta name="robots" content="noindex, nofollow"\s*/?>')
ENTRY = re.compile(r'(?:component-url|renderer-url|src)="(/_astro/[^"]+\.js)"')
# static imports and re-exports only: import("…") (a chunk loaded later) is not followed
STATIC_IMPORT = re.compile(r'\b(?:import|export)\s*(?:[\w$*\s{},]*?\bfrom\s*)?["\'](\.{1,2}/[^"\']+|/_astro/[^"\']+)["\']')
PLACEHOLDER = re.compile(r"\{(\w+)\}")
LEFT_PLACEHOLDER = re.compile(r"\{\w+\}")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)


@functools.lru_cache(maxsize=None)
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
    """en, es and x-default for a mutual pair of two indexable pages; none for any other page (stage 2 spec §3)."""
    table = pairs()
    pair = table.get(path)
    if pair is None or table.get(pair) != path or {path, pair} & noindex_pages():
        return set()
    en, es = (path, pair) if lang_of(path) == "en" else (pair, path)
    return {("en", canonical(en)), ("es", canonical(es)), ("x-default", canonical(en))}


def page_texts(page: dict) -> list[str]:
    return [page["title"], page["description"], page["h1"], page["lead"], page["capsule"] or "",
            *[t for b in page["blocks"] for t in (b["heading"], *b["paragraphs"])],
            *[t for f in page["faq"] for t in (f["q"], f["a"])]]


@functools.lru_cache(maxsize=None)
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


def built_noindex(dist: Path) -> set[str]:
    """Pages whose built file carries a robots meta with "noindex" in any spelling."""
    found = set()
    for path in expected_pages():
        file = dist / dist_file(path)
        if file.is_file() and "noindex" in parse_head(file).robots:
            found.add(path)
    return found


def indexable_pages(dist: Path | None = None) -> list[str]:
    """Pages that must be indexable; with a build, also without the pages that say noindex in any spelling."""
    noindex = noindex_pages() | (built_noindex(dist) if dist else set())
    return [p for p in expected_pages() if p not in EXTRA and p not in noindex]


def missing(dist: Path) -> list[str]:
    files = [dist_file(p) for p in expected_pages()] + list(DATA_FILES)
    return [f for f in files if not (dist / f).is_file()]


def unexpected_pages(dist: Path) -> list[str]:
    """A *.html file in the build that is not one of the expected pages is neither checked nor in the sitemap."""
    known = {dist_file(p) for p in expected_pages()}
    found = {f.relative_to(dist).as_posix() for f in dist.rglob("*.html")} if dist.is_dir() else set()
    return [f"unexpected page: site/dist/{name}" for name in sorted(found - known)]


def robots_problems(dist: Path) -> list[str]:
    """The private and the hidden pages carry the exact noindex meta; no other page says noindex in any spelling."""
    problems = []
    noindex = noindex_pages()
    for path in expected_pages():
        file = dist / dist_file(path)
        if not file.is_file():
            continue  # missing() reports it
        if path in noindex:
            if not ROBOTS.search(file.read_text(encoding="utf-8")):
                problems.append(f"no noindex meta: site/dist/{dist_file(path)}")
        elif "noindex" in parse_head(file).robots:
            problems.append(f"unexpected noindex meta: site/dist/{dist_file(path)}")
    return problems


class Head(HTMLParser):
    """Title, description, canonical, hreflang links and JSON-LD texts of a page."""

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description: str | None = None
        self.canonicals: list[str | None] = []
        self.robots = ""
        self._in_head = True
        self.alternates: set[tuple[str, str]] = set()
        self.ld: list[str] = []
        self._in_title = False
        self._ld: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title" and self._in_head:
            self._in_title = True
        elif tag == "meta" and a.get("name") == "description":
            self.description = a.get("content") or ""
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.robots += " " + (a.get("content") or "").lower()
        elif tag == "link" and a.get("rel") == "canonical" and self._in_head:
            self.canonicals.append(a.get("href"))
        elif tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
            self.alternates.add((a["hreflang"], a.get("href") or ""))
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._ld = []

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
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


def parse_head(file: Path) -> Head:
    head = Head()
    head.feed(file.read_text(encoding="utf-8"))
    return head


def head_problems(dist: Path) -> list[str]:
    problems = []
    for path in indexable_pages(dist):
        file = dist / dist_file(path)
        if not file.is_file():
            continue
        head = parse_head(file)
        name = f"site/dist/{dist_file(path)}"
        want = expected_alternates(path)
        if not head.title.strip():
            problems.append(f"no title: {name}")
        if not (head.description or "").strip():
            problems.append(f"no description: {name}")
        if head.canonicals != [canonical(path)]:
            problems.append(f"canonical {head.canonicals or None} instead of one {canonical(path)}: {name}")
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


def hreflang_target_problems(dist: Path) -> list[str]:
    """No hreflang link of any page points at a page that is not indexable (noindex, hidden, 404 or unknown)."""
    problems = []
    indexable = {canonical(p) for p in indexable_pages(dist)}
    for path in expected_pages():
        file = dist / dist_file(path)
        if not file.is_file():
            continue
        head = parse_head(file)
        problems += [f"hreflang {href} is not an indexable page: site/dist/{dist_file(path)}"
                     for href in sorted({href for _, href in head.alternates} - indexable)]
    return problems


def placeholder_problems(dist: Path) -> list[str]:
    """A {placeholder} left in the text or the JSON-LD of a page that is not hidden (other scripts and styles are not)."""
    problems = []
    hidden = hidden_pages()
    for path in expected_pages():
        file = dist / dist_file(path)
        if path in hidden or not file.is_file():
            continue
        html = file.read_text(encoding="utf-8")
        name = f"site/dist/{dist_file(path)}"
        text = SCRIPT_STYLE.sub("", html)
        problems += [f"placeholder {mark} left: {name}" for mark in sorted(set(LEFT_PLACEHOLDER.findall(text)))]
        ld = {mark for chunk in parse_head(file).ld for mark in LEFT_PLACEHOLDER.findall(chunk)}
        problems += [f"placeholder {mark} left in JSON-LD: {name}" for mark in sorted(ld)]
    return problems


def sitemap_problems(dist: Path) -> list[str]:
    file = dist / "sitemap.xml"
    if not file.is_file():
        return []  # missing() reports it
    try:
        root = ET.parse(file).getroot()
    except ET.ParseError as error:
        return [f"sitemap.xml is not well-formed XML: {error}"]
    if root.tag != f"{{{SITEMAP_NS}}}urlset":
        return [f"sitemap.xml root is {root.tag}, not {{{SITEMAP_NS}}}urlset"]
    problems = []
    locs: list[str] = []
    for entry in root:
        children = [child.tag for child in entry]
        if entry.tag != f"{{{SITEMAP_NS}}}url" or children != [f"{{{SITEMAP_NS}}}loc"]:
            problems.append(f"sitemap.xml entry is not a <url> with exactly one <loc>: {entry.tag} {children}")
            continue
        locs.append((entry[0].text or "").strip())
    if any("}" in el.tag and el.tag.split("}")[0] != "{" + SITEMAP_NS for el in root.iter()):
        problems.append("sitemap.xml has elements outside the sitemaps.org namespace (no xhtml links, hreflang is in the head)")
    problems += [f"sitemap.xml lists {url} twice" for url in sorted({u for u in locs if locs.count(u) > 1})]
    want = {canonical(p) for p in indexable_pages(dist)}
    return (problems + [f"sitemap.xml lacks {url}" for url in sorted(want - set(locs))]
            + [f"sitemap.xml lists {url}, not an indexable page" for url in sorted(set(locs) - want)])


def robots_txt_problems(dist: Path) -> list[str]:
    file = dist / "robots.txt"
    if file.is_file() and f"Sitemap: {SITE_URL}/sitemap.xml" not in file.read_text(encoding="utf-8").splitlines():
        return ["robots.txt does not name the sitemap"]
    return []


def launched_problems(dist: Path) -> list[str]:
    """The open site (--launched): no hidden service page, and robots.txt does not close the whole site."""
    problems = [f"hidden page on the open site: {path} (an operator placeholder has no value)"
                for path in sorted(hidden_pages() & set(expected_pages()))]
    file = dist / "robots.txt"
    if file.is_file() and DISALLOW_ALL.search(file.read_text(encoding="utf-8")):
        problems.append("robots.txt closes the whole site (Disallow: /) on the open site")
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


def card_paths(lang: str) -> dict[str, str]:
    """Path of every card of site/src/data/deck.json -> its card_id, in one language."""
    base, key = ("/cards/", "slug_en") if lang == "en" else ("/es/cartas/", "slug_es")
    deck = json.loads((SITE / "src/data/deck.json").read_text(encoding="utf-8"))
    return {base + card[key]: card["card_id"] for card in deck}


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a" and dict(attrs).get("href"):
            self.hrefs.append(dict(attrs)["href"])


def hidden_link_problems(dist: Path) -> list[str]:
    """No page links to a hidden service page (decision 35): not the footer, the menu, the language switch or a text."""
    hidden = hidden_pages()
    problems = []
    for path in expected_pages():
        file = dist / dist_file(path)
        if not file.is_file():
            continue
        found = Links()
        found.feed(file.read_text(encoding="utf-8"))
        for href in sorted({h.split("#")[0].split("?")[0].removeprefix(SITE_URL).rstrip("/") or "/" for h in found.hrefs} & hidden):
            problems.append(f"link to the hidden page {href}: site/dist/{dist_file(path)}")
    return problems


def card_link_sets(html: str, lang: str) -> set[str]:
    links = Links()
    links.feed(html)
    return set(links.hrefs) & set(card_paths(lang))


def list_problems(dist: Path) -> list[str]:
    """Card lists of stage 6: hubs 78 distinct card links, Major Arcana pages 22, yes/no page 78 with 45/13/20 by block."""
    deck = json.loads((SITE / "src/data/deck.json").read_text(encoding="utf-8"))
    votes = {v: sum(c["yes_no"] == v for c in deck) for v in ("yes", "no", "unclear")}
    majors = sum(c["arcana"] == "major" for c in deck)
    wants = [("/cards", "en", len(deck)), ("/es/cartas", "es", len(deck)),
             ("/cards/major-arcana", "en", majors), ("/es/cartas/arcanos-mayores", "es", majors),
             ("/yes-no/cards", "en", len(deck))]
    problems = []
    for path, lang, want in wants:
        file = dist / dist_file(path)
        if file.is_file():
            got = len(card_link_sets(file.read_text(encoding="utf-8"), lang))
            if got != want:
                problems.append(f"{got} distinct card links instead of {want}: site/dist/{dist_file(path)}")
    file = dist / dist_file("/yes-no/cards")
    if file.is_file():
        html = file.read_text(encoding="utf-8")
        for block, verdict in (("lean-yes", "yes"), ("lean-no", "no"), ("not-clear-yet", "unclear")):
            m = re.search(rf'<section\b[^>]*\bid="{block}".*?</section>', html, re.S)
            got = len(card_link_sets(m.group(0), "en")) if m else 0
            if got != votes[verdict]:
                problems.append(f"{got} card links in block {block} instead of {votes[verdict]}: site/dist/{dist_file('/yes-no/cards')}")
    return problems


class Markup(HTMLParser):
    """The markup findings of the stage 6 audit (docs/research/stage6/10-semantic-audit.md) that a script can see: the
    links of <main> outside <nav>, the footer links, the text of every link as it is read (where a tag boundary falls
    without a space between two words) and the <time datetime> elements."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    STICKY = set(".,;:!?)]}»”’…")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.main_links: list[str] = []
        self.footer_links: list[tuple[str, str | None]] = []
        self.joined: list[str] = []
        self.times: list[str] = []
        self._link: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self._link is not None:
            self._link["boundary"] = True
        if tag == "time" and a.get("datetime"):
            self.times.append(a["datetime"])
        if tag == "a" and a.get("href"):
            href = a["href"]
            if "main" in self.stack and "nav" not in self.stack and not href.startswith("#"):
                self.main_links.append(href)
            if "footer" in self.stack:
                self.footer_links.append((href, a.get("aria-current")))
            self._link = {"text": "", "boundary": False, "joined": False}
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "a" and self._link is not None:
            if self._link["joined"]:
                self.joined.append(" ".join(self._link["text"].split()))
            self._link = None
        elif self._link is not None:
            self._link["boundary"] = True
        if tag in self.stack:
            del self.stack[len(self.stack) - 1 - self.stack[::-1].index(tag):]

    def handle_data(self, data):
        link = self._link
        if link is None or not data:
            return
        if (link["boundary"] and link["text"] and not link["text"][-1].isspace() and not data[0].isspace()
                and data[0] not in self.STICKY):
            link["joined"] = True
        link["text"] += data
        link["boundary"] = False


def page_href(href: str) -> str:
    """An internal href without the site address and the #fragment (two links that differ only there are one URL)."""
    return href.removeprefix(SITE_URL).split("#")[0] or "/"


def markup_problems(dist: Path) -> list[str]:
    """Every built page: one link per address in <main> outside <nav> (SEO Monster 2027, 4.4: the first link in the DOM
    gives the anchor, a second one adds nothing; breadcrumbs, related cards and previous/next are navigation in <nav>); a footer link
    to the page itself carries aria-current="page"; no link text runs two words together at a tag boundary; a card
    page gives its review date as <time datetime>."""
    cards = set(card_paths("en")) | set(card_paths("es"))
    problems = []
    for path in sorted(expected_pages(), key=dist_file):
        file = dist / dist_file(path)
        if not file.is_file():
            continue
        name = f"site/dist/{dist_file(path)}"
        page = Markup()
        page.feed(file.read_text(encoding="utf-8"))
        counts: dict[str, int] = {}
        for href in page.main_links:
            counts[page_href(href)] = counts.get(page_href(href), 0) + 1
        problems += [f"{n} links to {href} in <main> outside <nav>: {name}" for href, n in counts.items() if n > 1]
        problems += [f'footer link to the page itself without aria-current="page": {page_href(href)}: {name}'
                     for href, current in page.footer_links if page_href(href) == path and current != "page"]
        problems += [f"link text runs together «{text}»: {name}" for text in page.joined]
        if path in cards and not any(re.fullmatch(r"\d{4}-\d{2}-\d{2}", t) for t in page.times):
            problems.append(f"no <time datetime> of the review date: {name}")
    return problems


def main(dist: Path | None = None, launched: bool = False) -> int:
    dist = dist or SITE / "dist"
    problems = ([f"missing: site/dist/{name}" for name in missing(dist)] + unexpected_pages(dist)
                + robots_problems(dist) + head_problems(dist) + hreflang_target_problems(dist)
                + placeholder_problems(dist) + sitemap_problems(dist) + robots_txt_problems(dist)
                + list_problems(dist) + auth_problems(dist) + hidden_link_problems(dist) + markup_problems(dist)
                + (launched_problems(dist) if launched else []))
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"OK: {len(expected_pages())} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main(launched="--launched" in sys.argv[1:]))
