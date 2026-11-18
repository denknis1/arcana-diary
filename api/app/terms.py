"""Term lists with '*' stems: the card-base dictionary, the live-answer dictionary and the crisis stop-phrases.

compile_terms/find_banned match exactly like tools/cards/validate_cards.py (the API image does not ship tools/,
so the two small functions are copied; tests/test_terms.py checks that both agree). normalize() is for the crisis
filter only (§8.6): people type without accents and with curly apostrophes.
"""
import json
import re
import unicodedata
from pathlib import Path

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'", "´": "'"})


def normalize(text: str) -> str:
    """Lower case, no accents (NFKD without combining marks), straight apostrophes, single spaces."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_APOSTROPHES))
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(plain.lower().split())


def compile_terms(terms: list[str]) -> list[tuple[str, re.Pattern]]:
    """«guarantee*» — the stem with any ending; otherwise a whole word or phrase; case-insensitive."""
    compiled = []
    for term in terms:
        stem = term.endswith("*")
        body = r"\s+".join(re.escape(w) for w in term.rstrip("*").split())
        pattern = r"\b" + body + (r"\w*" if stem else r"\b")
        compiled.append((term, re.compile(pattern, re.IGNORECASE)))
    return compiled


def find_banned(text: str, patterns: list[tuple[str, re.Pattern]]) -> list[str]:
    return [term for term, rx in patterns if rx.search(text)]


def load_terms(path: Path) -> dict[str, list[tuple[str, re.Pattern]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {lang: compile_terms(terms) for lang, terms in data.items()}
