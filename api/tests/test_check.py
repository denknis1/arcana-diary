import pytest

from app.config import load_settings
from app.reader.check import (FOLLOWUP_WORDS, banned_in, check_answer, find_claims, length_ok, load_reader_terms,
                              word_count)
from app.terms import find_banned, load_terms

TERMS = load_reader_terms()
BASE_TERMS = load_terms(load_settings({}).banned_terms_path)


def words(n: int) -> str:
    return " ".join(["calm"] * n)


def one_card(**overrides) -> dict:
    sections = {"headline": "A calm way forward.", "card1": words(100), "step": "Write one line today."}
    sections.update(overrides)
    return sections


def test_reader_terms_languages():
    assert set(TERMS) == {"en", "es"}


def test_clean_answer_passes():
    result = check_answer(one_card(), "one", "en", TERMS["en"], with_why=False)
    assert result.body_ok and result.why_ok and result.banned == () and result.length_ok


@pytest.mark.parametrize("lang, text, expected", [
    ("en", "This will happen for sure.", ("for sure", "will happen")),
    ("en", "He feels the same way about you.", ("feels the same", "he feels")),
    ("en", "Your ex still loves you and misses you.", ("misses you", "still loves you")),
    ("es", "Seguro que no es fácil, pero él siente lo mismo.", ("él siente",)),
    ("es", "Te extraña y volverá pronto.", ("te extraña", "volverá")),
])
def test_claims_in_body_are_caught(lang, text, expected):
    result = check_answer(one_card(card1=text), "one", lang, TERMS[lang], with_why=False)
    assert not result.body_ok and result.banned == expected


@pytest.mark.parametrize("lang, text", [
    ("en", "The cards can't tell you what he feels, but they can speak to what you need."),
    ("en", "I can't say what she thinks."),
    ("en", "Nothing here says this will happen."),
    ("es", "Las cartas no pueden decirte lo que siente por ti."),
    ("es", "No sé si piensa en ti."),
    ("es", "Nadie puede asegurar que volverá."),
    ("es", "Date un tiempo destinado solo a ti."),
])
def test_saying_the_cards_cannot_know_is_not_a_claim(lang, text):
    result = check_answer(one_card(card1=text), "one", lang, TERMS[lang], with_why=False)
    assert result.body_ok and result.banned == ()
    assert banned_in(text, TERMS[lang], lang) == []


@pytest.mark.parametrize("lang, text, expected", [
    ("en", "Don't worry, he still loves you.", ["still loves you"]),
    ("en", "I can't promise anything, but he misses you.", ["misses you"]),
    ("es", "No te preocupes: te extraña.", ["te extraña"]),
])
def test_a_negation_in_another_clause_does_not_hide_a_claim(lang, text, expected):
    assert find_claims(text, TERMS[lang], lang)[0] == expected


def test_negated_terms_are_reported_apart():
    result = check_answer(one_card(card1="I can't tell you what he feels."), "one", "en", TERMS["en"], False)
    assert result.body_ok and result.negated == ("he feels",)


@pytest.mark.parametrize("lang, text", [
    ("en", "I can't speak to the pregnancy itself, but this card can help you with how you carry it."),
    ("en", "A doctor is the right person for questions about illness."),
    ("en", "Look at what is coming up for you this week."),
    ("en", "The court cards in this deck are about people."),
    ("es", "No puedo hablar del embarazo, pero sí de cómo lo estás viviendo."),
    ("es", "Seguro que no es fácil, y está bien ir despacio."),
])
def test_naming_a_topic_is_not_a_violation(lang, text):
    assert find_banned(text, BASE_TERMS[lang])  # the card base's dictionary would have replaced it
    assert check_answer(one_card(card1=text), "one", lang, TERMS[lang], with_why=False).body_ok


