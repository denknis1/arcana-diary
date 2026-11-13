"""Этап 2: добавляет в карты страниц колонки структуры (спецификация 2026-11-13-stage2-structure-design.md).

Запуск: python3 tools/research/build_structure.py  — переписывает page-map-en.csv и page-map-es.csv на месте.
Повторный запуск даёт тот же результат.
"""
import csv
from pathlib import Path

from validate_page_map import COLUMNS_EN, COLUMNS_ES, STRUCTURE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
STAGE1 = ROOT / "docs/research/stage1"

# id: (url, entity_id, parent_id, breadcrumb, menu_item, host_id, pages)
NONCARD = {
    "en": {
        "EN-001": ("/", "page:home", "", "", "reading", "", "1"),
        "EN-002": ("/#ai-reader", "", "", "", "", "EN-001", "0"),
        "EN-003": ("/#what-a-reading-is", "", "", "", "", "EN-001", "0"),
        "EN-004": ("/#example-questions", "", "", "", "", "EN-001", "0"),
        "EN-005": ("/one-card", "tool:one-card", "EN-001", "", "", "", "1"),
        "EN-006": ("/daily", "tool:daily", "EN-001", "", "daily", "", "1"),
        "EN-007": ("/yes-no", "tool:yes-no", "EN-001", "", "yes-no", "", "1"),
        "EN-008": ("/yes-no#one-or-three", "", "", "", "", "EN-007", "0"),
        "EN-009": ("/yes-no/cards", "ref:yes-no-cards", "EN-007", "EN-007>EN-009", "yes-no", "", "1"),
        "EN-010": ("/yes-no#own-deck", "", "", "", "", "EN-007", "0"),
        "EN-011": ("/love", "tool:love", "EN-001", "", "love", "", "1"),
        "EN-012": ("/love#situation", "", "", "", "", "EN-011", "0"),
        "EN-013": ("/spreads/love", "spread:love", "EN-100", "", "", "", "1"),
        "EN-014": ("/cards", "hub:cards", "EN-001", "", "cards", "", "1"),
        "EN-093": ("/cards/major-arcana", "hub:major-arcana", "EN-014", "EN-014>EN-093", "cards", "", "1"),
        "EN-094": ("/cards#download", "", "", "", "", "EN-014", "0"),
        "EN-095": ("/cards/{slug_en}#reversed", "", "", "", "", "@cards", "0"),
        "EN-096": ("/cards/{slug_en}#love", "", "", "", "", "@cards", "0"),
        "EN-097": ("/cards/{slug_en}/yes-or-no", "card-yes-no:{card_id}", "@same-card", "", "cards", "", "78"),
        "EN-098": ("/cards/{slug_en}/feelings", "card-feelings:{card_id}", "@same-card", "", "cards", "", "78"),
        "EN-099": ("/cards/{slug_en}#advice", "", "", "", "", "@cards", "0"),
        "EN-100": ("/spreads", "spread:index", "EN-001", "", "", "", "1"),
        "EN-101": ("/spreads/celtic-cross", "spread:celtic-cross", "EN-100", "", "", "", "1"),
        "EN-102": ("/spreads/three-card", "spread:three-card", "EN-100", "", "", "", "1"),
        "EN-103": ("/spreads/guidance", "spread:guidance", "EN-100", "", "", "", "1"),
        "EN-104": ("/birth-card", "tool:birth-card", "EN-001", "", "", "", "1"),
        "EN-105": ("/birth-card#result", "", "", "", "", "EN-104", "0"),
        "EN-106": ("/horoscope/aries", "horoscope:aries", "EN-001", "", "", "", "1"),
        "EN-107": ("/horoscope/taurus", "horoscope:taurus", "EN-001", "", "", "", "1"),
        "EN-108": ("/horoscope/gemini", "horoscope:gemini", "EN-001", "", "", "", "1"),
        "EN-109": ("/horoscope/cancer", "horoscope:cancer", "EN-001", "", "", "", "1"),
        "EN-110": ("/horoscope/leo", "horoscope:leo", "EN-001", "", "", "", "1"),
        "EN-111": ("/horoscope/virgo", "horoscope:virgo", "EN-001", "", "", "", "1"),
        "EN-112": ("/horoscope/libra", "horoscope:libra", "EN-001", "", "", "", "1"),
        "EN-113": ("/horoscope/scorpio", "horoscope:scorpio", "EN-001", "", "", "", "1"),
        "EN-114": ("/horoscope/sagittarius", "horoscope:sagittarius", "EN-001", "", "", "", "1"),
        "EN-115": ("/horoscope/capricorn", "horoscope:capricorn", "EN-001", "", "", "", "1"),
        "EN-116": ("/horoscope/aquarius", "horoscope:aquarius", "EN-001", "", "", "", "1"),
        "EN-117": ("/horoscope/pisces", "horoscope:pisces", "EN-001", "", "", "", "1"),
        "EN-118": ("/horoscope/zodiac-cards", "ref:zodiac-cards", "EN-001", "", "", "", "1"),
        "EN-119": ("/quiz/{slug}", "", "", "", "", "", "1"),
        "EN-120": ("", "", "", "", "", "", "0"),
        "EN-121": ("", "", "", "", "", "", "0"),
        "EN-122": ("/cards/combinations", "", "", "", "", "", "1"),
        "EN-123": ("/learn", "", "", "", "", "", "1"),
        "EN-124": ("", "", "", "", "", "", "0"),
    },
    "es": {
        "ES-001": ("/es", "page:home", "", "", "reading", "", "1"),
        "ES-002": ("/es#que-es-el-tarot", "", "", "", "", "ES-001", "0"),
        "ES-003": ("/es#una-carta", "", "", "", "", "ES-001", "0"),
        "ES-004": ("/es/carta-del-dia", "tool:daily", "ES-001", "", "daily", "", "1"),
        "ES-005": ("/es/si-o-no", "tool:yes-no", "ES-001", "", "yes-no", "", "1"),
        "ES-006": ("/es/si-o-no#una-o-tres", "", "", "", "", "ES-005", "0"),
        "ES-007": ("/es/si-o-no#por-que", "", "", "", "", "ES-005", "0"),
        "ES-008": ("", "", "", "", "", "", "0"),
        "ES-009": ("/es/amor", "tool:love", "ES-001", "", "love", "", "1"),
        "ES-010": ("/es/amor#situacion", "", "", "", "", "ES-009", "0"),
        "ES-011": ("", "", "", "", "", "", "0"),
        "ES-012": ("/es/cartas", "hub:cards", "ES-001", "", "cards", "", "1"),
        "ES-091": ("/es/cartas/arcanos-mayores", "hub:major-arcana", "ES-012", "ES-012>ES-091", "cards", "", "1"),
        "ES-092": ("/es/cartas/{slug_es}#invertida", "", "", "", "", "@cards", "0"),
        "ES-093": ("/es/cartas/{slug_es}#amor", "", "", "", "", "@cards", "0"),
        "ES-094": ("/es/cartas/{slug_es}#si-o-no", "", "", "", "", "@cards", "0"),
        "ES-095": ("", "", "", "", "", "", "0"),
        "ES-096": ("", "", "", "", "", "", "0"),
        "ES-097": ("/es/tiradas", "spread:index", "ES-001", "", "", "", "1"),
        "ES-098": ("/es/tiradas/cruz-celta", "spread:celtic-cross", "ES-097", "", "", "", "1"),
        "ES-099": ("/es/tiradas/3-cartas", "spread:three-card", "ES-001", "ES-099", "reading", "", "1"),
        "ES-100": ("/es/arcano-de-nacimiento", "tool:birth-card", "ES-001", "", "", "", "1"),
        "ES-101": ("/es/arcano-de-nacimiento#resultado", "", "", "", "", "ES-100", "0"),
        "ES-102": ("", "", "", "", "", "", "0"),
        "ES-103": ("/es/arcano-de-nacimiento#por-preguntas", "", "", "", "", "ES-100", "0"),
        "ES-104": ("", "", "", "", "", "", "0"),
        "ES-105": ("", "", "", "", "", "", "0"),
        "ES-106": ("/es/aprender", "", "", "", "", "", "1"),
        "ES-107": ("", "", "", "", "", "", "0"),
    },
}
CARD_ROWS = {"en": (15, 92), "es": (13, 90)}
HUB = {"en": "EN-014", "es": "ES-012"}
MAJORS = {"en": "EN-093", "es": "ES-091"}
CARDS_PREFIX = {"en": "/cards/", "es": "/es/cartas/"}
NAME_COL = {"en": "name_en", "es": "name_es"}
SLUG_COL = {"en": "slug_en", "es": "slug_es"}


