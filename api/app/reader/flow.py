"""Generation behind the SSE stream (§2, §5.1, §8): model call, section events, finalize (§2.5), saving and the
call log. Events: meta, section, text, replace, fallback, crisis, done, error. No question text is logged.

Stage 4.7: after finalize, a Spanish section that is still the model's text and speaks of the reader with a
gendered form is rewritten once (rewrite.py, rewrite_section here: budget, llm_calls purpose "rewrite"); the
rewritten answer is saved and sent as `replace` (reason "gender", or finalize's own reason when it had replaced a
section too). A failed or rejected rewrite keeps the text as streamed.

A generation runs in its own thread (Detached): the HTTP response only reads its events from a queue, so a
client that disconnects (page reload, phone asleep) stops reading but the answer is still written and saved
(§8.11); the site then restores it with GET /api/readings/{id}.
"""
import json
import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timezone
from typing import Iterator

from app import repo
from app.cards import label
from app.config import FOLLOWUP_ATTEMPTS, FOLLOWUP_LIMIT, HISTORY_LIMIT, RETRY_LIMIT, cost_usd
from app.db import DatabaseUnavailable
from app.reader import check, compose, rewrite
from app.reader.engine import Chunk, run_stream
from app.reader.finalize import finalize
from app.reader.sections import SECTION_ORDER, Event, SectionParser
from app.safety import content

log = logging.getLogger("arcana.reader")

READER_MAX_TOKENS = 4000
_END = object()


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _event(event: Event) -> str:
    if event.kind == "section":
        return sse("section", {"name": event.name})
    return sse("text", {"name": event.name, "text": event.text})


class Detached:
    """Iterates a generation that runs in its own thread; abandoning the iterator does not stop the generation."""

    def __init__(self, events: Iterator[str]):
        self._queue: queue.Queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, args=(events,), daemon=True, name="generation")
        self.thread.start()

    def _run(self, events: Iterator[str]) -> None:
        try:
            for item in events:
                self._queue.put(item)
        except Exception:  # a bug must not leave the reader waiting forever
            log.exception("generation failed")
            self._queue.put(sse("error", {"reason": "internal"}))
        finally:
            self._queue.put(_END)

    def __iter__(self):
        return self

    def __next__(self) -> str:
        item = self._queue.get()
        if item is _END:
            raise StopIteration
        return item

    def join(self, timeout: float | None = None) -> bool:
        self.thread.join(timeout)
        return not self.thread.is_alive()


def day_start(now: datetime) -> datetime:
    return datetime.combine(now.astimezone(timezone.utc).date(), time(0), tzinfo=timezone.utc)


def over_budget(ctx) -> bool:
    """§8.4: DAILY_BUDGET_USD per UTC day, summed from llm_calls; above it the card base answers."""
    with ctx.db.connect() as conn:
        spent = repo.spent_since(conn, day_start(ctx.clock()))
    if spent >= ctx.settings.daily_budget_usd:
        log.warning("daily model budget reached: %.4f USD", spent)
        return True
    return False


def guard_over_budget(ctx) -> bool:
    """§9.2: the question check has its own ceiling, GUARD_BUDGET_USD of guard calls per UTC day; it keeps working
    when DAILY_BUDGET_USD is spent, and above its own ceiling only the stop-phrases answer."""
    with ctx.db.connect() as conn:
        spent = repo.spent_since(conn, day_start(ctx.clock()), "guard")
    if spent >= ctx.settings.guard_budget_usd:
        log.warning("guard budget reached: %.4f USD", spent)
        return True
    return False


def soft_line(ctx, lang: str, group: str) -> str | None:
    return content.soft_line(ctx.texts[lang], group)


def verdict_label(ctx, reading: dict) -> str | None:
    return label(reading["verdict"], reading["lang"], ctx.cards.rules) if reading.get("verdict") else None