@pytest.mark.parametrize("lang, why", [
    ("en", "Yes, the card is bright."), ("en", "The answer is no for now."), ("en", "No, not this time."),
    ("en", "It is not clear from the card."), ("en", "Maybe later."), ("en", "It leans toward yes."),
    ("es", "Sí, la carta brilla."), ("es", "No, por ahora no."), ("es", "La respuesta es no por ahora."),
    ("es", "Quizá más adelante."), ("es", "Todavía no está claro."), ("es", "Tal vez con calma."),
    ("en", "No — the card shows a wall."), ("en", "The card leans toward a no."),
    ("en", "Probably not, the card is heavy."), ("es", "No — la carta muestra un muro."),
    ("es", "La carta se inclina hacia un no."), ("es", "Probablemente no, la carta pesa."),
])
def test_verdict_words_in_why(lang, why):
    result = check_answer(one_card(why=why), "yes_no", lang, TERMS[lang], with_why=True)
    assert result.body_ok and not result.why_ok


@pytest.mark.parametrize("lang, why", [
    ("en", "There is no rush in this card, only open hands and a clear road."),
    ("en", "The card shows open hands and a clear road."),
    ("es", "La carta muestra calma y no hay prisa."),
    ("es", "Aún no se ve el camino completo, y la carta en sí habla de paciencia."),
    ("es", "La carta muestra manos abiertas y un camino despejado."),
])
def test_ordinary_no_in_why_passes(lang, why):
    assert check_answer(one_card(why=why), "yes_no", lang, TERMS[lang], with_why=True).why_ok


def test_live_term_in_why_only():
    result = check_answer(one_card(why="Your wish is destined to come true."), "yes_no", "en", TERMS["en"], True)
    assert result.body_ok and not result.why_ok


def test_missing_why_when_required():
    assert not check_answer(one_card(), "yes_no", "en", TERMS["en"], with_why=True).why_ok
    assert check_answer(one_card(), "yes_no", "en", TERMS["en"], with_why=False).why_ok


def test_length_limits():
    assert not check_answer(one_card(card1=words(40)), "one", "en", TERMS["en"], False).length_ok
    three = {"headline": words(10), "card1": words(50), "card2": words(50), "card3": words(50),
             "synthesis": words(20), "step": words(20)}
    assert check_answer(three, "three", "en", TERMS["en"], False).length_ok
    assert length_ok(words(70), FOLLOWUP_WORDS) and not length_ok(words(130), FOLLOWUP_WORDS)


def test_word_count_keeps_contractions_whole():
    assert word_count("Don't rush — it's fine, self-care first.") == 6


@pytest.mark.parametrize("lang, text, expected", [
    ("es", "No dudes que volverá.", ["volverá"]),
    ("es", "No tengas miedo porque te extraña.", ["te extraña"]),
    ("es", "Él no te olvidó y volverá.", ["volverá"]),
    ("en", "Nothing has changed and he still loves you.", ["still loves you"]),
    ("en", "Nobody else matters because he misses you.", ["misses you"]),
    ("en", "He loves you, and nobody else matters.", ["he loves you"]),
    ("es", "Nadie más importa porque te ama.", ["te ama"]),
])
def test_a_loose_negation_word_does_not_hide_a_claim(lang, text, expected):
    assert find_claims(text, TERMS[lang], lang)[0] == expected


@pytest.mark.parametrize("lang, text", [
    ("en", "The cards cannot tell you whether he loves you."),
    ("en", "No one can know if she regrets it."),
    ("en", "Nobody can promise that he will come back."),
    ("en", "There's no way to know what he feels."),
    ("en", "I can't be sure he misses you."),
    ("es", "No se puede saber si te quiere."),
    ("es", "No puedo decir si te extraña."),
    ("es", "No hay forma de saber si volverá."),
    ("es", "Nadie sabe si se arrepiente."),
    ("es", "No sé si te ama."),
])
def test_explicit_cannot_know_phrasing_is_negated(lang, text):
    assert find_claims(text, TERMS[lang], lang)[0] == []


@pytest.mark.parametrize("lang, text, term", [
    ("en", "He loves you.", "he loves you"), ("en", "She loves you.", "she loves you"),
    ("en", "He loves you back.", "loves you back"), ("en", "He wants you back.", "wants you back"),
    ("en", "He regrets it.", "he regrets"), ("en", "She regrets it.", "she regrets"),
    ("en", "Someone misses you.", "misses you"),
    ("es", "Él te ama.", "te ama"), ("es", "Ella te quiere.", "ella te quiere"),
    ("es", "Él se arrepiente.", "él se arrepiente"), ("es", "Alguien te extraña.", "te extraña"),
    ("es", "Pasará algo bueno.", "pasará algo"), ("es", "Llegará el amor.", "llegará el amor"),
])
def test_live_dictionary_claims(lang, text, term):
    assert term in find_claims(text, TERMS[lang], lang)[0]


