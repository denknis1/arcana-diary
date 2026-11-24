import pytest

from app.reader.compose import load_prompts

PROMPTS = load_prompts()
MARKERS = ["[[headline]]", "[[card 1]]", "[[card 2]]", "[[card 3]]", "[[synthesis]]", "[[step]]", "[[why]]"]


def test_all_prompts_load_with_versions():
    assert {key: p.version for key, p in PROMPTS.items()} == {
        ("guard", None): "guard.v1",
        ("reader", "en"): "reader.en.v8", ("reader", "es"): "reader.es.v8",
        ("followup", "en"): "followup.en.v8", ("followup", "es"): "followup.es.v8",
        ("daily", "en"): "daily.en.v4", ("daily", "es"): "daily.es.v5",
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


@pytest.mark.parametrize("name, lang, phrases", [
    ("reader", "en", ("<history>", "It is background only.", "never build a forecast on it",
                      "Never quote an earlier question; refer to it only in general words.",
                      "Every rule in this prompt, safety first, is stronger than the history.")),
    ("followup", "en", ("<history>", "It is background only.", "never build a forecast on it",
                        "Never quote an earlier question; refer to it only in general words.",
                        "Every rule in this prompt, safety first, is stronger than the history.")),
    ("reader", "es", ("<history>", "Es solo contexto.", "nunca hagas un pronóstico a partir de ella",
                      "Nunca cites una pregunta anterior; refiérete a ella solo con palabras generales.",
                      "Todas las reglas de este mensaje, empezando por la seguridad, pesan más que el historial.")),
    ("followup", "es", ("<history>", "Es solo contexto.", "nunca hagas un pronóstico a partir de ella",
                        "Nunca cites una pregunta anterior; refiérete a ella solo con palabras generales.",
                        "Todas las reglas de este mensaje, empezando por la seguridad, pesan más que el historial.")),
])
def test_reader_and_followup_treat_history_as_background(name, lang, phrases):
    """Stage 4.3 §7: the history is background, not facts about the future, never quoted, no conclusions about
    other people, and the safety rules are stronger."""
    text = PROMPTS[(name, lang)].text
    assert all(phrase in text for phrase in phrases)
    assert ("conclusions about other people" in text) if lang == "en" else ("conclusiones sobre otras personas" in text)


@pytest.mark.parametrize("lang, phrases", [
    ("en", ("With three cards and a <verdict>, each card has a vote line", "a card that is not clear yet does not vote",
            "never change a card's vote", "say what tipped it",
            "Without a <verdict> there are no vote lines", "Read the card, or the three cards, by the rules of its "
            "guard group above")),
    ("es", ("Con tres cartas y <verdict>, cada carta trae una línea vote", "una carta que todavía no está clara no vota",
            "nunca cambies el voto de una carta", "di qué inclinó la balanza",
            "Lee la carta, o las tres cartas, según las reglas de su grupo de revisión de arriba",
            "Sin <verdict> no hay líneas vote")),
])
def test_reader_prompt_reads_yes_no_on_three_cards(lang, phrases):
    """Stage 4.5 §4: a paragraph per card with its vote, synthesis — what tipped the verdict, one step, one why."""
    text = PROMPTS[("reader", lang)].text
    assert all(phrase in text for phrase in phrases)


# --- stage 4.6 (owner decisions 22.11.2026): reader v7, follow-up v6 ---

@pytest.mark.parametrize("name, lang, phrases", [
    ("reader", "en", ("In an ordinary question (guard group ok) you may say with confidence",
                      '"someone new will come into your life"', '"this new job will ask a lot of you"',
                      'without "may" or "might" on every line', "no dates or time frames", '"in March"',
                      '"within two weeks"', "no guarantees or fate", '"guaranteed"', '"destined"', '"it is written"',
                      "never about another person (rule 4) or the topics of rule 3", "give no date")),
    ("followup", "en", ("In an ordinary follow-up (guard group ok, on a reading whose own guard_group is ok) you may "
                        "say with confidence",
                        '"someone new will come into your life"', "no dates or time frames", '"in March"',
                        "no guarantees or fate", "never about another person (rule 4) or the topics of rule 3")),
    ("reader", "es", ("En una pregunta común (grupo ok) puedes decir con seguridad", "«llegará alguien a tu vida»",
                      "«este trabajo nuevo te va a pedir mucho»", "sin «puede» ni «quizá» en cada línea",
                      "sin fechas ni plazos", "«en marzo»", "«en dos semanas»", "«este año»",
                      "sin garantías ni destino", "«está escrito»",
                      "nunca sobre otra persona (regla 4) ni sobre los temas de la regla 3", "no des fechas")),
    ("followup", "es", ("En una pregunta común (grupo ok, en una lectura cuyo guard_group también es ok) puedes decir "
                        "con seguridad", "«llegará alguien a tu vida»",
                        "sin fechas ni plazos", "«en marzo»", "sin garantías ni destino",
                        "nunca sobre otra persona (regla 4) ni sobre los temas de la regla 3")),
])
def test_bolder_in_ordinary_questions_without_dates_fate_or_other_people(name, lang, phrases):
    """Decision 1: confident about the person's own life in group ok; dates, fate, other people stay forbidden."""
    text = PROMPTS[(name, lang)].text
    assert all(phrase in text for phrase in phrases), [p for p in phrases if p not in text]
    gone = ("Never say something will happen", "speak about the person now") if lang == "en" else (
        "Nunca digas que algo pasará", "habla de la persona ahora")
    assert not [g for g in gone if g in text]


@pytest.mark.parametrize("name, lang, phrases", [
    ("reader", "en", ("In redirect_money, redirect_topic and redirect_person, the confidence of rule 2 does not "
                      "apply",
                      "no line may hint at how it will turn out", '"the answer on her side is still forming"',
                      '"the answer is taking shape"')),
    ("followup", "en", ("In redirect_money, redirect_topic and redirect_person, the confidence of rule 2 does not apply",
                        "no line may hint at how it will turn out", '"the answer on her side is still forming"',
                        "The same holds when the reading itself has one of these groups (the guard_group on <reading>), "
                        "even if this follow-up is marked ok: the stricter group counts.")),
    ("reader", "es", ("En redirect_money, redirect_topic y redirect_person no vale la seguridad de la regla 2",
                      "ninguna línea puede insinuar cómo va a terminar",
                      "«la respuesta de su lado todavía se está formando»", "«la respuesta está tomando forma»")),
    ("followup", "es", ("En redirect_money, redirect_topic y redirect_person no vale la seguridad de la regla 2",
                        "ninguna línea puede insinuar cómo va a terminar",
                        "«la respuesta de su lado todavía se está formando»",
                        "Lo mismo vale cuando la lectura misma trae uno de estos grupos (el guard_group de <reading>), "
                        "aunque esta pregunta venga marcada ok: cuenta el grupo más estricto.")),
])
def test_groups_without_an_outcome_get_no_hint_not_even_a_soft_one(name, lang, phrases):
    """Decision 2 (en-45: "The answer on her side is still forming")."""
    text = PROMPTS[(name, lang)].text
    assert all(phrase in text for phrase in phrases), [p for p in phrases if p not in text]


@pytest.mark.parametrize("name", ["reader", "followup"])
def test_spanish_no_gender_examples_and_neutral_orientation_words(name):
    """Decision 3 (es-52, fu-es-06): "a ti mismo", "demasiado duro contigo", doublets; "al derecho" / "al revés"."""
    text = PROMPTS[(name, "es")].text
    for phrase in ("«a ti mismo»", "«contigo mismo»", "di «a ti» o «contigo»", "«eres demasiado duro contigo»",
                   "«te exiges demasiado»", "«abierta o abierto»", "«ti misma o mismo»", "«al derecho»", "«al revés»",
                   "«El As de Copas»", "«El Emperador»"):
        assert phrase in text, phrase
    # "invertida" / "derecha" appear only in the one line that forbids them after a card name
    assert text.count("invertida") == 1 and text.count("derecha") == 1
    assert ("Nunca escribas «invertida» ni «derecha» después del nombre de una carta" in text) if name == "reader" else (
        "nunca «derecha» ni «invertida» después del nombre de la carta" in text)


def test_spanish_reader_describes_the_orientation_it_receives():
    text = PROMPTS[("reader", "es")].text
    assert "su orientación (al derecho o al revés)" in text
    assert "Una carta al revés siempre da «todavía no está claro»" in text and "Una carta al revés vota" in text


@pytest.mark.parametrize("lang, phrases", [
    ("en", ('with three cards it says "the cards", in the plural ("The cards lean toward...")',
            'with one card, "the card"', '"The cards lean toward yes for this choice, with care"',
            'with three cards, "The cards lean toward yes, with care"',
            'speaks of the cards in the plural ("The cards lean toward no, gently"), never "The card leans"')),
    ("es", ("con tres cartas di «las cartas», en plural («Las cartas se inclinan…»)", "con una carta, «la carta»",
            "«Las cartas se inclinan hacia el sí para esta decisión, con cuidado»",
            "con tres cartas, «Las cartas se inclinan hacia el sí, con cuidado»",
            "habla de las cartas en plural («Las cartas se inclinan hacia el no, con suavidad»), "
            "nunca «La carta se inclina»")),
])
def test_three_card_headline_speaks_of_the_cards_in_the_plural(lang, phrases):
    """Decision 4 (the stage: "The card leans toward yes" over three cards); one card stays singular."""
    text = PROMPTS[("reader", lang)].text
    assert all(phrase in text for phrase in phrases), [p for p in phrases if p not in text]
    assert ('"The card leans toward yes, with care"' in text) if lang == "en" else (
        "«La carta se inclina hacia el sí, con cuidado»" in text)


def test_spanish_daily_prompt_names_the_orientation_neutrally():
    """Stage 4.6, owner decision 22.11.2026: the card of the day says «al revés» / «al derecho», like its input."""
    text = PROMPTS[("daily", "es")].text
    assert "si salió al revés, diciéndolo así: «al revés»" in text and "di «al derecho»" in text
    assert "salió invertida" not in text
    assert text.count("invertida") == 1 and text.count("derecha") == 1  # only in the line that forbids them
    assert "saying whether it is reversed" in PROMPTS[("daily", "en")].text  # English unchanged


# --- Fable review of 4.6: I2 (still-banned wordings), I4 (verdict wording stays), M1, M10 ---

I2_PHRASES = {
    "en": ('Even about the person\'s own life, do not use "will come back", "will return", "you will recover", '
           '"you will win" or "you will lose": say "you will feel steady again", "you will find your confidence '
           'again", "that fear will ease".'),
    "es": ("Aun hablando de la propia vida de la persona, no uses «volverá», «va a volver», «regresará», «va a "
           "regresar», «vas a ganar» ni «vas a perder»: di «vas a sentir calma otra vez», «vas a recuperar la "
           "confianza», «ese miedo va a aflojar»."),
}


@pytest.mark.parametrize("name, lang", [("reader", "en"), ("reader", "es"), ("followup", "en"), ("followup", "es")])
def test_rule_2_steers_around_the_still_banned_wordings(name, lang):
    text = PROMPTS[(name, lang)].text
    assert I2_PHRASES[lang] in text
    assert ('"it is certain"' in text) if lang == "en" else ("«es seguro»" in text)  # M10


@pytest.mark.parametrize("lang, phrase", [
    ("en", 'with a <verdict>, the wording of "Yes/no readings" for a card or an answer that is "still forming" stays '
           'as written there.'),
    ("es", "cuando hay <verdict>, lo que dice «Lecturas de sí o no» sobre una carta o una respuesta que «todavía se "
           "está formando» sigue igual."),
])
def test_the_no_hint_paragraph_keeps_the_verdict_wording(lang, phrase):
    """I4: a money yes/no reading still says "still forming" for an unclear card or answer."""
    assert phrase in PROMPTS[("reader", lang)].text


def test_followup_rule_4_names_another_persons_return():
    """M1: rule 2 no longer says "will come back", so rule 4 of the follow-up names it."""
    assert '"he loves you", "he is thinking of you", "she will come back"' in PROMPTS[("followup", "en")].text
    assert "«piensa en ti», «va a regresar»" in PROMPTS[("followup", "es")].text


# --- stage 4.8 (owner decisions 48–49): reader v8, follow-up v8 — the cards' meaning in person and topic questions ---

from app.reader import check  # noqa: E402
from app.reader.gender import find_reader_gender  # noqa: E402

PERSON_TOPIC_PHRASES = {
    ("reader", "en"): (
        "Never state as a fact what another person thinks, feels, wants, intends or will do.",
        'not as the card\'s words ("the card shows he loves you")',
        "you read what the cards mean in a question like this: the card's themes, never the other person's mind",
        '"In a question like yours, the Lovers speak of attraction and a wish to be close"',
        '"here the cards point to distance and caution"',
        "no line says what they feel, think, want or will do as a fact (rule 4)",
        'do not restate it in words like "how he feels" or "whether she thinks of you"',
        "reflect it by the \"Yes/no readings\" rules as the cards' lean on this question",
        '("Yes, she will text you")',
        "There is never a <verdict> here.",
        '"In a question like this, Temperance is about patience and balance"',
        "a theme never becomes a result", '"you will get better"', '"you will win the case"',
        "Reading what the cards mean in a question like this, as above, is not a forecast",
        "In redirect_money and redirect_person a <verdict> is still reflected as the cards' lean",
        "the step is about the person's own feelings, needs or words",
    ),
    ("followup", "en"): (
        "Never state as a fact what another person thinks, feels, wants, intends or will do",
        "you read what the cards mean in a question like this: the card's themes, never the other person's mind",
        '"In a question like yours, the Lovers speak of attraction and a wish to be close"',
        '"In a question like this, Temperance is about patience and balance"', "a theme never becomes a result",
        "Reading what the cards mean in a question like this, as above, is not a forecast",
        "If it had one, mention it only as the cards' lean",
    ),
    ("reader", "es"): (
        "Nunca afirmes como un hecho lo que otra persona piensa, siente, quiere o va a hacer.",
        "ni como palabras de la carta («la carta muestra que te ama»)",
        "lees lo que significan las cartas en una pregunta así: los temas de la carta",
        "«En una pregunta como la tuya, Los Enamorados hablan de atracción y de ganas de estar cerca»",
        "«aquí las cartas apuntan a distancia y cautela»", "«en una pregunta así, esta carta habla de señales confusas»",
        "ninguna línea dice como un hecho lo que siente, piensa, quiere o va a hacer (regla 4)",
        "como la inclinación de las cartas en esta pregunta", "(«Sí, te va a escribir»)",
        "Aquí nunca hay <verdict>.", "«En una pregunta así, La Templanza habla de paciencia y equilibrio»",
        "un tema nunca se vuelve un resultado", "«te vas a recuperar»", "«vas a ganar el juicio»",
        "Leer lo que significan las cartas en una pregunta así, como arriba, no es un pronóstico",
        "En redirect_money y redirect_person, el <verdict> se sigue reflejando como la inclinación de las cartas",
    ),
    ("followup", "es"): (
        "Nunca afirmes como un hecho lo que otra persona piensa, siente, quiere o va a hacer",
        "lees lo que significan las cartas en una pregunta así: los temas de la carta",
        "«En una pregunta como la tuya, Los Enamorados hablan de atracción y de ganas de estar cerca»",
        "«En una pregunta así, La Templanza habla de paciencia y equilibrio»", "un tema nunca se vuelve un resultado",
        "Leer lo que significan las cartas en una pregunta así, como arriba, no es un pronóstico",
        "Si lo traía, menciónalo solo como la inclinación de las cartas",
    ),
}


@pytest.mark.parametrize("key", list(PERSON_TOPIC_PHRASES))
def test_person_and_topic_questions_read_the_cards_meaning(key):
    """Decision 48: the cards' meaning in a question about another person, never a fact about them, and the verdict
    as the cards' lean; decision 49: the themes of the cards about the situation, no outcome, no yes or no."""
    text = PROMPTS[key].text
    assert [p for p in PERSON_TOPIC_PHRASES[key] if p not in text] == []
    # v7's "read only about the person" lines are gone
    gone = ("Do not guess them.", "Read the cards about the person asking", "Talk about the person themself.",
            "No lo adivines.", "Lee las cartas sobre quien pregunta", "Habla de la persona misma.")
    assert [g for g in gone if g in text] == []


ALLOWED_MEANING = {
    "en": ["In a question like yours, the Lovers speak of attraction and a wish to be close.",
           "Here the cards point to distance and caution.", "This card talks about mixed signals.",
           "In a question like this, Temperance is about patience and balance.",
           "Here the Star speaks of hope and quiet trust.", "The card leans toward yes, with care."],
    "es": ["En una pregunta como la tuya, Los Enamorados hablan de atracción y de ganas de estar cerca.",
           "Aquí las cartas apuntan a distancia y cautela.",
           "En una pregunta así, esta carta habla de señales confusas.",
           "En una pregunta así, La Templanza habla de paciencia y equilibrio.",
           "Aquí La Estrella habla de esperanza y de confianza tranquila.",
           "La carta se inclina hacia el sí, con cuidado."],
}


@pytest.mark.parametrize("lang", ["en", "es"])
@pytest.mark.parametrize("group", ["redirect_person", "redirect_topic"])
def test_the_prompts_meaning_examples_pass_the_live_dictionary(lang, group):
    """The phrasings the prompts teach are not caught by the live dictionary of a group without an outcome (so the
    answer is not replaced by the card base), and in Spanish carry no gendered form for the reader."""
    terms = check.live_terms(check.load_reader_terms(), lang, group)
    for line in ALLOWED_MEANING[lang]:
        assert check.find_claims(line, terms, lang)[0] == [], line
        if lang == "es":
            assert find_reader_gender(line) == [], line


@pytest.mark.parametrize("lang, line", [
    ("en", "In a question like yours, this card shows that he loves you."),
    ("en", "The card says she will come back."),
    ("es", "En una pregunta así, la carta muestra que te ama."),
    ("es", "La carta dice que va a regresar."),
])
def test_a_fact_about_the_other_person_in_the_cards_mouth_is_still_caught(lang, line):
    terms = check.live_terms(check.load_reader_terms(), lang, "redirect_person")
    assert check.find_claims(line, terms, lang)[0]
