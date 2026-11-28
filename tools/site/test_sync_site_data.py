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
    # spec §2: the operator facts of content/operator.json, all filled since 24.11.2026 (an empty one would stay out)
    assert set(f) == {"guest_limit", "user_limit", "followups", "diary_free", "yes_count", "no_count", "unclear_count",
                      "editor_name", "operator_name", "operator_address", "jurisdiction", "contact_email",
                      "hosting_provider", "email_provider", "effective_date"}
    assert f["effective_date"] == {"en": "November 28, 2026", "es": "28 de noviembre de 2026"}


def test_operator_facts_leave_out_empty_values_and_half_filled_dates(tmp_path, monkeypatch):
    import sync_site_data

    path = tmp_path / "operator.json"
    monkeypatch.setattr(sync_site_data, "OPERATOR", path)
    path.write_text(json.dumps({"_note": "x", "operator_name": " ", "contact_email": " a@b.c ",
                                "effective_date": {"en": "May 1, 2027", "es": ""}}), encoding="utf-8")
    assert sync_site_data.operator_facts() == {"contact_email": "a@b.c"}
    path.write_text(json.dumps({"effective_date": {"en": "May 1, 2027", "es": "1 de mayo de 2027"}}), encoding="utf-8")
    assert sync_site_data.operator_facts() == {"effective_date": {"en": "May 1, 2027", "es": "1 de mayo de 2027"}}
    path.write_text(json.dumps({"operator_nmae": "typo"}), encoding="utf-8")
    with pytest.raises(ValueError, match="operator_nmae"):
        sync_site_data.operator_facts()


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
    assert len(table) == 25 + 78 * 2
    assert table["/"] == "/es" and table["/es"] == "/"
    assert table["/one-card"] == "/es"
    assert table["/yes-no"] == "/es/si-o-no" and table["/es/si-o-no"] == "/yes-no"
    assert table["/love"] == "/es/amor" and table["/daily"] == "/es/carta-del-dia"
    assert table["/cards"] == "/es/cartas" and table["/es/cartas"] == "/cards"
    assert table["/cards/major-arcana"] == "/es/cartas/arcanos-mayores"
    assert table["/yes-no/cards"] == "/es/si-o-no" and table["/es/tiradas/3-cartas"] == "/"
    # stage 6 part 4: the service pages and their Spanish pairs (owner decision 8 of 14.11.2026)
    for en, es in (("/about", "/es/sobre-nosotros"), ("/how-readings-work", "/es/como-funcionan-las-lecturas"),
                   ("/contact", "/es/contacto"), ("/privacy", "/es/privacidad"), ("/terms", "/es/terminos")):
        assert table[en] == es and table[es] == en
    for card in deck():
        en, es = f"/cards/{card['slug_en']}", f"/es/cartas/{card['slug_es']}"
        assert table[en] == es and table[es] == en


def test_tokens_css_is_the_design_copy():
    assert (SITE / "src/styles/tokens.css").read_text() == (ROOT / "docs/design/tokens.css").read_text()


def test_the_build_check_expects_187_pages_with_their_files():
    pages = expected_pages()
    assert len(pages) == 187  # stage 6 part 4: + 10 service pages
    assert {"/", "/es", "/404", "/es/404", "/one-card", "/es/cartas/la-luna", "/diary", "/es/cuenta", "/cards",
            "/es/tiradas/3-cartas", "/about", "/es/terminos"} <= set(pages)
    assert [dist_file(p) for p in ("/", "/es", "/es/404", "/cards/the-moon", "/cards")] == [
        "index.html", "es.html", "es/404.html", "cards/the-moon.html", "cards.html"]