def crisis_answer(ctx, lang: str, cf_country: str | None, tz: str | None, violence: bool) -> dict:
    """The crisis payload with helplines for this request only (§3.2, §8.2, §8.7); the country is never stored."""
    country, source = content.resolve_country(cf_country, tz, lang)
    return content.crisis_payload(ctx.texts[lang], ctx.helplines, country, source, violence)


def shown_sections(reading: dict) -> dict | None:
    answer = reading.get("answer")
    if not answer or reading["answer_shown"] == "crisis":
        return None
    return answer["fallback"] if reading["answer_shown"] == "fallback" else answer["model"]


def has_history(reading: dict) -> bool:
    """Stage 4.3 §7: only a signed-in person's reading with a topic can have a history; guests never do."""
    return bool(reading.get("user_id") and reading.get("topic"))


def reader_history(conn, reading: dict) -> list[dict]:
    """Stage 4.3 §7: up to HISTORY_LIMIT earlier readings of the account on the reading's topic (date, question,
    headline); [] when the reading cannot have a history. Follow-ups use the same reading, so the same block."""
    if not has_history(reading):
        return []
    rows = repo.topic_history(conn, reading["user_id"], reading["topic"], reading["created_at"], reading["id"],
                              HISTORY_LIMIT)
    return [{"day": row["created_at"].astimezone(timezone.utc).date(), "question": row["question"],
             "headline": None if row["answer_shown"] == "fallback" else (shown_sections(row) or {}).get("headline")} for row in rows]


def load_history(ctx, reading: dict) -> list[dict]:
    """reader_history in a connection of its own, opened only when there can be a history: a guest follow-up
    makes no extra query."""
    if not has_history(reading):
        return []
    with ctx.db.connect() as conn:
        return reader_history(conn, reading)


def followup_text(followup: dict) -> str | None:
    answer = followup.get("answer")
    if not answer or answer.get("crisis"):  # a crisis tombstone has no answer to show (stage 4.5 review I1)
        return None
    return answer["fallback"] or answer["model"]


def stream_status(reading: dict, now: datetime) -> str:
    """pending — nobody is writing; streaming — a generation is running (wait and read again); done."""
    if reading.get("answer") is not None:
        return "done"
    started = reading.get("stream_started_at")
    return "streaming" if started and now - started < repo.STREAM_CLAIM_STALE else "pending"


def card_view(ctx, card: dict, lang: str, with_vote: bool) -> dict:
    """A drawn card with its name; in a yes/no reading with a verdict also its own vote (stage 4.5 §4)."""
    view = {**card, "name": ctx.cards.name(card["card_id"], lang)}
    if with_vote:
        view["vote"] = ctx.cards.vote(card)
    return view


def reading_view(ctx, reading: dict, owner: bool) -> dict:
    """§8.3: anyone with the link sees the cards and the answer; the question, topic and situation — the owner."""
    lang = reading["lang"]
    verdict = reading.get("verdict")
    view = {
        "id": str(reading["id"]), "lang": lang, "kind": reading["kind"], "owner": owner,
        "cards": [card_view(ctx, c, lang, verdict is not None) for c in reading["cards"]],
        "verdict": {"value": verdict, "label": verdict_label(ctx, reading)} if verdict else None,
        "soft_line": soft_line(ctx, lang, reading["guard_group"]),
    }
    if owner:
        view.update({"question": reading["question"], "topic": reading["topic"], "situation": reading["situation"],
                     "source_card_id": reading["source_card_id"], "guard_group": reading["guard_group"]})
    return view


