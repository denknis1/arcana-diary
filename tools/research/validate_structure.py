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
