# Этап 2: структура, адреса, перелинковка, hreflang — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Карты страниц EN и ES получают адрес, дом, крошки и меню; матрица ссылок и таблица языковых пар лежат в CSV и проходят проверку скриптом — до первого текста и до первой строки кода сайта.

**Architecture:** Данные, а не код сайта. Колонки структуры записывает воспроизводимый скрипт `build_structure.py` из явной таблицы в самом скрипте и `cards.csv`; матрица ссылок пишется руками по таблице спецификации; таблицу пар `hreflang.csv` собирает `build_hreflang.py` из карт. Проверка разбита на три модуля (`structure_map.py`, `structure_links.py`, `structure_hreflang.py`) и общий запуск `validate_structure.py`.

**Tech Stack:** Python 3.12, только стандартная библиотека; pytest из `~/arcana-diary/api/.venv/bin/pytest`.

Спецификация: `docs/superpowers/specs/2026-11-13-stage2-structure-design.md`. Перед задачей прочитать её разделы, указанные в задаче.

## Global Constraints

- Английский на корне без префикса, испанский в `/es`; без слеша на конце, кроме корня `/`; главная ES — `/es`.
- Адрес: строчная латиница, цифры, дефисы; в испанских адресах без диакритики, `ñ` → `n`.
- Коды hreflang — `en`, `es`, `x-default`; пары только один к одному; до открытия сайта у всех строк `status=planned`, `in_hreflang=no`.
- Волны: `запуск` < `V1.1` < `V2` < `V3`. Ссылка, родитель, хозяин раздела, цель переключателя языка — не позже своей строки.
- ID строк карт не меняются: EN-001…EN-124, ES-001…ES-107; строки карт EN-015…092 ↔ ES-013…090 идут в порядке `cards.csv`.
- Запросы, объёмы, KD, решения и волны в картах этапа 1 не меняются; меняются только колонки структуры и пять рабочих названий ES (Task 3).
- CSV: UTF-8, разделитель запятая, конец строки `\n` (`csv.DictWriter(..., lineterminator="\n")`).
- Скрипты запускаются из корня репозитория `~/arcana-diary`: `python3 tools/research/<скрипт>.py`. Тесты: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q`.
- Коммит после каждой задачи в ветку `stage2-structure`; без `git push`. Сообщение заканчивается строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Никогда не коммитить `deploy/.env` и `deploy/caddy/stage_auth.caddy`; не цитировать приватный план продукта в файлах репозитория.
- Финальное ревью всей ветки выполняет агент на модели **Fable 5.2** (`claude-fable-5-2`) — решение владельца 13.11.2026.

## Карта файлов

| Файл | Задача | Ответственность |
|---|---|---|
| `tools/research/validate_page_map.py`, `test_validate_page_map.py` | 1, 3 | колонки и значения карты страниц |
| `tools/research/structure_map.py`, `test_structure_map.py`, `fixtures_structure.py` | 2 | адрес, дом, крошки, меню, разделы |
| `tools/research/validate_structure.py` | 2, 4, 5 | общий запуск проверок |
| `tools/research/rename_es_cards.py`, `build_structure.py` | 3 | имена карт ES, колонки структуры |
| `docs/research/stage1/cards.csv`, `page-map-en.csv`, `page-map-es.csv` | 3 | данные |
| `tools/research/structure_links.py`, `test_structure_links.py` | 4 | проверка матрицы ссылок |
| `docs/research/stage2/links-en.csv`, `links-es.csv` | 4 | матрица ссылок |
| `tools/research/structure_hreflang.py`, `test_structure_hreflang.py`, `build_hreflang.py` | 5 | пары hreflang |
| `docs/research/stage2/hreflang.csv` | 5 | таблица пар |
| `docs/research/stage2/00-structure.md`, `99-changelog.md`, `docs/research/stage1/99-changelog.md` | 6 | документы этапа |

---

### Task 1: Доработка валидатора карты страниц

Спецификация: раздел 5 «Валидатор». Закрывает пункт «Валидатор» из «Передано этапу 2» журнала этапа 1.

**Files:**
- Modify: `tools/research/validate_page_map.py` (весь файл)
- Modify: `tools/research/test_validate_page_map.py`

**Interfaces:**
- Produces: `STRUCTURE_COLUMNS: list[str]` = `["url", "entity_id", "parent_id", "breadcrumb", "menu_item", "host_id", "pages"]`; `COLUMNS_EN_V12`, `COLUMNS_ES_V12` (колонки этапа 1); `COLUMNS_EN`, `COLUMNS_ES` (= V12 + `STRUCTURE_COLUMNS`); `validate(path: str, lang: str) -> list[str]` (бросает `ValueError` при языке не `en`/`es`); `main(argv: list[str]) -> int` (0 — OK, 1 — ошибки, 2 — неверный запуск).
- В этой задаче `validate` принимает и заголовок v1.2, и заголовок v1.3: карты получат новые колонки в Task 3, тогда приём v1.2 будет снят.

- [ ] **Step 1: Обновить заголовок тестового файла и помощники**

В `tools/research/test_validate_page_map.py` заменить начало файла (импорты, `write`, `good_row`) на:

```python
import csv
from pathlib import Path

import pytest

from validate_page_map import COLUMNS_EN, COLUMNS_EN_V12, COLUMNS_ES, main, validate


def write(tmp_path: Path, lang: str, rows: list[dict], cols: list[str] | None = None) -> str:
    cols = cols or (COLUMNS_EN if lang == "en" else COLUMNS_ES)
    p = tmp_path / f"map-{lang}.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "нет данных") for c in cols})
    return str(p)


def good_row(**over) -> dict:
    row = {
        "id": "en-001", "page_type": "yes-no", "working_title": "Yes or No Tarot",
        "task": "решает да/нет → перед решением → проверить знак карты → короткий ответ с причиной",
        "intent_label": "информационный", "top_entities": "tarot|yes or no|card",
        "queries": "yes or no tarot", "volume_us": "41000", "kd": "60", "data_date": "2026-11-11",
        "decision": "самостоятельная страница", "rationale": "40-tga.md#yes-no-en",
        "priority_value": "высокий", "priority_readiness": "средний", "priority_constraints": "нет",
        "maintenance_cost": "неизвестно", "dependencies": "нет", "open_questions": "нет", "wave": "запуск",
        "url": "/yes-no", "entity_id": "tool:yes-no", "parent_id": "EN-001", "breadcrumb": "",
        "menu_item": "yes-no", "host_id": "", "pages": "1",
    }
    row.update(over)
    return row
```

Существующие семь тестов не менять.

- [ ] **Step 2: Добавить тесты в конец файла**

```python
def test_kd_not_number_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(kd="высокий")]), "en")
    assert any("kd не число" in e for e in errs)


def test_kd_no_data_allowed(tmp_path):
    assert validate(write(tmp_path, "en", [good_row(kd="нет данных")]), "en") == []


def test_date_not_iso_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(data_date="11.11.2026")]), "en")
    assert any("ISO" in e for e in errs)


def test_date_no_data_allowed_without_volume(tmp_path):
    row = good_row(volume_us="нет данных", data_date="нет данных")
    assert validate(write(tmp_path, "en", [row]), "en") == []


def test_unknown_lang_raises(tmp_path):
    with pytest.raises(ValueError):
        validate(write(tmp_path, "en", [good_row()]), "fr")


def test_main_without_args_prints_usage(capsys):
    assert main(["validate_page_map.py"]) == 2
    assert "использование" in capsys.readouterr().out


def test_main_unknown_lang_exit_2(tmp_path, capsys):
    assert main(["validate_page_map.py", write(tmp_path, "en", [good_row()]), "fr"]) == 2
    assert "en или es" in capsys.readouterr().out


