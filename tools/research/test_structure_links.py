from fixtures_structure import en_map
from structure_links import LINK_COLUMNS, check_links


# --- матрица ссылок ---

def link(lid, src, dst, ltype, wave="запуск"):
    return {"link_id": lid, "from_id": src, "to_id": dst, "link_type": ltype, "moment": "вопрос",
            "anchor_pattern": "анкор", "context_terms": "", "wave": wave, "note": ""}


def good_links():
    return [
        link("L-EN-01", "EN-001", "@drawn", "подробность"),
        link("L-EN-02", "EN-007", "EN-009", "метод"),
        link("L-EN-03", "@cards", "EN-001", "действие"),
        link("L-EN-04", "EN-014", "@cards", "навигация"),
        link("L-EN-05", "EN-001", "@diary", "сохранение"),
        link("L-EN-06", "EN-007", "EN-097", "подробность", wave="V1.1"),
    ]


def test_good_links_pass():
    assert check_links(LINK_COLUMNS, good_links(), en_map(), "en") == []


def test_link_to_unknown_row_rejected():
    links = good_links() + [link("L-EN-07", "EN-001", "EN-555", "навигация")]
    assert any("EN-555" in e for e in check_links(LINK_COLUMNS, links, en_map(), "en"))


def test_link_to_rejected_row_rejected():
    links = good_links() + [link("L-EN-07", "EN-001", "EN-121", "навигация")]
    assert any("EN-121" in e for e in check_links(LINK_COLUMNS, links, en_map(), "en"))


def test_link_before_target_wave_rejected():
    links = good_links() + [link("L-EN-07", "EN-007", "EN-097", "подробность", wave="запуск")]
    assert any("раньше" in e for e in check_links(LINK_COLUMNS, links, en_map(), "en"))


def test_launch_must_cover_all_link_types():
    links = [l for l in good_links() if l["link_type"] != "метод"]
    assert any("метод" in e for e in check_links(LINK_COLUMNS, links, en_map(), "en"))


def test_link_header_checked():
    assert check_links(LINK_COLUMNS[:-1], good_links(), en_map(), "en")
