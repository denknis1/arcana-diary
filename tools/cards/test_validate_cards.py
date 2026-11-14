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
