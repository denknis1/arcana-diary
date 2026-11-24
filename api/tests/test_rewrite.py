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
    assert call["messages"] == [{"role": "user",
                                 "content": f"<parrafo>{ORIGINAL}</parrafo>\n<formas>estás cansada</formas>"}]
    assert call["max_tokens"] == max_tokens == rewrite.REWRITE_MIN_TOKENS == 1024
    assert "Si no hay nada que corregir, devuelve el párrafo igual." in rewrite.REWRITE_SYSTEM


def test_max_tokens_is_twice_the_section_plus_room_above_the_floor():
    long_text = "palabra " * 300  # 2400 characters ≈ 800 tokens
    assert rewrite.rewrite_max_tokens(long_text) == 1600 + 512
    assert rewrite.rewrite_max_tokens("Hola.") == rewrite.REWRITE_MIN_TOKENS
    assert rewrite.rewrite_max_tokens("x" * 600) == 1024  # Fable review I3: 600 characters no longer get 400


def test_the_section_is_escaped_inside_its_tag():
    content = rewrite.rewrite_messages("a <b> & c")[0]["content"]
    assert content == "<parrafo>a &lt;b&gt; &amp; c</parrafo>\n<formas></formas>"


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
    text = ("La carta habla de una pausa. Hoy te sientes sin energía para cargar con todo y va a salir bien bajar el "
            "ritmo.")
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


# --- Fable review I1: the verdict wording stays as it was ---

@pytest.mark.parametrize("original, candidate", [
    ("Sí, y estás lista para empezar el curso.", "No, todavía falta para empezar el curso."),
    ("Sí, estás lista para empezar.", "Quizá, hay lo necesario para empezar."),
    ("Sí, estás lista para empezar.", "Tienes lo necesario para empezar ya."),  # verdict dropped
    ("Probablemente no: estás cansada de insistir.", "Sí: te sobra energía para insistir."),
])
def test_a_flipped_hedged_or_dropped_verdict_is_not_taken(original, candidate):
    assert rewrite.accepted(original, candidate, ES, "es") is None


def test_the_same_verdict_wording_is_taken():
    new = "Sí, y tienes lo necesario para empezar el curso."
    assert rewrite.accepted("Sí, y estás lista para empezar el curso.", new, ES, "es") == new


# --- Fable review I2: still the same paragraph ---

EIGHT = ("El Ocho de Espadas habla de sentirte atada por tus propias ideas. Estás cansada de dar vueltas, pero la "
         "salida está más cerca de lo que parece si das un paso pequeño.")
EIGHT_NEUTRAL = ("El Ocho de Espadas habla de sentir que tus propias ideas te atan. Te pesa dar vueltas, pero la "
                 "salida está más cerca de lo que parece si das un paso pequeño.")


def test_a_reworded_paragraph_is_taken():
    assert rewrite.accepted(EIGHT, EIGHT_NEUTRAL, ES, "es") == EIGHT_NEUTRAL


@pytest.mark.parametrize("candidate", [
    # another paragraph, about another card, with a date and a promise the dictionary does not list
    "La Torre anuncia que en marzo recibirás una oferta de trabajo que cambiará tu forma de ver las cosas, y "
    "conviene que la recibas con calma y sin miedo.",
    # translated to English
    "The Eight of Swords speaks of feeling bound by your own ideas. You are tired of going in circles, but the way "
    "out is closer than it seems if you take a small step.",
    f"<parrafo>{EIGHT_NEUTRAL}</parrafo>",
    f"Aquí está el párrafo corregido: {EIGHT_NEUTRAL}",
    "**El Ocho de Espadas** habla de sentir que tus propias ideas te atan. Te pesa dar vueltas, pero la salida "
    "está más cerca de lo que parece si das un paso pequeño.",
    "El Ocho de Espadas habla de sentir que tus propias ideas te atan.\n- Te pesa dar vueltas, pero la salida está "
    "más cerca de lo que parece si das un paso pequeño.",
    EIGHT_NEUTRAL.replace("pequeño", "pequeño &amp; claro"),
    EIGHT_NEUTRAL.replace("un paso pequeño", "3 pasos pequeños"),
])
def test_a_reply_that_is_not_the_same_paragraph_is_not_taken(candidate):
    assert rewrite.accepted(EIGHT, candidate, ES, "es") is None


def test_a_short_headline_may_change_more_words():
    original = "Hoy estás lista para bajar el ritmo."
    assert rewrite.accepted(original, "Hoy tienes lo necesario para bajar el ritmo.", ES, "es") is not None
    assert rewrite.accepted(original, "Mañana conviene pensar en otra cosa distinta.", ES, "es") is None


