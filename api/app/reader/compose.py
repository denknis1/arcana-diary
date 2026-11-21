"""Model input (§2.1, §2.3) and versioned prompt files (§2.4).

Tags are in English for the model; values are in the reading's language. The person's text is HTML-escaped so it
cannot close or open tags; card meanings come only from content/cards (the reader reads only from them).
"""
import html
from dataclasses import dataclass
from pathlib import Path

from app.cards import label
from app.reader.sections import SECTION_ORDER

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
VERSION_PREFIX = "prompt-version: "
LANGS = ("en", "es")

NO_QUESTION = {"en": "(no question: read the cards as a message about where the person is now)",
               "es": "(sin pregunta: lee las cartas como un mensaje sobre el momento que vive la persona)"}
NO_PAST_QUESTION = {"en": "(no question)", "es": "(sin pregunta)"}
NOT_SPECIFIED = {"en": "not specified", "es": "no indicada"}
TOPIC_LABELS = {
    "en": {"love": "love", "work": "work", "self": "yourself", "decision": "a decision", "general": "general"},
    "es": {"love": "amor", "work": "trabajo", "self": "sobre ti", "decision": "una decisión", "general": "general"},
}
# The four /love chips approved in stage 3 (§8.5)
SITUATIONS = {
    "single": {"en": "single", "es": "sin pareja"},
    "relationship": {"en": "in a relationship", "es": "en pareja"},
    "after_breakup": {"en": "after a breakup", "es": "después de una ruptura"},
    "complicated": {"en": "it's complicated", "es": "es complicado"},
}
POSITION_LABELS = {
    "en": {"past": "past", "present": "present", "path": "where it leads", "card": "single card"},
    "es": {"past": "pasado", "present": "presente", "path": "hacia dónde va", "card": "carta única"},
}
ORIENTATION = {"en": ("upright", "reversed"), "es": ("derecha", "invertida")}
# stage 4.5 §4: the three cards of a yes/no reading have no time, each is one vote of three
ONE_OF_THREE = {"en": "one of three", "es": "una de tres"}


@dataclass(frozen=True)
class Prompt:
    name: str
    lang: str | None
    version: str
    text: str


def load_prompt(name: str, lang: str | None = None, root: Path = PROMPTS_DIR) -> Prompt:
    filename = f"{name}.{lang}.md" if lang else f"{name}.md"
    raw = (root / filename).read_text(encoding="utf-8")
    first, _, rest = raw.partition("\n")
    if not first.startswith(VERSION_PREFIX):
        raise ValueError(f"{filename}: the first line must be '{VERSION_PREFIX}<version>'")
    return Prompt(name, lang, first[len(VERSION_PREFIX):].strip(), rest.strip())


def load_prompts(root: Path = PROMPTS_DIR) -> dict[tuple[str, str | None], Prompt]:
    prompts = {("guard", None): load_prompt("guard", None, root)}
    for name in ("reader", "followup", "daily"):
        for lang in LANGS:
            prompts[(name, lang)] = load_prompt(name, lang, root)
    return prompts


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def card_votes(reading: dict, base) -> list[str] | None:
    """Stage 4.5 §4: each card's own vote, as a label in the reading's language, for a yes/no reading on three
    cards with a verdict; None otherwise (one card: its vote is the verdict; no verdict: no votes)."""
    if reading.get("verdict") is None or len(reading["cards"]) != 3:
        return None
    return [label(base.vote(card), reading["lang"], base.rules) for card in reading["cards"]]


def _position(excerpt: dict, n_cards: int, lang: str) -> str:
    if excerpt["position"] == "card" and n_cards == 3:
        return ONE_OF_THREE[lang]
    return POSITION_LABELS[lang][excerpt["position"]]


