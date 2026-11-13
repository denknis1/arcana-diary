"""Этап 2: таблица языковых пар hreflang.csv по entity_id из карт страниц (спецификация этапа 2, раздел 3).

Запуск: python3 tools/research/build_hreflang.py  — переписывает docs/research/stage2/hreflang.csv.
До открытия сайта для индексации у всех строк status=planned, in_hreflang=no.
"""
import csv
from pathlib import Path

from structure_hreflang import HREFLANG_COLUMNS
from structure_map import STAGE1, STAGE2, WAVE_ORDER, is_page

# Куда ведёт переключатель языка, пока у страницы нет пары (спецификация, раздел 3).
FALLBACK = {
    "EN-005": "/es",
    "EN-009": "/es/si-o-no",
    "EN-013": "/es/tiradas",
    "EN-097": "/es/cartas/{slug_es}",
    "EN-098": "/es/cartas/{slug_es}",
    "EN-103": "/es/tiradas",
    "EN-118": "/es/cartas",
    "ES-099": "/",
    **{f"EN-{n}": "/es" for n in range(106, 118)},
}


def read(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def expand(row: dict, cards: list[dict]) -> list[tuple[str, str, dict | None]]:
    """(entity_id, url, card) для строки карты; шаблон ×78 разворачивается по cards.csv."""
    if "{" not in row["url"]:
        return [(row["entity_id"], row["url"], None)]
    return [(row["entity_id"].format(card_id=c["card_id"]),
             row["url"].format(slug_en=c["slug_en"], slug_es=c["slug_es"]), c) for c in cards]


def build() -> list[dict]:
    cards = read(STAGE1 / "cards.csv")
    maps = {lang: read(STAGE1 / f"page-map-{lang}.csv") for lang in ("en", "es")}
    entries = []
    for lang, rows in maps.items():
        for r in rows:
            if is_page(r) and r["entity_id"] and WAVE_ORDER[r["wave"]] <= 1:
                for ent, url, card in expand(r, cards):
                    entries.append({"entity_id": ent, "template": r["page_type"], "lang": lang,
                                    "page_id": r["id"], "url": url, "wave": r["wave"], "status": "planned",
                                    "in_hreflang": "no", "_card": card})
    by_entity = {(e["entity_id"], e["lang"]): e for e in entries}
    for e in entries:
        other = "es" if e["lang"] == "en" else "en"
        pair = by_entity.get((e["entity_id"], other))
        if pair and WAVE_ORDER[pair["wave"]] <= WAVE_ORDER[e["wave"]]:
            e["switch_to"] = pair["url"]
        else:
            fallback = FALLBACK[e["page_id"]]
            card = e["_card"]
            e["switch_to"] = fallback.format(slug_es=card["slug_es"]) if card else fallback
    return entries


def write(entries: list[dict]) -> None:
    STAGE2.mkdir(parents=True, exist_ok=True)
    with open(STAGE2 / "hreflang.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HREFLANG_COLUMNS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(entries)


if __name__ == "__main__":
    rows = build()
    write(rows)
    print(f"OK: hreflang.csv — {len(rows)} строк")
