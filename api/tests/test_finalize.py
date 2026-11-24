import pytest

from app.cards import load_cards
from app.config import load_settings
from app.reader import fallback
from app.reader.check import load_reader_terms
from app.reader.engine import Failed, Finished
from app.reader.finalize import EMPTY, finalize
from app.reader.provider import StreamResult, canned_answer
from app.reader.sections import SectionParser
from helpers import make_reading

BASE = load_cards(load_settings({}).content_dir)
TERMS = load_reader_terms()
NOTICE = "The reader is unavailable right now."
DONE = Finished(StreamResult(120, 80, "end_turn", "fake-reader"), 10, 50)


def parsed(text: str):
    parser = SectionParser()
    parser.feed(text)
    parser.finish()
    return parser.sections(), parser.seen


def run(reading, text, outcome=DONE):
    streamed, seen = parsed(text)
    return finalize(reading, streamed, seen, outcome, BASE, TERMS, NOTICE)


def yes_no(verdict="yes", group="ok"):
    return make_reading(kind="yes_no", verdict=verdict, guard_group=group,
                        cards=[{"card_id": "major-19-sun", "position": "card", "reversed": False}])


def test_clean_answer_is_shown_as_is():
    final = run(make_reading(), canned_answer(3, False))
    assert (final.shown, final.event, final.reason) == ("model", None, None)
    assert final.answer == {"model": final.sections, "fallback": None}


@pytest.mark.parametrize("outcome, reason", [
    (None, "budget"),
    (Failed("timeout", False, None, 15000), "timeout"),
    (Failed("error", False, None, 30), "error"),
    (Failed("refusal", True, 5, 40, StreamResult(1, 1, "refusal", "m")), "refusal"),
])
def test_no_usable_text_gives_the_base_answer(outcome, reason):
    text = "" if reason != "refusal" else canned_answer(1, False)
    final = run(make_reading(kind="one", cards=[{"card_id": "major-18-moon", "position": "card",
                                                  "reversed": False}]), text, outcome)
    assert (final.shown, final.event, final.reason) == ("fallback", "fallback", reason)
    assert final.sections["headline"] == NOTICE and final.answer["model"] is None


def test_empty_stream_is_empty():
    assert run(make_reading(), "").reason == "empty"


def test_crisis_marker_wins():
    final = run(make_reading(), "[[crisis]]\nPlease talk to someone.\n")
    assert (final.shown, final.event, final.answer, final.sections) == ("crisis", "crisis", EMPTY, None)


def test_cut_drops_the_section_being_written():
    reading = make_reading()
    text = canned_answer(3, False)[:150]  # stops inside card 1
    final = run(reading, text, Failed("error", True, 5, 90))
    ex = BASE.excerpts(reading["cards"], "en", "work")
    assert (final.event, final.reason) == ("replace", "cut")
    assert final.sections["headline"] == "The cards may point to a quiet, steady way forward."
    assert final.sections["card1"] == fallback.card_line(ex[0], "en")


def test_max_tokens_counts_as_cut():
    reading = make_reading()
    text = canned_answer(3, False).rsplit("[[step]]", 1)[0] + "[[step]]\nWrite down one small"
    final = run(reading, text, Finished(StreamResult(1, 4000, "max_tokens", "m"), 5, 900))
    assert final.reason == "cut"
    assert final.sections["step"] == BASE.excerpts(reading["cards"], "en", "work")[2]["advice"]


def test_extra_sections_are_dropped():
    final = run(make_reading(kind="one", cards=[{"card_id": "major-18-moon", "position": "card", "reversed": False}]),
                canned_answer(1, True))  # a why without a verdict
    assert "why" not in final.sections and (final.event, final.reason) == ("replace", "sections")


def test_banned_claim_keeps_both_texts():
    text = canned_answer(3, False).replace("The cards may point to a quiet, steady way forward.", "He feels the same.")
    final = run(make_reading(), text)
    assert (final.shown, final.event, final.reason) == ("fallback", "replace", "banned")
    assert final.answer["model"]["headline"] == "He feels the same." and final.answer["fallback"] == final.sections


