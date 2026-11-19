from app.config import load_settings
import pytest

from app.terms import compile_terms, find_banned, load_terms, normalize
from helpers import load_tool

VALIDATE = load_tool("validate_cards")
BANNED_PATH = load_settings({}).banned_terms_path
SAMPLES = {
    "en": ["This will happen for sure.", "He feels the same way about you.", "A guaranteed result.",
           "Try a new diet.", "The court date.", "Calm, honest words.", "She thinks of you often.",
           "A pregnancy test."],
    "es": ["Seguro que pasará pronto.", "Lo que siente por ti.", "Está garantizado.", "Una dieta nueva.",
           "Palabras tranquilas.", "Un embarazo.", "Te extraña mucho."],
}


def test_patterns_match_validate_cards():
    data = VALIDATE.load_json(BANNED_PATH)
    for lang, terms in data.items():
        ours = [(t, rx.pattern, rx.flags) for t, rx in compile_terms(terms)]
        theirs = [(t, rx.pattern, rx.flags) for t, rx in VALIDATE.compile_terms(terms)]
        assert ours == theirs, lang


def test_find_banned_agrees_on_samples():
    data = VALIDATE.load_json(BANNED_PATH)
    for lang, texts in SAMPLES.items():
        ours, theirs = compile_terms(data[lang]), VALIDATE.compile_terms(data[lang])
        for text in texts:
            assert find_banned(text, ours) == VALIDATE.find_banned(text, theirs), text


def test_stems_and_whole_words():
    en = load_terms(BANNED_PATH)["en"]
    assert find_banned("This is guaranteed.", en) == ["guarantee*"]
    assert find_banned("Try a new diet.", en) == []
    assert find_banned("This WILL   happen.", en) == ["will happen"]


def test_load_terms_languages():
    assert set(load_terms(BANNED_PATH)) == {"en", "es"}


@pytest.mark.parametrize("raw, expected", [
    ("Mejor sin MÍ", "mejor sin mi"), ("I don\u2019t  want to live", "i don't want to live"),
    ("kill\u200bmyself", "killmyself"), ("kill\u200c\u200d\ufeffmyself", "killmyself"),
    ("kill-myself", "kill myself"), ("kil\u00adl\u2060myself", "killmyself"), ("kill\u2013myself", "kill myself"),
    ("kill\u2014myself", "kill myself"), ("Self-Harm", "self harm"),
    ("Me violó", "me violo"), ("ya no quiero estar aquí", "ya no quiero estar aqui"), ("Pingüino", "pinguino"),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_normalize_can_turn_zero_width_into_a_space():
    assert normalize("kill\u200bmyself", zero_width=" ") == "kill myself"
