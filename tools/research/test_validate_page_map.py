import csv
from pathlib import Path

from validate_page_map import COLUMNS_EN, COLUMNS_ES, validate


def write(tmp_path: Path, lang: str, rows: list[dict]) -> str:
    cols = COLUMNS_EN if lang == "en" else COLUMNS_ES
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
    }
    row.update(over)
    return row


def test_good_map_passes(tmp_path):
    assert validate(write(tmp_path, "en", [good_row()]), "en") == []


def test_zero_volume_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(volume_us="0")]), "en")
    assert any("нет данных" in e for e in errs)


def test_duplicate_id_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(), good_row()]), "en")
    assert any("id" in e for e in errs)


def test_unknown_decision_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(decision="сделать")]), "en")
    assert any("decision" in e for e in errs)


def test_volume_without_date_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(data_date="")]), "en")
    assert any("data_date" in e for e in errs)


def test_es_requires_country_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text(",".join(COLUMNS_EN) + "\n")
    errs = validate(str(p), "es")
    assert any("колонк" in e for e in errs)
