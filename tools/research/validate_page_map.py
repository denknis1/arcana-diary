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
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if header != expected:
            return [f"колонки не совпадают: ожидалось {expected}, получено {header}"]
        rows = list(reader)

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
