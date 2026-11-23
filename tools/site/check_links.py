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
