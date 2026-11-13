import pytest

from fixtures_structure import CARDS, en_map, es_map, replace, row
from structure_map import check_map, url_errors


# --- адреса ---

def test_url_rules():
    assert url_errors("/", "en") == []
    assert url_errors("/es/si-o-no", "es") == []
    assert url_errors("/cards/{slug_en}/yes-or-no", "en") == []
    assert url_errors("/yes-no/", "en")
    assert url_errors("/Yes-No", "en")
    assert url_errors("/es/sí-o-no", "es")
    assert url_errors("/es/amor", "en")
    assert url_errors("/amor", "es")


# --- карта страниц ---

def test_good_map_passes():
    assert check_map(en_map(), "en", CARDS) == []
    assert check_map(es_map(), "es", CARDS) == []


def test_duplicate_url_rejected():
    rows = replace(en_map(), "EN-009", url="/yes-no")
    assert any("уже у" in e for e in check_map(rows, "en", CARDS))


def test_missing_parent_rejected():
    rows = replace(en_map(), "EN-007", parent_id="EN-999")
    assert any("родитель" in e for e in check_map(rows, "en", CARDS))


def test_parent_from_later_wave_rejected():
    rows = en_map() + [row("EN-100", "/spreads", wave="V1.1", entity="spread:index", parent="EN-001",
                           page_type="spreads"),
                       row("EN-102", "/spreads/three-card", entity="spread:three-card", parent="EN-100",
                           page_type="spreads")]
    assert any("позже" in e for e in check_map(rows, "en", CARDS))


def test_breadcrumb_must_follow_home_chain():
    rows = replace(en_map(), "EN-033", breadcrumb="EN-014>EN-033")
    assert any("крошки" in e for e in check_map(rows, "en", CARDS))


def test_launch_page_below_hub_needs_breadcrumb():
    rows = replace(en_map(), "EN-087", breadcrumb="")
    assert any("нет крошек" in e for e in check_map(rows, "en", CARDS))


def test_section_needs_anchor_and_host():
    rows = replace(en_map(), "EN-095", url="/cards/{slug_en}")
    assert any("якорем" in e for e in check_map(rows, "en", CARDS))
    rows = replace(en_map(), "EN-095", host_id="")
    assert any("хозяин" in e for e in check_map(rows, "en", CARDS))


def test_rejected_row_has_no_structure():
    rows = replace(en_map(), "EN-121", url="/pairs")
    assert any("пустыми" in e for e in check_map(rows, "en", CARDS))


def test_card_without_page_rejected():
    rows = [r for r in en_map() if r["id"] != "EN-087"]
    assert any("нет страниц карт" in e for e in check_map(rows, "en", CARDS))


def test_reserved_slug_collision_rejected():
    cards = CARDS + [{"card_id": "x", "arcana": "minor", "slug_en": "major-arcana", "slug_es": "x"}]
    rows = en_map() + [row("EN-200", "/cards/major-arcana-2", entity="card:x", parent="EN-014",
                           crumbs="EN-014>EN-200")]
    assert any("служебный слаг" in e for e in check_map(rows, "en", cards))


# --- правила, добавленные после ревью ---

def errors(rows, lang="en"):
    return check_map(rows, lang, CARDS)


def test_v2_template_without_entity_must_have_one_page():
    rows = en_map() + [row("EN-130", "/pairs/{slug}", wave="V2", pages="5", page_type="pairs")]
    assert any("без сущности" in e for e in errors(rows))
    rows = en_map() + [row("EN-130", "/pairs/{slug}", wave="V2", pages="1", page_type="pairs")]
    assert errors(rows) == []


def test_same_card_needs_template_url():
    rows = replace(en_map(), "EN-087", parent_id="@same-card")
    assert any("допустим только у шаблона ×78" in e for e in errors(rows))


def test_all_cards_section_needs_cards_address():
    rows = replace(en_map(), "EN-095", url="/cards/{slug_es}#reversed")
    assert any("раздел на 78 картах, но адрес" in e for e in errors(rows))