def test_v12_header_accepted_until_maps_get_structure(tmp_path):
    assert validate(write(tmp_path, "en", [good_row()], cols=COLUMNS_EN_V12), "en") == []
```

- [ ] **Step 3: Запустить тесты — должны упасть**

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q test_validate_page_map.py`
Expected: ошибка импорта `COLUMNS_EN_V12` / `main`.

- [ ] **Step 4: Заменить `validate_page_map.py` целиком**

```python
"""Проверка итоговой карты страниц (колонки — спецификации этапов 1 и 2)."""
import csv
import re
import sys

COMMON_HEAD = ["id", "page_type", "working_title", "task", "intent_label", "top_entities", "queries"]
COMMON_TAIL = ["kd", "data_date", "decision", "rationale", "priority_value", "priority_readiness",
               "priority_constraints", "maintenance_cost", "dependencies", "open_questions", "wave"]
STRUCTURE_COLUMNS = ["url", "entity_id", "parent_id", "breadcrumb", "menu_item", "host_id", "pages"]
COLUMNS_EN_V12 = COMMON_HEAD + ["volume_us"] + COMMON_TAIL
COLUMNS_ES_V12 = COMMON_HEAD + ["volume_mx", "volume_ar", "volume_co", "volume_es", "volume_us_es"] + COMMON_TAIL
COLUMNS_EN = COLUMNS_EN_V12 + STRUCTURE_COLUMNS
COLUMNS_ES = COLUMNS_ES_V12 + STRUCTURE_COLUMNS

PAGE_TYPES = {"home", "one-card", "yes-no", "love", "cards", "card-context", "spreads",
              "birth-card", "horoscope", "quiz", "pairs", "learn"}
DECISIONS = {"доработать", "раздел", "имеющийся ответ", "самостоятельная страница", "отклонить", "получить данные"}
WAVES = {"запуск", "V1.1", "V2", "V3"}
LANGS = {"en", "es"}
NO_DATA = "нет данных"
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
USAGE = "использование: python3 tools/research/validate_page_map.py <путь к карте.csv> <en|es>"


def validate(path: str, lang: str) -> list[str]:
    if lang not in LANGS:
        raise ValueError(f"язык должен быть en или es, получено: {lang}")
    expected = COLUMNS_EN if lang == "en" else COLUMNS_ES
    legacy = COLUMNS_EN_V12 if lang == "en" else COLUMNS_ES_V12
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header not in (expected, legacy):
            return [f"колонки не совпадают: ожидалось {expected}, получено {header}"]
        rows = list(reader)
    if header == legacy:
        expected = legacy

    errors: list[str] = []
    volume_cols = [c for c in expected if c.startswith("volume_")]
    seen: set[str] = set()
    for n, row in enumerate(rows, start=2):
        rid = row["id"]
        if rid in seen:
            errors.append(f"строка {n}: повтор id {rid}")
        seen.add(rid)
        if row["page_type"] not in PAGE_TYPES:
            errors.append(f"строка {n}: неизвестный page_type {row['page_type']}")
        if row["decision"] not in DECISIONS:
            errors.append(f"строка {n}: неизвестный decision {row['decision']}")
        if row["wave"] not in WAVES:
            errors.append(f"строка {n}: неизвестный wave {row['wave']}")
        has_volume = False
        for c in volume_cols + ["kd"]:
            if not row[c].strip():
                errors.append(f"строка {n}: пустое {c} — для отсутствия данных писать «{NO_DATA}»")
        for c in volume_cols:
            v = row[c].strip()
            if v and v != NO_DATA:
                if not v.isdigit():
                    errors.append(f"строка {n}: {c} не число: {v}")
                has_volume = True
        kd = row["kd"].strip()
        if kd and kd != NO_DATA and not kd.isdigit():
            errors.append(f"строка {n}: kd не число: {kd}")
        date = row["data_date"].strip()
        if date and date != NO_DATA and not ISO_DATE.match(date):
            errors.append(f"строка {n}: data_date не дата ISO (ГГГГ-ММ-ДД): {date}")
        if has_volume and (not date or date == NO_DATA):
            errors.append(f"строка {n}: есть объём, но пустой data_date")
        for c in ("task", "rationale"):
            if not row[c].strip() or row[c] == NO_DATA:
                errors.append(f"строка {n}: пустое {c}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(USAGE)
        return 2
    try:
        errs = validate(argv[1], argv[2])
    except ValueError as e:
        print(e)
        print(USAGE)
        return 2
    for e in errs:
        print(e)
    print("OK" if not errs else f"ошибок: {len(errs)}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 5: Запустить тесты и валидатор на настоящих картах**

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q test_validate_page_map.py`
Expected: `15 passed`.

Run: `cd ~/arcana-diary && python3 tools/research/validate_page_map.py docs/research/stage1/page-map-en.csv en && python3 tools/research/validate_page_map.py docs/research/stage1/page-map-es.csv es; python3 tools/research/validate_page_map.py; echo "код $?"`
Expected: `OK`, `OK`, затем строка `использование: …` и `код 2`.

- [ ] **Step 6: Commit**

```bash
cd ~/arcana-diary && git add tools/research/validate_page_map.py tools/research/test_validate_page_map.py && git commit -m "tools(stage2): page-map validator checks kd, ISO dates, language, usage; knows structure columns

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Проверка колонок структуры в картах

Спецификация: раздел 1 (правила адреса, карты адресов, служебные слаги), раздел 2 «Хлебные крошки», раздел 5 «Колонки карты».

**Files:**
- Create: `tools/research/structure_map.py`
- Create: `tools/research/fixtures_structure.py`
- Create: `tools/research/test_structure_map.py`
- Create: `tools/research/validate_structure.py`

**Interfaces:**
- Produces (`structure_map.py`): `ROOT`, `STAGE1`, `STAGE2: Path`; `WAVE_ORDER: dict[str, int]`; `SAME_CARD = "@same-card"`, `ALL_CARDS = "@cards"`; `read_csv(path: Path) -> tuple[list[str], list[dict]]`; `is_page(row: dict) -> bool` (решение «самостоятельная страница»); `is_section(row: dict) -> bool` («раздел» или «доработать»); `url_errors(url: str, lang: str) -> list[str]`; `check_map(rows: list[dict], lang: str, cards: list[dict]) -> list[str]`.
- Produces (`fixtures_structure.py`): `CARDS` (две карты: `major-18-moon`, `cups-10-ten`; ID строк в тестовых картах условные), `row(...)`, `en_map()`, `es_map()`, `replace(rows, rid, **over)` — их используют тесты Task 4 и 5.
- Правила, которые проверяет `check_map` (по строкам карты):
  - страница (`самостоятельная страница`): `url` есть, без якоря, по правилам адреса, уникален; `host_id` пуст; `menu_item` ∈ {`reading`, `yes-no`, `love`, `daily`, `cards`} или пуст; `pages` = 1, у шаблона с `{slug_*}`/`{card_id}` — 78 (шаблон `{slug}` без сущности — V2, `pages` = 1); у волн `запуск` и `V1.1` есть `entity_id` и родитель-страница не позже по волне (главная — без родителя, `/` или `/es`; `@same-card` — только у шаблона ×78); у волн V2/V3 `entity_id`, `parent_id`, `breadcrumb` пусты;
  - крошки — цепочка ID дома без главной (`EN-014>EN-093>EN-033`); обязательны у страниц запуска, чей родитель не главная; у страницы с родителем-главной допустима только цепочка из неё самой (`ES-099`); у `@same-card` пусты;
  - раздел (`раздел`, `доработать`): `url` = адрес хозяина + `#якорь`; `host_id` — страница не позже по волне или `@cards` (тогда адрес `/cards/{slug_en}` / `/es/cartas/{slug_es}`); поля страницы пусты; `pages` = 0;
  - прочие решения: все поля структуры пусты, `pages` = 0;
  - у каждой карты из `cards.csv` есть страница; служебные слаги (`major-arcana`, `combinations`; ES `arcanos-mayores`) не совпадают со слагами карт.

