"""Card base for the API: deck.json, meanings.<lang>.json, yes-no-rules.json; yes/no verdict; reader excerpts.

The verdict rule is the same as the reference tools/cards/yes_no.py (tests/test_cards.py compares both on every
card and on every three-card combination); the rule itself lives in content/cards/yes-no-rules.json.
"""
import json
from dataclasses import dataclass
from pathlib import Path

VERDICTS = ("yes", "no", "unclear")
LANGS = ("en", "es")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def card_verdict(base: str, reversed_: bool, rules: dict) -> str:
    """One card: the base verdict from deck.json; a reversed card shifts by reversed_shift."""
    if base not in VERDICTS:
        raise ValueError(f"unknown verdict: {base}")
    return rules["reversed_shift"][base] if reversed_ else base


def spread_verdict(draws: list[tuple[str, bool]], deck: dict[str, dict], rules: dict) -> str:
    """draws — (card_id, reversed) pairs; deck — card_id → deck.json record."""
    if len(draws) not in rules["spread_sizes"]:
        raise ValueError(f"verdict needs {rules['spread_sizes']} cards, got {len(draws)}")
    verdicts = [card_verdict(deck[cid]["yes_no"], rev, rules) for cid, rev in draws]
    if len(verdicts) == 1:
        return verdicts[0]
    for v in VERDICTS:
        if verdicts.count(v) >= rules["majority"]:
            return v
    return rules["fallback"]


def label(verdict: str, lang: str, rules: dict) -> str:
    return rules["labels"][lang][verdict]


@dataclass(frozen=True)
class CardBase:
    deck: dict[str, dict]
    order: tuple[str, ...]
    meanings: dict[str, dict[str, dict]]
    rules: dict

    def name(self, card_id: str, lang: str) -> str:
        return self.meanings[lang][card_id]["name"]

    def meaning(self, card_id: str, lang: str) -> dict:
        return self.meanings[lang][card_id]

    def verdict(self, cards: list[dict]) -> str:
        return spread_verdict([(c["card_id"], c["reversed"]) for c in cards], self.deck, self.rules)

    def excerpts(self, cards: list[dict], lang: str, topic: str | None) -> list[dict]:
        """What the reader may use (§2.1): keywords, the meaning for the orientation, love for topic love, advice."""
        out = []
        for c in cards:
            m = self.meanings[lang][c["card_id"]]
            ex = {"card_id": c["card_id"], "name": m["name"], "position": c["position"], "reversed": c["reversed"],
                  "keywords": m["keywords"], "meaning": m["reversed"] if c["reversed"] else m["upright"],
                  "advice": m["advice"]}
            if topic == "love":
                ex["love"] = m["love"]
            out.append(ex)
        return out


def load_cards(content_dir: Path) -> CardBase:
    deck_list = load_json(content_dir / "deck.json")
    deck = {c["card_id"]: c for c in deck_list}
    if len(deck) != 78:
        raise ValueError(f"deck.json: {len(deck)} cards instead of 78")
    order = tuple(c["card_id"] for c in sorted(deck_list, key=lambda c: c["order"]))
    meanings = {}
    for lang in LANGS:
        records = {m["card_id"]: m for m in load_json(content_dir / f"meanings.{lang}.json")}
        if set(records) != set(deck):
            raise ValueError(f"meanings.{lang}.json: card_ids do not match deck.json")
        meanings[lang] = records
    return CardBase(deck=deck, order=order, meanings=meanings, rules=load_json(content_dir / "yes-no-rules.json"))
