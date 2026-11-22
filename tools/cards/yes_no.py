"""Вердикт «да / нет / пока неясно» по правилу content/cards/yes-no-rules.json.

Эталонная реализация правила для чтеца (4.2) и интерфейса (4.4); правило задаёт JSON, код его только исполняет.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "content/cards/yes-no-rules.json"
VERDICTS = ("yes", "no", "unclear")


def load_rules(path: Path = RULES) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def card_verdict(base: str, reversed_: bool, rules: dict) -> str:
    """Вердикт одной карты: базовый из deck.json, перевёрнутая сдвигается по reversed_shift."""
    if base not in VERDICTS:
        raise ValueError(f"неизвестный вердикт: {base}")
    return rules["reversed_shift"][base] if reversed_ else base


def spread_verdict(draws: list[tuple[str, bool]], deck: dict[str, dict], rules: dict) -> str:
    """draws — список (card_id, перевёрнута ли); deck — card_id → запись deck.json.

    Три карты, правило decisive_majority (этап 4.5, решение владельца 21.11.2026): карты «пока неясно»
    воздерживаются; «да» больше, чем «нет», — «да», «нет» больше — «нет»; ничья или ни одной решающей — fallback.
    """
    if len(draws) not in rules["spread_sizes"]:
        raise ValueError(f"вердикт считается по {rules['spread_sizes']} картам, а не по {len(draws)}")
    if rules.get("rule") != "decisive_majority":
        raise ValueError(f"неизвестное правило: {rules.get('rule')}")
    verdicts = [card_verdict(deck[cid]["yes_no"], rev, rules) for cid, rev in draws]
    if len(verdicts) == 1:
        return verdicts[0]
    yes, no = verdicts.count("yes"), verdicts.count("no")
    if yes != no:
        return "yes" if yes > no else "no"
    return rules["fallback"]


def label(verdict: str, lang: str, rules: dict) -> str:
    return rules["labels"][lang][verdict]