def test_section_address_must_match_host_address():
    rows = en_map() + [row("EN-140", "/cards/other#faq", decision="раздел", host="EN-087", pages="0")]
    assert any("не совпадает с адресом хозяина" in e for e in errors(rows))


def test_section_host_must_not_be_later():
    rows = en_map() + [row("EN-140", "/cards/{slug_en}/yes-or-no#faq", decision="раздел", host="EN-097",
                           pages="0")]
    assert any("выходит позже раздела" in e for e in errors(rows))


def test_page_must_not_have_host_id():
    rows = replace(en_map(), "EN-007", host_id="EN-001")
    assert any("у страницы заполнен host_id" in e for e in errors(rows))


def test_unknown_menu_item_rejected():
    rows = replace(en_map(), "EN-007", menu_item="blog")
    assert any("неизвестный menu_item blog" in e for e in errors(rows))


def test_card_template_must_have_78_pages():
    rows = replace(en_map(), "EN-097", pages="5")
    assert any("шаблон ×78, но pages=5" in e for e in errors(rows))


@pytest.mark.parametrize("wave", ["V2", "V3"])
@pytest.mark.parametrize("field,value", [("entity", "x:y"), ("parent", "EN-001"), ("crumbs", "EN-014>EN-200")])
def test_late_wave_page_has_no_structure_fields(wave, field, value):
    rows = en_map() + [row("EN-200", "/pairs", wave=wave, page_type="pairs", **{field: value})]
    assert any("задаются в своей волне" in e for e in errors(rows))


def test_home_child_breadcrumb_must_be_itself():
    rows = replace(en_map(), "EN-014", breadcrumb="EN-093")
    assert any("не совпадают с цепочкой дома EN-014" in e for e in errors(rows))


def test_home_must_be_root_without_parent():
    rows = replace(en_map(), "EN-001", url="/home")
    assert any("главная должна быть / без родителя" in e for e in errors(rows))
    rows = replace(en_map(), "EN-001", parent_id="EN-014")
    assert any("главная должна быть / без родителя" in e for e in errors(rows))


def test_es_address_needs_es_prefix():
    rows = replace(es_map(), "ES-012", url="/cartas")
    assert any("ES-адрес не в /es" in e for e in errors(rows, "es"))


def test_es_breadcrumb_must_follow_home_chain():
    rows = replace(es_map(), "ES-031", breadcrumb="ES-012>ES-031")
    assert any("не совпадают с цепочкой дома ES-012>ES-091>ES-031" in e for e in errors(rows, "es"))


# --- страница карты сверяется с cards.csv (финальное ревью, Important 1) ---

def test_swapped_card_entity_ids_rejected():
    rows = replace(replace(es_map(), "ES-031", entity_id="card:cups-10-ten"), "ES-085",
                   entity_id="card:major-18-moon")
    errs = errors(rows, "es")
    assert any("ES-031" in e and "/es/cartas/diez-de-copas" in e for e in errs)
    assert any("ES-085" in e and "/es/cartas/la-luna" in e for e in errs)


def test_swapped_card_urls_rejected():
    rows = replace(replace(en_map(), "EN-033", url="/cards/ten-of-cups"), "EN-087", url="/cards/the-moon")
    errs = errors(rows)
    assert any("EN-033" in e and "/cards/the-moon" in e for e in errs)
    assert any("EN-087" in e and "/cards/ten-of-cups" in e for e in errs)


def test_card_entity_must_be_known_and_unique():
    rows = replace(en_map(), "EN-087", entity_id="card:no-such-card")
    errs = errors(rows)
    assert any("card:no-such-card" in e and "cards.csv" in e for e in errs)
    assert any("cups-10-ten" in e and "нет строки" in e for e in errs)
    rows = en_map() + [row("EN-201", "/cards/the-moon-2", entity="card:major-18-moon", parent="EN-014",
                           crumbs="EN-014>EN-201")]
    assert any("major-18-moon" in e and "EN-033" in e and "EN-201" in e for e in errors(rows))
