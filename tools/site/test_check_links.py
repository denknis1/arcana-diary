"""tools/site/check_links.py on hand-made pages (spec stage 6 §7)."""
import check_links
from check_links import (ISLAND_TESTS, NOT_BUILT, Site, all_href_problems, check_row, href_path, is_runtime,
                         island_coverage, launch_rows, main, parse_links, parse_page)

LAUNCH = "запуск"


def write(dist, name, text, wrap=True):
    if wrap and "<main" not in text:
        text = f'<header><a href="/">Home</a></header><main id="main">{text}</main><footer></footer>'
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
    assert parse_links('<header><a href="/x">X</a></header><main id="main"><a href="/y">Y</a></main>')[0]["zones"] == {"header"}
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


def card_pages(dist, site, nav_id="card-nav", fragment=True, hub_ids=True):
    deck = site.deck
    for i, card in enumerate(deck):
        before, after = deck[i - 1], deck[(i + 1) % len(deck)]
        suit = card["suit"]
        suit_link = f'<a href="/cards{"#" + suit if fragment else ""}">{suit.title()}</a>' if suit else ""
        write(dist, f"cards/{card['slug_en']}.html",
              f'<nav class="card-nav" id="{nav_id}"><a href="/cards/{before["slug_en"]}"><small>← Previous</small>'
              f'{before["name_en"]}</a><a href="/cards/{after["slug_en"]}"><small>Next →</small>I {after["name_en"]}</a>'
              f'</nav>{suit_link}')
    hub = "".join(f'<div id="{c["suit"] if hub_ids else "x"}"><a href="/cards/{c["slug_en"]}">{c["name_en"]}</a></div>'
                  for c in deck if c["suit"])
    write(dist, "cards.html", hub)


NAV = {"link_id": "T-3", "from_id": "@cards", "to_id": "@neighbors", "anchor_pattern": "{card_name}", "wave": LAUNCH}
SUIT = {"link_id": "T-4", "from_id": "@minor", "to_id": "EN-014", "anchor_pattern": "{suit_name}", "wave": LAUNCH}


def test_card_rows_fill_in_the_card_and_the_suit_names(tmp_path):
    site = Site(tmp_path)
    card_pages(tmp_path, site)
    assert check_row(site, NAV, "en") == ([], 156)
    assert check_row(site, SUIT, "en") == ([], 56)


def test_previous_next_must_sit_in_the_card_nav(tmp_path):
    site = Site(tmp_path)
    card_pages(tmp_path, site, nav_id="other")
    problems, _ = check_row(Site(tmp_path), NAV, "en")
    assert len(problems) == 156 and problems[0].endswith("inside #card-nav")


def test_a_suit_row_needs_the_fragment_of_the_hubs_own_suit_block(tmp_path):
    site = Site(tmp_path)
    card_pages(tmp_path, site, fragment=False)
    problems, _ = check_row(Site(tmp_path), SUIT, "en")
    assert len(problems) == 56 and "the suit block of the hub is #wands" in problems[0]
    card_pages(tmp_path, site)
    write(tmp_path, "cards/ace-of-wands.html", '<a href="/cards#cups">Wands</a>')
    problems, _ = check_row(Site(tmp_path), SUIT, "en")
    assert len(problems) == 1 and problems[0].startswith("T-4: /cards/ace-of-wands links /cards#cups")


def test_menu_and_footer_links_do_not_count(tmp_path):
    row = {"link_id": "T-6", "from_id": "EN-093", "to_id": "EN-014", "anchor_pattern": "All 78 cards", "wave": LAUNCH}
    page = '<header><a href="/cards">All 78 cards</a></header><main id="main"></main><footer><a href="/cards">All 78 cards</a></footer>'
    write(tmp_path, "cards/major-arcana.html", page, wrap=False)
    assert check_row(Site(tmp_path), row, "en")[0] == ["T-6: /cards/major-arcana has no link to /cards «All 78 cards»"]


