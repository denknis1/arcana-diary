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
