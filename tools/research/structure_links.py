"""Этап 2: проверка матрицы ссылок links-en.csv / links-es.csv (спецификация, разделы 2 и 5)."""
from structure_map import ALL_CARDS, SAME_CARD, WAVE_ORDER

LINK_COLUMNS = ["link_id", "from_id", "to_id", "link_type", "moment", "anchor_pattern", "context_terms",
                "wave", "note"]
LINK_TYPES = {"подробность", "метод", "действие", "навигация", "сохранение"}
FROM_TOKENS = {ALL_CARDS}
TO_TOKENS = {ALL_CARDS, "@drawn", SAME_CARD, "@neighbors", "@diary"}


def check_links(header: list[str], links: list[dict], rows: list[dict], lang: str) -> list[str]:
    if header != LINK_COLUMNS:
        return [f"links-{lang}: колонки {header}, ожидалось {LINK_COLUMNS}"]
    errs: list[str] = []
    by_id = {r["id"]: r for r in rows if r["url"]}
    prefix = f"L-{lang.upper()}-"
    seen: set[str] = set()
    launch_types: set[str] = set()

    def wave_of(ref: str) -> int:
        return WAVE_ORDER[by_id[ref]["wave"]] if ref in by_id else 0

    for ln in links:
        lid = ln["link_id"]
        if not lid.startswith(prefix):
            errs.append(f"{lid}: id должен начинаться с {prefix}")
        if lid in seen:
            errs.append(f"{lid}: повтор id")
        seen.add(lid)
        src, dst = ln["from_id"], ln["to_id"]
        if src not in by_id and src not in FROM_TOKENS:
            errs.append(f"{lid}: from_id {src} — нет такой строки с адресом")
        if dst not in by_id and dst not in TO_TOKENS:
            errs.append(f"{lid}: to_id {dst} — нет такой строки с адресом")
        if src == dst and src not in FROM_TOKENS:
            errs.append(f"{lid}: ссылка на себя")
        if ln["link_type"] not in LINK_TYPES:
            errs.append(f"{lid}: неизвестный link_type {ln['link_type']}")
        for c in ("moment", "anchor_pattern"):
            if not ln[c].strip():
                errs.append(f"{lid}: пустое {c}")
        if ln["wave"] not in WAVE_ORDER:
            errs.append(f"{lid}: неизвестный wave {ln['wave']}")
            continue
        w = WAVE_ORDER[ln["wave"]]
        if w < max(wave_of(src), wave_of(dst)):
            errs.append(f"{lid}: ссылка ({ln['wave']}) раньше своей страницы")
        if w == 0:
            launch_types.add(ln["link_type"])
    if launch_types != LINK_TYPES:
        errs.append(f"links-{lang}: на запуске нет типов связи {sorted(LINK_TYPES - launch_types)}")
    return errs