def test_the_anchor_is_the_whole_text_or_a_part_not_a_substring(tmp_path):
    row = {"link_id": "T-7", "from_id": "EN-093", "to_id": "EN-014", "anchor_pattern": "All 78 cards", "wave": LAUNCH}
    for text, ok in [("All 78 cards", True), ("<b>0</b> All 78 cards", True), ("<small>See</small> All 78 cards", True),
                     ("Click here: all 78 cards, now", False), ("All 78 cards and more", False)]:
        write(tmp_path, "cards/major-arcana.html", f'<a href="/cards">{text}</a>')
        assert (check_row(Site(tmp_path), row, "en")[0] == []) is ok, text


def test_l_en_04_must_sit_in_the_rule_block(tmp_path):
    row = next(r for lang, r in launch_rows() if r["link_id"] == "L-EN-04")
    link = '<a href="/yes-no/cards">How we read yes and no</a>'
    write(tmp_path, "yes-no.html", f'<section id="rule">{link}</section>')
    assert check_row(Site(tmp_path), row, "en") == ([], 1)
    write(tmp_path, "yes-no.html", f'<section id="rule"></section>{link}')
    assert check_row(Site(tmp_path), row, "en")[0][0].endswith("inside #rule")


def test_context_terms_are_counted_in_a_window_around_the_link(tmp_path):
    row = {"link_id": "T-8", "from_id": "EN-093", "to_id": "EN-014", "anchor_pattern": "Card meanings",
           "context_terms": "tarot cards|78", "wave": LAUNCH}
    near = '<p>What each of the 78 tarot cards means <a href="/cards">Card meanings</a></p>'
    far = f'<p>78 tarot cards {"x " * 300}</p><a href="/cards">Card meanings</a>'
    for html, expect in [(near, (2, 2)), (far, (0, 2))]:
        write(tmp_path, "cards/major-arcana.html", html)
        terms = {}
        assert check_row(Site(tmp_path), row, "en", terms)[0] == []
        assert terms == {"T-8": expect}


def test_card_name_terms_of_a_card_list_row_are_the_name_of_the_linked_card(tmp_path):
    # the hub's link to The Fool counts "The Fool", not a literal "{card_name}"; previous/next count the neighbour's name
    row = {"link_id": "T-9", "from_id": "EN-093", "to_id": "@major", "anchor_pattern": "{card_name}",
           "context_terms": "{card_name}|major arcana", "wave": LAUNCH}
    site = Site(tmp_path)
    majors = [c for c in site.deck if c["arcana"] == "major"]
    write(tmp_path, "cards/major-arcana.html", "".join(f'<p><a href="/cards/{c["slug_en"]}">{c["name_en"]}</a>{"x " * 200}</p>'
                                                         for c in majors))
    terms = {}
    assert check_row(Site(tmp_path), row, "en", terms)[0] == []
    assert terms == {"T-9": (1, 2)}
    nav = {**NAV, "context_terms": "{card_name}|tarot card"}
    card_pages(tmp_path, site)
    terms = {}
    assert check_row(Site(tmp_path), nav, "en", terms)[0] == []
    assert terms == {"T-3": (1, 2)}


def test_every_href_must_be_canonical_and_live(tmp_path):
    write(tmp_path, "about.html", "")
    write(tmp_path, "cards.html", '<h2 id="wands"></h2>')
    good = ('<a href="/cards#wands">a</a><a href="https://arcanadiary.com/about">b</a><a href="https://x.org/a/">c</a>'
            '<a href="#main">d</a>')
    write(tmp_path, "index.html", good)
    assert all_href_problems(Site(tmp_path)) == []
    for bad, why in [('<a href="/nope">x</a>', "no page"), ('<a href="/about/">x</a>', "canonical"),
                     ('<a href="/about?x=1">x</a>', "canonical"), ('<a href="/cards#cups">x</a>', "no #cups"),
                     ('<a href="/about.html">x</a>', "canonical")]:
        write(tmp_path, "index.html", bad)
        problems = all_href_problems(Site(tmp_path))
        assert len(problems) == 1 and why in problems[0], (bad, problems)


