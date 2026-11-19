import pytest

from app.cards import load_cards
from app.config import load_settings
from app.reader.fallback import (REVERSED_WHY, card_line, daily_fallback, fallback_answer, fill_missing,
                                 followup_fallback, why_line)
from helpers import make_reading

BASE = load_cards(load_settings({}).content_dir)
NOTICE = "The reader is unavailable right now."


def one(card_id="major-18-moon", reversed_=False, kind="one", lang="en", verdict=None):
    if kind == "yes_no" and verdict is None:
        verdict = "unclear" if reversed_ else BASE.deck[card_id]["yes_no"]
    return make_reading(kind=kind, lang=lang, verdict=verdict,
                        cards=[{"card_id": card_id, "position": "card", "reversed": reversed_}])


def test_one_card_upright_en():
    m = BASE.meanings["en"]["major-18-moon"]
    assert fallback_answer(BASE, one(), NOTICE) == {"headline": NOTICE, "card1": f"The Moon. {m['upright']}",
                                                    "step": m["advice"]}


def test_three_cards_es_positions_and_reversed():
    sections = fallback_answer(BASE, make_reading(lang="es"), "Aviso.")
    assert sections["card2"] == f"Presente: La Luna, invertida. {BASE.meanings['es']['major-18-moon']['reversed']}"
    assert sections["card1"].startswith("Pasado: El Loco. ")
    assert sections["step"] == BASE.meanings["es"]["cups-02-two"]["advice"]
    assert set(sections) == {"headline", "card1", "card2", "card3", "step"}


@pytest.mark.parametrize("lang, line", [
    ("en", "The card is reversed, so its answer softens: not clear yet."),
    ("es", "La carta salió invertida: su respuesta se suaviza, todavía no está claro."),
])
def test_reversed_why_line_is_fixed(lang, line):
    sections = fallback_answer(BASE, one(reversed_=True, kind="yes_no", lang=lang), NOTICE)
    assert sections["why"] == line == REVERSED_WHY[lang]


def test_yes_no_without_verdict_has_no_why():
    reading = make_reading(kind="yes_no", verdict=None, guard_group="redirect_topic",
                           cards=[{"card_id": "major-18-moon", "position": "card", "reversed": True}])
    assert "why" not in fallback_answer(BASE, reading, NOTICE)
    assert "why" not in fill_missing({"headline": "H."}, BASE, reading)


def test_upright_why_is_base_line():
    reading = one(card_id="major-19-sun", kind="yes_no")
    assert why_line(BASE, reading["cards"][0], "en") == BASE.meanings["en"]["major-19-sun"]["yes_no_why"]


def test_fill_missing_keeps_written_and_fills_the_rest():
    reading = make_reading()
    filled = fill_missing({"headline": "Model headline.", "card1": "Model card one."}, BASE, reading)
    ex = BASE.excerpts(reading["cards"], "en", reading["topic"])
    assert filled["headline"] == "Model headline." and filled["card1"] == "Model card one."
    assert filled["card2"] == card_line(ex[1], "en") and filled["card3"] == card_line(ex[2], "en")
    assert filled["step"] == ex[2]["advice"]
    assert "synthesis" not in filled


def test_fill_missing_leaves_complete_answer_alone():
    full = {"headline": "H.", "card1": "C.", "step": "S.", "why": "W."}
    assert fill_missing(full, BASE, one(kind="yes_no")) == full


def test_followup_and_daily_fallbacks():
    text = followup_fallback(BASE, make_reading())
    assert text.startswith("The Fool: ") and BASE.meanings["en"]["cups-02-two"]["advice"] in text
    [ex] = BASE.excerpts([{"card_id": "major-18-moon", "position": "card", "reversed": True}], "es", None)
    assert daily_fallback(ex) == f"{ex['meaning']} {ex['advice']}"