def full_view(ctx, reading: dict, followups: list[dict], owner: bool, now: datetime) -> dict:
    shown = reading["answer_shown"]
    view = {**reading_view(ctx, reading, owner), "answer": shown_sections(reading), "answer_shown": shown,
            "status": stream_status(reading, now)}
    if owner:
        answered = [f for f in followups if followup_text(f)]
        view.update({
            "retries_left": RETRY_LIMIT - reading["retries"] if shown == "fallback" else 0,
            "followups": [{"n": f["n"], "question": f["question"], "answer": followup_text(f),
                           "soft_line": soft_line(ctx, reading["lang"], f["guard_group"])} for f in answered],
            "followups_left": followups_left(followups, reading["followup_attempts"]),
            "followup_attempts_left": max(FOLLOWUP_ATTEMPTS - reading["followup_attempts"], 0),
            # stage 4.3 §6: the owner (the account; for a guest reading, its device) also sees the diary fields
            "in_diary": reading.get("user_id") is not None,
            "outcome": reading.get("outcome"), "note": reading.get("note"),
            "created_at": reading["created_at"],  # stage 4.4b §5: "did it come true?" opens 7 days after it
        })
    return view


def followups_left(followups: list[dict], attempts: int = 0) -> int:
    """Free follow-ups left (§10.1: after them each one uses a reading). Only follow-ups that use a slot count — a
    cut or replaced answer does not (§9.4) — and never more than the attempts left of the reading (§10.2)."""
    free = max(FOLLOWUP_LIMIT - sum(1 for f in followups if f["counted"]), 0)
    return max(min(free, FOLLOWUP_ATTEMPTS - attempts), 0)


def upper_cost(model: str, tokens_in, tokens_out, max_tokens: int | None) -> float | None:
    """The price of a call; a call cut before its usage arrived (a timeout) counts as max_tokens of output, so the
    budget errs on the safe side. Callers pass max_tokens only when the call may have reached the model: a
    connection error, a wrong key or a provider 429 before any text costs nothing (м5)."""
    cost = cost_usd(model, tokens_in, tokens_out)
    if cost is None and tokens_out is None and max_tokens:
        cost = cost_usd(model, 0, max_tokens)
    return cost


def log_call(conn, ctx, reading_id, purpose: str, model: str, prompt_version: str | None, outcome,
             max_tokens: int | None = None) -> None:
    """One llm_calls row and one log line per model call (§5.4); never any text."""
    result = outcome.result
    tokens_in = result.tokens_in if result else None
    tokens_out = result.tokens_out if result else None
    stop = result.stop_reason if result and result.stop_reason else getattr(outcome, "reason", None)
    category = result.refusal_category if result else None
    reached = getattr(outcome, "reason", None) == "timeout" or getattr(outcome, "after_text", True)
    cost = upper_cost(model, tokens_in, tokens_out, max_tokens if reached else None)
    repo.log_llm_call(conn, {"reading_id": reading_id, "purpose": purpose, "model": model,
                             "prompt_version": prompt_version, "ms_first_token": outcome.ms_first_token,
                             "ms_total": outcome.ms_total, "tokens_in": tokens_in, "tokens_out": tokens_out,
                             "cost_usd": cost, "stop_reason": stop, "refusal_category": category,
                             "created_at": ctx.clock()})
    log.info("llm_call purpose=%s model=%s prompt=%s first_token_ms=%s total_ms=%s tokens_in=%s tokens_out=%s"
             " cost_usd=%s stop=%s", purpose, model, prompt_version, outcome.ms_first_token, outcome.ms_total,
             tokens_in, tokens_out, cost, stop)


def record_guard(conn, ctx, result, lang: str, day, reading_id) -> None:
    """A count per group and source and, if the model was called, one llm_calls row — never the question."""
    repo.count_guard_event(conn, day, lang, result.group, result.source)
    if result.model is not None:
        repo.log_llm_call(conn, {
            "reading_id": reading_id, "purpose": "guard", "model": result.model,
            "prompt_version": ctx.guard.prompt_version, "ms_first_token": None, "ms_total": result.ms_total,
            "tokens_in": result.tokens_in, "tokens_out": result.tokens_out,
            "cost_usd": upper_cost(result.model, result.tokens_in, result.tokens_out,
                                   ctx.guard.max_tokens if result.source == "timeout" or result.responded else None),
            "stop_reason": result.stop_reason or result.source, "refusal_category": None, "created_at": ctx.clock(),
        })


