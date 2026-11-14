import pytest

import copy

from validate_cards import check_rules
from yes_no import card_verdict, label, load_rules, spread_verdict

RULES = load_rules()
DECK = {"sun": {"yes_no": "yes"}, "tower": {"yes_no": "no"}, "moon": {"yes_no": "unclear"},
        "star": {"yes_no": "yes"}, "ten-swords": {"yes_no": "no"}}


@pytest.mark.parametrize("base", ["yes", "no", "unclear"])
def test_upright_keeps_base(base):
    assert card_verdict(base, False, RULES) == base


@pytest.mark.parametrize("base", ["yes", "no", "unclear"])
def test_reversed_moves_to_unclear(base):
    assert card_verdict(base, True, RULES) == "unclear"


def test_unknown_verdict_raises():
    with pytest.raises(ValueError):
        card_verdict("maybe", False, RULES)


def test_one_card():
    assert spread_verdict([("sun", False)], DECK, RULES) == "yes"
    assert spread_verdict([("tower", True)], DECK, RULES) == "unclear"


def test_three_cards_majority_yes():
    assert spread_verdict([("sun", False), ("star", False), ("tower", False)], DECK, RULES) == "yes"


def test_three_cards_majority_no():
    assert spread_verdict([("tower", False), ("ten-swords", False), ("sun", False)], DECK, RULES) == "no"


def test_three_cards_reversed_breaks_majority():
    # sun перевёрнута → unclear; yes, no, unclear — большинства нет
    assert spread_verdict([("sun", True), ("star", False), ("tower", False)], DECK, RULES) == "unclear"


def test_three_cards_majority_unclear():
    assert spread_verdict([("moon", False), ("sun", True), ("star", False)], DECK, RULES) == "unclear"


@pytest.mark.parametrize("n", [0, 2, 4])
def test_other_sizes_raise(n):
    with pytest.raises(ValueError):
        spread_verdict([("sun", False)] * n, DECK, RULES)


def test_labels():
    assert label("unclear", "en", RULES) == "Not clear yet"
    assert label("yes", "es", RULES) == "Sí"
    assert label("unclear", "es", RULES) == "Todavía no está claro"


# --- проверка файла правила ---

def test_rules_file_valid():
    assert check_rules(RULES) == []


def test_rules_missing_label():
    rules = copy.deepcopy(RULES)
    del rules["labels"]["es"]["unclear"]
    assert any("labels.es" in e for e in check_rules(rules))


def test_rules_wrong_majority():
    rules = dict(RULES, majority=1)
    assert any("majority" in e for e in check_rules(rules))
