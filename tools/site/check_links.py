"""Stage 6 part 5 (spec §7): every link of the launch wave of docs/research/stage2/links-{en,es}.csv is on the built
pages in site/dist — the link is there, goes to the right address (the #fragment of the href does not count) and its
text IS the row's anchor_pattern with {card_name} / {suit_name} filled in (case-insensitive; the whole link text, the
text of a child element or a text node of the link, a leading Roman numeral allowed). Only links inside <main> count:
the menu and the footer do not satisfy a row. A row that starts in a section (ES-093: /es/cartas/{slug_es}#amor,
L-EN-04 in #rule, previous/next in #card-nav) needs its link inside the element with that id. A {suit_name} row needs the
#fragment of the hub's own suit block for that card. Every <a href> of <main>, header and footer must be canonical and
live (no 404, no query, no trailing slash, the #fragment is an id of the target). Context terms are reported, not
enforced: "terms: L-EN-21 1/2" lists the rows whose links have fewer than 2 of their terms in a 350-character window.

Listed, not checked: rows whose links an island draws after a reading or on the Card of the Day — to "@drawn",
"@diary" or to a section of the drawn card (ES-093, ES-094) — are never in site/dist. Owner decision 38 (23.11.2026):
the islands follow these rows (drawnCardLink in site/src/lib/routes.ts), and each row is asserted, href and text, by a
vitest case whose title names the row id: ISLAND_TESTS says which file, and the script fails when the file does not
name the row or a runtime row has neither a test nor a NOT_BUILT reason. L-EN-07 and L-ES-05 ("Draw a
card for your question" from every card page) are the card page's own draw button: the reading panel is on the page,
so a <button> with that text counts for these two rows.

  python3 tools/site/check_links.py   — prints "OK: N rows, M links" and the rows drawn by islands with the test
                                        that covers each, or the problems
"""
import csv
import json
import re
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
PINNED = {"L-EN-04": "rule"}
NEIGHBORS_SECTION = "card-nav"
NIGHT_TEST = "site/src/components/ui/NightRoom.test.tsx"
DAILY_TEST = "site/src/islands/DailyIsland.test.tsx"
ISLAND_TESTS = {row: NIGHT_TEST for row in ("L-EN-01", "L-EN-02", "L-EN-03", "L-EN-31", "L-ES-01", "L-ES-02", "L-ES-03",
                                            "L-ES-04", "L-ES-23")} | {"L-EN-15": DAILY_TEST, "L-ES-15": DAILY_TEST}
NOT_BUILT = {row: "the Card of the Day is not a reading and is not saved to the diary (spec 4.4b §2.10); owner decision"
             for row in ("L-EN-16", "L-ES-16")}