@pytest.mark.parametrize("text", ["Esta etapa pasará.", "El miedo pasará con calma.", "El cansancio llegará y se irá."])
def test_a_phase_passing_is_not_an_event_claim(text):
    assert find_claims(text, TERMS["es"], "es")[0] == []


def test_say_yes_to_yourself_is_not_a_verdict_in_why():
    for text in ("You can say yes to yourself, and the card shows open hands.",):
        assert check_answer(one_card(why=text), "yes_no", "en", TERMS["en"], with_why=True).why_ok


@pytest.mark.parametrize("why", ["Yes — the card is bright.", "Yes.", "The answer is yes.", "It leans toward a yes.",
                                 "The card is warm. Yes, go."])
def test_yes_as_the_answer_is_a_verdict_in_why(why):
    assert not check_answer(one_card(why=why), "yes_no", "en", TERMS["en"], with_why=True).why_ok


@pytest.mark.parametrize("why", ["Sí — la carta brilla.", "La respuesta es sí."])
def test_es_yes_verdict_in_why(why):
    assert not check_answer(one_card(why=why), "yes_no", "es", TERMS["es"], with_why=True).why_ok


@pytest.mark.parametrize("lang, text, expected", [
    ("es", "Nadie puede negar que te extraña.", ["te extraña"]),
    ("es", "Nadie sabe amarte como él y volverá.", ["volverá"]),
    ("es", "No sé por qué dudas de que volverá.", ["volverá"]),
    ("en", "I don't know why you doubt that he will come back.", ["will come back"]),
    ("en", "Whether you believe it or not he will come back.", ["will come back"]),
    ("en", "Not sure why you worry when he still loves you.", ["still loves you"]),
    ("en", "You can't see how much he misses you.", ["misses you"]),
    ("es", "Él te quiere.", ["él te quiere"]), ("es", "Ella se arrepiente.", ["ella se arrepiente"]),
])
def test_knowing_verbs_only_negate(lang, text, expected):
    assert find_claims(text, TERMS[lang], lang)[0] == expected


@pytest.mark.parametrize("lang, text", [
    ("en", "I don't know whether he feels the same."), ("en", "Not sure if she thinks of you."),
    ("en", "I cannot speak to whether he misses you."), ("en", "No one can know whether he misses you."),
    ("es", "No sé si piensa en ti."), ("es", "Nadie sabe si volverá."), ("es", "Nadie puede saber si te extraña."),
    ("es", "No sé qué siente por ti."),
])
def test_knowing_phrasing_stays_negated(lang, text):
    assert find_claims(text, TERMS[lang], lang)[0] == []


@pytest.mark.parametrize("text", ["Esta carta te quiere decir que confíes.", "La vida te quiere mostrar algo.",
                                  "Nadie se arrepiente de cuidarse."])
def test_te_quiere_and_se_arrepiente_need_a_person(text):
    assert find_claims(text, TERMS["es"], "es")[0] == []


@pytest.mark.parametrize("lang, why", [("en", "The cards say yes."), ("en", "The card points to a yes."),
                                       ("en", "It leans yes."), ("es", "Las cartas dicen que sí."),
                                       ("es", "La carta apunta a un sí.")])
def test_say_yes_forms_are_verdicts(lang, why):
    assert not check_answer(one_card(why=why), "yes_no", lang, TERMS[lang], with_why=True).why_ok


def test_three_yes_no_cards_use_the_three_card_length():
    sections = {"headline": "A lean.", "card1": "word " * 60, "card2": "word " * 60, "card3": "word " * 60,
                "step": "Write it down.", "why": "Two of the cards lean the same way."}
    assert check_answer(sections, "yes_no", "en", TERMS["en"], True, 3).length_ok is True
    assert check_answer(sections, "yes_no", "en", TERMS["en"], True).length_ok is False  # one card: 90–150
