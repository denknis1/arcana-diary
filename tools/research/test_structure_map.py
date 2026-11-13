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
