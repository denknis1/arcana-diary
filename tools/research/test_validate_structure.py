import shutil

import pytest

import validate_structure
from structure_map import STAGE2

FILES = ["links-en.csv", "links-es.csv", "hreflang.csv"]


def stage2_copy(tmp_path, monkeypatch, missing=None):
    """Копия файлов этапа 2 во временном корне; карты и cards.csv — настоящие."""
    stage2 = tmp_path / "docs/research/stage2"
    stage2.mkdir(parents=True)
    for name in FILES:
        if name != missing:
            shutil.copy(STAGE2 / name, stage2 / name)
    monkeypatch.setattr(validate_structure, "ROOT", tmp_path)
    monkeypatch.setattr(validate_structure, "STAGE2", stage2)


@pytest.mark.parametrize("missing", FILES)
def test_missing_file_is_error(missing, tmp_path, monkeypatch, capsys):
    stage2_copy(tmp_path, monkeypatch, missing)
    code = validate_structure.main()
    out = capsys.readouterr().out
    assert code == 1
    assert f"нет файла: docs/research/stage2/{missing}" in out
    assert "ошибок: 1" in out
    assert "OK" not in out.splitlines()


def test_all_files_present_ok(tmp_path, monkeypatch, capsys):
    stage2_copy(tmp_path, monkeypatch)
    assert validate_structure.main() == 0
    assert capsys.readouterr().out.splitlines()[-1] == "OK"
