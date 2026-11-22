import pytest

from app.cards import load_cards
from app.config import load_settings
from app.reader.fallback import (MAJORITY_WHY, REVERSED_VOTE, REVERSED_WHY, card_line, daily_fallback,
                                 fallback_answer, fill_missing, followup_fallback, reading_why, why_line)
from app.reader.check import banned_in, load_reader_terms, why_ok
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


SUN, STAR, TOWER = "major-19-sun", "major-17-star", "major-16-tower"  # yes, yes, no in the card base


def three_votes(*cards, lang="en", group="ok"):
    drawn = [{"card_id": cid, "position": "card", "reversed": rev} for cid, rev in cards]
    verdict = BASE.verdict(drawn) if group == "ok" else None
    return make_reading(kind="yes_no", lang=lang, verdict=verdict, guard_group=group, cards=drawn)


def test_three_yes_no_cards_from_the_base_give_each_vote_and_its_why():
    reading = three_votes((SUN, False), (STAR, False), (TOWER, True))  # yes, yes, unclear
    sections = fallback_answer(BASE, reading, NOTICE)
    assert set(sections) == {"headline", "card1", "card2", "card3", "step", "why"}
    assert sections["card1"] == f"The Sun: Yes. {BASE.meanings['en'][SUN]['yes_no_why']}"
    assert sections["card3"] == f"The Tower, reversed: Not clear yet. {REVERSED_VOTE['en']}"  # said once
    assert REVERSED_WHY["en"] not in sections["card3"]
    assert sections["why"] == MAJORITY_WHY["en"]["two"]


MOON = "major-18-moon"  # "not clear" in the card base


@pytest.mark.parametrize("cards, lang, key", [
    (((SUN, False), (STAR, False), ("major-21-world", False)), "en", "all"),
    (((SUN, False), (STAR, False), (MOON, False)), "en", "two"),
    (((SUN, False), (STAR, False), (TOWER, False)), "es", "two_of_three"),
    (((TOWER, False), (MOON, False), (STAR, True)), "en", "one"),  # one decisive card: the verdict is no
    (((SUN, False), (TOWER, False), (STAR, True)), "es", "tie"),  # yes, no, unclear: not clear yet
    (((MOON, False), (SUN, True), (TOWER, True)), "en", "forming"),  # no decisive card: not clear yet
])
def test_the_majority_why(cards, lang, key):
    reading = three_votes(*cards, lang=lang)
    assert reading_why(BASE, reading) == MAJORITY_WHY[lang][key]


def test_three_yes_no_cards_without_a_verdict_read_like_three_cards():
    reading = three_votes((SUN, False), (STAR, False), (TOWER, False), group="redirect_topic")
    sections = fallback_answer(BASE, reading, NOTICE)
    first = BASE.excerpts(reading["cards"], "en", reading["topic"])[0]
    assert "why" not in sections and sections["card1"] == card_line(first, "en")


def test_fill_missing_on_three_yes_no_cards():
    reading = three_votes((SUN, False), (STAR, False), (TOWER, False))
    filled = fill_missing({"headline": "H.", "card1": "Model card."}, BASE, reading)
    assert filled["card1"] == "Model card." and filled["card2"].startswith("The Star: Yes. ")
    assert filled["why"] == MAJORITY_WHY["en"]["two_of_three"] and "synthesis" not in filled


def test_every_majority_why_and_reversed_vote_line_passes_the_check_and_has_no_banned_terms():
    """Final review: the why lines sit right under the verdict the site shows; they must never be refused by the
    why check the live answers pass, nor say a verdict or a banned claim (stage 5 rewrites the lines)."""
    terms = load_reader_terms()
    for lang in ("en", "es"):
        lines = [*MAJORITY_WHY[lang].values(), REVERSED_VOTE[lang]]
        assert len(MAJORITY_WHY[lang]) == 6
        for line in lines:
            assert why_ok(line, lang, terms[lang]), (lang, line)
            assert banned_in(line, terms[lang], lang) == [], (lang, line)
