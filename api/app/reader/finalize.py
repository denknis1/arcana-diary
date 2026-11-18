"""What the person sees once the stream ends (§2.5, §5.1, §8.6, §8.10). One pure function, used by the API
stream and by the evals, so the evals grade exactly what a person would see.

- [[crisis]] from the reader (its safety net): no reading, the crisis answer instead.
- No usable text (timeout or error before text, refusal, empty, over budget): the card base answer.
- A cut stream (an error after text, or stop_reason max_tokens): the section being written when it stopped is
  dropped, written sections stay, the missing ones come from the base.
- Sections the reading does not ask for are dropped (no `why` without a verdict, no synthesis for one card).
- A live-dictionary hit in the body: the card base answer is shown; both texts are kept.
- A bad `why` written by the model: only `why` is replaced by the fixed line (a `why` filled from the base
  after a cut is not checked, so the reason stays "cut").
- A yes/no reading without a verdict whose headline still sounds like one ("Yes, …", "Probably not"): only the
  headline is replaced by the card's keywords.
"""
from dataclasses import dataclass

from app.reader import check, fallback
from app.reader.engine import Failed
from app.reader.sections import required_sections

EMPTY = {"model": None, "fallback": None}


@dataclass(frozen=True)
class Final:
    shown: str               # "model" | "fallback" | "crisis"
    answer: dict             # stored: {"model": sections | None, "fallback": sections | None}
    sections: dict | None    # what is on screen now (None for crisis)
    event: str | None        # SSE event after the stream: None, "replace", "fallback" or "crisis"
    reason: str | None       # timeout, error, refusal, empty, budget, banned, why, headline, cut, sections, crisis
    length_ok: bool = True


def finalize(reading: dict, streamed: dict[str, str], seen: list[str], outcome, base, terms, notice: str) -> Final:
    """streamed — SectionParser.sections(); seen — SectionParser.seen; outcome — engine Finished / Failed, or
    None when the model was not called (the daily budget is spent)."""
    lang, kind = reading["lang"], reading["kind"]
    with_why = reading.get("verdict") is not None
    if "crisis" in seen:
        return Final("crisis", EMPTY, None, "crisis", "crisis")
    required = required_sections(kind, with_why)
    written = {name: text for name, text in streamed.items() if name in required}
    failed = isinstance(outcome, Failed)
    cut = (failed and outcome.after_text) or (not failed and outcome is not None
                                             and outcome.result.stop_reason == "max_tokens")
    if cut and seen:
        written.pop(seen[-1], None)
    if outcome is None:
        reason = "budget"
    elif failed and (outcome.reason == "refusal" or not outcome.after_text):
        reason = outcome.reason  # refusal, timeout or error before any text
    elif not written:
        reason = outcome.reason if failed else "empty"
    else:
        reason = None
    if reason:
        sections = fallback.fallback_answer(base, reading, notice)
        return Final("fallback", {"model": None, "fallback": sections}, sections, "fallback", reason)
    filled = fallback.fill_missing(written, base, reading)
    result = check.check_answer(filled, kind, lang, terms, with_why)
    if not result.body_ok:
        sections = fallback.fallback_answer(base, reading, notice)
        return Final("fallback", {"model": filled, "fallback": sections}, sections, "replace", "banned",
                     result.length_ok)
    final = dict(filled)
    why_replaced = with_why and bool(written.get("why")) and not result.why_ok
    if why_replaced:
        final["why"] = fallback.why_line(base, reading["cards"][0], lang)
    headline_replaced = kind == "yes_no" and not with_why and check.verdict_in(final.get("headline", ""), lang)
    if headline_replaced:
        final["headline"] = fallback.headline_line(base, reading)
    if final == streamed:
        return Final("model", {"model": final, "fallback": None}, final, None, None, result.length_ok)
    reason = "why" if why_replaced else "headline" if headline_replaced else "cut" if cut else "sections"
    return Final("model", {"model": final, "fallback": None}, final, "replace", reason, result.length_ok)