def test_bad_why_is_replaced_alone():
    reading = yes_no()
    text = canned_answer(1, True).replace("The card shows open hands and a clear road, a sign of easy movement.",
                                          "Yes, clearly.")
    final = run(reading, text)
    assert (final.shown, final.event, final.reason) == ("model", "replace", "why")
    assert final.sections["why"] == fallback.why_line(BASE, reading["cards"][0], "en")


def test_money_reading_keeps_its_verdict_and_why():
    final = run(yes_no(group="redirect_money"), canned_answer(1, True))
    assert final.shown == "model" and "why" in final.sections


def test_cut_before_why_on_a_reversed_card_stays_cut():
    reading = make_reading(kind="yes_no", verdict="unclear",
                           cards=[{"card_id": "major-19-sun", "position": "card", "reversed": True}])
    text = canned_answer(1, True).split("[[why]]")[0]  # the stream stopped before why
    final = run(reading, text, Failed("error", True, 5, 90))
    assert (final.shown, final.reason) == ("model", "cut")
    assert final.sections["why"] == fallback.REVERSED_WHY["en"]


def test_a_verdict_in_the_headline_without_a_verdict_is_replaced():
    reading = yes_no(verdict=None, group="redirect_topic")
    text = canned_answer(1, False).replace("The cards may point to a quiet, steady way forward.", "Yes, it will.")
    final = run(reading, text)
    assert (final.shown, final.event, final.reason) == ("model", "replace", "headline")
    assert final.sections["headline"] == fallback.headline_line(BASE, reading)


def test_a_bad_why_on_three_yes_no_cards_gets_the_majority_line():
    cards = [{"card_id": cid, "position": "card", "reversed": False}
             for cid in ("major-19-sun", "major-17-star", "major-16-tower")]
    reading = make_reading(kind="yes_no", verdict="yes", cards=cards)
    text = canned_answer(3, True).replace("The card shows open hands and a clear road, a sign of easy movement.",
                                          "Yes, two of them say so.")
    final = run(reading, text)
    assert (final.shown, final.reason) == ("model", "why")
    assert final.sections["why"] == fallback.MAJORITY_WHY["en"]["two_of_three"]
    assert final.sections["card3"] and final.sections["synthesis"]


@pytest.mark.parametrize("group, shown", [("ok", "model"), ("redirect_topic", "fallback"),
                                          ("redirect_person", "fallback"), ("redirect_money", "fallback")])
def test_redirect_phrases_are_banned_only_outside_group_ok(group, shown):
    """Stage 4.6, Fable I5: "will happen" is allowed in group ok (decision 1), still banned without an outcome."""
    text = canned_answer(3, False).replace("The cards may point to a quiet, steady way forward.",
                                           "It will happen when the time is right.")
    final = run(make_reading(guard_group=group), text)
    assert final.shown == shown
    assert final.reason == (None if group == "ok" else "banned")


# --- Fable review of 4.8 (I2, M4): a redirect_person reading with and without a verdict ---

def test_person_one_card_headline_with_a_lean_is_replaced():
    """I2: no verdict, not even in a one-card spread of a question about another person."""
    reading = make_reading(kind="one", verdict=None, guard_group="redirect_person",
                           cards=[{"card_id": "major-19-sun", "position": "card", "reversed": False}])
    text = canned_answer(1, False).replace("The cards may point to a quiet, steady way forward.",
                                           "The card leans toward yes.")
    final = run(reading, text)
    assert (final.shown, final.event, final.reason) == ("model", "replace", "headline")
    assert final.sections["headline"] == fallback.headline_line(BASE, reading)


def test_person_reading_with_a_verdict_keeps_a_lean_in_the_headline():
    reading = yes_no(group="redirect_person")
    text = canned_answer(1, True).replace("The cards may point to a quiet, steady way forward.",
                                          "The card leans toward yes, with care.")
    final = run(reading, text)
    assert final.shown == "model" and final.reason is None
    assert final.sections["headline"] == "The card leans toward yes, with care."


def test_person_reading_with_a_verdict_replaces_a_bad_why_alone():
    reading = yes_no(group="redirect_person")
    text = canned_answer(1, True).replace("The card shows open hands and a clear road, a sign of easy movement.",
                                          "Yes, clearly.")
    final = run(reading, text)
    assert (final.shown, final.event, final.reason) == ("model", "replace", "why")
    assert final.sections["why"] == fallback.reading_why(BASE, reading)
