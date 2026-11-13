from fixtures_structure import CARDS, en_map, es_map
from structure_hreflang import HREFLANG_COLUMNS, check_hreflang


# --- hreflang ---

def hl(ent, lang, pid, url, switch, wave="запуск", template="cards"):
    return {"entity_id": ent, "template": template, "lang": lang, "page_id": pid, "url": url, "wave": wave,
            "status": "planned", "in_hreflang": "no", "switch_to": switch}


def good_hreflang():
    rows = [
        hl("page:home", "en", "EN-001", "/", "/es", template="home"),
        hl("page:home", "es", "ES-001", "/es", "/", template="home"),
        hl("tool:yes-no", "en", "EN-007", "/yes-no", "/es", template="yes-no"),
        hl("ref:yes-no-cards", "en", "EN-009", "/yes-no/cards", "/es", template="yes-no"),
        hl("hub:cards", "en", "EN-014", "/cards", "/es/cartas"),
        hl("hub:cards", "es", "ES-012", "/es/cartas", "/cards"),
        hl("hub:major-arcana", "en", "EN-093", "/cards/major-arcana", "/es/cartas/arcanos-mayores"),
        hl("hub:major-arcana", "es", "ES-091", "/es/cartas/arcanos-mayores", "/cards/major-arcana"),
        hl("card:major-18-moon", "en", "EN-033", "/cards/the-moon", "/es/cartas/la-luna"),
        hl("card:major-18-moon", "es", "ES-031", "/es/cartas/la-luna", "/cards/the-moon"),
        hl("card:cups-10-ten", "en", "EN-087", "/cards/ten-of-cups", "/es/cartas/diez-de-copas"),
        hl("card:cups-10-ten", "es", "ES-085", "/es/cartas/diez-de-copas", "/cards/ten-of-cups"),
    ]
    for c in CARDS:
        rows.append(hl(f"card-yes-no:{c['card_id']}", "en", "EN-097", f"/cards/{c['slug_en']}/yes-or-no",
                       f"/es/cartas/{c['slug_es']}", wave="V1.1", template="card-context"))
    return rows


def maps():
    return {"en": en_map(), "es": es_map()}


def test_good_hreflang_passes():
    assert check_hreflang(HREFLANG_COLUMNS, good_hreflang(), maps(), CARDS, launch_clusters=5) == []


def test_switch_must_go_to_pair():
    rows = [dict(h, switch_to="/es") if h["page_id"] == "EN-033" else h for h in good_hreflang()]
    assert any("на пару" in e for e in check_hreflang(HREFLANG_COLUMNS, rows, maps(), CARDS, launch_clusters=5))


def test_in_hreflang_requires_published_pair():
    rows = [dict(h, in_hreflang="yes") if h["page_id"] == "EN-033" else h for h in good_hreflang()]
    assert any("опубликованной" in e for e in check_hreflang(HREFLANG_COLUMNS, rows, maps(), CARDS, launch_clusters=5))


def test_template_rows_must_cover_all_cards():
    rows = [h for h in good_hreflang() if h["url"] != "/cards/ten-of-cups/yes-or-no"]
    errs = check_hreflang(HREFLANG_COLUMNS, rows, maps(), CARDS, launch_clusters=5)
    assert any("EN-097" in e for e in errs)


def test_wave_must_match_map():
    rows = [dict(h, wave="V1.1") if h["page_id"] == "EN-014" else h for h in good_hreflang()]
    assert any("wave" in e for e in check_hreflang(HREFLANG_COLUMNS, rows, maps(), CARDS, launch_clusters=5))


def test_launch_cluster_count_checked():
    errs = check_hreflang(HREFLANG_COLUMNS, good_hreflang(), maps(), CARDS, launch_clusters=84)
    assert any("кластеров запуска 5" in e for e in errs)


# --- адрес и сущность строки hreflang сверяются с картой (финальное ревью, Important 1) ---

def test_stale_url_after_map_change_rejected():
    m = maps()
    m["en"] = [dict(r, url="/yes-or-no") if r["id"] == "EN-007" else r for r in m["en"]]
    errs = check_hreflang(HREFLANG_COLUMNS, good_hreflang(), m, CARDS, launch_clusters=5)
    assert any("EN-007" in e and "/yes-or-no" in e for e in errs)


def test_swapped_entity_ids_in_es_map_rejected():
    m = maps()
    swap = {"ES-031": "card:cups-10-ten", "ES-085": "card:major-18-moon"}
    m["es"] = [dict(r, entity_id=swap[r["id"]]) if r["id"] in swap else r for r in m["es"]]
    errs = check_hreflang(HREFLANG_COLUMNS, good_hreflang(), m, CARDS, launch_clusters=5)
    assert any("entity_id" in e and "ES-031" in e for e in errs)


def test_swapped_urls_in_map_rejected():
    m = maps()
    swap = {"EN-007": "/yes-no/cards", "EN-009": "/yes-no"}
    m["en"] = [dict(r, url=swap[r["id"]]) if r["id"] in swap else r for r in m["en"]]
    errs = check_hreflang(HREFLANG_COLUMNS, good_hreflang(), m, CARDS, launch_clusters=5)
    assert any("EN-007" in e and "url" in e for e in errs)
    assert any("EN-009" in e and "url" in e for e in errs)


def test_template_row_needs_known_card_and_expanded_url():
    rows = [dict(h, entity_id="card-yes-no:no-such-card") if h["url"] == "/cards/the-moon/yes-or-no" else h
            for h in good_hreflang()]
    errs = check_hreflang(HREFLANG_COLUMNS, rows, maps(), CARDS, launch_clusters=5)
    assert any("card-yes-no:no-such-card" in e for e in errs)
    rows = [dict(h, url="/cards/ten-of-cups/yes-or-no") if h["entity_id"] == "card-yes-no:major-18-moon"
            else dict(h, url="/cards/the-moon/yes-or-no") if h["entity_id"] == "card-yes-no:cups-10-ten" else h
            for h in good_hreflang()]
    errs = check_hreflang(HREFLANG_COLUMNS, rows, maps(), CARDS, launch_clusters=5)
    assert any("card-yes-no:major-18-moon" in e and "url" in e for e in errs)
