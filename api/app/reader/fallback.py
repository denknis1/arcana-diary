"""Answers from the card base (§2.5, §5.1): the reader is unavailable, refused, broke a rule or stopped halfway."""
from app.reader.sections import required_sections

REVERSED_WHY = {"en": "The card is reversed, so its answer softens: not clear yet.",
                "es": "La carta salió invertida: su respuesta se suaviza, todavía no está claro."}
POSITION_TITLES = {"en": {"past": "Past", "present": "Present", "path": "Where it leads"},
                   "es": {"past": "Pasado", "present": "Presente", "path": "Hacia dónde va"}}
REVERSED_WORD = {"en": "reversed", "es": "invertida"}


def card_line(excerpt: dict, lang: str) -> str:
    name = excerpt["name"] + (f", {REVERSED_WORD[lang]}" if excerpt["reversed"] else "")
    title = POSITION_TITLES[lang].get(excerpt["position"])
    return f"{title + ': ' if title else ''}{name}. {excerpt['meaning']}"


def why_line(base, card: dict, lang: str) -> str:
    """The fixed line for a reversed card; for an upright card — yes_no_why from the base."""
    return REVERSED_WHY[lang] if card["reversed"] else base.meaning(card["card_id"], lang)["yes_no_why"]


def _excerpts(base, reading: dict) -> list[dict]:
    return base.excerpts(reading["cards"], reading["lang"], reading.get("topic"))


def fallback_answer(base, reading: dict, notice: str) -> dict[str, str]:
    """The cards' meanings from the base with the "reader unavailable" line as the headline."""
    lang = reading["lang"]
    excerpts = _excerpts(base, reading)
    sections = {"headline": notice}
    for i, ex in enumerate(excerpts, 1):
        sections[f"card{i}"] = card_line(ex, lang)
    sections["step"] = excerpts[-1]["advice"]
    if reading.get("verdict") is not None:
        sections["why"] = why_line(base, reading["cards"][0], lang)
    return sections


def headline_line(base, reading: dict) -> str:
    return " · ".join(_excerpts(base, reading)[0]["keywords"])


def fill_missing(sections: dict[str, str], base, reading: dict) -> dict[str, str]:
    """A cut stream keeps what was written; missing cards, step, headline and why come from the base."""
    lang = reading["lang"]
    excerpts = _excerpts(base, reading)
    out = {name: text for name, text in sections.items() if text}
    for name in required_sections(reading["kind"], reading.get("verdict") is not None):
        if name in out or name == "synthesis":
            continue
        if name == "headline":
            out[name] = headline_line(base, reading)
        elif name.startswith("card"):
            out[name] = card_line(excerpts[int(name[4:]) - 1], lang)
        elif name == "step":
            out[name] = excerpts[-1]["advice"]
        elif name == "why":
            out[name] = why_line(base, reading["cards"][0], lang)
    return out


def followup_fallback(base, reading: dict) -> str:
    return " ".join(f"{ex['name']}: {ex['advice']}" for ex in _excerpts(base, reading))


def daily_fallback(excerpt: dict) -> str:
    return f"{excerpt['meaning']} {excerpt['advice']}"