def rewrite_section(ctx, lang: str, section_name: str, text: str, *, terms, reading_id=None) -> str | None:
    """Stage 4.7: one call that rewrites a Spanish section without gendered forms for the reader (rewrite.py);
    the rewritten text, or None to keep the original — English, the daily budget spent, a database or model
    failure, or an answer that fails the checks. The call gets an llm_calls row (purpose "rewrite")."""
    if lang not in rewrite.REWRITE_LANGS:
        return None
    try:
        if over_budget(ctx):
            return None
    except DatabaseUnavailable:
        return None
    new, outcome, max_tokens = rewrite.call_rewrite(ctx.reader, lang, text, terms)
    try:
        with ctx.db.connect() as conn:
            log_call(conn, ctx, reading_id, "rewrite", ctx.reader.model, rewrite.REWRITE_VERSION, outcome, max_tokens)
    except Exception as exc:  # the database is down, or migration 006 has not run: the answer must not break
        log.warning("rewrite call not logged: %s", type(exc).__name__)
    log.info("gender rewrite of %s: %s", section_name, "taken" if new else "original kept")
    return new


def rewrite_sections(ctx, lang: str, sections: dict[str, str], terms, reading_id=None) -> dict[str, str]:
    """rewrite_section for each section at once (one call each, in parallel): {section: new text} for those
    rewritten."""
    def one(name: str) -> str | None:
        return rewrite_section(ctx, lang, name, sections[name], terms=terms, reading_id=reading_id)

    names = list(sections)
    if len(names) <= 1:
        results = [one(name) for name in names]
    else:
        with ThreadPoolExecutor(max_workers=len(names), thread_name_prefix="rewrite") as pool:
            results = list(pool.map(one, names))
    return {name: new for name, new in zip(names, results) if new}


def _meta(ctx, reading: dict, prompt_version: str | None, replay: bool) -> str:
    lang = reading["lang"]
    return sse("meta", {"reading_id": str(reading["id"]), "kind": reading["kind"], "lang": lang, "replay": replay,
                        "prompt_version": prompt_version, "soft_line": soft_line(ctx, lang, reading["guard_group"])})


def replay_reading(ctx, reading: dict, cf_country: str | None, tz: str | None) -> Iterator[str]:
    """A second request for the same reading gets the saved text (§1.1)."""
    yield _meta(ctx, reading, reading["prompt_version"], True)
    shown = reading["answer_shown"]
    if shown == "crisis":
        yield sse("crisis", crisis_answer(ctx, reading["lang"], cf_country, tz, False))
    elif shown == "fallback":
        yield sse("fallback", {"sections": shown_sections(reading), "reason": "saved",
                               "retry": reading["retries"] < RETRY_LIMIT})
    else:
        sections = shown_sections(reading)
        for name in SECTION_ORDER:
            if sections.get(name):
                yield sse("section", {"name": name})
                yield sse("text", {"name": name, "text": sections[name]})
    yield sse("done", {"answer_shown": shown})


def release_claim(ctx, reading_id) -> None:
    """Stage 4.3 §10 (м-н8): best effort — when the database is still down, the claim frees itself after
    STREAM_CLAIM_STALE."""
    try:
        with ctx.db.connect() as conn:
            repo.release_stream(conn, reading_id)
    except DatabaseUnavailable:
        log.warning("stream claim not released: the database is unavailable")


