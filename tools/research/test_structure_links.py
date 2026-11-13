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


# --- дополнительные проверки матрицы ---

def errs_for(extra):
    return check_links(LINK_COLUMNS, good_links() + extra, en_map(), "en")


def test_duplicate_link_id_rejected():
    assert any("повтор id" in e for e in errs_for([link("L-EN-01", "EN-001", "EN-007", "навигация")]))


def test_wrong_link_id_prefix_rejected():
    assert any("должен начинаться с L-EN-" in e for e in errs_for([link("L-ES-07", "EN-001", "EN-007", "навигация")]))


def test_self_link_rejected():
    assert any("ссылка на себя" in e for e in errs_for([link("L-EN-07", "EN-001", "EN-001", "навигация")]))


def test_unknown_link_type_rejected():
    assert any("неизвестный link_type" in e for e in errs_for([link("L-EN-07", "EN-001", "EN-007", "реклама")]))


def test_empty_moment_rejected():
    bad = link("L-EN-07", "EN-001", "EN-007", "навигация")
    bad["moment"] = " "
    assert any("пустое moment" in e for e in errs_for([bad]))


def test_empty_anchor_pattern_rejected():
    bad = link("L-EN-07", "EN-001", "EN-007", "навигация")
    bad["anchor_pattern"] = ""
    assert any("пустое anchor_pattern" in e for e in errs_for([bad]))


def test_target_tokens_accepted():
    extra = [link(f"L-EN-{i}", "EN-001", tok, "навигация")
             for i, tok in zip(range(10, 14), ["@neighbors", "@diary", "@major", "@minor"])]
    assert errs_for(extra) == []


def test_source_tokens_accepted():
    extra = [link("L-EN-10", "@major", "EN-001", "навигация"),
             link("L-EN-11", "@minor", "EN-001", "навигация")]
    assert errs_for(extra) == []


def test_unknown_target_token_rejected():
    assert any("to_id @everything" in e for e in errs_for([link("L-EN-07", "EN-001", "@everything", "навигация")]))


def test_unknown_source_token_rejected():
    assert any("from_id @everything" in e for e in errs_for([link("L-EN-07", "@everything", "EN-001", "навигация")]))
