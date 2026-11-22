"""Stage 4.7: the gender rewrite of a Spanish section (app/reader/rewrite.py), without the database."""
import pytest

from app.reader import rewrite
from app.reader.check import live_terms, load_reader_terms
from app.reader.engine import Failed, Finished
from app.reader.finalize import Final
from app.reader.provider import FakeProvider, ProviderError, ProviderRefusal, ProviderTimeout, StreamResult

TERMS = load_reader_terms()
ES = live_terms(TERMS, "es", "ok")
ORIGINAL = "La carta habla de una pausa. Hoy estás cansada de cargar con todo y está bien bajar el ritmo."
NEUTRAL = "La carta habla de una pausa. Hoy te sientes sin energía para cargar con todo y está bien bajar el ritmo."


def test_a_neutral_rewrite_is_taken_and_the_call_is_short():
    provider = FakeProvider(json_replies=[{"text": NEUTRAL}])
    new, outcome, max_tokens = rewrite.call_rewrite(provider, "es", ORIGINAL, ES)
    assert new == NEUTRAL and isinstance(outcome, Finished) and outcome.result.tokens_in == 60
    [call] = provider.json_calls()
    assert call["system"] == rewrite.REWRITE_SYSTEM and call["schema"] == rewrite.REWRITE_SCHEMA
    assert call["messages"] == [{"role": "user", "content": f"<parrafo>{ORIGINAL}</parrafo>"}]
    assert call["max_tokens"] == max_tokens == rewrite.REWRITE_MIN_TOKENS


def test_max_tokens_is_one_and_a_half_times_the_section_above_the_floor():
    long_text = "palabra " * 300  # 2400 characters ≈ 800 tokens
    assert rewrite.rewrite_max_tokens(long_text) == 1200 + 64
    assert rewrite.rewrite_max_tokens("Hola.") == rewrite.REWRITE_MIN_TOKENS


def test_the_section_is_escaped_inside_its_tag():
    assert rewrite.rewrite_messages("a <b> & c")[0]["content"] == "<parrafo>a &lt;b&gt; &amp; c</parrafo>"


@pytest.mark.parametrize("reply, reason", [
    (ProviderTimeout("APITimeoutError"), "timeout"),
    (ProviderError("APIConnectionError"), "error"),
    (ProviderError("max_tokens: structured output truncated", StreamResult(60, 400, "max_tokens", "m")), "error"),
    (ProviderRefusal(StreamResult(60, 0, "refusal", "m")), "refusal"),
    (RuntimeError("a bug"), "error"),
])
def test_a_failed_call_keeps_the_original(reply, reason):
    new, outcome, _ = rewrite.call_rewrite(FakeProvider(json_replies=[reply]), "es", ORIGINAL, ES)
    assert new is None and isinstance(outcome, Failed) and outcome.reason == reason


def test_a_billed_error_keeps_its_usage_for_the_log():
    cut = StreamResult(60, 400, "max_tokens", "m")
    _, outcome, _ = rewrite.call_rewrite(FakeProvider(json_replies=[ProviderError("cut", cut)]), "es", ORIGINAL, ES)
    assert outcome.result == cut and outcome.after_text is True


@pytest.mark.parametrize("candidate", [
    None, 42, "", "   ", ORIGINAL,
    "La carta habla de una pausa. Hoy estás agotada de cargar con todo y está bien bajar el ritmo.",  # gendered
    "La carta habla de una pausa. Hoy te sientes sin energía, pero volverá pronto y está bien bajar el ritmo.",
    "Bajar el ritmo.",  # far shorter
    NEUTRAL + " " + NEUTRAL,  # far longer
    "[[card 1]] " + NEUTRAL,
    "Sí. La carta habla de una pausa. Hoy te sientes sin energía y está bien bajar el ritmo.",  # a new verdict word
])
def test_a_rewrite_that_fails_a_check_is_not_taken(candidate):
    assert rewrite.accepted(ORIGINAL, candidate, ES, "es") is None


def test_a_reply_without_text_is_not_taken():
    new, outcome, _ = rewrite.call_rewrite(FakeProvider(), "es", ORIGINAL, ES)  # the fake's default JSON
    assert new is None and isinstance(outcome, Finished)


def test_length_has_a_small_slack_for_a_short_headline():
    assert rewrite.accepted("Estás lista para avanzar.", "Tienes lo necesario para avanzar.", ES, "es") == \
        "Tienes lo necesario para avanzar."


def test_the_redirect_list_is_used_when_given():
    strict = live_terms(TERMS, "es", "redirect_person")
    text = "La carta habla de una pausa. Hoy te sientes sin energía y todo va a salir bien con calma."
    assert rewrite.accepted(ORIGINAL, text, ES, "es") == text
    assert rewrite.accepted(ORIGINAL, text, strict, "es") is None


def model_final(sections, event=None, reason=None):
    return Final("model", {"model": sections, "fallback": None}, sections, event, reason)


def test_only_model_text_with_a_hit_is_sent_to_rewrite():
    streamed = {"headline": "Hoy conviene ir con calma.", "card1": ORIGINAL, "step": "Escribe una cosa.",
                "why": "Estás lista: la carta lo dice."}
    # finalize replaced why (our fixed line has no gender anyway, but a section that is ours is never sent)
    final = model_final({**streamed, "why": "Estás cansada de esperar, dice la base."}, "replace", "why")
    asked = []

    def rewrite_all(todo):
        asked.append(dict(todo))
        return {"card1": NEUTRAL}

    out, done = rewrite.rewrite_answer(final, streamed, "es", rewrite_all)
    assert asked == [{"card1": ORIGINAL}] and done == {"card1": NEUTRAL}
    assert out.sections == {**final.sections, "card1": NEUTRAL} and out.answer["model"] == out.sections
    assert (out.event, out.reason, out.shown) == ("replace", "why", "model")  # finalize's reason stays


def test_a_gender_only_change_sends_replace_with_reason_gender():
    streamed = {"headline": "Hoy conviene ir con calma.", "card1": ORIGINAL, "step": "Escribe una cosa."}
    out, done = rewrite.rewrite_answer(model_final(streamed), streamed, "es", lambda todo: {"card1": NEUTRAL})
    assert (out.event, out.reason, done) == ("replace", "gender", {"card1": NEUTRAL})


def test_nothing_changes_without_an_accepted_rewrite_english_or_a_fallback():
    streamed = {"headline": "Hoy conviene ir con calma.", "card1": ORIGINAL, "step": "Escribe una cosa."}
    final = model_final(streamed)
    assert rewrite.rewrite_answer(final, streamed, "es", lambda todo: {}) == (final, {})
    called = []
    assert rewrite.rewrite_answer(final, streamed, "en", lambda todo: called.append(1) or {}) == (final, {})
    fallback = Final("fallback", {"model": streamed, "fallback": {"headline": "x"}}, {"headline": "x"}, "replace",
                     "banned")
    assert rewrite.rewrite_answer(fallback, streamed, "es", lambda todo: called.append(1) or {}) == (fallback, {})
    crisis = Final("crisis", {"model": None, "fallback": None}, None, "crisis", "crisis")
    assert rewrite.rewrite_answer(crisis, streamed, "es", lambda todo: called.append(1) or {}) == (crisis, {})
    assert called == []
