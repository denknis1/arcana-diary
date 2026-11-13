"""Общие тестовые данные проверок этапа 2: маленькие карты EN и ES с двумя картами колоды."""

CARDS = [
    {"card_id": "major-18-moon", "arcana": "major", "slug_en": "the-moon", "slug_es": "la-luna"},
    {"card_id": "cups-10-ten", "arcana": "minor", "slug_en": "ten-of-cups", "slug_es": "diez-de-copas"},
]


def row(rid, url="", decision="самостоятельная страница", wave="запуск", entity="", parent="", crumbs="",
        menu="", host="", pages="1", page_type="cards"):
    return {"id": rid, "url": url, "decision": decision, "wave": wave, "entity_id": entity,
            "parent_id": parent, "breadcrumb": crumbs, "menu_item": menu, "host_id": host, "pages": pages,
            "page_type": page_type}


def en_map():
    return [
        row("EN-001", "/", entity="page:home", menu="reading", page_type="home"),
        row("EN-007", "/yes-no", entity="tool:yes-no", parent="EN-001", menu="yes-no", page_type="yes-no"),
        row("EN-009", "/yes-no/cards", entity="ref:yes-no-cards", parent="EN-007", crumbs="EN-007>EN-009",
            menu="yes-no", page_type="yes-no"),
        row("EN-014", "/cards", entity="hub:cards", parent="EN-001", menu="cards"),
        row("EN-093", "/cards/major-arcana", entity="hub:major-arcana", parent="EN-014",
            crumbs="EN-014>EN-093", menu="cards"),
        row("EN-033", "/cards/the-moon", entity="card:major-18-moon", parent="EN-093",
            crumbs="EN-014>EN-093>EN-033", menu="cards"),
        row("EN-087", "/cards/ten-of-cups", entity="card:cups-10-ten", parent="EN-014",
            crumbs="EN-014>EN-087", menu="cards"),
        row("EN-095", "/cards/{slug_en}#reversed", decision="раздел", host="@cards", pages="0",
            page_type="card-context"),
        row("EN-097", "/cards/{slug_en}/yes-or-no", wave="V1.1", entity="card-yes-no:{card_id}",
            parent="@same-card", menu="cards", pages="78", page_type="card-context"),
        row("EN-121", "", decision="отклонить", wave="V2", pages="0", page_type="pairs"),
    ]


def es_map():
    return [
        row("ES-001", "/es", entity="page:home", menu="reading", page_type="home"),
        row("ES-012", "/es/cartas", entity="hub:cards", parent="ES-001", menu="cards"),
        row("ES-091", "/es/cartas/arcanos-mayores", entity="hub:major-arcana", parent="ES-012",
            crumbs="ES-012>ES-091", menu="cards"),
        row("ES-031", "/es/cartas/la-luna", entity="card:major-18-moon", parent="ES-091",
            crumbs="ES-012>ES-091>ES-031", menu="cards"),
        row("ES-085", "/es/cartas/diez-de-copas", entity="card:cups-10-ten", parent="ES-012",
            crumbs="ES-012>ES-085", menu="cards"),
    ]


def replace(rows, rid, **over):
    return [dict(r, **over) if r["id"] == rid else r for r in rows]
