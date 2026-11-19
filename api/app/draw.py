"""Drawing cards (§1.2 step 4, §2.6): a crypto-random seed, a deterministic draw from it, the card of the day.

random.Random(seed) is used only for the permutation; each card's orientation is one bit of sha256(seed, index),
so every card is reversed with probability 1/2 and a saved seed reproduces the same reading.
"""
import hashlib
import random
import secrets
from datetime import date
from typing import Sequence

KIND_COUNTS = {"one": 1, "three": 3, "yes_no": 1, "card_page": 1}
THREE_POSITIONS = ("past", "present", "path")
SINGLE_POSITION = "card"


def new_seed() -> str:
    return secrets.token_hex(16)


def _reversed(seed: str, index: int) -> bool:
    return (hashlib.sha256(f"{seed}|reversed|{index}".encode()).digest()[0] & 1) == 1


def draw(seed: str, n: int, card_ids: Sequence[str]) -> list[tuple[str, bool]]:
    if not 1 <= n <= len(card_ids):
        raise ValueError(f"cannot draw {n} cards from {len(card_ids)}")
    deck = list(card_ids)
    random.Random(seed).shuffle(deck)
    return [(deck[i], _reversed(seed, i)) for i in range(n)]


def positions(kind: str) -> tuple[str, ...]:
    return THREE_POSITIONS if KIND_COUNTS[kind] == 3 else (SINGLE_POSITION,)


def draw_spread(seed: str, kind: str, card_ids: Sequence[str]) -> list[dict]:
    drawn = draw(seed, KIND_COUNTS[kind], card_ids)
    return [{"card_id": cid, "position": pos, "reversed": rev} for (cid, rev), pos in zip(drawn, positions(kind))]


def daily_seed(guest_id: str, day: date) -> str:
    return hashlib.sha256(f"daily|{guest_id}|{day.isoformat()}".encode()).hexdigest()


def daily_draw(guest_id: str, day: date, card_ids: Sequence[str]) -> tuple[str, bool]:
    """The personal card of the day: same all day for this guest, new after local midnight."""
    return draw(daily_seed(guest_id, day), 1, card_ids)[0]
