"""Собирает content/cards/deck.json из docs/research/stage1/cards.csv и таблицы вердиктов «да/нет».

Запуск из корня репозитория: python3 tools/cards/build_deck.py
Вердикты — черновик (status draft в meanings); практик проверяет их на этапе 5.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS_CSV = ROOT / "docs/research/stage1/cards.csv"
DECK = ROOT / "content/cards/deck.json"

NUMERALS = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV",
            "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI"]
SUITS = ["wands", "cups", "swords", "pentacles"]

# Черновик вердиктов: старшие — по справочнику «да/нет» прототипа (экран 10); младшие — по ранговым значениям.
MAJOR_VERDICTS = ["yes", "yes", "unclear", "yes", "yes", "yes", "yes", "yes", "yes", "unclear", "yes", "unclear",
                  "unclear", "no", "yes", "no", "no", "yes", "unclear", "yes", "yes", "yes"]
MINOR_VERDICTS = {
    "wands": ["yes", "yes", "yes", "yes", "unclear", "yes", "unclear", "yes", "unclear", "no",
              "yes", "yes", "yes", "yes"],
    "cups": ["yes", "yes", "yes", "unclear", "no", "yes", "unclear", "no", "yes", "yes",
             "yes", "yes", "yes", "yes"],
    "swords": ["yes", "unclear", "no", "unclear", "no", "unclear", "no", "no", "no", "no",
               "unclear", "unclear", "unclear", "yes"],
    "pentacles": ["yes", "unclear", "yes", "unclear", "no", "yes", "unclear", "yes", "yes", "yes",
                  "yes", "unclear", "yes", "yes"],
}


def build() -> list[dict]:
    with open(CARDS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    deck = []
    for order, r in enumerate(rows, start=1):
        number = int(r["rank"])
        if r["arcana"] == "major":
            suit, numeral, verdict = None, NUMERALS[number], MAJOR_VERDICTS[number]
        else:
            suit, numeral, verdict = r["suit"], None, MINOR_VERDICTS[r["suit"]][number - 1]
        deck.append({
            "card_id": r["card_id"], "arcana": r["arcana"], "suit": suit, "number": number,
            "numeral": numeral, "order": order, "yes_no": verdict, "image": r["slug_en"],
            "slug_en": r["slug_en"], "slug_es": r["slug_es"],
        })
    return deck


if __name__ == "__main__":
    DECK.parent.mkdir(parents=True, exist_ok=True)
    DECK.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {DECK.relative_to(ROOT)} — 78 карт")