def test_no_launch_rows_and_an_unknown_id_are_problems(tmp_path, monkeypatch, capsys):
    (tmp_path / "docs").mkdir()
    for lang in ("en", "es"):
        (tmp_path / "docs" / f"links-{lang}.csv").write_text("link_id,wave\nL-1,V1.1\n", encoding="utf-8")
    monkeypatch.setattr(check_links, "STAGE2", tmp_path / "docs")
    assert main(tmp_path) == 1
    assert "no launch rows" in capsys.readouterr().out
    monkeypatch.setattr(check_links, "launch_rows", lambda: [("en", {
        "link_id": "T-9", "from_id": "EN-093", "to_id": "EN-999", "anchor_pattern": "x", "wave": LAUNCH})])
    assert main(tmp_path) == 1
    assert "T-9: unknown page id EN-999" in capsys.readouterr().out


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
        "L-EN-01", "L-EN-02", "L-EN-03", "L-EN-15", "L-EN-31", "L-EN-32",
        "L-ES-01", "L-ES-02", "L-ES-03", "L-ES-04", "L-ES-15", "L-ES-23", "L-ES-26"]
    assert main(tmp_path) == 1
    assert "L-EN-04: no page /yes-no in site/dist" in capsys.readouterr().out


def test_every_row_drawn_by_an_island_has_a_vitest_case_or_a_reason(tmp_path):
    site = Site(tmp_path)
    runtime = [r["link_id"] for lang, r in launch_rows() if is_runtime(site, r, lang)]
    assert sorted(runtime) == sorted([*ISLAND_TESTS, *NOT_BUILT])
    lines, problems = island_coverage(runtime)
    assert problems == []
    assert "  L-ES-03: site/src/components/ui/NightRoom.test.tsx" in lines
    assert "  L-EN-15: site/src/islands/DailyIsland.test.tsx" in lines
    assert "  L-EN-32: site/src/components/ui/NightRoom.test.tsx" in lines
    assert not any("not built" in line for line in lines)  # owner decision 42: L-EN-16, L-ES-16 are V1.1


def test_a_row_not_built_is_listed_with_its_reason(monkeypatch):
    monkeypatch.setitem(check_links.NOT_BUILT, "L-EN-99", "waits for the owner")
    lines, problems = island_coverage(["L-EN-99"])
    assert (lines, problems) == (["  L-EN-99: not built — waits for the owner"], [])


def test_a_row_its_test_does_not_name_or_an_unknown_row_is_a_problem(tmp_path):
    test = tmp_path / ISLAND_TESTS["L-EN-01"]
    test.parent.mkdir(parents=True)
    test.write_text("it('L-EN-010: not this row', () => {});\nit('L-EN-02: one card', () => {});\n", encoding="utf-8")
    lines, problems = island_coverage(["L-EN-01", "L-EN-02", "L-EN-99"], tmp_path)
    assert lines == ["  L-EN-02: site/src/components/ui/NightRoom.test.tsx"]
    assert problems == ["L-EN-01: drawn by an island, but site/src/components/ui/NightRoom.test.tsx has no vitest case "
                        "that names it", "L-EN-99: drawn by an island, but no vitest case covers it (ISLAND_TESTS)"]


def test_a_leading_roman_numeral_of_the_deck_is_skipped_but_not_a_word_of_those_letters():
    link = lambda text: {"text": text, "parts": [], "direct": []}  # noqa: E731
    assert check_links.text_is(link("XIX The Sun"), "the sun")
    assert check_links.text_is(link("0 The Fool"), "the fool")
    assert check_links.text_is(link("XVIII The Moon"), "the moon")
    assert not check_links.text_is(link("Ill omen"), "omen")
    assert not check_links.text_is(link("Vivid dreams"), "dreams")
