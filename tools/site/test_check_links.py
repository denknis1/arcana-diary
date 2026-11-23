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