def reading_input(reading: dict, excerpts: list[dict], verdict_label: str | None,
                  votes: list[str] | None = None) -> str:
    """<verdict> only when the reading has one: a yes/no question about health, death, courts, safety or another
    person keeps kind="yes_no" but gets no verdict (§8.1), and the prompt says not to answer yes or no.
    votes — card_votes(): a "vote:" line in each card of a three-card yes/no reading (stage 4.5 §4)."""
    lang = reading["lang"]
    question, topic, situation = reading.get("question"), reading.get("topic"), reading.get("situation")
    lines = [
        f'<reading kind="{reading["kind"]}" lang="{lang}" guard_group="{reading["guard_group"]}">',
        f"<question>{_escape(question) if question else NO_QUESTION[lang]}</question>",
        f"<topic>{TOPIC_LABELS[lang][topic] if topic else NOT_SPECIFIED[lang]}</topic>",
        f"<situation>{SITUATIONS[situation][lang] if situation else NOT_SPECIFIED[lang]}</situation>",
        f'<cards count="{len(excerpts)}">',
    ]
    for i, ex in enumerate(excerpts, 1):
        lines += [
            f'<card n="{i}" position="{_position(ex, len(excerpts), lang)}"'
            f' orientation="{ORIENTATION[lang][int(ex["reversed"])]}">',
            f"name: {ex['name']}",
            f"keywords: {', '.join(ex['keywords'])}",
            f"meaning: {ex['meaning']}",
        ]
        if "love" in ex:
            lines.append(f"love: {ex['love']}")
        lines.append(f"advice: {ex['advice']}")
        if votes:
            lines.append(f"vote: {votes[i - 1]}")
        lines.append("</card>")
    lines.append("</cards>")
    if verdict_label:
        lines.append(f'<verdict value="{reading["verdict"]}">{verdict_label}</verdict>')
    lines.append("</reading>")
    return "\n".join(lines)


def history_block(history: list[dict], lang: str) -> str:
    """Stage 4.3 §7: earlier readings on the same topic as background, oldest first — the date, the question and
    the headline only (never a note or an outcome). The person's text is escaped like the question."""
    lines = ["<history>"]
    for item in history:
        question = _escape(item["question"]) if item.get("question") else NO_PAST_QUESTION[lang]
        lines += [f'<past date="{item["day"].isoformat()}">', f"<past_question>{question}</past_question>",
                  f"<past_headline>{_escape(item.get('headline') or '')}</past_headline>", "</past>"]
    lines.append("</history>")
    return "\n".join(lines)


def _with_history(content: str, history: list[dict] | None, lang: str) -> str:
    return f"{history_block(history, lang)}\n{content}" if history else content


def reader_messages(reading: dict, excerpts: list[dict], verdict_label: str | None,
                    history: list[dict] | None = None, votes: list[str] | None = None) -> list[dict]:
    content = _with_history(reading_input(reading, excerpts, verdict_label, votes), history, reading["lang"])
    return [{"role": "user", "content": content}]


def answer_text(sections: dict[str, str]) -> str:
    return "\n\n".join(sections[name] for name in SECTION_ORDER if sections.get(name))


def followup_messages(reading: dict, excerpts: list[dict], verdict_label: str | None, first_answer: str,
                      previous: list[tuple[str, str]], question: str, group: str,
                      history: list[dict] | None = None, votes: list[str] | None = None) -> list[dict]:
    """§2.3: the reading (after the same <history> as the reading had, stage 4.3 §7), the first answer, earlier
    follow-ups, then the new question — no new cards."""
    first = _with_history(reading_input(reading, excerpts, verdict_label, votes), history, reading["lang"])
    messages = [{"role": "user", "content": first}, {"role": "assistant", "content": first_answer}]
    for earlier_question, earlier_answer in previous:
        messages += [{"role": "user", "content": f"<followup>{_escape(earlier_question)}</followup>"},
                     {"role": "assistant", "content": earlier_answer}]
    messages.append({"role": "user", "content": f'<followup guard_group="{group}">{_escape(question)}</followup>'})
    return messages


def daily_messages(excerpt: dict, lang: str) -> list[dict]:
    content = "\n".join([
        f'<daily lang="{lang}">',
        f'<card orientation="{ORIENTATION[lang][int(excerpt["reversed"])]}">',
        f"name: {excerpt['name']}",
        f"keywords: {', '.join(excerpt['keywords'])}",
        f"meaning: {excerpt['meaning']}",
        f"advice: {excerpt['advice']}",
        "</card>",
        "</daily>",
    ])
    return [{"role": "user", "content": content}]
