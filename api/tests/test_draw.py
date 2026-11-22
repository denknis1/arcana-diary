import re
from datetime import date

import pytest

from app.cards import load_cards
from app.config import load_settings
from app.draw import KIND_COUNTS, card_count, daily_draw, draw, draw_spread, new_seed, positions

ORDER = load_cards(load_settings({}).content_dir).order


def test_new_seed_is_hex_and_unique():
    seeds = {new_seed() for _ in range(200)}
    assert len(seeds) == 200
    assert all(re.fullmatch(r"[0-9a-f]{32}", s) for s in seeds)


def test_same_seed_same_draw():
    assert draw("abc", 3, ORDER) == draw("abc", 3, ORDER)


def test_known_seed_is_stable():
    # Pins the algorithm: if this changes, saved readings no longer reproduce from their seed.
    assert draw("arcana-test-seed", 3, ORDER) == [("swords-07-seven", True), ("swords-10-ten", True),
                                                   ("swords-08-eight", True)]


def test_different_seeds_differ():
    assert len({tuple(draw(f"seed-{i}", 3, ORDER)) for i in range(50)}) == 50


def test_three_distinct_cards():
    for i in range(200):
        assert len({cid for cid, _ in draw(f"s{i}", 3, ORDER)}) == 3


def test_every_card_can_appear_and_orientation_is_fair():
    first = [draw(f"fair-{i}", 1, ORDER)[0] for i in range(4000)]
    assert {cid for cid, _ in first} == set(ORDER)
    share = sum(rev for _, rev in first) / len(first)
    assert 0.46 < share < 0.54


@pytest.mark.parametrize("n", [0, 79])
def test_bad_count_raises(n):
    with pytest.raises(ValueError):
        draw("abc", n, ORDER)


def test_positions_and_kinds():
    assert KIND_COUNTS == {"one": 1, "three": 3, "yes_no": 1, "card_page": 1}
    assert positions("three") == ("past", "present", "path")
    assert positions("yes_no") == ("card",)
    assert positions("card_page") == ("card",)


def test_draw_spread_three():
    spread = draw_spread("abc", "three", ORDER)
    assert [c["position"] for c in spread] == ["past", "present", "path"]
    assert [(c["card_id"], c["reversed"]) for c in spread] == draw("abc", 3, ORDER)


def test_daily_same_all_day_new_next_day():
    day = date(2026, 11, 20)
    assert daily_draw("guest-1", day, ORDER) == daily_draw("guest-1", day, ORDER)
    assert len({daily_draw("guest-1", date(2026, 11, k), ORDER) for k in range(1, 31)}) >= 20


def test_daily_differs_between_guests():
    day = date(2026, 11, 20)
    assert len({daily_draw(f"guest-{i}", day, ORDER) for i in range(40)}) >= 25


def test_yes_no_on_three_cards_has_no_time():
    assert [card_count("yes_no"), card_count("yes_no", 1), card_count("yes_no", 3)] == [1, 1, 3]
    assert card_count("three") == 3 and card_count("one") == 1
    assert positions("yes_no", 3) == ("card", "card", "card")
    assert positions("yes_no", 1) == positions("yes_no") == ("card",)
    spread = draw_spread("abc", "yes_no", ORDER, 3)
    assert [c["position"] for c in spread] == ["card"] * 3
    assert [(c["card_id"], c["reversed"]) for c in spread] == draw("abc", 3, ORDER)
    assert draw_spread("abc", "yes_no", ORDER) == spread[:1]  # one card: the same first card of the seed
    with pytest.raises(ValueError):
        card_count("yes_no", 2)