WINDOW = 350
ZONES = {"main", "header", "footer"}
SKIP_TEXT = {"script", "style"}
INLINE = {"a", "b", "i", "em", "strong", "span", "small", "abbr", "mark", "sup", "sub"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Links(HTMLParser):
    """Every <a> and <button>: tag, href, text (spaces collapsed), the ids and zones (main/header/footer) around it,
    its parts (child elements' texts and its own text nodes), where it sits in the page text; plus all ids of the page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.open: list[dict] = []
        self.found: list[dict] = []
        self.ids: set[str] = set()
        self.text: list[str] = []
        self.pos = 0

    def _put(self, chunk: str) -> None:
        self.text.append(chunk)
        self.pos += len(chunk)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag not in INLINE:
            self._put(" ")
        for link in self.open:
            if tag not in VOID:
                link["frames"].append([])
        if tag in ("a", "button"):
            self.open.append({"tag": tag, "href": a.get("href"), "text": [], "frames": [], "direct": [], "parts": [],
                              "ids": {i for _, i in self.stack if i}, "zones": {t for t, _ in self.stack} & ZONES,
                              "start": self.pos})
        if tag not in VOID:
            self.stack.append((tag, a.get("id")))

    def handle_endtag(self, tag):
        if tag in ("a", "button") and self.open and self.open[-1]["tag"] == tag:
            link = self.open.pop()
            link["text"] = " ".join(" ".join(link["text"]).split())
            link["end"] = self.pos
            link["parts"] = [" ".join(p.split()) for p in link["parts"] if p.strip()]
            link["direct"] = [" ".join(p.split()) for p in link["direct"] if p.strip()]
            self.found.append(link)
        elif tag not in VOID:
            for link in self.open:
                if link["frames"]:
                    link["parts"].append(" ".join(link["frames"].pop()))
        if tag not in INLINE:
            self._put(" ")
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.stack and self.stack[-1][0] in SKIP_TEXT:
            return
        chunk = re.sub(r"\s+", " ", data)
        self._put(chunk)
        for link in self.open:
            link["text"].append(data)
            if link["frames"]:
                for frame in link["frames"]:
                    frame.append(data)
            else:
                link["direct"].append(data)


def parse_page(html: str) -> Links:
    parser = Links()
    parser.feed(html)
    parser.close()
    return parser


def parse_links(html: str) -> list[dict]:
    return parse_page(html).found


def split_href(href: str | None) -> tuple[str | None, str | None]:
    """(path, #fragment) of an internal href, the site's own absolute address included; None path for no href."""
    if href is None:
        return None, None
    if href.startswith(SITE_URL):
        href = href[len(SITE_URL):] or "/"
    path, _, fragment = href.partition("#")
    return (path or None), (fragment or None)


def href_path(href: str | None) -> str | None:
    return split_href(href)[0]


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def dist_file(path: str) -> str:
    return "index.html" if path == "/" else f"{path[1:]}.html"


class UnknownId(KeyError):
    """A from_id / to_id of a matrix row that the page map does not have."""

    def __str__(self) -> str:
        return f"unknown page id {self.args[0]}"


class Site:
    def __init__(self, dist: Path | None = None) -> None:
        self.dist = dist or SITE / "dist"
        self.deck: list[dict] = json.loads((SITE / "src/data/deck.json").read_text(encoding="utf-8"))
        self.strings = json.loads((SITE / "src/data/cardpages/template-strings.json").read_text(encoding="utf-8"))
        self.maps = {lang: {r["id"]: r for r in read_csv(STAGE1 / f"page-map-{lang}.csv")} for lang in ("en", "es")}
        self._pages: dict[str, Links | None] = {}

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
        try:
            return self.maps[lang][page_id]["url"]
        except KeyError:
            raise UnknownId(page_id) from None

    def page(self, path: str) -> Links | None:
        if path not in self._pages:
            file = self.dist / dist_file(path)
            self._pages[path] = parse_page(file.read_text(encoding="utf-8")) if file.is_file() else None
        return self._pages[path]

    def links(self, path: str) -> list[dict] | None:
        page = self.page(path)
        return None if page is None else page.found

    def sources(self, row: dict, lang: str) -> list[tuple[str, str | None, dict | None]]:
        """(page, id of the section the link must sit in, the card of that page) for each page the row starts on."""
        src = row["from_id"]
        if src in CARD_SETS:
            section = NEIGHBORS_SECTION if row["to_id"] == "@neighbors" else None
            return [(self.card_url(c, lang), section, c) for c in self.cards(src)]
        base, _, anchor = self.url(src, lang).partition("#")
        section = anchor or PINNED.get(row["link_id"])
        if "{" in base:
            return [(self.card_url(c, lang), section, c) for c in self.deck]
        return [(base, section, None)]

    def targets(self, row: dict, lang: str, card: dict | None) -> list[tuple[str, str, dict | None]]:
        """(address, anchor text, the card that fills {card_name}) of each link the row asks for on one page: the
        linked card for a row to a set of cards or to the neighbours, else the card of the page."""
        pattern, to = row["anchor_pattern"], row["to_id"]
        if to in ("@cards", "@major"):
            return [(self.card_url(c, lang), pattern.replace("{card_name}", c[f"name_{lang}"]), c) for c in self.cards(to)]
        if to == "@neighbors" and card is not None:
            return [(self.card_url(c, lang), pattern.replace("{card_name}", c[f"name_{lang}"]), c)
                    for c in self.neighbors(card)]
        text = pattern
        if card is not None:
            text = text.replace("{card_name}", card[f"name_{lang}"])
            if card["suit"]:
                text = text.replace("{suit_name}", self.strings[lang]["facts"]["suits"][card["suit"]])
        return [(self.url(to, lang).split("#", 1)[0], text, card)]

    def hub_ids(self, hub: str, card: dict, lang: str) -> set[str]:
        """The ids around the hub's own link to this card (its suit block), or empty."""
        for link in self.links(hub) or []:
            if link["tag"] == "a" and href_path(link["href"]) == self.card_url(card, lang):
                return link["ids"] - {"main"}
        return set()


def is_runtime(site: Site, row: dict, lang: str) -> bool:
    """A link an island draws: to "@drawn"/"@diary", or to a section of a card page from a page that is not one."""
    to = row["to_id"]
    return to in RUNTIME or (to not in CARD_SETS | {"@neighbors"} and "{" in site.url(to, lang))


NUMERAL = re.compile(r"^(0|[IVXL]+)\s+")


def text_is(link: dict, want: str) -> bool:
    """The anchor is the whole link text, the text of a child element or one of its own text nodes — a leading
    Roman numeral ("I The Magician") does not count against it."""
    for candidate in [link["text"], *link["parts"], *link["direct"]]:
        candidate = candidate.casefold()
        if candidate == want or NUMERAL.sub("", candidate.upper()).casefold() == want:
            return True
    return False


def find_link(links: list[dict], url: str, text: str, section: str | None, button: bool) -> dict | None:
    """The first link inside <main> (and the section, if the row has one) to url with this anchor."""
    want = text.casefold()
    for link in links:
        if "main" not in link["ids"] or (section is not None and section not in link["ids"]):
            continue
        if not text_is(link, want):
            continue
        if link["tag"] == "a" and href_path(link["href"]) == url:
            return link
        if button and link["tag"] == "button":
            return link
    return None


def has_link(links: list[dict], url: str, text: str, section: str | None, button: bool) -> bool:
    return find_link(links, url, text, section, button) is not None


def terms_found(site: Site, page: Links, link: dict, terms: list[str]) -> int:
    """How many of the terms stand in a WINDOW-character stretch of the page text around the link."""
    text = "".join(page.text)
    half = max(0, (WINDOW - (link["end"] - link["start"])) // 2)
    around = " ".join(text[max(0, link["start"] - half):link["end"] + half].split()).casefold()
    return sum(1 for term in terms if term.casefold() in around)


def row_terms(row: dict, lang: str, card: dict | None, site: Site) -> list[str]:
    terms = [t for t in row.get("context_terms", "").split("|") if t.strip()]
    out = []
    for term in terms:
        if card is not None:
            term = term.replace("{card_name}", card[f"name_{lang}"])
            if card["suit"]:
                term = term.replace("{suit_name}", site.strings[lang]["facts"]["suits"][card["suit"]])
        out.append(term)
    return out


def check_row(site: Site, row: dict, lang: str, terms: dict | None = None) -> tuple[list[str], int]:
    """(problems, links checked); `terms`, if given, collects row id -> the lowest (found, of) over its links."""
    problems: list[str] = []
    checked = 0
    hub = site.url(row["to_id"], lang).split("#", 1)[0] if "{suit_name}" in row["anchor_pattern"] else None
    for page, section, card in site.sources(row, lang):
        links = site.links(page)
        if links is None:
            problems.append(f"{row['link_id']}: no page {page} in site/dist")
            continue
        for url, text, named in site.targets(row, lang, card):
            checked += 1
            link = find_link(links, url, text, section, row["link_id"] in IN_PLACE)
            where = f" inside #{section}" if section else ""
            if link is None:
                problems.append(f"{row['link_id']}: {page} has no link to {url} «{text}»{where}")
                continue
            if hub is not None and card is not None:
                wanted = site.hub_ids(hub, card, lang)
                fragment = split_href(link["href"])[1]
                if fragment is None or fragment not in wanted:
                    problems.append(f"{row['link_id']}: {page} links {link['href']} — the suit block of the hub is "
                                    f"#{'/#'.join(sorted(wanted)) or '(none found)'}")
            if terms is not None and link["tag"] == "a":
                have = row_terms(row, lang, named, site)
                if have:
                    found = terms_found(site, site.page(page), link, have)
                    low = terms.get(row["link_id"])
                    if low is None or (found, len(have)) < low:
                        terms[row["link_id"]] = (found, len(have))
    return problems, checked


def all_href_problems(site: Site) -> list[str]:
    """Every <a href> in <main>, header and footer of every built page: canonical, live, its #fragment an id there."""
    problems: list[str] = []
    for file in sorted(site.dist.rglob("*.html")):
        rel = file.relative_to(site.dist).as_posix()
        path = "/" if rel == "index.html" else "/" + rel[:-5]
        page = site.page(path)
        if page is None:
            continue
        for link in page.found:
            href = link["href"]
            if link["tag"] != "a" or not href or not link["zones"]:
                continue
            if href.startswith("#"):
                target, fragment = path, href[1:] or None
            elif href.startswith("/") or href.startswith(SITE_URL):
                target, fragment = split_href(href)
                if target is None:
                    target = path
            else:
                continue  # mailto:, tel:, external sites
            if "?" in target or (len(target) > 1 and target.endswith("/")) or target.endswith(".html") or "//" in target:
                problems.append(f"{path}: href {href} is not canonical (no query, trailing slash or .html)")
                continue
            if site.page(target) is None and not (site.dist / target[1:]).is_file():
                problems.append(f"{path}: href {href} leads to no page or file in site/dist")
                continue
            if fragment and (site.page(target) is None or fragment not in site.page(target).ids):
                problems.append(f"{path}: href {href} — no #{fragment} on {target}")
    return problems


def island_coverage(rows: list[str], root: Path = ROOT) -> tuple[list[str], list[str]]:
    """(one line per runtime row: the vitest file that asserts it or why it is not built, problems)."""
    lines: list[str] = []
    problems: list[str] = []
    texts: dict[str, str] = {}
    for row in rows:
        if row in ISLAND_TESTS:
            test = ISLAND_TESTS[row]
            if test not in texts:
                file = root / test
                texts[test] = file.read_text(encoding="utf-8") if file.is_file() else ""
            if re.search(rf"\b{re.escape(row)}\b", texts[test]):
                lines.append(f"  {row}: {test}")
            else:
                problems.append(f"{row}: drawn by an island, but {test} has no vitest case that names it")
        elif row in NOT_BUILT:
            lines.append(f"  {row}: not built — {NOT_BUILT[row]}")
        else:
            problems.append(f"{row}: drawn by an island, but no vitest case covers it (ISLAND_TESTS)")
    return lines, problems


def launch_rows() -> list[tuple[str, dict]]:
    return [(lang, r) for lang in ("en", "es") for r in read_csv(STAGE2 / f"links-{lang}.csv") if r["wave"] == LAUNCH]


def main(dist: Path | None = None) -> int:
    site = Site(dist)
    problems: list[str] = []
    rows = links = 0
    runtime: list[str] = []
    terms: dict[str, tuple[int, int]] = {}
    for lang, row in launch_rows():
        try:
            if is_runtime(site, row, lang):
                runtime.append(row["link_id"])
                continue
            found, checked = check_row(site, row, lang, terms)
        except UnknownId as error:
            problems.append(f"{row['link_id']}: {error}")
            continue
        problems += found
        rows += 1
        links += checked
    if rows + len(runtime) == 0:
        problems.append("no launch rows in docs/research/stage2/links-{en,es}.csv (did the wave label change?)")
    covered, uncovered = island_coverage(runtime)
    problems += uncovered
    problems += all_href_problems(site)
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"OK: {rows} rows, {links} links")
    print(f"drawn by islands, not in site/dist: {', '.join(runtime)}")
    for line in covered:
        print(line)
    for row_id, (found, of) in sorted(terms.items()):
        if found < min(2, of):
            print(f"terms: {row_id} {found}/{of}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
