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


def test_good_map_passes(tmp_path):
    assert validate(write(tmp_path, "en", [good_row()]), "en") == []


def test_measured_zero_volume_allowed(tmp_path):
    assert validate(write(tmp_path, "en", [good_row(volume_us="0")]), "en") == []


def test_empty_volume_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row(volume_us="")]), "en")
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


def test_v12_header_rejected(tmp_path):
    errs = validate(write(tmp_path, "en", [good_row()], cols=COLUMNS_EN_V12), "en")
    assert any("колонки" in e for e in errs)
