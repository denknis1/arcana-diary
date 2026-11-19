import itertools
import json
import shutil

import pytest

from app.cards import VERDICTS, card_verdict, label, load_cards, spread_verdict
from app.config import load_settings
from helpers import load_tool

CONTENT = load_settings({}).content_dir
BASE = load_cards(CONTENT)
REF = load_tool("yes_no")
REF_RULES = REF.load_rules()


def test_base_loaded():
    assert len(BASE.deck) == 78
    assert len(BASE.order) == 78 and BASE.order[0] == "major-00-fool"
    assert set(BASE.meanings) == {"en", "es"}
    assert all(len(BASE.meanings[lang]) == 78 for lang in ("en", "es"))
    assert BASE.name("major-18-moon", "es") == "La Luna"


def test_rules_are_the_reference_file():
    assert BASE.rules == REF_RULES


def test_card_verdict_matches_reference_for_all_cards():
    for card_id, record in BASE.deck.items():
        for reversed_ in (False, True):
            assert card_verdict(record["yes_no"], reversed_, BASE.rules) == \
                REF.card_verdict(record["yes_no"], reversed_, REF_RULES), (card_id, reversed_)
            assert BASE.verdict([{"card_id": card_id, "reversed": reversed_}]) == \
                REF.spread_verdict([(card_id, reversed_)], BASE.deck, REF_RULES), (card_id, reversed_)


def test_three_card_verdicts_match_reference_for_every_combination():
    sample = {v: next(cid for cid in BASE.order if BASE.deck[cid]["yes_no"] == v) for v in VERDICTS}
    options = [(sample[v], rev) for v in VERDICTS for rev in (False, True)]
    combos = list(itertools.product(options, repeat=3))
    assert len(combos) == 216
    for combo in combos:
        cards = [{"card_id": cid, "reversed": rev} for cid, rev in combo]
        assert BASE.verdict(cards) == REF.spread_verdict(list(combo), BASE.deck, REF_RULES), combo


def test_reversed_is_unclear_and_upright_keeps_base():
    assert card_verdict("yes", True, BASE.rules) == "unclear"
    assert card_verdict("no", False, BASE.rules) == "no"


def test_unknown_base_raises():
    with pytest.raises(ValueError):
        card_verdict("maybe", False, BASE.rules)


def test_wrong_spread_size_raises():
    with pytest.raises(ValueError):
        spread_verdict([("major-00-fool", False)] * 2, BASE.deck, BASE.rules)


def test_labels():
    assert label("unclear", "en", BASE.rules) == "Not clear yet"
    assert label("yes", "es", BASE.rules) == "Sí"


def test_excerpts_upright_general():
    [ex] = BASE.excerpts([{"card_id": "major-18-moon", "position": "card", "reversed": False}], "en", "general")
    m = BASE.meanings["en"]["major-18-moon"]
    assert ex == {"card_id": "major-18-moon", "name": m["name"], "position": "card", "reversed": False,
                  "keywords": m["keywords"], "meaning": m["upright"], "advice": m["advice"]}


def test_excerpts_reversed_love_es():
    [ex] = BASE.excerpts([{"card_id": "cups-02-two", "position": "present", "reversed": True}], "es", "love")
    m = BASE.meanings["es"]["cups-02-two"]
    assert ex["meaning"] == m["reversed"]
    assert ex["love"] == m["love"]
    assert ex["name"] == "Dos de Copas"


def test_excerpts_keep_order_of_three():
    cards = [{"card_id": cid, "position": pos, "reversed": False}
             for cid, pos in zip(BASE.order[:3], ("past", "present", "path"))]
    assert [e["position"] for e in BASE.excerpts(cards, "en", None)] == ["past", "present", "path"]


def test_load_cards_rejects_missing_meaning(tmp_path):
    for name in ("deck.json", "yes-no-rules.json", "meanings.es.json"):
        shutil.copy(CONTENT / name, tmp_path / name)
    en = json.loads((CONTENT / "meanings.en.json").read_text(encoding="utf-8"))
    (tmp_path / "meanings.en.json").write_text(json.dumps(en[:-1]), encoding="utf-8")
    with pytest.raises(ValueError, match="meanings.en.json"):
        load_cards(tmp_path)
