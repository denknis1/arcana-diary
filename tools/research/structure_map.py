"""Этап 2: проверка колонок структуры в картах страниц — адрес, дом, крошки, меню, разделы.

Спецификация: docs/superpowers/specs/2026-11-13-stage2-structure-design.md, разделы 1 и 5.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE1 = ROOT / "docs/research/stage1"
STAGE2 = ROOT / "docs/research/stage2"

WAVE_ORDER = {"запуск": 0, "V1.1": 1, "V2": 2, "V3": 3}
PAGE_DECISION = "самостоятельная страница"
SECTION_DECISIONS = {"раздел", "доработать"}
MENU_ITEMS = {"reading", "yes-no", "love", "daily", "cards"}
HOME = {"en": "EN-001", "es": "ES-001"}
HOME_URL = {"en": "/", "es": "/es"}
CARDS_PREFIX = {"en": "/cards/", "es": "/es/cartas/"}
SLUG_COL = {"en": "slug_en", "es": "slug_es"}
RESERVED = {"en": {"major-arcana", "combinations"}, "es": {"arcanos-mayores"}}
SEGMENT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TEMPLATE_VAR = re.compile(r"\{(slug_en|slug_es|slug|card_id)\}")
SAME_CARD = "@same-card"
ALL_CARDS = "@cards"


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def is_page(row: dict) -> bool:
    return row["decision"] == PAGE_DECISION


def is_section(row: dict) -> bool:
    return row["decision"] in SECTION_DECISIONS


def url_errors(url: str, lang: str) -> list[str]:
    """Адрес без якоря: строчная латиница и цифры, дефисы, без слеша на конце, префикс языка."""
    if url == "/":
        return [] if lang == "en" else ["адрес / принадлежит английской версии"]
    if not url.startswith("/"):
        return [f"адрес не начинается с /: {url}"]
    if url.endswith("/"):
        return [f"слеш на конце: {url}"]
    segs = url[1:].split("/")
    errs = []
    if lang == "es" and segs[0] != "es":
        errs.append(f"ES-адрес не в /es: {url}")
    if lang == "en" and segs[0] == "es":
        errs.append(f"EN-адрес в /es: {url}")
    for s in segs:
        if not SEGMENT.match(TEMPLATE_VAR.sub("x", s)):
            errs.append(f"недопустимый сегмент «{s}» в {url}")
    return errs


def ancestors_chain(rid: str, by_id: dict, home: str) -> list[str]:
    chain = [rid]
    seen = {rid}
    parent = by_id[rid]["parent_id"]
    while parent and parent != home:
        if parent in seen or parent not in by_id:
            return []
        chain.append(parent)
        seen.add(parent)
        parent = by_id[parent]["parent_id"]
    return list(reversed(chain))


def check_map(rows: list[dict], lang: str, cards: list[dict]) -> list[str]:
    errs: list[str] = []
    by_id = {r["id"]: r for r in rows}
    home = HOME[lang]
    page_urls: dict[str, str] = {}
    for r in rows:
        rid, url, wave = r["id"], r["url"], r["wave"]
        w = WAVE_ORDER[wave]
        if not r["pages"].isdigit():
            errs.append(f"{rid}: pages не число: {r['pages']}")
        if is_page(r):
            if not url:
                errs.append(f"{rid}: у страницы нет url")
                continue
            if "#" in url:
                errs.append(f"{rid}: у страницы якорь в url: {url}")
            errs += [f"{rid}: {e}" for e in url_errors(url, lang)]
            if url in page_urls:
                errs.append(f"{rid}: url {url} уже у {page_urls[url]}")
            page_urls[url] = rid
            if r["host_id"]:
                errs.append(f"{rid}: у страницы заполнен host_id")
            if r["menu_item"] and r["menu_item"] not in MENU_ITEMS:
                errs.append(f"{rid}: неизвестный menu_item {r['menu_item']}")
            templated = bool(TEMPLATE_VAR.search(url))
            if templated and r["entity_id"] and r["pages"] != "78" and "{slug}" not in url:
                errs.append(f"{rid}: шаблон ×78, но pages={r['pages']}")
            if not templated and r["pages"] != "1":
                errs.append(f"{rid}: у страницы pages должно быть 1, а не {r['pages']}")
            if w <= 1:
                if not r["entity_id"]:
                    errs.append(f"{rid}: у страницы {wave} нет entity_id")
                if rid == home:
                    if url != HOME_URL[lang] or r["parent_id"]:
                        errs.append(f"{rid}: главная должна быть {HOME_URL[lang]} без родителя")
                    continue
                parent = r["parent_id"]
                if parent == SAME_CARD:
                    if not templated:
                        errs.append(f"{rid}: {SAME_CARD} допустим только у шаблона ×78")
                elif parent not in by_id or not is_page(by_id[parent]):
                    errs.append(f"{rid}: родитель {parent or '—'} не страница карты")
                    continue
                elif WAVE_ORDER[by_id[parent]["wave"]] > w:
                    errs.append(f"{rid}: родитель {parent} выходит позже ({by_id[parent]['wave']})")
                crumbs = r["breadcrumb"]
                if parent not in (home, SAME_CARD):
                    expected = ">".join(ancestors_chain(rid, by_id, home))
                    if w == 0 and not crumbs:
                        errs.append(f"{rid}: у страницы запуска с родителем не на главной нет крошек")
                    elif crumbs and crumbs != expected:
                        errs.append(f"{rid}: крошки {crumbs} не совпадают с цепочкой дома {expected}")
                elif crumbs and parent == home and crumbs != rid:
                    errs.append(f"{rid}: крошки {crumbs} не совпадают с цепочкой дома {rid}")
                elif crumbs and parent == SAME_CARD:
                    errs.append(f"{rid}: у шаблона {SAME_CARD} крошки не задаются в карте")
            elif r["entity_id"] or r["parent_id"] or r["breadcrumb"]:
                errs.append(f"{rid}: у страницы {wave} entity_id, parent_id и breadcrumb задаются в своей волне")
        elif is_section(r):
            base, _, anchor = url.partition("#")
            if not url or not anchor or not SEGMENT.match(anchor):
                errs.append(f"{rid}: у раздела нужен url с якорем, получено «{url}»")
                continue
            if r["entity_id"] or r["parent_id"] or r["breadcrumb"] or r["menu_item"]:
                errs.append(f"{rid}: у раздела заполнены поля страницы")
            if r["pages"] != "0":
                errs.append(f"{rid}: у раздела pages должно быть 0")
            host = r["host_id"]
            if host == ALL_CARDS:
                if base != CARDS_PREFIX[lang] + "{" + SLUG_COL[lang] + "}":
                    errs.append(f"{rid}: раздел на 78 картах, но адрес {base}")
            elif host not in by_id or not is_page(by_id[host]):
                errs.append(f"{rid}: хозяин {host or '—'} не страница карты")
            else:
                if by_id[host]["url"] != base:
                    errs.append(f"{rid}: адрес {base} не совпадает с адресом хозяина {by_id[host]['url']}")
                if WAVE_ORDER[by_id[host]["wave"]] > w:
                    errs.append(f"{rid}: хозяин {host} выходит позже раздела")
        else:
            if any(r[c] for c in ("url", "entity_id", "parent_id", "breadcrumb", "menu_item", "host_id")):
                errs.append(f"{rid}: у строки «{r['decision']}» поля структуры должны быть пустыми")
            if r["pages"] != "0":
                errs.append(f"{rid}: у строки «{r['decision']}» pages должно быть 0")
    card_urls = {CARDS_PREFIX[lang] + c[SLUG_COL[lang]] for c in cards}
    missing = card_urls - set(page_urls)
    if missing:
        errs.append(f"нет страниц карт: {sorted(missing)[:5]}")
    for slug in RESERVED[lang]:
        if CARDS_PREFIX[lang] + slug in card_urls:
            errs.append(f"служебный слаг {slug} совпадает со слагом карты")
    return errs
