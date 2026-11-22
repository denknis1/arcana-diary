from check_dist import dist_file, expected_pages
from sync_site_data import ROOT, SITE, build, deck, meanings, pairs, stale


def test_committed_site_data_matches_its_sources():
    assert stale(build()) == []


def test_deck_has_78_cards_in_deck_order_with_both_names():
    cards = deck()
    assert len(cards) == 78
    assert cards[0]["card_id"] == "major-00-fool" and cards[0]["name_es"] == "El Loco"
    assert cards[18]["slug_en"] == "the-moon" and cards[18]["slug_es"] == "la-luna" and cards[18]["numeral"] == "XVIII"
    assert all(c["name_en"] and c["name_es"] for c in cards)


def test_every_card_has_its_three_image_sizes():
    for card in deck():
        for suffix in ("", "@350", "@160"):
            assert (SITE / "public/cards" / f"{card['image']}{suffix}.webp").exists(), card["image"]


def test_meanings_cover_the_deck_in_both_languages():
    ids = {c["card_id"] for c in deck()}
    for lang in ("en", "es"):
        records = meanings(lang)
        assert {m["card_id"] for m in records} == ids
        assert all(m["upright"] and m["reversed"] and m["keywords"] for m in records)


def test_pairs_are_the_44a_pages_of_hreflang_csv():
    table = pairs()
    assert len(table) == 9 + 78 * 2
    assert table["/"] == "/es" and table["/es"] == "/"
    assert table["/one-card"] == "/es"
    assert table["/yes-no"] == "/es/si-o-no" and table["/es/si-o-no"] == "/yes-no"
    assert table["/love"] == "/es/amor" and table["/daily"] == "/es/carta-del-dia"
    for card in deck():
        en, es = f"/cards/{card['slug_en']}", f"/es/cartas/{card['slug_es']}"
        assert table[en] == es and table[es] == en


def test_tokens_css_is_the_design_copy():
    assert (SITE / "src/styles/tokens.css").read_text() == (ROOT / "docs/design/tokens.css").read_text()


def test_the_build_check_expects_171_pages_with_their_files():
    pages = expected_pages()
    assert len(pages) == 171  # stage 4.4b: + /diary, /es/diario, /account, /es/cuenta
    assert {"/", "/es", "/404", "/es/404", "/one-card", "/es/cartas/la-luna", "/diary", "/es/cuenta"} <= set(pages)
    assert [dist_file(p) for p in ("/", "/es", "/es/404", "/cards/the-moon")] == [
        "index.html", "es.html", "es/404.html", "cards/the-moon.html"]