- [ ] **Step 1: Создать тестовые данные `fixtures_structure.py`**

```python
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
```

- [ ] **Step 2: Написать тесты `test_structure_map.py`**

```python
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
```

- [ ] **Step 3: Запустить — должны упасть**

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q test_structure_map.py`
Expected: `ModuleNotFoundError: No module named 'structure_map'`.

- [ ] **Step 4: Создать `structure_map.py`**

```python
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
```

- [ ] **Step 5: Создать общий запуск `validate_structure.py` (пока только карты)**

```python
"""Этап 2: проверка структуры — карты страниц, матрица ссылок, hreflang.

Спецификация: docs/superpowers/specs/2026-11-13-stage2-structure-design.md.
Запуск из корня репозитория: python3 tools/research/validate_structure.py
"""
import sys

from structure_map import ROOT, STAGE1, STAGE2, check_map, read_csv


def main() -> int:
    errs: list[str] = []
    skipped: list[str] = []
    _, cards = read_csv(STAGE1 / "cards.csv")
    maps = {}
    for lang in ("en", "es"):
        _, maps[lang] = read_csv(STAGE1 / f"page-map-{lang}.csv")
        errs += [f"page-map-{lang}: {e}" for e in check_map(maps[lang], lang, cards)]
        skipped.append(str((STAGE2 / f"links-{lang}.csv").relative_to(ROOT)))
    skipped.append(str((STAGE2 / "hreflang.csv").relative_to(ROOT)))
    for s in skipped:
        print(f"пропущено, файла нет: {s}")
    for e in errs:
        print(e)
    print("OK" if not errs else f"ошибок: {len(errs)}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Запустить тесты**

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `26 passed` (15 + 11). Запуск `validate_structure.py` на настоящих картах — в Task 3: до неё в картах нет колонок структуры.

- [ ] **Step 7: Commit**

```bash
cd ~/arcana-diary && git add tools/research/structure_map.py tools/research/fixtures_structure.py tools/research/test_structure_map.py tools/research/validate_structure.py && git commit -m "tools(stage2): structure checks for page maps — URL rules, structural home, breadcrumbs, sections

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Имена карт ES и колонки структуры в картах (v1.3)

Спецификация: раздел 1 целиком (испанские названия карт, карты адресов EN/ES, V1.1, V2/V3) и раздел 5 «Колонки карты».

**Files:**
- Create: `tools/research/rename_es_cards.py`
- Create: `tools/research/build_structure.py`
- Modify: `tools/research/validate_page_map.py` (строки проверки заголовка в `validate`)
- Modify: `tools/research/test_validate_page_map.py` (последний тест)
- Modify (скриптами): `docs/research/stage1/cards.csv`, `page-map-en.csv`, `page-map-es.csv`

**Interfaces:**
- Consumes: `COLUMNS_EN`, `COLUMNS_ES`, `STRUCTURE_COLUMNS` из `validate_page_map` (Task 1); `check_map` через `validate_structure.py` (Task 2).
- Produces: карты v1.3 с колонками `url`, `entity_id`, `parent_id`, `breadcrumb`, `menu_item`, `host_id`, `pages`; `cards.csv` с `slug_es` `el-papa` и `caballero-de-{bastos,copas,espadas,oros}`. Значения `entity_id` (`page:home`, `tool:yes-no`, `card:<card_id>`, `card-yes-no:{card_id}` …) — ключи пар hreflang в Task 5.

- [ ] **Step 1: Переименовать пять испанских карт**

Создать `tools/research/rename_es_cards.py`:

```python
"""Одноразово: испанские имена карт по правилу «одна система имён на колоду» (спецификация этапа 2, раздел 1)."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE1 = ROOT / "docs/research/stage1"
# card_id: (новое name_es, новый slug_es)
RENAME = {
    "major-05-hierophant": ("El Papa", "el-papa"),
    "wands-12-knight": ("Caballero de Bastos", "caballero-de-bastos"),
    "cups-12-knight": ("Caballero de Copas", "caballero-de-copas"),
    "swords-12-knight": ("Caballero de Espadas", "caballero-de-espadas"),
    "pentacles-12-knight": ("Caballero de Oros", "caballero-de-oros"),
}
# id строки page-map-es.csv: card_id
MAP_ROWS = {"ES-018": "major-05-hierophant", "ES-046": "wands-12-knight", "ES-060": "cups-12-knight",
            "ES-074": "swords-12-knight", "ES-088": "pentacles-12-knight"}


def rewrite(path: Path, fn) -> None:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        rows = list(reader)
    for r in rows:
        fn(r)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def fix_card(r: dict) -> None:
    if r["card_id"] not in RENAME:
        return
    new_name, new_slug = RENAME[r["card_id"]]
    if r["name_es"] == new_name:
        return
    old = r["name_es"]
    variants = [v for v in r["es_variants"].split("|") if v and v != new_name]
    r["es_variants"] = "|".join([old] + variants)
    r["name_es"], r["slug_es"] = new_name, new_slug


def fix_title(r: dict) -> None:
    cid = MAP_ROWS.get(r["id"])
    if not cid:
        return
    new_name = RENAME[cid][0]
    old_name, sep, rest = r["working_title"].partition(" — ")
    if old_name.startswith(new_name):
        return
    suffix = old_name[len(old_name.split(" (")[0]):]  # « (V)» у старших арканов
    r["working_title"] = new_name + suffix + sep + rest


if __name__ == "__main__":
    rewrite(STAGE1 / "cards.csv", fix_card)
    rewrite(STAGE1 / "page-map-es.csv", fix_title)
    print("OK: 5 карт переименованы")
```

Run: `cd ~/arcana-diary && python3 tools/research/rename_es_cards.py && python3 tools/research/rename_es_cards.py && grep -E "hierophant|knight" docs/research/stage1/cards.csv`
Expected: дважды `OK: 5 карт переименованы` (второй запуск ничего не меняет), затем строки:

```
major-05-hierophant,major,,5,The Hierophant,the-hierophant,El Papa,el-papa,El Hierofante|El Sumo Sacerdote
wands-12-knight,minor,wands,12,Knight of Wands,knight-of-wands,Caballero de Bastos,caballero-de-bastos,Caballo de Bastos
cups-12-knight,minor,cups,12,Knight of Cups,knight-of-cups,Caballero de Copas,caballero-de-copas,Caballo de Copas
swords-12-knight,minor,swords,12,Knight of Swords,knight-of-swords,Caballero de Espadas,caballero-de-espadas,Caballo de Espadas
pentacles-12-knight,minor,pentacles,12,Knight of Pentacles,knight-of-pentacles,Caballero de Oros,caballero-de-oros,Caballo de Oros|Caballo de Pentáculos|Caballero de Pentáculos
```

Run: `git diff --stat`
Expected: изменены только `cards.csv` (5 строк) и `page-map-es.csv` (5 строк: ES-018, ES-046, ES-060, ES-074, ES-088 — колонка `working_title`).

- [ ] **Step 2: Создать `build_structure.py`**

Таблица `NONCARD` — карта адресов спецификации, раздел 1, построчно; строки карт (EN-015…092, ES-013…090) считаются из `cards.csv`. Скрипт падает, если в карте есть строка без структуры или лишняя, и если строка карты не совпадает с `cards.csv` по имени.

```python
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
```

- [ ] **Step 3: Записать колонки и проверить, что изменилось только нужное**

Run: `cd ~/arcana-diary && python3 tools/research/build_structure.py && python3 tools/research/build_structure.py && git diff --stat`
Expected: дважды `OK: колонки структуры записаны …`; изменены `page-map-en.csv`, `page-map-es.csv` (124 и 107 строк + заголовок).

Проверка, что колонки этапа 1 не тронуты (кроме пяти названий из Step 1):

```bash
cd ~/arcana-diary && python3 - <<'EOF'
import csv, subprocess, io
for lang in ("en", "es"):
    old = list(csv.DictReader(io.StringIO(subprocess.run(
        ["git", "show", f"HEAD:docs/research/stage1/page-map-{lang}.csv"], capture_output=True, text=True).stdout)))
    new = list(csv.DictReader(open(f"docs/research/stage1/page-map-{lang}.csv")))
    diff = [(a["id"], k) for a, b in zip(old, new) for k in a if a[k] != b[k]]
    print(lang, len(old), len(new), diff)
EOF
```

Expected: `en 124 124 []` и `es 107 107 [('ES-018', 'working_title'), ('ES-046', 'working_title'), ('ES-060', 'working_title'), ('ES-074', 'working_title'), ('ES-088', 'working_title')]`.

- [ ] **Step 4: Снять приём заголовка v1.2 — тест**

В `tools/research/test_validate_page_map.py` заменить тест `test_v12_header_accepted_until_maps_get_structure` на:

```python
def test_v12_header_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row()], cols=COLUMNS_EN_V12), "en")
    assert any("колонки" in e for e in errs)
```

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q test_validate_page_map.py`
Expected: `1 failed` (`test_v12_header_rejected`).

- [ ] **Step 5: Снять приём заголовка v1.2 — код**

В `validate` файла `tools/research/validate_page_map.py` заменить

```python
    expected = COLUMNS_EN if lang == "en" else COLUMNS_ES
    legacy = COLUMNS_EN_V12 if lang == "en" else COLUMNS_ES_V12
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header not in (expected, legacy):
            return [f"колонки не совпадают: ожидалось {expected}, получено {header}"]
        rows = list(reader)
    if header == legacy:
        expected = legacy
```

на

```python
    expected = COLUMNS_EN if lang == "en" else COLUMNS_ES
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header != expected:
            return [f"колонки не совпадают: ожидалось {expected}, получено {header}"]
        rows = list(reader)
```

- [ ] **Step 6: Все проверки**

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `26 passed`.

Run: `cd ~/arcana-diary && python3 tools/research/validate_page_map.py docs/research/stage1/page-map-en.csv en && python3 tools/research/validate_page_map.py docs/research/stage1/page-map-es.csv es && python3 tools/research/validate_structure.py`
Expected: `OK`, `OK`, три строки `пропущено, файла нет: …` (матрицы и пары — Task 4 и 5), `OK`.

Выборочно глазами: `grep -E "^(EN-033|EN-060|EN-097|ES-099|ES-092)," docs/research/stage1/page-map-*.csv` и последние семь полей этих строк совпадают с картами адресов спецификации (раздел 1): EN-033 `/cards/the-moon`, дом EN-093, крошки `EN-014>EN-093>EN-033`; EN-060 `/cards/ten-of-cups`, дом EN-014, крошки `EN-014>EN-060`; EN-097 `/cards/{slug_en}/yes-or-no`, `@same-card`, 78; ES-099 `/es/tiradas/3-cartas`, дом ES-001, крошки `ES-099`; ES-092 `/es/cartas/{slug_es}#invertida`, хозяин `@cards`.

- [ ] **Step 7: Commit**

```bash
cd ~/arcana-diary && git add tools/research/rename_es_cards.py tools/research/build_structure.py tools/research/validate_page_map.py tools/research/test_validate_page_map.py docs/research/stage1/cards.csv docs/research/stage1/page-map-en.csv docs/research/stage1/page-map-es.csv && git commit -m "research(stage2): page maps v1.3 with URL, home, breadcrumbs, menu; ES card names by deck rule

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Матрица ссылок

Спецификация: раздел 2 («Правило ссылки», «Матрица ссылок запуска», «Запреты») и раздел 5 «Колонки матрицы ссылок».

**Files:**
- Create: `tools/research/structure_links.py`
- Create: `tools/research/test_structure_links.py`
- Modify: `tools/research/validate_structure.py` (целиком)
- Create: `docs/research/stage2/links-en.csv`, `docs/research/stage2/links-es.csv`

**Interfaces:**
- Consumes: `ALL_CARDS`, `SAME_CARD`, `WAVE_ORDER`, `read_csv`, `check_map` (`structure_map`, Task 2); `en_map()` (`fixtures_structure`).
- Produces: `LINK_COLUMNS = ["link_id", "from_id", "to_id", "link_type", "moment", "anchor_pattern", "context_terms", "wave", "note"]`; `LINK_TYPES = {"подробность", "метод", "действие", "навигация", "сохранение"}`; `check_links(header: list[str], links: list[dict], rows: list[dict], lang: str) -> list[str]`.
- Правила: `link_id` уникален и начинается с `L-EN-` / `L-ES-`; `from_id` — строка карты с адресом или `@cards`; `to_id` — строка с адресом или токен `@cards`, `@drawn`, `@same-card`, `@neighbors`, `@diary`; ссылки на строки без адреса (отклонённые) — ошибка; `moment` и `anchor_pattern` не пусты; волна ссылки не раньше волн обеих сторон; на запуске есть все пять типов связи.

- [ ] **Step 1: Тесты `test_structure_links.py`**

```python
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
```

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q test_structure_links.py`
Expected: `ModuleNotFoundError: No module named 'structure_links'`.

- [ ] **Step 2: Создать `structure_links.py`**

```python
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
```

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `32 passed`.

- [ ] **Step 3: Подключить ссылки к общему запуску — заменить `validate_structure.py` целиком**

```python
"""Этап 2: проверка структуры — карты страниц, матрица ссылок, hreflang.

Спецификация: docs/superpowers/specs/2026-11-13-stage2-structure-design.md.
Запуск из корня репозитория: python3 tools/research/validate_structure.py
"""
import sys

from structure_links import check_links
from structure_map import ROOT, STAGE1, STAGE2, check_map, read_csv


def main() -> int:
    errs: list[str] = []
    skipped: list[str] = []
    _, cards = read_csv(STAGE1 / "cards.csv")
    maps = {}
    for lang in ("en", "es"):
        _, maps[lang] = read_csv(STAGE1 / f"page-map-{lang}.csv")
        errs += [f"page-map-{lang}: {e}" for e in check_map(maps[lang], lang, cards)]
        links_path = STAGE2 / f"links-{lang}.csv"
        if links_path.exists():
            header, links = read_csv(links_path)
            errs += check_links(header, links, maps[lang], lang)
        else:
            skipped.append(str(links_path.relative_to(ROOT)))
    skipped.append(str((STAGE2 / "hreflang.csv").relative_to(ROOT)))
    for s in skipped:
        print(f"пропущено, файла нет: {s}")
    for e in errs:
        print(e)
    print("OK" if not errs else f"ошибок: {len(errs)}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Записать матрицы**

`docs/research/stage2/links-en.csv` (связи V1.1 — по списку «С V1.1 добавляются» спецификации; L-EN-03 заменяется L-EN-22 в день выхода раздела «In love»):

```csv
link_id,from_id,to_id,link_type,moment,anchor_pattern,context_terms,wave,note
L-EN-01,EN-001,@drawn,подробность,Что эта карта значит вообще?,{card_name} — full meaning,{card_name}|meaning|upright,запуск,после ответа чтения под каждой выпавшей картой
L-EN-02,EN-005,@drawn,подробность,Что эта карта значит вообще?,{card_name} — full meaning,{card_name}|meaning|upright,запуск,после ответа
L-EN-03,EN-011,@drawn,подробность,А в любви подробнее?,{card_name} — full meaning,{card_name}|love|meaning,запуск,с V1.1 заменяется связью L-EN-22
L-EN-04,EN-007,EN-009,метод,Почему ответ такой?,How we read yes and no,yes or no|card|answer,запуск,инструмент ссылается на свой метод (8.6)
L-EN-05,EN-009,@cards,подробность,Что эта карта значит целиком?,{card_name},{card_name}|yes or no|meaning,запуск,строка справочника — имя карты
L-EN-06,EN-009,EN-007,действие,Хочу спросить своё,Ask your question,yes or no|question|tarot,запуск,
L-EN-07,@cards,EN-001,действие,Хочу вытянуть сам,Draw a card for your question,{card_name}|reading|question,запуск,кнопка после значения
L-EN-08,@cards,@neighbors,навигация,Листать колоду,{card_name},{card_name}|tarot card,запуск,предыдущая и следующая по порядку колоды
L-EN-09,@cards,EN-093,навигация,Какие ещё старшие арканы?,Major Arcana,major arcana|{card_name},запуск,только 22 старших аркана
L-EN-10,@cards,EN-014,навигация,Какие ещё карты этой масти?,{suit_name},{suit_name}|minor arcana,запуск,младшие арканы — блок масти на хабе (#wands и т. д.)
L-EN-11,EN-014,@cards,навигация,Найти карту,{card_name},{card_name}|meaning,запуск,
L-EN-12,EN-014,EN-093,навигация,Что такое старшие арканы?,Major Arcana,major arcana|22 cards,запуск,
L-EN-13,EN-093,@cards,навигация,Найти старший аркан,{card_name},{card_name}|major arcana,запуск,только 22 старших аркана
L-EN-14,EN-093,EN-014,навигация,А все 78 карт?,All 78 cards,tarot cards|meanings,запуск,
L-EN-15,EN-006,@drawn,подробность,Что значит карта дня подробнее?,Today's card: {card_name},{card_name}|card of the day|meaning,запуск,
L-EN-16,EN-006,@diary,сохранение,Сохранить карту дня,Save to diary,diary|card of the day,запуск,служебная страница за входом
L-EN-17,EN-001,EN-005,навигация,Хочу одну карту,One card,one card|reading,запуск,переключатель формата
L-EN-18,EN-001,EN-007,навигация,Хочу ответ да или нет,Yes or No,yes or no|tarot,запуск,
L-EN-19,EN-001,EN-011,навигация,Вопрос о любви,Love reading,love|reading,запуск,
L-EN-20,EN-001,EN-006,навигация,Что на сегодня?,Card of the Day,card of the day,запуск,
L-EN-21,EN-001,EN-014,навигация,Хочу узнать значения карт,Card meanings,tarot cards|meanings,запуск,
L-EN-22,EN-011,EN-096,подробность,А в любви подробнее?,{card_name} in love,{card_name}|love|meaning,V1.1,якорь #love на странице выпавшей карты
L-EN-23,EN-007,EN-097,подробность,Почему эта карта — да или нет?,{card_name}: yes or no,{card_name}|yes or no|answer,V1.1,страница yes-or-no выпавшей карты
L-EN-24,@cards,EN-097,подробность,А в вопросе да/нет?,{card_name} yes or no,{card_name}|yes or no,V1.1,на странице той же карты
L-EN-25,@cards,EN-098,подробность,Что карта говорит о чувствах?,{card_name} as feelings,{card_name}|feelings,V1.1,только если EN-098 прошла проверку подачи OPP-18
L-EN-26,EN-096,EN-011,действие,Хочу любовный расклад,Do a love reading,love|reading|{card_name},V1.1,
L-EN-27,EN-001,EN-100,навигация,Какие бывают расклады?,Tarot spreads,tarot spreads|layout,V1.1,
```

`docs/research/stage2/links-es.csv`:

```csv
link_id,from_id,to_id,link_type,moment,anchor_pattern,context_terms,wave,note
L-ES-01,ES-001,@drawn,подробность,Что эта карта значит вообще?,{card_name} — significado completo,{card_name}|significado|tarot,запуск,после ответа чтения под каждой выпавшей картой
L-ES-02,ES-099,@drawn,подробность,Что эта карта значит вообще?,{card_name} — significado completo,{card_name}|significado|tarot,запуск,
L-ES-03,ES-009,ES-093,подробность,А в любви подробнее?,{card_name} en el amor,{card_name}|amor|significado,запуск,якорь #amor на странице выпавшей карты
L-ES-04,ES-005,ES-094,метод,Почему ответ такой?,Por qué {card_name} dice {verdict},{card_name}|sí o no|respuesta,запуск,метод в ES — строка на странице карты (ES-007)
L-ES-05,@cards,ES-001,действие,Хочу вытянуть сам,Saca una carta para tu pregunta,{card_name}|tirada|pregunta,запуск,кнопка после значения
L-ES-06,ES-093,ES-009,действие,Хочу любовный расклад,Haz una tirada de amor,amor|tirada|{card_name},запуск,
L-ES-07,ES-094,ES-005,действие,Хочу спросить своё,Pregunta sí o no,sí o no|pregunta|tarot,запуск,
L-ES-08,@cards,@neighbors,навигация,Листать колоду,{card_name},{card_name}|carta del tarot,запуск,предыдущая и следующая по порядку колоды
L-ES-09,@cards,ES-091,навигация,Какие ещё старшие арканы?,Arcanos mayores,arcanos mayores|{card_name},запуск,только 22 старших аркана
L-ES-10,@cards,ES-012,навигация,Какие ещё карты этой масти?,{suit_name},{suit_name}|arcanos menores,запуск,младшие арканы — блок масти на хабе
L-ES-11,ES-012,@cards,навигация,Найти карту,{card_name},{card_name}|significado,запуск,
L-ES-12,ES-012,ES-091,навигация,Что такое старшие арканы?,Arcanos mayores,arcanos mayores|22 cartas,запуск,
L-ES-13,ES-091,@cards,навигация,Найти старший аркан,{card_name},{card_name}|arcanos mayores,запуск,только 22 старших аркана
L-ES-14,ES-091,ES-012,навигация,А все 78 карт?,Las 78 cartas,cartas del tarot|significados,запуск,
L-ES-15,ES-004,@drawn,подробность,Что значит карта дня подробнее?,Carta de hoy: {card_name},{card_name}|carta del día|significado,запуск,
L-ES-16,ES-004,@diary,сохранение,Сохранить карту дня,Guardar en el diario,diario|carta del día,запуск,служебная страница за входом
L-ES-17,ES-001,ES-005,навигация,Хочу ответ да или нет,Sí o no,sí o no|tarot,запуск,
L-ES-18,ES-001,ES-009,навигация,Вопрос о любви,Tarot del amor,amor|tirada,запуск,
L-ES-19,ES-001,ES-004,навигация,Что на сегодня?,Carta del día,carta del día,запуск,
L-ES-20,ES-001,ES-099,навигация,Хочу расклад на три карты,Tirada de 3 cartas,3 cartas|tirada,запуск,
L-ES-21,ES-001,ES-012,навигация,Хочу узнать значения карт,Significados de las cartas,cartas del tarot|significados,запуск,
L-ES-22,ES-001,ES-097,навигация,Какие бывают расклады?,Tiradas de tarot,tiradas|tarot,V1.1,
```

- [ ] **Step 5: Проверить**

Run: `cd ~/arcana-diary && python3 tools/research/validate_structure.py`
Expected: `пропущено, файла нет: docs/research/stage2/hreflang.csv`, затем `OK`.

Сверка с таблицей «Матрица ссылок запуска» спецификации: каждая строка таблицы имеет хотя бы одну связь в `links-en.csv` или `links-es.csv` (в EN раздел «в любви» — V1.1, поэтому результат `/love` на запуске ведёт на начало страницы карты, L-EN-03). Записать в отчёт задачи, какой строке таблицы соответствует каждая связь.

- [ ] **Step 6: Commit**

```bash
cd ~/arcana-diary && git add tools/research/structure_links.py tools/research/test_structure_links.py tools/research/validate_structure.py docs/research/stage2/links-en.csv docs/research/stage2/links-es.csv && git commit -m "research(stage2): internal link matrix EN/ES with reasons, anchors and waves; link checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Таблица языковых пар hreflang

Спецификация: раздел 3 целиком.

**Files:**
- Create: `tools/research/structure_hreflang.py`
- Create: `tools/research/test_structure_hreflang.py`
- Create: `tools/research/build_hreflang.py`
- Modify: `tools/research/validate_structure.py` (целиком)
- Create (скриптом): `docs/research/stage2/hreflang.csv`

**Interfaces:**
- Consumes: `WAVE_ORDER`, `is_page`, `url_errors`, `STAGE1`, `STAGE2` (`structure_map`); `check_links` (Task 4); карты v1.3 и `cards.csv` (Task 3); `CARDS`, `en_map()`, `es_map()` (`fixtures_structure`).
- Produces: `HREFLANG_COLUMNS = ["entity_id", "template", "lang", "page_id", "url", "wave", "status", "in_hreflang", "switch_to"]`; `LAUNCH_CLUSTERS = 84`; `check_hreflang(header, hl, maps, cards, launch_clusters=LAUNCH_CLUSTERS) -> list[str]`.
- Правила: строка на каждую страницу запуска и V1.1 с `entity_id` (шаблоны ×78 развёрнуты по `cards.csv`); `page_id` — страница карты того же языка; `wave` и `template` (= `page_type`) как в карте; адрес развёрнут и по правилам; пара `(entity_id, lang)` уникальна; `in_hreflang=yes` только при опубликованной паре; `switch_to` — адрес из таблицы другого языка не позже по волне, а при паре не позже по волне — адрес пары; пар запуска ровно 84.

- [ ] **Step 1: Тесты `test_structure_hreflang.py`**

```python
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
```

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q test_structure_hreflang.py`
Expected: `ModuleNotFoundError: No module named 'structure_hreflang'`.

- [ ] **Step 2: Создать `structure_hreflang.py`**

```python
"""Этап 2: проверка таблицы языковых пар hreflang.csv (спецификация, раздел 3)."""
from structure_map import WAVE_ORDER, is_page, url_errors

HREFLANG_COLUMNS = ["entity_id", "template", "lang", "page_id", "url", "wave", "status", "in_hreflang",
                    "switch_to"]
LAUNCH_CLUSTERS = 84


def check_hreflang(header: list[str], hl: list[dict], maps: dict[str, list[dict]], cards: list[dict],
                   launch_clusters: int = LAUNCH_CLUSTERS) -> list[str]:
    if header != HREFLANG_COLUMNS:
        return [f"hreflang: колонки {header}, ожидалось {HREFLANG_COLUMNS}"]
    errs: list[str] = []
    by_id = {lang: {r["id"]: r for r in rows} for lang, rows in maps.items()}
    by_entity: dict[tuple[str, str], dict] = {}
    urls = {"en": {}, "es": {}}
    per_page: dict[str, int] = {}
    for h in hl:
        lang, pid, ent = h["lang"], h["page_id"], h["entity_id"]
        if lang not in by_id:
            errs.append(f"{ent}: неизвестный lang {lang}")
            continue
        row = by_id[lang].get(pid)
        if not row or not is_page(row):
            errs.append(f"{ent}: page_id {pid} не страница карты {lang}")
            continue
        if (ent, lang) in by_entity:
            errs.append(f"{ent}: две строки на язык {lang}")
        by_entity[(ent, lang)] = h
        per_page[pid] = per_page.get(pid, 0) + 1
        errs += [f"{ent}: {e}" for e in url_errors(h["url"], lang)]
        if "{" in h["url"] or "#" in h["url"]:
            errs.append(f"{ent}: адрес не развёрнут: {h['url']}")
        if h["wave"] != row["wave"]:
            errs.append(f"{ent}: wave {h['wave']} не как в карте ({row['wave']})")
        if h["template"] != row["page_type"]:
            errs.append(f"{ent}: template {h['template']} не как page_type карты")
        if h["status"] not in ("planned", "published"):
            errs.append(f"{ent}: неизвестный status {h['status']}")
        if h["in_hreflang"] not in ("yes", "no"):
            errs.append(f"{ent}: in_hreflang должно быть yes или no")
        urls[lang][h["url"]] = h
    for (ent, lang), h in by_entity.items():
        other = "es" if lang == "en" else "en"
        pair = by_entity.get((ent, other))
        w = WAVE_ORDER[h["wave"]]
        if h["in_hreflang"] == "yes":
            if h["status"] != "published" or not pair or pair["status"] != "published":
                errs.append(f"{ent} ({lang}): в hreflang без опубликованной пары")
        target = urls[other].get(h["switch_to"])
        if not target:
            errs.append(f"{ent} ({lang}): switch_to {h['switch_to'] or '—'} не адрес из таблицы {other}")
        elif WAVE_ORDER[target["wave"]] > w:
            errs.append(f"{ent} ({lang}): switch_to ведёт на страницу более поздней волны")
        if pair and WAVE_ORDER[pair["wave"]] <= w and h["switch_to"] != pair["url"]:
            errs.append(f"{ent} ({lang}): switch_to должен вести на пару {pair['url']}")
    for lang, rows in maps.items():
        for r in rows:
            if is_page(r) and r["entity_id"] and WAVE_ORDER[r["wave"]] <= 1:
                need = len(cards) if "{" in r["url"] else 1
                if per_page.get(r["id"], 0) != need:
                    errs.append(f"{r['id']}: в hreflang {per_page.get(r['id'], 0)} строк, нужно {need}")
    launch = {e for (e, l), h in by_entity.items() if l == "en" and h["wave"] == "запуск"
              and by_entity.get((e, "es"), {}).get("wave") == "запуск"}
    if len(launch) != launch_clusters:
        errs.append(f"кластеров запуска {len(launch)}, ожидалось {launch_clusters}")
    return errs
```

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `38 passed`.

- [ ] **Step 3: Создать `build_hreflang.py`**

`FALLBACK` — переключатель языка для страниц без пары (спецификация, раздел 3 «Переключатель языка»; для страниц V1.1 только в EN — ближайший по смыслу раздел ES).

```python
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
```

- [ ] **Step 4: Подключить пары к общему запуску — заменить `validate_structure.py` целиком**

```python
"""Этап 2: проверка структуры — карты страниц, матрица ссылок, hreflang.

Спецификация: docs/superpowers/specs/2026-11-13-stage2-structure-design.md.
Запуск из корня репозитория: python3 tools/research/validate_structure.py
"""
import sys

from structure_hreflang import check_hreflang
from structure_links import check_links
from structure_map import ROOT, STAGE1, STAGE2, check_map, read_csv


def main() -> int:
    errs: list[str] = []
    skipped: list[str] = []
    _, cards = read_csv(STAGE1 / "cards.csv")
    maps = {}
    for lang in ("en", "es"):
        _, maps[lang] = read_csv(STAGE1 / f"page-map-{lang}.csv")
        errs += [f"page-map-{lang}: {e}" for e in check_map(maps[lang], lang, cards)]
        links_path = STAGE2 / f"links-{lang}.csv"
        if links_path.exists():
            header, links = read_csv(links_path)
            errs += check_links(header, links, maps[lang], lang)
        else:
            skipped.append(str(links_path.relative_to(ROOT)))
    hl_path = STAGE2 / "hreflang.csv"
    if hl_path.exists():
        header, hl = read_csv(hl_path)
        errs += check_hreflang(header, hl, maps, cards)
    else:
        skipped.append(str(hl_path.relative_to(ROOT)))
    for s in skipped:
        print(f"пропущено, файла нет: {s}")
    for e in errs:
        print(e)
    print("OK" if not errs else f"ошибок: {len(errs)}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Собрать таблицу и проверить**

Run: `cd ~/arcana-diary && python3 tools/research/build_hreflang.py && python3 tools/research/validate_structure.py`
Expected: `OK: hreflang.csv — 349 строк`, затем `OK` (строк «пропущено» нет).

Run:

```bash
cd ~/arcana-diary && python3 - <<'EOF'
import csv, collections
rows = list(csv.DictReader(open("docs/research/stage2/hreflang.csv")))
print(collections.Counter((r["lang"], r["wave"]) for r in rows))
ents = collections.defaultdict(dict)
for r in rows:
    ents[r["entity_id"]][r["lang"]] = r["wave"]
pairs = [v for v in ents.values() if len(v) == 2]
print(len(pairs), collections.Counter("V1.1" if "V1.1" in v.values() else "запуск" for v in pairs))
for r in rows:
    if r["page_id"] in ("EN-005", "EN-009", "ES-099") or r["entity_id"] == "card:major-05-hierophant":
        print(r["page_id"], r["url"], "→", r["switch_to"])
EOF
```

Expected:

```
Counter({('en', 'V1.1'): 175, ('en', 'запуск'): 86, ('es', 'запуск'): 85, ('es', 'V1.1'): 3})
88 Counter({'запуск': 84, 'V1.1': 4})
EN-005 /one-card → /es
EN-009 /yes-no/cards → /es/si-o-no
EN-020 /cards/the-hierophant → /es/cartas/el-papa
ES-018 /es/cartas/el-papa → /cards/the-hierophant
ES-099 /es/tiradas/3-cartas → /
```

(порядок строк вывода может отличаться).

- [ ] **Step 6: Commit**

```bash
cd ~/arcana-diary && git add tools/research/structure_hreflang.py tools/research/test_structure_hreflang.py tools/research/build_hreflang.py tools/research/validate_structure.py docs/research/stage2/hreflang.csv && git commit -m "research(stage2): hreflang pair table by entity ID — 84 launch pairs, language switch fallbacks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Документы этапа и итоговая проверка

Спецификация: раздел 5 «Файлы этапа», раздел 2 «Путь пользователя», раздел 6 «Ворота этапа 2».

**Files:**
- Create: `docs/research/stage2/00-structure.md`
- Create: `docs/research/stage2/99-changelog.md`
- Modify: `docs/research/stage1/99-changelog.md` (новая версия в начале)

**Interfaces:**
- Consumes: все файлы Task 1–5. Числа в документах сверяются с выводом команд Step 1, а не переписываются из плана.

- [ ] **Step 1: Собрать числа**

```bash
cd ~/arcana-diary && python3 - <<'EOF'
import csv, collections
for lang in ("en", "es"):
    rows = list(csv.DictReader(open(f"docs/research/stage1/page-map-{lang}.csv")))
    pages = collections.Counter()
    for r in rows:
        if r["decision"] == "самостоятельная страница":
            pages[r["wave"]] += int(r["pages"])
    links = list(csv.DictReader(open(f"docs/research/stage2/links-{lang}.csv")))
    print(lang, dict(pages), "связи", dict(collections.Counter(l["wave"] for l in links)))
hl = list(csv.DictReader(open("docs/research/stage2/hreflang.csv")))
print("hreflang", dict(collections.Counter(r["lang"] for r in hl)))
EOF
```

Expected: `en {'запуск': 86, 'V1.1': 175, 'V2': 2, 'V3': 1} связи {'запуск': 21, 'V1.1': 6}`, `es {'запуск': 85, 'V1.1': 3, 'V3': 1} связи {'запуск': 21, 'V1.1': 1}`, `hreflang {'en': 261, 'es': 88}`. Если числа другие — в документы идут фактические, расхождение с планом записать в отчёт.

- [ ] **Step 2: Создать `docs/research/stage2/00-structure.md`**

```markdown
# Структура сайта: адреса, дом, меню, ссылки, hreflang

Версия 1.0 — 13.11.2026. Решения и основания — спецификация
`docs/superpowers/specs/2026-11-13-stage2-structure-design.md`; здесь — что получилось в файлах и как ими
пользоваться.

## Где что лежит

| Файл | Что в нём |
|---|---|
| `docs/research/stage1/page-map-en.csv`, `page-map-es.csv` (v1.3) | колонки структуры: `url`, `entity_id`, `parent_id`, `breadcrumb`, `menu_item`, `host_id`, `pages` |
| `docs/research/stage1/cards.csv` | испанские имена карт по правилу «одна система имён на колоду» |
| `links-en.csv`, `links-es.csv` | матрица ссылок: откуда, куда, тип, момент вопроса, анкор, волна |
| `hreflang.csv` | языковые пары по `entity_id`, по строке на страницу (шаблоны ×78 развёрнуты) |
| `tools/research/validate_structure.py` | проверка всех трёх видов файлов; `validate_page_map.py` — проверка колонок карты |

Как читать колонки:

- `breadcrumb` — цепочка ID без главной (`EN-014>EN-093>EN-033`); шаблон страницы сам ставит первым звеном
  Home / Inicio и подписи из названий страниц.
- `@cards` — все 78 страниц карт языка; `@same-card` — страница той же карты; `@drawn` — карты, выпавшие в
  результате чтения; `@neighbors` — предыдущая и следующая карта по порядку колоды; `@diary` — дневник
  (служебная страница за входом, не индексируется).
- `{slug_en}`, `{slug_es}`, `{card_id}` в адресе — шаблон, который разворачивается по `cards.csv`.

Проверка: из корня репозитория

```bash
python3 tools/research/validate_page_map.py docs/research/stage1/page-map-en.csv en
python3 tools/research/validate_page_map.py docs/research/stage1/page-map-es.csv es
python3 tools/research/validate_structure.py
```

После правки карты таблица пар пересобирается: `python3 tools/research/build_hreflang.py`.

## Сводка

| | EN | ES |
|---|---|---|
| Страниц запуска | 86 | 85 |
| Страниц V1.1 | 175 (78 «feelings» — при прохождении проверки подачи OPP-18) | 3 |
| Связей в матрице: запуск / V1.1 | 21 / 6 | 21 / 1 |
| Строк в `hreflang.csv` | 261 | 88 |

Языковых пар запуска — 84 (главная, карта дня, да/нет, любовь, хаб, старшие арканы, 78 карт); в V1.1
добавляются 4 (обзор раскладов, кельтский крест, три карты, карта рождения). Без пары: EN `/one-card`,
`/yes-no/cards`; ES `/es/tiradas/3-cartas` до V1.1.

## Меню

| `menu_item` | EN | ES |
|---|---|---|
| `reading` | Reading → `/` | Tirada → `/es` |
| `yes-no` | Yes or No → `/yes-no` | Sí o no → `/es/si-o-no` |
| `love` | Love → `/love` | Amor → `/es/amor` |
| `daily` | Card of the Day → `/daily` | Carta del día → `/es/carta-del-dia` |
| `cards` | Card Meanings → `/cards` | Significados → `/es/cartas` |

`/one-card`, расклады, карта рождения и гороскопы в меню не входят: на них ведут переключатель формата на
главной, подвал и ссылки из инструментов.

## Что меняется в день выхода V1.1

- `ES-099` (`/es/tiradas/3-cartas`): дом — `ES-097` вместо главной, крошки `ES-097>ES-099`; появляется пара
  `spread:three-card`, переключатель языка ведёт на `/spreads/three-card` вместо `/`.
- Результат `/love` ведёт на раздел `#love` страницы карты (`L-EN-22`) вместо начала страницы (`L-EN-03`).
- Включаются связи V1.1 из `links-*.csv` — каждая в день публикации своей цели.
- Наборы `/cards/<slug>/yes-or-no` и `/cards/<slug>/feelings` выходят волнами по 10–20 адресов.

## Путь пользователя: действий до первого расклада

Принцип плана продукта — первый расклад без регистрации за два клика. Счёт ведётся от входа из поиска.

| Вход | Страницы | Действий до расклада |
|---|---|---|
| Инструмент | главная, одна карта, да/нет, любовь, `3 cartas`, `carta del día` (EN и ES) | 1 — вытянуть карты на самой странице |
| Справочная страница | страница карты, старшие арканы, хаб, справочник «да/нет» | 2 — кнопка «Draw a card for your question» / «Saca una carta para tu pregunta», затем вытянуть |

Условия, которые этот счёт предполагает и которые проверяет этап 3 (прототипы и проверка на людях): поле
вопроса необязательное; выбор ситуации на `/love` и `/es/amor` необязательный, со значением по умолчанию;
ни согласия, ни пола, ни регистрации до ответа (антипримеры конкурентов, `30-opportunities.md`, раздел 2а).
```

- [ ] **Step 3: Создать `docs/research/stage2/99-changelog.md`**

```markdown
# Журнал версий и ворота этапа 2: структура, адреса, перелинковка, hreflang

## Версия 1.0 — 13.11.2026

- **Ответственный:** Claude (исполнители-субагенты и ревьюеры на каждую задачу); финальное ревью ветки —
  независимый агент Fable 5.2; структурные решения утверждает владелец.
- **Состояние утверждения:** разделы дизайна 1–4 утверждены владельцем в чате 12–13.11.2026; файлы этапа
  владельцем **ещё не просмотрены**.

### Состав

| Файл | Версия | Что в нём |
|---|---|---|
| `00-structure.md` | 1.0 | Как читать файлы, сводка, меню, изменения в V1.1, путь пользователя |
| `links-en.csv`, `links-es.csv` | 1.0 | Матрица ссылок: 27 и 22 связи |
| `hreflang.csv` | 1.0 | 349 строк, 84 пары запуска, 4 пары V1.1 |
| `../stage1/page-map-en.csv`, `page-map-es.csv` | 1.3 | Колонки структуры |
| `../stage1/cards.csv` | — | Пять испанских имён карт по правилу колоды |
| `tools/research/validate_structure.py`, `structure_*.py` | — | Проверка структуры, ссылок, пар |

### Изменения в файлах этапа 1

- `page-map-en.csv`, `page-map-es.csv` v1.2 → v1.3: добавлены семь колонок структуры; в `page-map-es.csv`
  у пяти строк карт обновлено рабочее название (ES-018 El Papa, ES-046, 060, 074, 088 — Caballero de …).
  Запросы, объёмы и решения не менялись.
- `cards.csv`: El Hierofante → El Papa (`el-papa`); Caballo de <масть> → Caballero de <масть>
  (`caballero-de-…`) у четырёх рыцарей; прежние имена — в `es_variants`. Основание — спрос MX
  2026-11-10 (`corpus/ahrefs/card-context-mx.csv`), правило — спецификация этапа 2, раздел 1.
- Пункты «Передано этапу 2» журнала этапа 1 закрыты: колонки `pages` и `host_id`, пары EN ↔ ES
  (`hreflang.csv`), доработка валидатора (`kd` — число, `data_date` — ISO, язык только en/es, подсказка при
  запуске без аргументов).

## Ворота этапа (спецификация `2026-11-13-stage2-structure-design.md`, раздел 6)

| Ворота | Состояние | Доказательство |
|---|---|---|
| У каждой строки-страницы запуска и V1.1 — адрес, дом, меню; у запуска — крошки | выполнено | `validate_structure.py` — OK |
| Карты v1.3 проходят валидатор | выполнено | `validate_page_map.py` — OK для EN и ES |
| Матрица ссылок запуска покрывает все типы связи | выполнено | `validate_structure.py` проверяет пять типов на запуске в каждом языке |
| 84 кластера hreflang запуска, без висячих пар | выполнено | `validate_structure.py` — OK |
| С каждой страницы запуска до расклада ≤ 2 действий | выполнено в структуре | `00-structure.md`, раздел «Путь пользователя»; условия проверяет этап 3 |
| Финальное ревью ветки — агент Fable 5.2 | ждёт | заполняется после ревью |
| Владелец просмотрел файлы этапа | **не выполнено** | ждёт просмотра владельцем |

## Что осталось непроверенным

- Матрица — план связей. Наличие ссылок в HTML, якоря и фактический текст вокруг ссылок проверяются после
  вёрстки (этапы 5–7) краулером и по тексту (8.6).
- Испанские имена и слаги карт не проверены носителем языка (вопрос владельцу №4 этапа 1).
- Английские анкоры разделов главной и инструментов (`#ai-reader`, `#one-or-three` и т. п.) — рабочие; этап 3
  может переименовать их вместе с блоками.
```

- [ ] **Step 4: Запись в журнал этапа 1**

В `docs/research/stage1/99-changelog.md` сразу после строки `## Версия 1.1 — 12.11.2026` вставить перед ней новый раздел (то есть он становится первым разделом версий):

```markdown
## Версия 1.2 — 13.11.2026 (изменения этапа 2)

- Карты `page-map-en.csv`, `page-map-es.csv` → v1.3: колонки структуры этапа 2; у пяти строк карт ES обновлено
  рабочее название по новым именам карт. `cards.csv`: El Papa и Caballero de <масть> вместо El Hierofante и
  Caballo de <масть>. Запросы, объёмы и решения TGA не изменились. Подробности и основания —
  `docs/research/stage2/99-changelog.md`.
- Пункты раздела «Передано этапу 2» закрыты этапом 2.

```

(раздел вставляется над `## Версия 1.1 — 12.11.2026`, заголовок файла и абзац о форме журнала остаются наверху.)

- [ ] **Step 5: Итоговая проверка**

Run: `cd ~/arcana-diary/tools/research && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `38 passed`.

Run: `cd ~/arcana-diary && python3 tools/research/validate_page_map.py docs/research/stage1/page-map-en.csv en && python3 tools/research/validate_page_map.py docs/research/stage1/page-map-es.csv es && python3 tools/research/validate_structure.py && python3 tools/research/build_hreflang.py && git status --short`
Expected: `OK`, `OK`, `OK`, `OK: hreflang.csv — 349 строк`; `git status` показывает только три файла этого шага (повторная сборка `hreflang.csv` его не меняет).

- [ ] **Step 6: Commit**

```bash
cd ~/arcana-diary && git add docs/research/stage2/00-structure.md docs/research/stage2/99-changelog.md docs/research/stage1/99-changelog.md && git commit -m "docs(stage2): structure guide, changelog and gates; stage 1 changelog notes map v1.3

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## После задач (контролёр)

1. Финальное ревью всей ветки `stage2-structure` от `main` — агент на модели **Fable 5.2** (`model: fable`), по пакету `review-package <merge-base> HEAD`; ревьюер получает спецификацию и файлы, без выводов исполнителя. Найденное Critical/Important — одним фикс-агентом; затем строка «Финальное ревью ветки — агент Fable 5.2» в `docs/research/stage2/99-changelog.md` получает состояние и ссылку на итог.
2. Владелец просматривает файлы этапа; запись — в `99-changelog.md` этапа 2.
3. `docs/stages.md`: состояние этапа 2 — «готово» с датой; слияние в `main` — по выбору владельца (finishing-a-development-branch).
