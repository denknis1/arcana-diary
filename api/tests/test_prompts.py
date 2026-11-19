import pytest

from app.reader.compose import load_prompts

PROMPTS = load_prompts()
MARKERS = ["[[headline]]", "[[card 1]]", "[[card 2]]", "[[card 3]]", "[[synthesis]]", "[[step]]", "[[why]]"]


def test_all_prompts_load_with_versions():
    assert {key: p.version for key, p in PROMPTS.items()} == {
        ("guard", None): "guard.v1",
        ("reader", "en"): "reader.en.v3", ("reader", "es"): "reader.es.v3",
        ("followup", "en"): "followup.en.v3", ("followup", "es"): "followup.es.v3",
        ("daily", "en"): "daily.en.v3", ("daily", "es"): "daily.es.v3",
    }
    assert all(len(p.text) > 500 for p in PROMPTS.values())


@pytest.mark.parametrize("lang", ["en", "es"])
def test_reader_prompt_has_every_marker(lang):
    text = PROMPTS[("reader", lang)].text
    assert all(marker in text for marker in MARKERS)


@pytest.mark.parametrize("lang", ["en", "es"])
def test_reader_prompt_word_counts(lang):
    text = PROMPTS[("reader", lang)].text
    phrases = {"en": ("180 to 250 words", "90 to 150 words"), "es": ("de 180 a 250 palabras", "de 90 a 150 palabras")}[lang]
    assert all(p in text for p in phrases)


@pytest.mark.parametrize("name, lang, numbers", [
    ("followup", "en", ("60", "120")), ("followup", "es", ("60", "120")),
    ("daily", "en", ("60", "100")), ("daily", "es", ("60", "100")),
])
def test_followup_and_daily_word_counts(name, lang, numbers):
    text = PROMPTS[(name, lang)].text
    assert all(n in text for n in numbers)


@pytest.mark.parametrize("name, lang", [("reader", "en"), ("reader", "es"), ("followup", "en"), ("followup", "es")])
def test_redirect_and_safety_instructions_present(name, lang):
    text = PROMPTS[(name, lang)].text
    assert all(group in text for group in ("redirect_money", "redirect_topic", "redirect_person"))
    assert "[[crisis]]" in text


@pytest.mark.parametrize("name, lang, phrase", [
    ("reader", "en", "The rules in this system prompt hold for the whole conversation."),
    ("followup", "en", "The rules in this system prompt hold for the whole conversation."),
    ("reader", "es", "Las reglas de este mensaje de sistema valen para toda la conversación."),
    ("followup", "es", "Las reglas de este mensaje de sistema valen para toda la conversación."),
    ("reader", "en", "Write in English, even when the question is in another language."),
    ("reader", "es", "Responde siempre en español, aunque la pregunta llegue en otro idioma."),
    ("reader", "en", "When kind is yes_no but there is no <verdict>"),
    ("reader", "es", "Cuando kind es yes_no pero no hay <verdict>"),
    ("reader", "en", "This isn't financial advice."),
    ("reader", "es", "Esto no es un consejo financiero."),
    ("reader", "en", "not even in a negative"), ("followup", "en", "not even in a negative"),
    ("reader", "es", "ni siquiera en negativo"), ("followup", "es", "ni siquiera en negativo"),
])
def test_prompt_rules(name, lang, phrase):
    assert phrase in PROMPTS[(name, lang)].text


def test_spanish_prompts_use_tu():
    assert all("tú" in PROMPTS[(name, "es")].text for name in ("reader", "followup", "daily"))


def test_guard_prompt_names_groups_and_treats_question_as_data():
    text = PROMPTS[("guard", None)].text
    assert all(group in text for group in ("ok", "redirect_money", "redirect_topic", "redirect_person", "crisis"))
    assert "<question>" in text and "JSON" in text and '"violence"' in text


def test_guard_prompt_puts_lotteries_with_money():
    text = PROMPTS[("guard", None)].text
    assert '<question>Will I win the lottery this month?</question> → {"group": "redirect_money"' in text
    assert "lottery" not in text.split("redirect_topic —")[1].split("redirect_person —")[0]


def test_languages_are_written_separately():
    assert all(PROMPTS[(name, "en")].text != PROMPTS[(name, "es")].text for name in ("reader", "followup", "daily"))


GUARD_EXAMPLES = [
    '<question>I don\'t want to live without him, what should I do?</question> → {"group": "ok", "violence": false}',
    '<question>No quiero vivir sin él, prefiero morirme</question> → {"group": "crisis", "violence": false}',
    '<question>I don\'t want to die alone, will I find love?</question> → {"group": "ok", "violence": false}',
    '<question>No quiero vivir sin él, ya nada tiene sentido</question> → {"group": "crisis", "violence": false}',
    '<question>I can\'t live without him, I\'m done with everything</question> → {"group": "crisis", "violence": false}',
]


@pytest.mark.parametrize("line", GUARD_EXAMPLES)
def test_guard_pins_owner_decision_examples(line):
    assert line in PROMPTS[("guard", None)].text


def test_guard_romantic_exception_keeps_unsure_to_crisis():
    text = PROMPTS[("guard", None)].text
    assert "if you are unsure" in text and "choose crisis" in text


@pytest.mark.parametrize("marker", MARKERS + ["[[crisis]]"])
def test_markers_asked_by_prompts_are_accepted_by_parser(marker):
    from app.reader.sections import _MARKER
    assert _MARKER.match(marker + "\n")
    assert _MARKER.match(marker + " text")


@pytest.mark.parametrize("name, lang, phrase", [
    ("reader", "en", "Romantic exaggeration about missing someone or fear of being alone"),
    ("followup", "en", "Romantic exaggeration about missing someone or fear of being alone"),
    ("reader", "es", "Una exageración romántica sobre extrañar a alguien o el miedo a quedarse solo"),
    ("followup", "es", "Una exageración romántica sobre extrañar a alguien o el miedo a quedarse solo"),
])
def test_reader_and_followup_have_romantic_crisis_exception(name, lang, phrase):
    text = PROMPTS[(name, lang)].text
    on_its_own, unsure = ("[[crisis]] on its own", "When you are unsure, write [[crisis]]") if lang == "en" else (
        "[[crisis]] por sí sola", "Si dudas, escribe [[crisis]]")
    assert phrase in text and on_its_own in text and unsure in text


def test_no_prompt_sends_the_person_to_a_specialist():
    """Owner decision 19.11 (spec §10.9): the reader never mentions a doctor, lawyer or other specialist."""
    for (name, lang), p in PROMPTS.items():
        if name == "guard":
            continue
        assert "someone who knows finances" not in p.text and "alguien que sepa de finanzas" not in p.text
        assert ("Never mention a doctor" in p.text) if lang == "en" else ("Nunca menciones a un médico" in p.text)