def load_cards() -> list[dict]:
    with open(STAGE1 / "cards.csv", newline="") as f:
        return list(csv.DictReader(f))


def card_structure(lang: str, rid: str, card: dict) -> tuple:
    major = card["arcana"] == "major"
    parent = MAJORS[lang] if major else HUB[lang]
    crumbs = f"{HUB[lang]}>{MAJORS[lang]}>{rid}" if major else f"{HUB[lang]}>{rid}"
    url = CARDS_PREFIX[lang] + card[SLUG_COL[lang]]
    return (url, f"card:{card['card_id']}", parent, crumbs, "cards", "", "1")


def build(lang: str) -> None:
    path = STAGE1 / f"page-map-{lang}.csv"
    columns = COLUMNS_EN if lang == "en" else COLUMNS_ES
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    cards = load_cards()
    first, last = CARD_ROWS[lang]
    prefix = lang.upper()
    card_ids = [f"{prefix}-{n:03d}" for n in range(first, last + 1)]
    assert len(card_ids) == len(cards) == 78
    card_of = dict(zip(card_ids, cards))
    covered = set(NONCARD[lang]) | set(card_ids)
    ids = {r["id"] for r in rows}
    assert ids == covered, f"строки без структуры или лишние: {sorted(ids ^ covered)}"
    for row in rows:
        rid = row["id"]
        if rid in card_of:
            card = card_of[rid]
            assert row["working_title"].startswith(card[NAME_COL[lang]]), (rid, row["working_title"])
            values = card_structure(lang, rid, card)
        else:
            values = NONCARD[lang][rid]
        row.update(dict(zip(STRUCTURE_COLUMNS, values)))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in columns})


if __name__ == "__main__":
    for lang in ("en", "es"):
        build(lang)
    print("OK: колонки структуры записаны в page-map-en.csv и page-map-es.csv")