def test_a_bug_in_the_checks_keeps_the_original(monkeypatch):
    def broken(*args):
        raise ValueError("bug")

    monkeypatch.setattr(rewrite, "rejection", broken)
    new, outcome, _ = rewrite.call_rewrite(FakeProvider(json_replies=[{"text": NEUTRAL}]), "es", ORIGINAL, ES)
    assert new is None and isinstance(outcome, Finished)


# --- the reason a reply was not taken (paid eval 24.11.2026: es-04 and fu-es-07 kept their original, unexplained) ---

ES_04 = ("Juntas, las cartas muestran un corazón que se protege y que empieza a buscar algo más verdadero. "
         "Para abrirte a alguien nuevo, quizá te ayude sentirte acompañado primero.")
FU_ES_07 = ("Entiendo que quieras emocionarte con el partido, pero aquí no puedo decirte si conviene apostar ni cómo. "
            "Lo que sí puedo leer en el Nueve de Bastos es que estás cansada de tanto esfuerzo, o al menos que tu "
            "energía anda corta. Antes de decidir algo con dinero, revisa cuánto tienes disponible de verdad y si te "
            "sientes con claridad. Lo más sensato es esperar un día y ver cómo te sientes entonces. Empieza por "
            "anotar cuánto puedes perder sin que te afecte.")
STRICT = live_terms(TERMS, "es", "redirect_money")


@pytest.mark.parametrize("original, candidate, terms", [
    (ES_04, ES_04.replace("sentirte acompañado primero", "sentir compañía primero"), ES),
    (FU_ES_07, FU_ES_07.replace("estás cansada de tanto esfuerzo", "te sientes sin energía por tanto esfuerzo"),
     STRICT),
])
def test_the_two_texts_kept_in_the_paid_eval_are_taken_when_the_reply_is_neutral(original, candidate, terms):
    assert rewrite.accepted(original, candidate, terms, "es") == candidate


@pytest.mark.parametrize("candidate, reason", [
    (None, "not a string"),
    ("  ", "empty"),
    ("[[synthesis]] " + ORIGINAL, "section markers"),
    (ORIGINAL, "unchanged"),
    ("La carta habla de una pausa. Hoy estás agotada de cargar con todo y está bien bajar el ritmo.",
     "gender still found (1 form)"),
    ("La carta habla de una pausa. Hoy te sientes sin energía, pero volverá pronto y está bien bajar el ritmo.",
     "banned: volverá"),
    ("Sí. La carta habla de una pausa. Hoy te sientes sin energía y está bien bajar el ritmo.",
     "verdict wording changed"),
    ("Bajar el ritmo.", "not the same paragraph: similarity"),
    (NEUTRAL + " Y " + NEUTRAL[:60], "length"),
])
def test_every_rejection_has_a_reason(candidate, reason):
    new, why = rewrite.rejection(ORIGINAL, candidate, ES, "es")
    assert new is None and why.startswith(reason), why


def test_a_synonym_for_a_hedge_changes_the_verdict_wording():
    """«quizá» -> «tal vez» is two different verdict rules: the reason names them, so a paid eval shows this case."""
    candidate = ES_04.replace("quizá", "tal vez").replace("sentirte acompañado", "sentir compañía")
    new, why = rewrite.rejection(ES_04, candidate, ES, "es")
    assert new is None and why.startswith("verdict wording changed") and "quizás" in why and "tal vez" in why


def test_a_rejected_reply_is_logged_with_its_reason_and_no_answer_text(caplog):
    reasons = []
    reply = {"text": ORIGINAL.replace("cansada", "agotada")}
    with caplog.at_level("INFO", logger="arcana.reader"):
        new, _, _ = rewrite.call_rewrite(FakeProvider(json_replies=[reply]), "es", ORIGINAL, ES, reasons.append)
    assert new is None and reasons == ["gender still found (1 form)"]
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "gender rewrite rejected, the original stays: gender still found (1 form)" in logged
    assert "agotada" not in logged and "cargar" not in logged  # the answer's words stay out of the log


def test_an_accepted_reply_does_not_call_on_reject():
    reasons = []
    new, _, _ = rewrite.call_rewrite(FakeProvider(json_replies=[{"text": NEUTRAL}]), "es", ORIGINAL, ES,
                                     reasons.append)
    assert new == NEUTRAL and reasons == []
