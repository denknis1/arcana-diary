"""Проверка базы карт content/cards/ против docs/research/stage1/cards.csv.

Запуск из корня репозитория:
  python3 tools/cards/validate_cards.py              — все файлы базы
  python3 tools/cards/validate_cards.py --lang en    — deck, правило, источники и только meanings.en.json
Код выхода 0 — «OK», 1 — список ошибок.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS_CSV = ROOT / "docs/research/stage1/cards.csv"
CONTENT = ROOT / "content/cards"
BANNED = Path(__file__).resolve().parent / "banned_terms.json"

LANGS = ("en", "es")
SUITS = ("wands", "cups", "swords", "pentacles")
VERDICTS = ("yes", "no", "unclear")
NUMERALS = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV",
            "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI"]
DECK_FIELDS = {"card_id", "arcana", "suit", "number", "numeral", "order", "yes_no", "image", "slug_en", "slug_es"}
MEANING_FIELDS = {"card_id", "name", "keywords", "upright", "reversed", "love", "advice", "yes_no_why", "status"}
TEXT_LIMITS = {"upright": (200, 420), "reversed": (200, 420), "love": (80, 260), "advice": (40, 140),
               "yes_no_why": (40, 140)}
SOURCE_FIELDS = {"card_id", "commons_title", "url", "sha256", "width", "height", "bytes"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_cards_csv(path: Path = CARDS_CSV) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compile_terms(terms: list[str]) -> list[tuple[str, re.Pattern]]:
    """«guarantee*» — основа с любым окончанием; остальное — целое слово или фраза; без учёта регистра."""
    compiled = []
    for term in terms:
        stem = term.endswith("*")
        body = r"\s+".join(re.escape(w) for w in term.rstrip("*").split())
        pattern = r"\b" + body + (r"\w*" if stem else r"\b")
        compiled.append((term, re.compile(pattern, re.IGNORECASE)))
    return compiled


def find_banned(text: str, patterns: list[tuple[str, re.Pattern]]) -> list[str]:
    return [term for term, rx in patterns if rx.search(text)]


def check_deck(deck: list[dict], rows: list[dict]) -> list[str]:
    errors = []
    if len(deck) != 78:
        errors.append(f"deck.json: {len(deck)} записей вместо 78")
    by_csv = {r["card_id"]: r for r in rows}
    if [c.get("card_id") for c in deck] != [r["card_id"] for r in rows]:
        errors.append("deck.json: card_id не совпадают с cards.csv (состав или порядок)")
    orders = sorted(c.get("order") for c in deck if isinstance(c.get("order"), int))
    if orders != list(range(1, 79)):
        errors.append("deck.json: order — не 1–78 без пропусков и повторов")
    for c in deck:
        cid = c.get("card_id")
        if set(c) != DECK_FIELDS:
            errors.append(f"deck.json {cid}: поля {sorted(set(c) ^ DECK_FIELDS)} лишние или отсутствуют")
            continue
        row = by_csv.get(cid)
        if row is None:
            continue
        if c["slug_en"] != row["slug_en"] or c["slug_es"] != row["slug_es"]:
            errors.append(f"deck.json {cid}: слаги не совпадают с cards.csv")
        if c["image"] != row["slug_en"]:
            errors.append(f"deck.json {cid}: image должен быть слагом EN «{row['slug_en']}»")
        if c["yes_no"] not in VERDICTS:
            errors.append(f"deck.json {cid}: yes_no «{c['yes_no']}» не из {VERDICTS}")
        if c["arcana"] != row["arcana"] or c["number"] != int(row["rank"]):
            errors.append(f"deck.json {cid}: arcana/number не совпадают с cards.csv")
        if c["arcana"] == "major":
            if c["suit"] is not None or c["numeral"] != NUMERALS[int(row["rank"])]:
                errors.append(f"deck.json {cid}: у старшего аркана suit — null, numeral — римская цифра")
        elif c["suit"] != row["suit"] or c["suit"] not in SUITS or c["numeral"] is not None:
            errors.append(f"deck.json {cid}: у младшего аркана suit из {SUITS}, numeral — null")
    majors = sum(1 for c in deck if c.get("arcana") == "major")
    if majors != 22:
        errors.append(f"deck.json: старших арканов {majors} вместо 22")
    for suit in SUITS:
        n = sum(1 for c in deck if c.get("suit") == suit)
        if n != 14:
            errors.append(f"deck.json: в масти {suit} {n} карт вместо 14")
    return errors


def check_meanings(meanings: list[dict], lang: str, rows: list[dict],
                   patterns: list[tuple[str, re.Pattern]]) -> list[str]:
    name = f"meanings.{lang}.json"
    errors = []
    if len(meanings) != 78:
        errors.append(f"{name}: {len(meanings)} записей вместо 78")
    if sorted(m.get("card_id") or "" for m in meanings) != sorted(r["card_id"] for r in rows):
        errors.append(f"{name}: card_id не совпадают с cards.csv (пропуски или повторы)")
    by_csv = {r["card_id"]: r for r in rows}
    for m in meanings:
        cid = m.get("card_id")
        if set(m) != MEANING_FIELDS:
            errors.append(f"{name} {cid}: поля {sorted(set(m) ^ MEANING_FIELDS)} лишние или отсутствуют")
            continue
        row = by_csv.get(cid)
        if row is not None and m["name"] != row[f"name_{lang}"]:
            errors.append(f"{name} {cid}: name «{m['name']}» ≠ cards.csv «{row[f'name_{lang}']}»")
        kw = m["keywords"]
        if not (isinstance(kw, list) and 3 <= len(kw) <= 5 and all(isinstance(k, str) and k.strip() for k in kw)):
            errors.append(f"{name} {cid}: keywords — 3–5 непустых строк")
            kw = []
        for field, (lo, hi) in TEXT_LIMITS.items():
            text = m[field]
            if not isinstance(text, str) or not lo <= len(text.strip()) <= hi:
                size = len(text.strip()) if isinstance(text, str) else "не строка"
                errors.append(f"{name} {cid}: {field} — {size} знаков, нужно {lo}–{hi}")
        if m["status"] not in ("draft", "reviewed"):
            errors.append(f"{name} {cid}: status «{m['status']}» не draft/reviewed")
        texts = {f"keywords[{i}]": k for i, k in enumerate(kw)}
        texts.update({f: m[f] for f in TEXT_LIMITS if isinstance(m[f], str)})
        for field, text in texts.items():
            for term in find_banned(text, patterns):
                errors.append(f"{name} {cid}: {field} — запрещённое «{term}»")
    return errors


def check_rules(rules: dict) -> list[str]:
    errors = []
    shift = rules.get("reversed_shift")
    if not (isinstance(shift, dict) and set(shift) == set(VERDICTS) and set(shift.values()) <= set(VERDICTS)):
        errors.append("yes-no-rules.json: reversed_shift — по одному вердикту на yes/no/unclear")
    if rules.get("spread_sizes") != [1, 3] or rules.get("majority") != 2:
        errors.append("yes-no-rules.json: spread_sizes [1, 3] и majority 2")
    if rules.get("fallback") not in VERDICTS:
        errors.append("yes-no-rules.json: fallback не из yes/no/unclear")
    labels = rules.get("labels", {})
    for lang in LANGS:
        lab = labels.get(lang)
        if not (isinstance(lab, dict) and set(lab) == set(VERDICTS) and all(str(v).strip() for v in lab.values())):
            errors.append(f"yes-no-rules.json: labels.{lang} — непустые подписи yes/no/unclear")
    return errors


def check_sources(sources: list[dict], rows: list[dict]) -> list[str]:
    errors = []
    if sorted(s.get("card_id") or "" for s in sources) != sorted(r["card_id"] for r in rows):
        errors.append("sources.json: card_id не совпадают с cards.csv (78 карт без повторов)")
    for s in sources:
        cid = s.get("card_id")
        if set(s) != SOURCE_FIELDS:
            errors.append(f"sources.json {cid}: поля {sorted(set(s) ^ SOURCE_FIELDS)} лишние или отсутствуют")
            continue
        if not re.fullmatch(r"File:RWS1909 - .+\.jpe?g", s["commons_title"]):
            errors.append(f"sources.json {cid}: commons_title «{s['commons_title']}» не из набора RWS1909")
        if not s["url"].startswith("https://upload.wikimedia.org/"):
            errors.append(f"sources.json {cid}: url не с upload.wikimedia.org")
        if not re.fullmatch(r"[0-9a-f]{64}", str(s["sha256"])):
            errors.append(f"sources.json {cid}: sha256 — 64 шестнадцатеричных знака")
        if not all(isinstance(s[k], int) and s[k] > 0 for k in ("width", "height", "bytes")):
            errors.append(f"sources.json {cid}: width, height, bytes — положительные целые")
    return errors


def validate(root: Path = ROOT, langs: tuple[str, ...] = LANGS) -> list[str]:
    content = root / "content/cards"
    rows = load_cards_csv(root / "docs/research/stage1/cards.csv")
    banned = load_json(BANNED)
    checks = [("deck.json", lambda d: check_deck(d, rows)),
              ("yes-no-rules.json", check_rules),
              ("sources.json", lambda d: check_sources(d, rows))]
    checks += [(f"meanings.{lang}.json", lambda d, lang=lang: check_meanings(d, lang, rows, compile_terms(banned[lang])))
               for lang in langs]
    errors = []
    for fname, check in checks:
        path = content / fname
        if not path.exists():
            errors.append(f"нет файла content/cards/{fname}")
            continue
        errors += check(load_json(path))
    return errors


def main(argv: list[str]) -> int:
    langs = LANGS
    if "--lang" in argv:
        langs = (argv[argv.index("--lang") + 1],)
        if langs[0] not in LANGS:
            print(f"--lang: одно из {LANGS}")
            return 2
    errors = validate(langs=langs)
    for e in errors:
        print(e)
    print("OK" if not errors else f"ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
