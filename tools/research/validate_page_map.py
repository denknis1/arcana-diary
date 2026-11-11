"""Проверка итоговой карты страниц этапа 1 (колонки — спецификация этапа 1)."""
import csv
import sys

COMMON_HEAD = ["id", "page_type", "working_title", "task", "intent_label", "top_entities", "queries"]
COMMON_TAIL = ["kd", "data_date", "decision", "rationale", "priority_value", "priority_readiness",
               "priority_constraints", "maintenance_cost", "dependencies", "open_questions", "wave"]
COLUMNS_EN = COMMON_HEAD + ["volume_us"] + COMMON_TAIL
COLUMNS_ES = COMMON_HEAD + ["volume_mx", "volume_ar", "volume_co", "volume_es", "volume_us_es"] + COMMON_TAIL

PAGE_TYPES = {"home", "one-card", "yes-no", "love", "cards", "card-context", "spreads",
              "birth-card", "horoscope", "quiz", "pairs", "learn"}
DECISIONS = {"доработать", "раздел", "имеющийся ответ", "самостоятельная страница", "отклонить", "получить данные"}
WAVES = {"запуск", "V1.1", "V2", "V3"}
NO_DATA = "нет данных"


def validate(path: str, lang: str) -> list[str]:
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
        if has_volume and not row["data_date"].strip():
            errors.append(f"строка {n}: есть объём, но пустой data_date")
        for c in ("task", "rationale"):
            if not row[c].strip() or row[c] == NO_DATA:
                errors.append(f"строка {n}: пустое {c}")
    return errors


if __name__ == "__main__":
    errs = validate(sys.argv[1], sys.argv[2])
    for e in errs:
        print(e)
    print("OK" if not errs else f"ошибок: {len(errs)}")
    sys.exit(1 if errs else 0)
