"""Answer check after the stream (§2.5, §8.10).

- Live answers are checked with reader_banned_terms.json: claims and predictions ("will come back", "he feels",
  "te extraña"), not the names of topics — the card base's dictionary (banned_terms.json) is for the base only,
  so "I can't speak to the pregnancy itself" or "No puedo hablar del embarazo" does not replace an answer.
- A term in a clause that already says the cards cannot know ("The cards can't tell you what he feels",
  "No sé si piensa en ti", "Nadie puede asegurar que volverá") is not a claim: it is reported as `negated`,
  not as a hit. A clause ends at . , ! ? ; : — or at but / pero / aunque.
- Stage 4.6 (owner decision 1, Fable I5): in group ok the reader may be confident about the person's own life,
  so "will happen" / «llegará alguien» are not in the `en` / `es` lists. They stay in `en_redirect` /
  `es_redirect`, which live_terms() adds for a question without an outcome (any group but ok; for a follow-up,
  the stricter of the reading's and the follow-up's group) and for the card of the day (no group).
- In `why`, verdict words used as the answer are forbidden ("Yes, …", "the answer is no", "sí", "quizá"),
  not every "no" ("There is no rush", "no hay prisa").
- The length (§2.2) is logged only.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from app.terms import find_banned, load_terms

READER_TERMS = Path(__file__).resolve().parent / "reader_banned_terms.json"
VERDICT_RULES = {
    "en": [r"(?<!\bcan )(?<!\bto )\b(say|says|lean|leans|point|points)\s+(to\s+)?(a\s+)?yes\b(?!\s+to\b)",
           r"^\W*yes\b", r"[.!?]\s+yes\s*[,.!:;—–]", r"\bthe answer is (a )?yes\b", r"\bit'?s a yes\b",
           r"\btowards? (a )?yes\b", r"^\W*no\s*[,.!:;—–]", r"\bthe answer is (a )?no\b", r"\bit'?s a no\b",
           r"\btowards? (a )?no\b(?! one)", r"\bprobably not\b", r"\bnot (yet )?clear\b", r"\bunclear\b",
           r"\bmaybe\b"],
    "es": [r"(?<!\ben )(?<!\bpara )\bsí\b(?! mism)", r"^\W*no\s*[,.!:;—–]", r"\bla respuesta es (sí|no)\b",
           r"\bes un (sí|no)\b", r"\bhacia (el|un) (sí|no)\b", r"\bprobablemente no\b", r"\bmás bien no\b",
           r"\bno está clar[oa]\b", r"\bquizás?\b", r"\btal vez\b"],
}
VERDICT_PATTERNS = {lang: [(rule, re.compile(rule, re.IGNORECASE)) for rule in rules]
                    for lang, rules in VERDICT_RULES.items()}
# Explicit "cannot know / cannot tell / cannot promise" phrasing before a term in the same clause (В14 of the
# re-review). A bare no / nadie / nothing / nobody is NOT enough ("No dudes que volverá", "Nobody else matters
# because he misses you" are claims).
NEGATION_RULES = {
    "en": r"\b((can['’]t|cannot|can not|couldn['’]t|could not)\s+(\w+\s+)?(tell|know|say|promise|predict|guarantee"
          r"|be sure)"
          r"|(can['’]t|cannot|can not)\s+speak to (whether|if)"
          r"|(no one|nobody)\s+can\s+(\w+\s+)?(tell|know|say|promise|predict|guarantee|be sure)"
          r"|nothing\s+(here\s+|in (the|this) (cards?|spread)\s+)?(says|shows|tells|promises|guarantees)"
          r"|there['’]?s no way to"
          r"|((don['’]t|do not|doesn['’]t|does not) know|not sure)\s+(if|whether|what|when))\b",
    "es": r"\b(no\s+(sé\s+(si|qué|lo que|cuándo)|se sabe|sabemos|se puede saber|se puede decir|puedo saber"
          r"|puedo decir|puedo asegurar|puedo prometer|podemos saber|pueden decir\w*|pueden saber|puede decir\w*"
          r"|puede saber|hay (forma|manera) de saber)"
          r"|nadie (puede|podría) (saber|decir|asegurar|prometer|predecir|garantizar|adivinar)"
          r"|nadie sabe\s+(si|qué|lo que|cuándo)|nada (dice|muestra|asegura|garantiza))(?!\w)",
}
NEGATION = {lang: re.compile(rule, re.IGNORECASE) for lang, rule in NEGATION_RULES.items()}
_CLAUSE_END = re.compile(r"[.,!?;:—–\n]|\b(but|pero|aunque)\b", re.IGNORECASE)
WORD_LIMITS = {1: (90, 150), 3: (180, 250)}
FOLLOWUP_WORDS = (60, 120)
DAILY_WORDS = (60, 100)
_WORD = re.compile(r"[\w’'-]+")


def load_reader_terms(path: Path = READER_TERMS) -> dict:
    return load_terms(path)


def live_terms(terms: dict, lang: str, *groups: str | None) -> list:
    """The live dictionary for `lang`: the `lang` list, plus `<lang>_redirect` unless every group given is ok.
    No group (the card of the day) is strict too."""
    strict = not groups or any(group != "ok" for group in groups)
    return terms[lang] + (terms.get(f"{lang}_redirect", []) if strict else [])


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


@dataclass(frozen=True)
class CheckResult:
    body_ok: bool
    why_ok: bool
    banned: tuple[str, ...]
    words: int
    length_ok: bool
    negated: tuple[str, ...] = ()


def _clause_before(text: str, start: int) -> str:
    begin = 0
    for m in _CLAUSE_END.finditer(text, 0, start):
        begin = m.end()
    return text[begin:start]


def find_claims(text: str, terms, lang: str) -> tuple[list[str], list[str]]:
    """(hits, negated): a term counts as a hit if at least one of its matches is not negated in its clause."""
    hits, negated = [], []
    for term, rx in terms:
        starts = [m.start() for m in rx.finditer(text)]
        if not starts:
            continue
        if any(not NEGATION[lang].search(_clause_before(text, start)) for start in starts):
            hits.append(term)
        else:
            negated.append(term)
    return hits, negated


def verdict_in(text: str, lang: str) -> bool:
    return bool(find_banned(text, VERDICT_PATTERNS[lang]))


def why_ok(why: str, lang: str, terms) -> bool:
    return bool(why) and not verdict_in(why, lang) and not find_claims(why, terms, lang)[0]


def check_answer(sections: dict[str, str], kind: str, lang: str, terms, with_why: bool,
                 cards: int | None = None) -> CheckResult:
    """cards: how many were drawn (stage 4.5 §4); None — the kind's own number. Only the length depends on it."""
    body = [text for name, text in sections.items() if name != "why" and text]
    found = [find_claims(text, terms, lang) for text in body]
    hits = sorted({term for h, _ in found for term in h})
    negated = sorted({term for _, n in found for term in n} - set(hits))
    why_good = why_ok(sections.get("why", ""), lang, terms) if with_why else True
    words = sum(word_count(text) for text in body)
    low, high = WORD_LIMITS[cards or (3 if kind == "three" else 1)]
    return CheckResult(not hits, why_good, tuple(hits), words, low <= words <= high, tuple(negated))


def banned_in(text: str, terms, lang: str) -> list[str]:
    return find_claims(text, terms, lang)[0]


def length_ok(text: str, limits: tuple[int, int]) -> bool:
    return limits[0] <= word_count(text) <= limits[1]