def _reading_events(ctx, reading: dict, cf_country: str | None, tz: str | None) -> Iterator[str]:
    lang, kind = reading["lang"], reading["kind"]
    if reading["answer"] is not None:
        yield from replay_reading(ctx, reading, cf_country, tz)
        return
    claimed = False
    try:
        with ctx.db.connect() as conn:
            claimed = repo.claim_stream(conn, reading["id"], ctx.clock())
            history = reader_history(conn, reading) if claimed else []
        spent = claimed and over_budget(ctx)
    except DatabaseUnavailable as exc:
        log.error("reading stream: database unavailable before the answer: %s", exc)  # stage 4.4b §9
        if claimed:
            release_claim(ctx, reading["id"])
        yield sse("error", {"reason": "db"})
        return
    if not claimed:
        yield sse("error", {"reason": "in_progress"})
        return
    prompt = ctx.prompts[("reader", lang)]
    yield _meta(ctx, reading, prompt.version, False)
    parser, outcome = SectionParser(), None
    if not spent:
        excerpts = ctx.cards.excerpts(reading["cards"], lang, reading["topic"])
        messages = compose.reader_messages(reading, excerpts, verdict_label(ctx, reading), history,
                                           compose.card_votes(reading, ctx.cards))
        for item in run_stream(ctx.reader, prompt.text, messages, READER_MAX_TOKENS,
                               ctx.settings.first_token_timeout_s):
            if isinstance(item, Chunk):
                for event in parser.feed(item.text):
                    if "crisis" not in parser.seen:  # the safety net: nothing after [[crisis]] is shown
                        yield _event(event)
            else:
                outcome = item
        for event in parser.finish():
            if "crisis" not in parser.seen:
                yield _event(event)
    streamed = parser.sections()
    final = finalize(reading, streamed, parser.seen, outcome, ctx.cards, ctx.terms,
                     ctx.texts[lang]["reader_unavailable"])
    # stage 4.7: after finalize's own replacements, a Spanish section still written by the model that speaks of
    # the reader with a gendered form is rewritten once; a failed rewrite keeps the text as it was
    live = check.live_terms(ctx.terms, lang, reading["guard_group"])
    try:
        final, rewritten = rewrite.rewrite_answer(
            final, streamed, lang, lambda todo: rewrite_sections(ctx, lang, todo, live, reading["id"]))
    except Exception:  # Fable review I4: nothing after the stream may lose the finished answer
        log.exception("gender rewrite failed: the answer stays as written")
        rewritten = {}
    if rewritten:
        log.info("reader answer: %s rewritten without gender", ", ".join(sorted(rewritten)))
    try:
        with ctx.db.connect() as conn:
            if final.shown == "crisis":
                repo.save_crisis(conn, reading["id"], ctx.reader.model, prompt.version)
                repo.count_guard_event(conn, day_start(ctx.clock()).date(), lang, "crisis", "reader")
            else:
                repo.save_answer(conn, reading["id"], final.answer, final.shown, ctx.reader.model, prompt.version)
            if outcome is not None:
                log_call(conn, ctx, reading["id"], "reader", ctx.reader.model, prompt.version, outcome,
                         READER_MAX_TOKENS)
    except DatabaseUnavailable as exc:
        log.error("reading stream: the answer was not saved: %s", exc)  # stage 4.4b §9
        release_claim(ctx, reading["id"])  # nothing was saved: the next stream may write the answer
        if final.shown == "crisis":  # the helplines need no database: the client gets them first
            yield sse("crisis", crisis_answer(ctx, lang, cf_country, tz, False))
        yield sse("error", {"reason": "db"})
        return
    if final.event == "crisis":
        yield sse("crisis", crisis_answer(ctx, lang, cf_country, tz, False))
    elif final.event:
        log.warning("reader answer %s: %s", final.event, final.reason)
        yield sse(final.event, {"sections": final.sections, "reason": final.reason,
                                "retry": final.shown == "fallback" and reading["retries"] < RETRY_LIMIT})
    if not final.length_ok:
        log.info("reader answer length out of range (%s)", kind)
    yield sse("done", {"answer_shown": final.shown})


def stream_reading(ctx, reading: dict, cf_country: str | None = None, tz: str | None = None) -> Detached:
    return Detached(_reading_events(ctx, reading, cf_country, tz))
