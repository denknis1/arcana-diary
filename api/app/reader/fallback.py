"""Answers from the card base (§2.5, §5.1): the reader is unavailable, refused, broke a rule or stopped halfway.
A yes/no reading on three cards (stage 4.5 §4) gets each card's vote and its "why" line, and a "why" about the
majority."""
from app.cards import label
from app.reader.sections import required_sections

REVERSED_WHY = {"en": "The card is reversed, so its answer softens: not clear yet.",
                "es": "La carta salió al revés: su respuesta se suaviza, todavía no está claro."}
POSITION_TITLES = {"en": {"past": "Past", "present": "Present", "path": "Where it leads"},
                   "es": {"past": "Pasado", "present": "Presente", "path": "Hacia dónde va"}}
REVERSED_WORD = {"en": "reversed", "es": "al revés"}  # stage 4.6: agrees with every card name
# how three yes/no votes add up (rule decisive_majority: "not clear" cards abstain); no verdict words, the site
# shows the verdict right above
MAJORITY_WHY = {
    "en": {"all": "All three cards lean the same way.",
           "two": "Two of the three cards lean the same way; the third is still forming.",
           "two_of_three": "Two of the three cards lean the same way, against one.",
           "one": "One card leans clearly and the other two are still forming, so that card decides.",
           "tie": "One card leans each way and the third is still forming: they balance out.",
           "forming": "All three cards are still forming their answer."},
    "es": {"all": "Las tres cartas se inclinan hacia el mismo lado.",
           "two": "Dos de las tres cartas se inclinan hacia el mismo lado; la tercera todavía se está formando.",
           "two_of_three": "Dos de las tres cartas se inclinan hacia el mismo lado, frente a una.",
           "one": "Una carta se inclina con claridad y las otras dos todavía se están formando: decide ella.",
           "tie": "Una carta se inclina hacia cada lado y la tercera todavía se está formando: se equilibran.",
           "forming": "Las tres cartas todavía están formando su respuesta."},
}
REVERSED_VOTE = {"en": "Reversed, its answer is still forming.",
                 "es": "Al revés, su respuesta todavía se está formando."}


def card_line(excerpt: dict, lang: str) -> str:
    name = excerpt["name"] + (f", {REVERSED_WORD[lang]}" if excerpt["reversed"] else "")
    title = POSITION_TITLES[lang].get(excerpt["position"])
    return f"{title + ': ' if title else ''}{name}. {excerpt['meaning']}"


def why_line(base, card: dict, lang: str) -> str:
    """The fixed line for a reversed card; for an upright card — yes_no_why from the base."""
    return REVERSED_WHY[lang] if card["reversed"] else base.meaning(card["card_id"], lang)["yes_no_why"]


def voting(reading: dict) -> bool:
    """A yes/no reading on three cards with a verdict: each card votes (stage 4.5 §4)."""
    return reading.get("verdict") is not None and len(reading["cards"]) == 3


def vote_line(base, card: dict, excerpt: dict, lang: str) -> str:
    """One card of a three-card yes/no reading: its name, its vote and the line that explains the vote (a
    reversed card: one short line, not the fixed one-card sentence that would repeat "not clear yet")."""
    vote = label(base.vote(card), lang, base.rules)
    if excerpt["reversed"]:
        return f"{excerpt['name']}, {REVERSED_WORD[lang]}: {vote}. {REVERSED_VOTE[lang]}"
    return f"{excerpt['name']}: {vote}. {why_line(base, card, lang)}"


def majority_key(votes: list[str]) -> str:
    """Which MAJORITY_WHY line fits three votes: the cards that lead, against how many, or a tie or none."""
    yes, no = votes.count("yes"), votes.count("no")
    lead, other = max(yes, no), min(yes, no)
    if lead == 0:
        return "forming"
    if lead == other:
        return "tie"
    if lead == 3:
        return "all"
    if lead == 2:
        return "two" if other == 0 else "two_of_three"
    return "one"


def reading_why(base, reading: dict) -> str:
    """The base "why" of a reading with a verdict: the one card's line, or for three cards how the votes add up."""
    if not voting(reading):
        return why_line(base, reading["cards"][0], reading["lang"])
    return MAJORITY_WHY[reading["lang"]][majority_key([base.vote(card) for card in reading["cards"]])]


def _excerpts(base, reading: dict) -> list[dict]:
    return base.excerpts(reading["cards"], reading["lang"], reading.get("topic"))


def _card_text(base, reading: dict, excerpts: list[dict], i: int) -> str:
    """Card i (from 1) as the base tells it: a vote line in a voting reading, else name and meaning."""
    if voting(reading):
        return vote_line(base, reading["cards"][i - 1], excerpts[i - 1], reading["lang"])
    return card_line(excerpts[i - 1], reading["lang"])


def fallback_answer(base, reading: dict, notice: str) -> dict[str, str]:
    """The cards' meanings from the base with the "reader unavailable" line as the headline."""
    excerpts = _excerpts(base, reading)
    sections = {"headline": notice}
    for i in range(1, len(excerpts) + 1):
        sections[f"card{i}"] = _card_text(base, reading, excerpts, i)
    sections["step"] = excerpts[-1]["advice"]
    if reading.get("verdict") is not None:
        sections["why"] = reading_why(base, reading)
    return sections


def headline_line(base, reading: dict) -> str:
    return " · ".join(_excerpts(base, reading)[0]["keywords"])


def fill_missing(sections: dict[str, str], base, reading: dict) -> dict[str, str]:
    """A cut stream keeps what was written; missing cards, step, headline and why come from the base."""
    excerpts = _excerpts(base, reading)
    out = {name: text for name, text in sections.items() if text}
    for name in required_sections(reading["kind"], reading.get("verdict") is not None, len(reading["cards"])):
        if name in out or name == "synthesis":
            continue
        if name == "headline":
            out[name] = headline_line(base, reading)
        elif name.startswith("card"):
            out[name] = _card_text(base, reading, excerpts, int(name[4:]))
        elif name == "step":
            out[name] = excerpts[-1]["advice"]
        elif name == "why":
            out[name] = reading_why(base, reading)
    return out


def followup_fallback(base, reading: dict) -> str:
    return " ".join(f"{ex['name']}: {ex['advice']}" for ex in _excerpts(base, reading))


def daily_fallback(excerpt: dict) -> str:
    return f"{excerpt['meaning']} {excerpt['advice']}"
