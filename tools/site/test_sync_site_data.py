import json

import pytest

from check_dist import dist_file, expected_pages
from sync_site_data import (API_CONFIG, ROOT, SITE, build, card_pages, config_constant, deck, facts, meanings, pairs,
                            stale, text_pages)


def test_committed_site_data_matches_its_sources():
    assert stale(build()) == []


def test_deck_has_78_cards_in_deck_order_with_both_names():
    cards = deck()
    assert len(cards) == 78
    assert cards[0]["card_id"] == "major-00-fool" and cards[0]["name_es"] == "El Loco"
    assert cards[18]["slug_en"] == "the-moon" and cards[18]["slug_es"] == "la-luna" and cards[18]["numeral"] == "XVIII"
    assert all(c["name_en"] and c["name_es"] for c in cards)


def test_deck_carries_the_yes_no_verdict_of_the_card_base():
    cards = deck()
    assert {c["yes_no"] for c in cards} == {"yes", "no", "unclear"}
    assert cards[18]["yes_no"] == "unclear"  # The Moon
    assert next(c for c in cards if c["card_id"] == "swords-03-three")["yes_no"] == "no"


def test_every_card_has_its_three_image_sizes():
    for card in deck():
        for suffix in ("", "@350", "@160"):
            assert (SITE / "public/cards" / f"{card['image']}{suffix}.webp").exists(), card["image"]


def test_meanings_cover_the_deck_in_both_languages():
    ids = {c["card_id"] for c in deck()}
    for lang in ("en", "es"):
        records = meanings(lang)
        assert {m["card_id"] for m in records} == ids
        assert all(m["upright"] and m["reversed"] and m["keywords"] and m["yes_no_why"] for m in records)


def test_config_constant_reads_a_number_and_refuses_a_missing_name():
    text = "DAILY_LIMIT = 2            # a guest\nUSER_DAILY_LIMIT = 3\n"
    assert config_constant(text, "DAILY_LIMIT") == 2
    assert config_constant(text, "USER_DAILY_LIMIT") == 3
    with pytest.raises(ValueError, match="FOLLOWUP_LIMIT"):
        config_constant(text, "FOLLOWUP_LIMIT")


def test_facts_come_from_the_api_constants_and_the_deck():
    f = facts()
    text = API_CONFIG.read_text(encoding="utf-8")
    assert f["guest_limit"] == config_constant(text, "DAILY_LIMIT")
    assert f["user_limit"] == config_constant(text, "USER_DAILY_LIMIT")
    assert f["followups"] == config_constant(text, "FOLLOWUP_LIMIT")
    assert f["diary_free"] == config_constant(text, "FREE_DIARY_VISIBLE")
    assert f["yes_count"] + f["no_count"] + f["unclear_count"] == 78
    assert f["editor_name"] == "Adrian Solenne"
    # spec §2: operator placeholders ({operator_name}, …) stay out until the operator's data exists
    assert set(f) == {"guest_limit", "user_limit", "followups", "diary_free", "yes_count", "no_count", "unclear_count",
                      "editor_name"}


def test_text_pages_are_copied_for_both_languages():
    files = text_pages()
    assert len(files) == 25
    home = json.loads(files[SITE / "src/data/pages/en/home.json"])
    assert home["url"] == "/" and home["h1"] == "Free tarot reading: ask the cards"
    three = json.loads(files[SITE / "src/data/pages/es/tres-cartas.json"])
    assert three["url"] == "/es/tiradas/3-cartas"


def test_card_pages_are_copied_without_the_reviewers_excerpts():
    files = card_pages()
    assert len(files) == 78 * 2 + 1
    moon = json.loads(files[SITE / "src/data/cardpages/es/major-18-moon.json"])
    assert moon["name_forms"]["name"] == "La Luna" and "citations" not in moon
    strings = json.loads(files[SITE / "src/data/cardpages/template-strings.json"])
    assert strings["es"]["waite"]["translation_label"] == "Traducción nuestra"


def test_pairs_are_every_launch_page_of_hreflang_csv():
    table = pairs()
    assert len(table) == 15 + 78 * 2
    assert table["/"] == "/es" and table["/es"] == "/"
    assert table["/one-card"] == "/es"
    assert table["/yes-no"] == "/es/si-o-no" and table["/es/si-o-no"] == "/yes-no"
    assert table["/love"] == "/es/amor" and table["/daily"] == "/es/carta-del-dia"
    assert table["/cards"] == "/es/cartas" and table["/es/cartas"] == "/cards"
    assert table["/cards/major-arcana"] == "/es/cartas/arcanos-mayores"
    assert table["/yes-no/cards"] == "/es/si-o-no" and table["/es/tiradas/3-cartas"] == "/"
    for card in deck():
        en, es = f"/cards/{card['slug_en']}", f"/es/cartas/{card['slug_es']}"
        assert table[en] == es and table[es] == en


def test_tokens_css_is_the_design_copy():
    assert (SITE / "src/styles/tokens.css").read_text() == (ROOT / "docs/design/tokens.css").read_text()


def test_the_build_check_expects_177_pages_with_their_files():
    pages = expected_pages()
    assert len(pages) == 177  # stage 6 part 1: + /cards, /cards/major-arcana, /yes-no/cards and three ES pages
    assert {"/", "/es", "/404", "/es/404", "/one-card", "/es/cartas/la-luna", "/diary", "/es/cuenta", "/cards",
            "/es/tiradas/3-cartas"} <= set(pages)
    assert [dist_file(p) for p in ("/", "/es", "/es/404", "/cards/the-moon", "/cards")] == [
        "index.html", "es.html", "es/404.html", "cards/the-moon.html", "cards.html"]
