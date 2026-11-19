"""Follow-up generation (§2.3, §8, §9.4): the same cards, the first answer, earlier follow-ups and the new
question; plain text, 60–120 words. It runs Detached like the reading, so a disconnect does not lose the answer.

- A follow-up that fails without text (no text, refusal, budget spent) is deleted.
- A cut answer or a live-dictionary hit: the card base line is shown, both texts are kept, and the follow-up does
  not use one of the two free slots (counted = false, §9.4). FOLLOWUP_ATTEMPTS bounds the retries (§9.2, §10.2).
- A paid follow-up (paid_day set, §10.1) that fails either way gives its reading back to the guest's day; the
  done event of a paid follow-up says whether the reading was used (used_reading).
- The reader's safety net: an answer with [[crisis]] anywhere is never kept; the follow-up is deleted and the
  crisis answer is sent (the site clears any text it already showed). A tail that may still become the marker
  ("[", "[[cri") is held back until it is clear, so the marker itself is never sent; after it nothing more is sent.
  Other brackets ("Try this [a small step] today") stream as usual (м3).
- м10: a follow-up without an answer older than 180 s is freed by the next request even if its generation is still
  running (a refund for a paid one). Such a generation finds its row gone: it refunds nothing more and saves
  nothing; if it ends well, the person still watching sees the answer and done says used_reading = false.
"""
import logging
import re
from typing import Iterator

from app import limits, repo
from app.config import FOLLOWUP_ATTEMPTS
from app.db import DatabaseUnavailable
from app.reader import check, compose, fallback
from app.reader.engine import Chunk, Failed, run_stream
from app.reader.flow import (Detached, crisis_answer, day_start, followup_text, followups_left, load_history,
                             log_call, over_budget, shown_sections, soft_line, sse, verdict_label)

log = logging.getLogger("arcana.reader")

FOLLOWUP_MAX_TOKENS = 2000
CRISIS_MARK = re.compile(r"\[\[\s*crisis\s*\]\]", re.IGNORECASE)
PARTIAL_MARK = re.compile(r"\[(?:\[\s*(?:c(?:r(?:i(?:s(?:i(?:s\s*\]?)?)?)?)?)?)?)?$", re.IGNORECASE)  # a start of it


def _followup_events(ctx, reading: dict, followup: dict, previous: list[dict], group: str,
                     cf_country: str | None, tz: str | None) -> Iterator[str]:
    lang = reading["lang"]
    prompt = ctx.prompts[("followup", lang)]
    n = followup["n"]
    paid = followup.get("paid_day") is not None
    attempts_left = FOLLOWUP_ATTEMPTS - followup.get("attempts", 0)
    free = followups_left(previous)  # free follow-ups before this one; 0 for a paid one
    left, left_after = min(free, attempts_left), min(max(free - 1, 0), attempts_left)

    def done(shown: str, used: bool) -> str:
        data = {"answer_shown": shown, "followups_left": left_after if used and not paid else left,
                "followup_attempts_left": attempts_left}
        return sse("done", {**data, "used_reading": used} if paid else data)

    yield sse("meta", {"reading_id": str(reading["id"]), "followup": n, "replay": False, "paid": paid,
                       "prompt_version": prompt.version, "soft_line": soft_line(ctx, lang, group)})
    try:
        spent = over_budget(ctx)
        history = load_history(ctx, reading)  # stage 4.3 §7: the same block as the reading had
    except DatabaseUnavailable:
        yield sse("error", {"reason": "db"})
        return
    yield sse("section", {"name": "followup"})
    parts, outcome, held, crisis = [], None, "", False
    if not spent:
        excerpts = ctx.cards.excerpts(reading["cards"], lang, reading["topic"])
        earlier = [(f["question"], followup_text(f)) for f in previous if followup_text(f)]
        messages = compose.followup_messages(reading, excerpts, verdict_label(ctx, reading),
                                             compose.answer_text(shown_sections(reading)), earlier,
                                             followup["question"], group, history)
        for item in run_stream(ctx.reader, prompt.text, messages, FOLLOWUP_MAX_TOKENS,
                               ctx.settings.first_token_timeout_s):
            if not isinstance(item, Chunk):
                outcome = item
                continue
            parts.append(item.text)
            if crisis:
                continue
            if CRISIS_MARK.search("".join(parts)):  # on any line, also split between chunks
                crisis = True
                continue
            held += item.text
            tail = PARTIAL_MARK.search(held)  # a tail that may still become [[crisis]]
            send, held = (held[:tail.start()], held[tail.start():]) if tail else (held, "")
            if send:
                yield sse("text", {"name": "followup", "text": send})
        if not crisis and held:
            yield sse("text", {"name": "followup", "text": held})
    text = "".join(parts).strip()
    failed = spent or not text or (isinstance(outcome, Failed) and outcome.reason == "refusal")
    cut = isinstance(outcome, Failed) or (outcome is not None and not isinstance(outcome, Failed)
                                          and outcome.result.stop_reason == "max_tokens")
    answer, replace = None, False
    if not crisis and not failed:
        replace = cut or bool(check.banned_in(text, ctx.terms[lang], lang))
        answer = {"model": text, "fallback": fallback.followup_fallback(ctx.cards, reading) if replace else None}
        if not check.length_ok(text, check.FOLLOWUP_WORDS):
            log.info("follow-up length out of range: %s words", check.word_count(text))
    gone = False  # м10: the row was freed as stale while this generation ran; whoever deleted it did the refund
    try:
        with ctx.db.connect() as conn:
            if outcome is not None:
                log_call(conn, ctx, reading["id"], "followup", ctx.reader.model, prompt.version, outcome,
                         FOLLOWUP_MAX_TOKENS)
            if answer is None:
                gone = not repo.delete_followup(conn, followup["id"])
                if crisis:
                    repo.count_guard_event(conn, day_start(ctx.clock()).date(), lang, "crisis", "reader")
            else:
                gone = not repo.save_followup_answer(conn, followup["id"], answer, ctx.reader.model, counted=not replace)
            # §10.1: a failed paid follow-up gives back its reading, once: only the call that removed the row
            if paid and not crisis and not gone and (answer is None or replace):
                limits.give_back_slot(conn, limits.owner_quota(reading).subject, followup["paid_day"])
    except DatabaseUnavailable:
        if crisis:  # the helplines need no database: the client gets them first (as in the reading flow)
            yield sse("crisis", crisis_answer(ctx, lang, cf_country, tz, False))
        yield sse("error", {"reason": "db"})
        return
    if crisis:
        yield sse("crisis", crisis_answer(ctx, lang, cf_country, tz, False))
        yield done("crisis", paid and not gone)  # §9.5: the reader's marker uses the paid reading (no row, nothing to refund)
        return
    if answer is None:
        reason = "budget" if spent else (outcome.reason if isinstance(outcome, Failed) else "empty")
        yield sse("fallback", {"sections": {"followup": ctx.texts[lang]["followup_unavailable"]}, "reason": reason,
                               "retry": False})
        yield done("fallback", False)
        return
    if replace:
        yield sse("replace", {"sections": {"followup": answer["fallback"]}, "reason": "cut" if cut else "banned",
                              "retry": False})
        yield done("fallback", False)
        return
    yield done("model", not gone)


def stream_followup(ctx, reading: dict, followup: dict, previous: list[dict], group: str,
                    cf_country: str | None = None, tz: str | None = None) -> Detached:
    return Detached(_followup_events(ctx, reading, followup, previous, group, cf_country, tz))
