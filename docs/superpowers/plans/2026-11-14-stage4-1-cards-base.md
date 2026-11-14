# Этап 4.1: база карт — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Одна база 78 карт в репозитории — описание колоды, короткие значения EN и ES, правило «да / нет / пока неясно», рисунки «Roses & Lilies» в трёх размерах — с проверкой, которая не пропускает ошибки и запрещённые формулировки.

**Architecture:** Данные — JSON в `content/cards/`, рисунки — WebP в `site/public/cards/`. Скрипты в `tools/cards/` на стандартной библиотеке Python: сборка `deck.json` из `cards.csv`, проверка базы, эталонное правило «да/нет», список и скачивание сканов с Wikimedia Commons, обработка рисунков через ffmpeg. Значения пишут два отдельных исполнителя — английский и испанский независимо.

**Tech Stack:** Python 3.12 (стандартная библиотека) + pytest (`~/arcana-diary/api/.venv/bin/pytest`), ffmpeg с libwebp и librsvg, API Wikimedia Commons.

Спецификация: `docs/superpowers/specs/2026-11-14-stage4-1-cards-base-design.md`. Ветка: `stage4-core`.

## Global Constraints

- Все пути — от корня репозитория `~/arcana-diary`; скрипты запускаются из корня: `python3 tools/cards/<скрипт>.py`.
- Тесты: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q` (как в `tools/research` и `tools/design`; `conftest.py` не нужен).
- Без новых зависимостей: стандартная библиотека Python, ffmpeg. Pillow нет.
- JSON — UTF-8, `ensure_ascii=False`, отступ 2, перевод строки LF в конце файла.
- `card_id`, `slug_en`, `slug_es`, `name_en`, `name_es` — только из `docs/research/stage1/cards.csv`; `cards.csv` не менять.
- `deck.json`: поля `card_id`, `arcana` (`major`/`minor`), `suit` (`wands`, `cups`, `swords`, `pentacles` или `null`), `number` (0–21 у старших, 1–14 у младших), `numeral` (римская цифра у старших, `null` у младших), `order` (1–78), `yes_no` (`yes`, `no`, `unclear`), `image` (слаг EN без расширения), `slug_en`, `slug_es`.
- `meanings.<lang>.json`: `card_id`, `name`, `keywords` (3–5), `upright` (2–3 предложения, 200–420 знаков), `reversed` (2–3 предложения, 200–420), `love` (1–2 предложения, 80–260), `advice` (одна строка-действие, 40–140), `yes_no_why` (одна строка, 40–140), `status` (`draft` / `reviewed`). Все записи этапа 4.1 — `status: "draft"`.
- Без «чувств другого» (запрет З4): никаких «что он чувствует», «что она думает», «lo que siente», «piensa de ti».
- Тон — дизайн-система: спокойно, честно, от второго лица, без запугивания и обещаний; не утверждать фактов о прошлом и будущем — «may point to», «puede indicar».
- Испанский — мексиканский вариант, на «tú», не перевод английского; без родовых форм, обращённых к читателю («segura/seguro», «lista/listo» — переписать нейтрально).
- Правило «да/нет»: перевёрнутая карта сдвигает вердикт к `unclear` (`yes`→`unclear`, `no`→`unclear`, `unclear` остаётся); три карты — большинство, без большинства — `unclear`; подписи EN `Yes` / `No` / `Not clear yet`, ES `Sí` / `No` / `Todavía no está claro`.
- Рисунки: только файлы `File:RWS1909 - …jpeg` категории «Rider-Waite tarot deck (Roses & Lilies)»; скачивание — только после «да» владельца на точный список (имя, размер, байты). Сканы — в `~/arcana-diary-work/scans-1909/`, не в репозитории. Выход — `site/public/cards/<slug_en>.webp` (700 px), `<slug_en>@350.webp`, `<slug_en>@160.webp`, плюс `back.svg`. Цвета классические, без тонирования.
- Сетевые запросы — с нейтральным User-Agent без имени и почты владельца.
- Коммиты — на ветке `stage4-core`, сообщение заканчивается строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Не коммитить `deploy/.env`, `deploy/caddy/stage_auth.caddy`, сканы и контактный лист.

## Файлы

| Файл | Отвечает за |
|---|---|
| `tools/cards/build_deck.py` | сборка `content/cards/deck.json` из `cards.csv` и таблицы вердиктов |
| `tools/cards/validate_cards.py` | проверка всех файлов базы; CLI с `--lang` |
| `tools/cards/banned_terms.json` | словарь запрещённых слов EN/ES |
| `tools/cards/yes_no.py` | эталонная реализация правила «да/нет» по `yes-no-rules.json` |
| `tools/cards/fetch_sources.py` | список сканов с Commons (`--list`) и скачивание с записью `sources.json` (`--download`) |
| `tools/cards/process_cards.py` | обрезка и WebP трёх размеров, контактный лист |
| `tools/cards/test_*.py` | тесты к каждому скрипту |
| `content/cards/deck.json`, `meanings.en.json`, `meanings.es.json`, `yes-no-rules.json`, `sources.json`, `README.md` | база карт |
| `site/public/cards/*.webp`, `back.svg` | рисунки и рубашка |
| `docs/design/tokens.json`, `tokens.css` | `card.artCrop` под «Roses & Lilies» |
| `docs/stages.md` | статус 4.1 |

---

### Task 1: `deck.json` и проверка базы

**Files:**
- Create: `tools/cards/build_deck.py`, `tools/cards/validate_cards.py`, `tools/cards/banned_terms.json`, `tools/cards/test_validate_cards.py`
- Create (генерируется): `content/cards/deck.json`

**Interfaces:**
- Consumes: `docs/research/stage1/cards.csv` (колонки `card_id,arcana,suit,rank,name_en,slug_en,name_es,slug_es,es_variants`).
- Produces:
  - `build_deck.build() -> list[dict]`, `build_deck.ROOT: Path`;
  - `validate_cards.load_json(path) -> Any`, `load_cards_csv(path=CARDS_CSV) -> list[dict]`, `compile_terms(terms: list[str]) -> list[tuple[str, re.Pattern]]`, `find_banned(text: str, patterns) -> list[str]`, `check_deck(deck, rows) -> list[str]`, `check_meanings(meanings, lang, rows, patterns) -> list[str]`, `check_rules(rules: dict) -> list[str]`, `check_sources(sources, rows) -> list[str]`, `validate(root=ROOT, langs=("en","es")) -> list[str]`, `main(argv) -> int`; константы `BANNED`, `TEXT_LIMITS`, `VERDICTS`, `LANGS`.
  - Каждая `check_*` возвращает список строк-ошибок вида `"<файл> <card_id>: <поле> — <что не так>"`; пустой список — всё в порядке.

- [ ] **Step 1: Написать тесты**

Создать `tools/cards/test_validate_cards.py`:

```python
import copy

import pytest

import build_deck
from validate_cards import (BANNED, check_deck, check_meanings, check_sources, compile_terms, find_banned,
                            load_cards_csv, load_json)

ROWS = load_cards_csv()
DECK = build_deck.build()
EN = compile_terms(load_json(BANNED)["en"])
ES = compile_terms(load_json(BANNED)["es"])


def text(n: int) -> str:
    """Нейтральный текст ровно из n знаков."""
    return ("Calm, honest words about a choice. " * 20)[:n].strip().ljust(n, "x")


def meaning(row: dict, lang: str = "en") -> dict:
    return {"card_id": row["card_id"], "name": row[f"name_{lang}"], "keywords": ["one", "two", "three"],
            "upright": text(300), "reversed": text(300), "love": text(150), "advice": text(80),
            "yes_no_why": text(80), "status": "draft"}


def meanings(lang: str = "en") -> list[dict]:
    return [meaning(r, lang) for r in ROWS]


def source(row: dict) -> dict:
    return {"card_id": row["card_id"], "commons_title": "File:RWS1909 - 00 Fool.jpeg",
            "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/RWS1909_-_00_Fool.jpeg",
            "sha256": "a" * 64, "width": 814, "height": 1441, "bytes": 322903}


# --- deck.json ---

def test_built_deck_is_valid():
    assert check_deck(DECK, ROWS) == []


def test_deck_counts():
    assert sum(c["arcana"] == "major" for c in DECK) == 22
    assert all(sum(c["suit"] == s for c in DECK) == 14 for s in ("wands", "cups", "swords", "pentacles"))


def test_deck_moon():
    moon = next(c for c in DECK if c["card_id"] == "major-18-moon")
    assert moon == {"card_id": "major-18-moon", "arcana": "major", "suit": None, "number": 18, "numeral": "XVIII",
                    "order": 19, "yes_no": "unclear", "image": "the-moon", "slug_en": "the-moon",
                    "slug_es": "la-luna"}


def test_deck_missing_card():
    errors = check_deck(DECK[:-1], ROWS)
    assert any("77 записей" in e for e in errors)


def test_deck_bad_verdict():
    deck = copy.deepcopy(DECK)
    deck[0]["yes_no"] = "maybe"
    assert any("major-00-fool: yes_no" in e for e in check_deck(deck, ROWS))


def test_deck_bad_slug():
    deck = copy.deepcopy(DECK)
    deck[5]["slug_es"] = "otro"
    assert any("слаги не совпадают" in e for e in check_deck(deck, ROWS))


def test_deck_order_gap():
    deck = copy.deepcopy(DECK)
    deck[3]["order"] = 99
    assert any("order" in e for e in check_deck(deck, ROWS))


def test_deck_major_with_suit():
    deck = copy.deepcopy(DECK)
    deck[0]["suit"] = "cups"
    assert any("major-00-fool" in e and "старшего" in e for e in check_deck(deck, ROWS))


def test_deck_extra_field():
    deck = copy.deepcopy(DECK)
    deck[0]["color"] = "gold"
    assert any("major-00-fool" in e and "color" in e for e in check_deck(deck, ROWS))


# --- meanings ---

def test_valid_meanings_pass():
    assert check_meanings(meanings(), "en", ROWS, EN) == []


def test_meanings_short_upright():
    m = meanings()
    m[0]["upright"] = text(150)
    assert any("major-00-fool: upright — 150 знаков" in e for e in check_meanings(m, "en", ROWS, EN))


def test_meanings_long_advice():
    m = meanings()
    m[0]["advice"] = text(141)
    assert any("advice — 141 знаков" in e for e in check_meanings(m, "en", ROWS, EN))


@pytest.mark.parametrize("kw", [["a", "b"], ["a"] * 6, ["a", "", "c"]])
def test_meanings_keywords_count(kw):
    m = meanings()
    m[0]["keywords"] = kw
    assert any("keywords" in e for e in check_meanings(m, "en", ROWS, EN))


def test_meanings_wrong_name():
    m = meanings("es")
    m[4]["name"] = "The Pope"
    assert any("name «The Pope»" in e for e in check_meanings(m, "es", ROWS, ES))


def test_meanings_duplicate_card():
    m = meanings()
    m[1] = copy.deepcopy(m[0])
    assert any("пропуски или повторы" in e for e in check_meanings(m, "en", ROWS, EN))


def test_meanings_bad_status():
    m = meanings()
    m[0]["status"] = "final"
    assert any("status" in e for e in check_meanings(m, "en", ROWS, EN))


def test_meanings_banned_phrase_reported_with_card_and_field():
    m = meanings()
    m[18]["love"] = text(100) + " He feels the same way about you."
    errors = check_meanings(m, "en", ROWS, EN)
    assert "meanings.en.json major-18-moon: love — запрещённое «he feels»" in errors


# --- словарь запретов ---

@pytest.mark.parametrize("phrase,term", [
    ("This is guaranteed.", "guarantee*"),
    ("It WILL HAPPEN soon.", "will happen"),
    ("you are destined", "destined"),
    ("she\nthinks of you", "she thinks"),
])
def test_banned_en_hits(phrase, term):
    assert term in find_banned(phrase, EN)


@pytest.mark.parametrize("phrase", [
    "Death is a card of endings and change.",   # название карты — не запрет
    "Judgement asks you to listen.",
    "Diet and courtship are not in scope.",     # «die», «court» только целым словом
    "A courageous step.",
])
def test_banned_en_misses(phrase):
    assert find_banned(phrase, EN) == []


@pytest.mark.parametrize("phrase,term", [
    ("Esto te lo garantizo.", "garantiz*"),
    ("Seguro que vuelve.", "seguro que"),
    ("Una maldición antigua.", "maldici*"),
    ("Sin duda, sí.", "sin duda"),
    ("Pasará pronto.", "pasará"),
])
def test_banned_es_hits(phrase, term):
    assert term in find_banned(phrase, ES)


@pytest.mark.parametrize("phrase", ["La Muerte habla de cierres.", "El Juicio te invita a escuchar.",
                                    "Te sientes en calma con tu decisión."])
def test_banned_es_misses(phrase):
    assert find_banned(phrase, ES) == []


# --- sources.json ---

def test_sources_valid():
    assert check_sources([source(r) for r in ROWS], ROWS) == []


def test_sources_bad_sha():
    s = [source(r) for r in ROWS]
    s[0]["sha256"] = "xyz"
    assert any("sha256" in e for e in check_sources(s, ROWS))


def test_sources_wrong_set():
    s = [source(r) for r in ROWS]
    s[0]["commons_title"] = "File:RWS Tarot 18 Moon.jpg"
    assert any("RWS1909" in e for e in check_sources(s, ROWS))
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q test_validate_cards.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_deck'`.

- [ ] **Step 3: Сборка колоды**

Создать `tools/cards/build_deck.py`:

```python
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
```

- [ ] **Step 4: Словарь запретов**

Создать `tools/cards/banned_terms.json` (спецификация, раздел 1; `*` — любое окончание; названия карт «Death», «La Muerte», «Judgement», «El Juicio» в словарь не входят):

```json
{
  "en": [
    "will happen", "guarantee*", "definitely", "for sure", "destined",
    "illness", "pregnan*", "die", "dying", "lawsuit", "court",
    "he feels", "she feels", "they feel", "he thinks", "she thinks",
    "curse*"
  ],
  "es": [
    "pasará", "garantiz*", "seguro que", "sin duda", "destinad*",
    "enfermedad*", "embaraz*", "morir*", "tribunal*", "demanda judicial",
    "lo que siente", "piensa de ti",
    "maldici*"
  ]
}
```

- [ ] **Step 5: Проверка базы**

Создать `tools/cards/validate_cards.py`:

```python
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
```

- [ ] **Step 6: Тесты зелёные**

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q test_validate_cards.py`
Expected: `38 passed`.

- [ ] **Step 7: Собрать `deck.json` и проверить**

Run: `cd ~/arcana-diary && python3 tools/cards/build_deck.py && python3 -I -c "import json,collections;d=json.load(open('content/cards/deck.json'));print(len(d),collections.Counter(x['yes_no'] for x in d))"`
Expected: `OK: content/cards/deck.json — 78 карт`, затем `78 Counter({'yes': 45, 'unclear': 20, 'no': 13})`.

Запись Луны должна быть ровно такой: `{"card_id": "major-18-moon", "arcana": "major", "suit": null, "number": 18, "numeral": "XVIII", "order": 19, "yes_no": "unclear", "image": "the-moon", "slug_en": "the-moon", "slug_es": "la-luna"}`.

- [ ] **Step 8: Commit**

```bash
cd ~/arcana-diary
git add tools/cards/build_deck.py tools/cards/validate_cards.py tools/cards/banned_terms.json tools/cards/test_validate_cards.py content/cards/deck.json
git commit -m "feat(cards): deck.json from cards.csv and base validator

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: правило «да / нет / пока неясно»

**Files:**
- Create: `content/cards/yes-no-rules.json`, `tools/cards/yes_no.py`, `tools/cards/test_yes_no.py`

**Interfaces:**
- Consumes: `validate_cards.check_rules(rules) -> list[str]` (Task 1); записи `deck.json` с полем `yes_no`.
- Produces: `yes_no.load_rules(path=RULES) -> dict`, `card_verdict(base: str, reversed_: bool, rules: dict) -> str`, `spread_verdict(draws: list[tuple[str, bool]], deck: dict[str, dict], rules: dict) -> str`, `label(verdict: str, lang: str, rules: dict) -> str`. Файл `yes-no-rules.json` — контракт для 4.2 и 4.4: ключи `version`, `reversed_shift`, `spread_sizes`, `majority`, `fallback`, `labels`.

- [ ] **Step 1: Файл правила**

Создать `content/cards/yes-no-rules.json`:

```json
{
  "version": 1,
  "reversed_shift": {"yes": "unclear", "no": "unclear", "unclear": "unclear"},
  "spread_sizes": [1, 3],
  "majority": 2,
  "fallback": "unclear",
  "labels": {
    "en": {"yes": "Yes", "no": "No", "unclear": "Not clear yet"},
    "es": {"yes": "Sí", "no": "No", "unclear": "Todavía no está claro"}
  }
}
```

- [ ] **Step 2: Написать тесты**

Создать `tools/cards/test_yes_no.py`:

```python
import pytest

import copy

from validate_cards import check_rules
from yes_no import card_verdict, label, load_rules, spread_verdict

RULES = load_rules()
DECK = {"sun": {"yes_no": "yes"}, "tower": {"yes_no": "no"}, "moon": {"yes_no": "unclear"},
        "star": {"yes_no": "yes"}, "ten-swords": {"yes_no": "no"}}


@pytest.mark.parametrize("base", ["yes", "no", "unclear"])
def test_upright_keeps_base(base):
    assert card_verdict(base, False, RULES) == base


@pytest.mark.parametrize("base", ["yes", "no", "unclear"])
def test_reversed_moves_to_unclear(base):
    assert card_verdict(base, True, RULES) == "unclear"


def test_unknown_verdict_raises():
    with pytest.raises(ValueError):
        card_verdict("maybe", False, RULES)


def test_one_card():
    assert spread_verdict([("sun", False)], DECK, RULES) == "yes"
    assert spread_verdict([("tower", True)], DECK, RULES) == "unclear"


def test_three_cards_majority_yes():
    assert spread_verdict([("sun", False), ("star", False), ("tower", False)], DECK, RULES) == "yes"


def test_three_cards_majority_no():
    assert spread_verdict([("tower", False), ("ten-swords", False), ("sun", False)], DECK, RULES) == "no"


def test_three_cards_reversed_breaks_majority():
    # sun перевёрнута → unclear; yes, no, unclear — большинства нет
    assert spread_verdict([("sun", True), ("star", False), ("tower", False)], DECK, RULES) == "unclear"


def test_three_cards_majority_unclear():
    assert spread_verdict([("moon", False), ("sun", True), ("star", False)], DECK, RULES) == "unclear"


@pytest.mark.parametrize("n", [0, 2, 4])
def test_other_sizes_raise(n):
    with pytest.raises(ValueError):
        spread_verdict([("sun", False)] * n, DECK, RULES)


def test_labels():
    assert label("unclear", "en", RULES) == "Not clear yet"
    assert label("yes", "es", RULES) == "Sí"
    assert label("unclear", "es", RULES) == "Todavía no está claro"


# --- проверка файла правила ---

def test_rules_file_valid():
    assert check_rules(RULES) == []


def test_rules_missing_label():
    rules = copy.deepcopy(RULES)
    del rules["labels"]["es"]["unclear"]
    assert any("labels.es" in e for e in check_rules(rules))


def test_rules_wrong_majority():
    rules = dict(RULES, majority=1)
    assert any("majority" in e for e in check_rules(rules))
```

- [ ] **Step 3: Запустить — тесты падают**

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q test_yes_no.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'yes_no'`.

- [ ] **Step 4: Реализация**

Создать `tools/cards/yes_no.py`:

```python
"""Вердикт «да / нет / пока неясно» по правилу content/cards/yes-no-rules.json.

Эталонная реализация правила для чтеца (4.2) и интерфейса (4.4); правило задаёт JSON, код его только исполняет.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "content/cards/yes-no-rules.json"
VERDICTS = ("yes", "no", "unclear")


def load_rules(path: Path = RULES) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def card_verdict(base: str, reversed_: bool, rules: dict) -> str:
    """Вердикт одной карты: базовый из deck.json, перевёрнутая сдвигается по reversed_shift."""
    if base not in VERDICTS:
        raise ValueError(f"неизвестный вердикт: {base}")
    return rules["reversed_shift"][base] if reversed_ else base


def spread_verdict(draws: list[tuple[str, bool]], deck: dict[str, dict], rules: dict) -> str:
    """draws — список (card_id, перевёрнута ли); deck — card_id → запись deck.json."""
    if len(draws) not in rules["spread_sizes"]:
        raise ValueError(f"вердикт считается по {rules['spread_sizes']} картам, а не по {len(draws)}")
    verdicts = [card_verdict(deck[cid]["yes_no"], rev, rules) for cid, rev in draws]
    if len(verdicts) == 1:
        return verdicts[0]
    for v in VERDICTS:
        if verdicts.count(v) >= rules["majority"]:
            return v
    return rules["fallback"]


def label(verdict: str, lang: str, rules: dict) -> str:
    return rules["labels"][lang][verdict]
```

- [ ] **Step 5: Тесты зелёные**

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `57 passed`.

- [ ] **Step 6: Commit**

```bash
cd ~/arcana-diary
git add content/cards/yes-no-rules.json tools/cards/yes_no.py tools/cards/test_yes_no.py
git commit -m "feat(cards): yes/no rule file and reference implementation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: сканы «Roses & Lilies» и `sources.json`

**Files:**
- Create: `tools/cards/fetch_sources.py`, `tools/cards/test_fetch_sources.py`
- Create (генерируется после скачивания): `content/cards/sources.json`

**Interfaces:**
- Consumes: `validate_cards.load_cards_csv()`, `check_sources()` (Task 1).
- Produces: `fetch_sources.card_id_for(title: str, rows) -> str | None`, `list_files() -> list[dict]`, `match_cards(files, rows) -> tuple[list[dict], list[str]]`, `download(entries, workdir: Path) -> list[dict]`. Сканы в `~/arcana-diary-work/scans-1909/` с именами как на Commons без `File:` (например, `RWS1909 - 18 Moon.jpeg`); `sources.json` — 78 записей в порядке `cards.csv` с полями `card_id`, `commons_title`, `url`, `sha256`, `width`, `height`, `bytes`.

- [ ] **Step 1: Написать тесты (без сети)**

Создать `tools/cards/test_fetch_sources.py`:

```python
from fetch_sources import card_id_for, match_cards
from validate_cards import load_cards_csv

ROWS = load_cards_csv()


def test_major_titles():
    assert card_id_for("File:RWS1909 - 00 Fool.jpeg", ROWS) == "major-00-fool"
    assert card_id_for("File:RWS1909 - 02 High Priestess.jpeg", ROWS) == "major-02-high-priestess"
    assert card_id_for("File:RWS1909 - 10 Wheel of Fortune.jpeg", ROWS) == "major-10-wheel-of-fortune"


def test_minor_titles():
    assert card_id_for("File:RWS1909 - Cups 14.jpeg", ROWS) == "cups-14-king"
    assert card_id_for("File:RWS1909 - Wands 01.jpeg", ROWS) == "wands-01-ace"


def test_other_files_skipped():
    assert card_id_for("File:Waite–Smith Tarot Roses and Lilies.jpg", ROWS) is None
    assert card_id_for("File:RWS Tarot 18 Moon.jpg", ROWS) is None


def entry(title):
    return {"commons_title": title, "url": "u", "width": 1, "height": 1, "bytes": 1, "sha1": "s"}


def test_match_reports_missing_and_duplicate():
    files = [entry("File:RWS1909 - 00 Fool.jpeg"), entry("File:RWS1909 - 00 Fool.jpg")]
    entries, errors = match_cards(files, ROWS)
    assert len(entries) == 1
    assert any("две картинки для major-00-fool" in e for e in errors)
    assert any("нет файлов для" in e and "cups-14-king" in e for e in errors)
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q test_fetch_sources.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_sources'`.

- [ ] **Step 3: Реализация**

Создать `tools/cards/fetch_sources.py`:

```python
"""Список сканов «Roses & Lilies» (1909) с Wikimedia Commons и их скачивание.

Запуск из корня репозитория:
  python3 tools/cards/fetch_sources.py --list               — таблица 78 файлов: имя, размер, байты (без скачивания)
  python3 tools/cards/fetch_sources.py --download WORKDIR   — скачать в WORKDIR (только после «да» владельца),
                                                              сверить sha1 Commons, записать content/cards/sources.json
"""
import csv
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS_CSV = ROOT / "docs/research/stage1/cards.csv"
SOURCES = ROOT / "content/cards/sources.json"
API = "https://commons.wikimedia.org/w/api.php"
CATEGORY = "Category:Rider-Waite tarot deck (Roses & Lilies)"
USER_AGENT = "cards-fetch/1.0 (python-urllib; one-time download of public-domain scans)"
TITLE_RE = re.compile(r"^File:RWS1909 - (?:(\d{2}) [A-Za-z ]+|(Wands|Cups|Swords|Pentacles) (\d{2}))\.jpe?g$")


def card_id_for(title: str, rows: list[dict]) -> str | None:
    """«File:RWS1909 - 18 Moon.jpeg» → major-18-moon; «… - Cups 14.jpeg» → cups-14-king; иначе None."""
    m = TITLE_RE.match(title)
    if not m:
        return None
    if m.group(1) is not None:
        arcana, suit, rank = "major", "", int(m.group(1))
    else:
        arcana, suit, rank = "minor", m.group(2).lower(), int(m.group(3))
    for r in rows:
        if r["arcana"] == arcana and r["suit"] == suit and int(r["rank"]) == rank:
            return r["card_id"]
    return None


def _get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_files() -> list[dict]:
    """Все файлы категории с url, размерами и sha1 (API Commons, без скачивания картинок)."""
    params = {"action": "query", "format": "json", "generator": "categorymembers", "gcmtitle": CATEGORY,
              "gcmtype": "file", "gcmlimit": "100", "prop": "imageinfo", "iiprop": "url|size|sha1"}
    files = []
    while True:
        data = _get(params)
        for page in data.get("query", {}).get("pages", {}).values():
            info = page["imageinfo"][0]
            files.append({"commons_title": page["title"], "url": info["url"], "width": info["width"],
                          "height": info["height"], "bytes": info["size"], "sha1": info["sha1"]})
        if "continue" not in data:
            return files
        params.update(data["continue"])


def match_cards(files: list[dict], rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Сопоставить файлы картам; вернуть 78 записей в порядке cards.csv и список ошибок."""
    by_card, errors = {}, []
    for f in files:
        cid = card_id_for(f["commons_title"], rows)
        if cid is None:
            continue
        if cid in by_card:
            errors.append(f"две картинки для {cid}: {by_card[cid]['commons_title']} и {f['commons_title']}")
        by_card[cid] = {"card_id": cid, **f}
    missing = [r["card_id"] for r in rows if r["card_id"] not in by_card]
    if missing:
        errors.append(f"нет файлов для: {', '.join(missing)}")
    return [by_card[r["card_id"]] for r in rows if r["card_id"] in by_card], errors


def download(entries: list[dict], workdir: Path) -> list[dict]:
    workdir.mkdir(parents=True, exist_ok=True)
    sources = []
    for e in entries:
        path = workdir / e["commons_title"].removeprefix("File:")
        if not path.exists():
            req = urllib.request.Request(e["url"], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                path.write_bytes(resp.read())
            time.sleep(1)
        data = path.read_bytes()
        if hashlib.sha1(data).hexdigest() != e["sha1"] or len(data) != e["bytes"]:
            raise SystemExit(f"{path.name}: sha1 или размер не совпадают с Commons — файл удалить и скачать заново")
        sources.append({"card_id": e["card_id"], "commons_title": e["commons_title"], "url": e["url"],
                        "sha256": hashlib.sha256(data).hexdigest(), "width": e["width"], "height": e["height"],
                        "bytes": e["bytes"]})
    return sources


def main(argv: list[str]) -> int:
    with open(CARDS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    entries, errors = match_cards(list_files(), rows)
    if errors:
        print("\n".join(errors))
        return 1
    if "--list" in argv:
        for e in entries:
            print(f"{e['card_id']}\t{e['commons_title']}\t{e['width']}×{e['height']}\t{e['bytes']}")
        print(f"всего {len(entries)} файлов, {sum(e['bytes'] for e in entries) / 1e6:.1f} МБ")
        return 0
    if "--download" in argv:
        workdir = Path(argv[argv.index("--download") + 1])
        sources = download(entries, workdir)
        SOURCES.parent.mkdir(parents=True, exist_ok=True)
        SOURCES.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: {len(sources)} файлов в {workdir}, записан {SOURCES.relative_to(ROOT)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Тесты зелёные**

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q test_fetch_sources.py`
Expected: `4 passed`.

- [ ] **Step 5: Список без скачивания**

Run: `cd ~/arcana-diary && python3 tools/cards/fetch_sources.py --list > ~/arcana-diary-work/scans-1909-list.txt; tail -1 ~/arcana-diary-work/scans-1909-list.txt`
Expected: `всего 78 файлов, 22.1 МБ` (на 14.11.2026: размеры от 818 × 1419 до 860 × 1459 px). Два файла категории, не являющиеся картами (`Waite–Smith Tarot Roses and Lilies.jpg` и `…cropped.jpg`), в список не входят.

- [ ] **Step 6: ⛔ Разрешение владельца**

Скачивание — только после «да» владельца на этот список (имена, размеры, байты, источник — upload.wikimedia.org). Если «да» уже дано в чате на тот же список (78 файлов, 22,1 МБ) — шаг выполнен; если список изменился — показать заново.

- [ ] **Step 7: Скачать и записать `sources.json`**

Run: `cd ~/arcana-diary && python3 tools/cards/fetch_sources.py --download ~/arcana-diary-work/scans-1909`
Expected: `OK: 78 файлов в /home/deploy/arcana-diary-work/scans-1909, записан content/cards/sources.json`. Скрипт сверяет sha1 и размер каждого файла с Commons; при несовпадении — остановка с именем файла.

- [ ] **Step 8: Проверка `sources.json`**

Run: `cd ~/arcana-diary && python3 -I -c "import sys;sys.path.insert(0,'tools/cards');import validate_cards as v;print(v.check_sources(v.load_json(v.CONTENT/'sources.json'),v.load_cards_csv()))"`
Expected: `[]`.

- [ ] **Step 9: Commit**

```bash
cd ~/arcana-diary
git add tools/cards/fetch_sources.py tools/cards/test_fetch_sources.py content/cards/sources.json
git commit -m "feat(cards): Roses & Lilies scan list from Commons and sources.json

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: рисунки, обрезка под «Roses & Lilies», рубашка, контактный лист

**Files:**
- Create: `tools/cards/process_cards.py`, `tools/cards/test_process_cards.py`, `site/public/cards/back.svg`
- Create (генерируется): `site/public/cards/*.webp` (78 × 3 = 234 файла)
- Modify: `docs/design/tokens.json` (`card.artCrop`), `docs/design/tokens.css` (генерируется `tools/design/tokens.py`)

**Interfaces:**
- Consumes: `content/cards/sources.json` (Task 3), `content/cards/deck.json` (Task 1), `docs/design/tokens.json` → `card.artCrop` `{top, bottom, sides}` — доли от высоты (top, bottom) и ширины (sides с каждой стороны).
- Produces: `process_cards.out_name(slug, width) -> str`, `art_height(sources, crop, width) -> int`, `crop_filter(width, height, crop, out_w, out_h) -> str`, `check_scan(path, source) -> None`, `process(src_dir, out_dir, sources, deck, crop, only=None) -> list[Path]`, `contact_sheet(out_dir, deck, dst, only=None) -> None`. Все 78 рисунков одного размера внутри ширины (700 × H700, 350 × H350, 160 × H160; H — медиана пропорций обрезанных сканов, чётная) — для атрибутов `width`/`height` в 4.4.

- [ ] **Step 1: Написать тесты**

Создать `tools/cards/test_process_cards.py`:

```python
import hashlib
import shutil
import subprocess

import pytest

from process_cards import art_height, check_scan, contact_sheet, crop_filter, out_name, process

CROP = {"top": 0.1, "bottom": 0.1, "sides": 0.05}
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="нет ffmpeg")


def test_out_names():
    assert out_name("the-moon", 700) == "the-moon.webp"
    assert out_name("the-moon", 350) == "the-moon@350.webp"
    assert out_name("the-moon", 160) == "the-moon@160.webp"


def test_crop_filter_numbers():
    assert crop_filter(1000, 2000, CROP, 700, 1400) == (
        "crop=900:1600:50:200,scale=700:1400:force_original_aspect_ratio=increase:flags=lanczos,crop=700:1400")


def test_art_height_median_even():
    sources = [{"width": 1000, "height": 2000}, {"width": 1000, "height": 2100}, {"width": 1000, "height": 1900}]
    # медиана: 2000 × 0.8 / 900 = 1.777… → 700 × 1.777 = 1244.4 → 1244
    assert art_height(sources, CROP, 700) == 1244
    assert art_height(sources, CROP, 160) % 2 == 0


def test_check_scan_rejects_wrong_hash(tmp_path):
    scan = tmp_path / "a.jpeg"
    scan.write_bytes(b"not the scan")
    with pytest.raises(SystemExit):
        check_scan(scan, {"sha256": "0" * 64})


def make_scan(path, w, h):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c=white:s={w}x{h},drawbox=x=40:y=140:w={w - 80}:h={h - 280}:color=navy:t=fill",
                    "-frames:v", "1", str(path)], check=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def webp_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return tuple(int(v) for v in out.stdout.strip().split(","))


@needs_ffmpeg
def test_process_writes_three_sizes_and_sheet(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    sources, deck = [], []
    for i, (w, h) in enumerate([(820, 1430), (850, 1450)]):
        title = f"File:RWS1909 - 0{i} Test.jpeg"
        sha = make_scan(src / title.removeprefix("File:"), w, h)
        sources.append({"card_id": f"c{i}", "commons_title": title, "sha256": sha, "width": w, "height": h})
        deck.append({"card_id": f"c{i}", "image": f"card-{i}", "order": i + 1})
    out = tmp_path / "out"
    written = process(src, out, sources, deck, CROP)
    assert len(written) == 6
    h700 = art_height(sources, CROP, 700)
    assert webp_size(out / "card-0.webp") == (700, h700)
    assert webp_size(out / "card-1.webp") == (700, h700)      # разные сканы — один размер
    assert webp_size(out / "card-1@160.webp") == (160, art_height(sources, CROP, 160))
    sheet = tmp_path / "sheet.jpg"
    contact_sheet(out, deck, sheet)
    assert sheet.stat().st_size > 0
```

- [ ] **Step 2: Запустить — тесты падают**

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q test_process_cards.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'process_cards'`.

- [ ] **Step 3: Реализация**

Создать `tools/cards/process_cards.py`:

```python
"""Рисунки колоды: сканы «Roses & Lilies» → WebP 700/350/160 px в site/public/cards/ и контактный лист.

Запуск из корня репозитория:
  python3 tools/cards/process_cards.py SRC_DIR                                — все 78 карт в site/public/cards/
  python3 tools/cards/process_cards.py SRC_DIR --only ID,ID --out WORKDIR     — проба обрезки на нескольких картах
  python3 tools/cards/process_cards.py SRC_DIR --sheet WORKDIR/contact-sheet.jpg  — плюс контактный лист
SRC_DIR — папка со сканами из fetch_sources.py; доли обрезки — card.artCrop в docs/design/tokens.json.
"""
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content/cards"
TOKENS = ROOT / "docs/design/tokens.json"
OUT = ROOT / "site/public/cards"
WIDTHS = (700, 350, 160)
QUALITY = 80
SHEET_COLUMNS = 13


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def out_name(slug: str, width: int) -> str:
    return f"{slug}.webp" if width == WIDTHS[0] else f"{slug}@{width}.webp"


def art_height(sources: list[dict], crop: dict, width: int) -> int:
    """Высота выхода при ширине width: медианная пропорция обрезанных сканов, округлено до чётного."""
    ratios = [s["height"] * (1 - crop["top"] - crop["bottom"]) / (s["width"] * (1 - 2 * crop["sides"]))
              for s in sources]
    return 2 * round(width * statistics.median(ratios) / 2)


def crop_filter(width: int, height: int, crop: dict, out_w: int, out_h: int) -> str:
    """Фильтр ffmpeg: срезать поля по долям, вписать с заполнением в out_w × out_h, лишнее срезать по центру."""
    x, y = round(width * crop["sides"]), round(height * crop["top"])
    cw = width - 2 * x
    ch = height - y - round(height * crop["bottom"])
    return (f"crop={cw}:{ch}:{x}:{y},scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={out_w}:{out_h}")


def check_scan(path: Path, source: dict) -> None:
    if not path.exists():
        raise SystemExit(f"нет скана {path}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
        raise SystemExit(f"{path.name}: sha256 не совпадает с sources.json")


def run_ffmpeg(src: Path, vf: str, dst: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vf", vf,
                    "-c:v", "libwebp", "-quality", str(QUALITY), "-compression_level", "6", str(dst)], check=True)


def process(src_dir: Path, out_dir: Path, sources: list[dict], deck: list[dict], crop: dict,
            only: set[str] | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id = {c["card_id"]: c for c in deck}
    heights = {w: art_height(sources, crop, w) for w in WIDTHS}
    written = []
    for s in sources:
        if only and s["card_id"] not in only:
            continue
        src = src_dir / s["commons_title"].removeprefix("File:")
        check_scan(src, s)
        for w in WIDTHS:
            dst = out_dir / out_name(by_id[s["card_id"]]["image"], w)
            run_ffmpeg(src, crop_filter(s["width"], s["height"], crop, w, heights[w]), dst)
            written.append(dst)
    return written


def contact_sheet(out_dir: Path, deck: list[dict], dst: Path, only: set[str] | None = None) -> None:
    """Все миниатюры 160 px сеткой по 13 в ряд, в порядке колоды, с серым зазором — видно края и обрезку."""
    cards = [c for c in sorted(deck, key=lambda c: c["order"]) if not only or c["card_id"] in only]
    rows = -(-len(cards) // SHEET_COLUMNS)
    with tempfile.TemporaryDirectory() as tmp:
        for i, c in enumerate(cards):
            shutil.copy(out_dir / out_name(c["image"], 160), Path(tmp) / f"{i:03d}.webp")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f"{tmp}/%03d.webp",
                        "-vf", f"pad=iw+8:ih+8:4:4:color=gray,tile={SHEET_COLUMNS}x{rows}",
                        "-frames:v", "1", "-q:v", "3", str(dst)], check=True)


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args or args[0].startswith("--"):
        print(__doc__)
        return 2
    src_dir = Path(args[0])
    out_dir = Path(args[args.index("--out") + 1]) if "--out" in args else OUT
    only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    sources = load_json(CONTENT / "sources.json")
    deck = load_json(CONTENT / "deck.json")
    crop = load_json(TOKENS)["card"]["artCrop"]
    written = process(src_dir, out_dir, sources, deck, crop, only)
    print(f"OK: {len(written)} файлов в {out_dir}")
    if "--sheet" in args:
        sheet = Path(args[args.index("--sheet") + 1])
        contact_sheet(out_dir, deck, sheet, only)
        print(f"контактный лист: {sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Тесты зелёные**

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q test_process_cards.py`
Expected: `5 passed`.

- [ ] **Step 5: Рубашка**

Создать `site/public/cards/back.svg` (рубашка из дизайн-системы, компонент TarotCard → Back, в масштабе 700 × 1200):

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 1200" width="700" height="1200" role="img" aria-label="Card back">
  <rect x="3" y="3" width="694" height="1194" rx="64" fill="#10163A" stroke="#C9A45C" stroke-width="6"/>
  <rect x="38" y="38" width="624" height="1124" rx="40" fill="none" stroke="#C9A45C" stroke-opacity="0.55" stroke-width="6"/>
  <g transform="translate(180 430) scale(5.3125)" fill="none" stroke="#C9A45C">
    <circle cx="32" cy="32" r="27" stroke-width="0.8" stroke-dasharray="1.5 3"/>
    <circle cx="32" cy="32" r="21" stroke-width="0.8"/>
    <path d="M37 18a14 14 0 1 0 0 28A11 11 0 1 1 37 18Z" stroke-width="1.4"/>
    <path d="M32 2v6M32 56v6M2 32h6M56 32h6" stroke-width="0.8"/>
    <g fill="#C9A45C" stroke="none">
      <circle cx="41" cy="24" r="1.1"/>
      <circle cx="44" cy="32" r="0.8"/>
      <circle cx="41" cy="40" r="0.8"/>
    </g>
  </g>
</svg>
```

Проверка: `cd ~/arcana-diary && ffmpeg -hide_banner -loglevel error -y -i site/public/cards/back.svg -vf scale=350:-1 ~/arcana-diary-work/back-check.png` — открыть PNG: тёмно-синяя карта, золотая рамка и внутренняя рамка, по центру полумесяц в двух кольцах с четырьмя засечками.

- [ ] **Step 6: Калибровка обрезки на шести картах**

Пробный прогон с текущими долями (`top 0.088, bottom 0.132, sides 0.025` — откалиброваны на серии «RWS Tarot»):

Run:
```bash
cd ~/arcana-diary && python3 tools/cards/process_cards.py ~/arcana-diary-work/scans-1909 \
  --only major-00-fool,major-12-hanged-man,major-18-moon,wands-01-ace,cups-14-king,pentacles-10-ten \
  --out ~/arcana-diary-work/crop-try --sheet ~/arcana-diary-work/crop-try/sheet.jpg
```

Открыть `~/arcana-diary-work/crop-try/sheet.jpg` и по одному `…/the-moon.webp` (Read показывает картинку). Цель: сверху не видно напечатанного номера и верхней рамки, снизу — подписи и нижней рамки, по бокам — белых полей; сам рисунок срезан минимально. Если остаток виден — увеличить соответствующую долю шагом 0,005; если срезан рисунок — уменьшить. Править прямо в `docs/design/tokens.json` → `card.artCrop`, повторять прогон, пока все шесть не чистые. Все шесть `card_id` есть в `cards.csv`.

- [ ] **Step 7: Токены**

Run: `cd ~/arcana-diary && python3 tools/design/tokens.py && python3 tools/design/tokens.py --check && (cd tools/design && ~/arcana-diary/api/.venv/bin/pytest -q)`
Expected: `tokens.css` перегенерирован; `--check` — OK; `8 passed`.

- [ ] **Step 8: Все 78 карт и контактный лист**

Run: `cd ~/arcana-diary && python3 tools/cards/process_cards.py ~/arcana-diary-work/scans-1909 --sheet ~/arcana-diary-work/contact-sheet.jpg && ls site/public/cards/*.webp | wc -l && du -sh site/public/cards`
Expected: `OK: 234 файлов в …/site/public/cards`; `234`; объём около 8 МБ (если больше 12 МБ — снизить `QUALITY` до 75 и сообщить в отчёте).

- [ ] **Step 9: Просмотр контактного листа**

Открыть `~/arcana-diary-work/contact-sheet.jpg` (13 × 6, порядок колоды). Проверить каждую карту: остатки номера или подписи, белые края, перекос, срезанный рисунок. Карты с браком перечислить в отчёте; если брак у нескольких — вернуться к шагу 6; если у одной-двух из-за особенностей скана — записать в отчёт, не подгонять общие доли под исключение. Контролёр (не исполнитель) затем показывает лист владельцу.

- [ ] **Step 10: Commit**

```bash
cd ~/arcana-diary
git add tools/cards/process_cards.py tools/cards/test_process_cards.py site/public/cards docs/design/tokens.json docs/design/tokens.css
git commit -m "feat(cards): Roses & Lilies art in three WebP sizes, card back, artCrop recalibrated

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: значения на английском

**Files:**
- Create: `content/cards/meanings.en.json`

**Interfaces:**
- Consumes: `cards.csv` (`card_id`, `name_en`), `deck.json` (`yes_no` — вердикт, который объясняет `yes_no_why`), `validate_cards.py --lang en`.
- Produces: 78 записей в порядке `cards.csv` с полями из Global Constraints, `status: "draft"`.

Образец — запись Луны (проходит проверку; длины 261 / 253 / 138 / 72 / 76):

```json
{
  "card_id": "major-18-moon",
  "name": "The Moon",
  "keywords": [
    "uncertainty",
    "intuition",
    "dreams",
    "hidden feelings"
  ],
  "upright": "The Moon points to a stretch where things are not fully visible yet. Feelings, hints and half-formed fears can blur together, so move slowly and check what is real before you act. Your intuition is useful here: let it shape your questions, not your conclusions.",
  "reversed": "Reversed, The Moon may suggest that confusion is starting to lift, or that something you avoided looking at is coming into view. It can also point to worry running ahead of the facts. Name what you actually know, and let the rest wait for clearer light.",
  "love": "In love, The Moon asks for patience with mixed signals. Notice what you feel, ask openly instead of guessing, and give trust time to grow.",
  "advice": "Wait for clearer light: write down what you know and what you only fear.",
  "yes_no_why": "The Moon is about what cannot be seen yet, so the answer stays open for now.",
  "status": "draft"
}
```

- [ ] **Step 1: Старшие арканы (22)**

Написать записи `major-00-fool` … `major-21-world` в `content/cards/meanings.en.json` (JSON-массив). Правила письма:
- `name` — ровно `name_en` из `cards.csv`;
- `keywords` — 3–5 коротких слов или пар слов, строчными;
- `upright`, `reversed` — 2–3 предложения: что карта может значить → как это ощущается → что с этим делать; перевёрнутое — не «плохое прямое», а заблокированная, внутренняя или ослабленная сторона;
- `love` — 1–2 предложения о чувствах и выборе самого человека, не партнёра;
- `advice` — одно действие в повелительном наклонении, выполнимое сегодня;
- `yes_no_why` — объясняет именно вердикт из `deck.json` (`yes` — почему скорее да, `no` — почему скорее нет, `unclear` — почему пока открыто);
- нельзя: обещания и сроки («will happen», «definitely»), здоровье, беременность, смерть как событие, суд, чужие мысли и чувства, проклятия; «Death» и «Judgement» — только как названия карт.

Run: `cd ~/arcana-diary && python3 tools/cards/validate_cards.py --lang en`
Expected: только две ошибки о составе (`22 записей вместо 78`, `card_id не совпадают с cards.csv`); ошибок по полям записанных карт нет.

- [ ] **Step 2: Жезлы и кубки (28)**

Дописать `wands-01-ace` … `wands-14-king`, `cups-01-ace` … `cups-14-king` по тем же правилам. Масть задаёт область: жезлы — энергия, начинания, работа; кубки — чувства, близость.

Run: `cd ~/arcana-diary && python3 tools/cards/validate_cards.py --lang en`
Expected: ошибок по полям 50 записанных карт нет.

- [ ] **Step 3: Мечи и пентакли (28)**

Дописать `swords-01-ace` … `swords-14-king`, `pentacles-01-ace` … `pentacles-14-king`. Мечи — мысли, решения, конфликты (без запугивания: 10 мечей, 9 мечей — о тяжёлом, но с опорой); пентакли — деньги, тело как повседневность, дом, работа руками (без советов о здоровье и инвестициях).

Run: `cd ~/arcana-diary && python3 tools/cards/validate_cards.py --lang en`
Expected: `OK`.

- [ ] **Step 4: Самопроверка текста**

Перечитать все 78 записей подряд: нет ли одинаковых начал у соседних карт (не больше двух `upright`, начинающихся одинаково), повторов `advice`, утверждений о прошлом («Something ended»), прямых обещаний. Исправить.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add content/cards/meanings.en.json
git commit -m "content(cards): short EN meanings for 78 cards (draft)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: значения на испанском

**Files:**
- Create: `content/cards/meanings.es.json`

**Interfaces:**
- Consumes: `cards.csv` (`card_id`, `name_es`), `deck.json` (`yes_no`), `validate_cards.py --lang es`. **Не читать `meanings.en.json`** — испанский пишется самостоятельно, не переводом.
- Produces: 78 записей в порядке `cards.csv`, `status: "draft"`.

Образец — запись La Luna (проходит проверку; длины 259 / 242 / 169 / 70 / 77):

```json
{
  "card_id": "major-18-moon",
  "name": "La Luna",
  "keywords": [
    "incertidumbre",
    "intuición",
    "sueños",
    "lo que no se ve"
  ],
  "upright": "La Luna habla de un momento en el que todavía no ves todo con claridad. Las emociones, las señales y los miedos se mezclan, así que avanza despacio y revisa qué es real antes de actuar. Tu intuición te ayuda a hacer mejores preguntas, no a sacar conclusiones.",
  "reversed": "Invertida, La Luna puede indicar que la confusión empieza a disiparse o que algo que evitabas mirar sale a la luz. También puede señalar que la ansiedad va más rápido que los hechos. Separa lo que sabes de lo que temes y dale tiempo al resto.",
  "love": "En el amor, La Luna te pide paciencia con las señales confusas. Escucha lo que sientes, pregunta de frente en lugar de adivinar y deja que la confianza crezca con calma.",
  "advice": "Espera a ver con más claridad: anota lo que sabes y lo que solo temes.",
  "yes_no_why": "La Luna habla de lo que todavía no se ve, así que la respuesta sigue abierta.",
  "status": "draft"
}
```

- [ ] **Step 1: Arcanos mayores (22)**

Написать записи `major-00-fool` … `major-21-world` в `content/cards/meanings.es.json`. Правила — те же, что в задаче 5, плюс:
- `name` — ровно `name_es` из `cards.csv` (например, `El Papa`, `Caballero de Copas`);
- испанский Мексики, обращение на «tú», повелительное «tú» в `advice` («Anota», «Pregunta», «Date tiempo»);
- без родовых форм, обращённых к читателю: не «estás lista/listo», а «es buen momento para…»;
- естественные формулировки, как в мексиканских сайтах о таро, но без их обещаний и запугивания; не калька с английского;
- запрещено: «pasará», «garantiz…», «seguro que», «sin duda», «destinad…», здоровье, беременность, смерть как событие, суд, «lo que siente», «piensa de ti», «maldición»; «La Muerte» и «El Juicio» — только как названия карт.

Run: `cd ~/arcana-diary && python3 tools/cards/validate_cards.py --lang es`
Expected: ошибок по полям 22 записанных карт нет.

- [ ] **Step 2: Bastos y copas (28)**

Дописать `wands-*` и `cups-*`. Run: `python3 tools/cards/validate_cards.py --lang es` — ошибок по полям 50 карт нет.

- [ ] **Step 3: Espadas y oros (28)**

Дописать `swords-*` и `pentacles-*`. Run: `python3 tools/cards/validate_cards.py --lang es` — `OK`.

- [ ] **Step 4: Самопроверка текста**

Перечитать все 78 записей: «tú» везде, нет «usted», нет родовых форм к читателю, нет повторов начал и `advice`, нет утверждений о прошлом. Исправить.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add content/cards/meanings.es.json
git commit -m "content(cards): short ES (Mexico) meanings for 78 cards (draft)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: README, проверка всей базы, статус этапа

**Files:**
- Create: `content/cards/README.md`
- Modify: `tools/cards/test_validate_cards.py` (тест на настоящую базу), `docs/stages.md` (строка этапа 4)

**Interfaces:**
- Consumes: всё из задач 1–6.
- Produces: `validate_cards.py` без аргументов → `OK`; README для этапов 4.2, 4.4, 5, 6.

- [ ] **Step 1: Тест на настоящую базу**

Дописать в конец `tools/cards/test_validate_cards.py`:

```python


# --- настоящая база в репозитории ---

def test_repository_base_is_valid():
    from validate_cards import validate
    assert validate() == []
```

Run: `cd ~/arcana-diary/tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q`
Expected: `67 passed`.

- [ ] **Step 2: README**

Создать `content/cards/README.md`:

```markdown
# База карт Arcana Diary

Единый источник данных о 78 картах для чтеца (этап 4.2), интерфейса (4.4), текстов (этап 5) и страниц карт
(этап 6). Спецификация: `docs/superpowers/specs/2026-11-14-stage4-1-cards-base-design.md`.

## Файлы

| Файл | Что внутри |
|---|---|
| `deck.json` | 78 карт, общие для языков: `card_id`, аркан, масть, номер, римская цифра, порядок, базовый вердикт «да/нет», имя рисунка, слаги EN/ES. Собирается `python3 tools/cards/build_deck.py` из `docs/research/stage1/cards.csv` |
| `meanings.en.json`, `meanings.es.json` | короткие значения: ключевые слова, прямое, перевёрнутое, «в любви», «как совет», строка «почему» к вердикту «да/нет», статус |
| `yes-no-rules.json` | правило вердикта для 1 и 3 карт и подписи EN/ES; эталонная реализация — `tools/cards/yes_no.py` |
| `sources.json` | откуда взяты сканы: файл Commons, адрес, sha256, размеры |

Рисунки: `site/public/cards/<slug_en>.webp` (700 px), `<slug_en>@350.webp`, `<slug_en>@160.webp`, рубашка `back.svg`.

## Рисунки

Колода Райдера–Уэйта, издание «Roses & Lilies» 1909 года (частная коллекция Саскии Янсен), сканы с Wikimedia
Commons, категория «Rider-Waite tarot deck (Roses & Lilies)». Общественное достояние: колода опубликована до
1931 года, художница Памела Колман Смит умерла в 1951 году — в ЕС, США и России срок охраны истёк. Цвета
классические, без тонирования. Обработка воспроизводима:

```bash
python3 tools/cards/fetch_sources.py --list                       # список, без скачивания
python3 tools/cards/fetch_sources.py --download ~/arcana-diary-work/scans-1909
python3 tools/cards/process_cards.py ~/arcana-diary-work/scans-1909 --sheet ~/arcana-diary-work/contact-sheet.jpg
```

Доли обрезки номера, подписи и полей — `card.artCrop` в `docs/design/tokens.json`. Сканы и контактный лист в
репозиторий не входят.

## Тексты

Черновики написаны Claude отдельно на каждом языке; испанский — мексиканский вариант, на «tú», не перевод.
Все записи — `status: "draft"`. Практик на этапе 5 проверяет запись и переводит её в `reviewed`.

Не пишем: обещания точности и предсказания событий, здоровье, беременность, смерть как событие, суд, мысли и
чувства другого человека, запугивание. Словарь запретов — `tools/cards/banned_terms.json` (`*` в конце — любое
окончание); его можно расширять.

## Как вносить правки

1. Ветка и pull request; правка — в `meanings.<lang>.json` (тексты) или в таблице вердиктов
   `tools/cards/build_deck.py` с пересборкой `deck.json` (вердикты).
2. Проверка: `python3 tools/cards/validate_cards.py` → `OK`; тесты:
   `cd tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q`.
3. Длины: `upright`, `reversed` — 200–420 знаков; `love` — 80–260; `advice`, `yes_no_why` — 40–140; ключевых
   слов 3–5. `name`, `card_id` и слаги берутся из `cards.csv` и не меняются здесь.
```

- [ ] **Step 3: Статус этапа**

В `docs/stages.md`, строка этапа 4, колонку статуса `следующий` заменить на `в работе: 4.1 база карт — готово <ДД.ММ.ГГГГ>` (дата коммита).

- [ ] **Step 4: Итоговые проверки**

Run:
```bash
cd ~/arcana-diary
python3 tools/cards/validate_cards.py
python3 tools/design/tokens.py --check
(cd tools/cards && ~/arcana-diary/api/.venv/bin/pytest -q)
(cd tools/design && ~/arcana-diary/api/.venv/bin/pytest -q)
(cd tools/research && ~/arcana-diary/api/.venv/bin/pytest -q)
ls site/public/cards | wc -l
git status --short
```
Expected: `OK`; tokens OK; `67 passed`; `8 passed`; `77 passed`; `235` (234 WebP + `back.svg`); в `git status` только файлы этой задачи, без сканов и `deploy/`.

- [ ] **Step 5: Commit**

```bash
cd ~/arcana-diary
git add content/cards/README.md tools/cards/test_validate_cards.py docs/stages.md
git commit -m "docs(cards): cards base README; stage 4.1 done

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## После задач

- Контролёр показывает владельцу контактный лист (SendUserFile) и по 2–3 значения EN и ES на выбор.
- Финальная проверка ветки — по процессу subagent-driven-development; итоговую проверку подпроекта 4.1 и следующих делает Fable 5.2 (решение владельца).
- Дальше — подпроект 4.2 (расклад и чтец): свой brainstorming, спецификация и план.
