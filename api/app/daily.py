"""The card of the day (§2.6, §8.8). Texts are written ahead by a background job, never during a request.

- One text per (card, orientation, language, day): 78 × 2 × 2 = 312 a day. The day is the visitor's local day,
  the same day that picks the card, so the text never changes before local midnight. Local days span
  yesterday..tomorrow in UTC, so the job keeps those three days filled — today first, then tomorrow, then
  yesterday; the first start writes 936 texts (≈ $0.30), afterwards 312 a day (≈ $0.10).
- The job runs at start and every DAILY_JOB_INTERVAL_S; it writes only missing texts, so a failed or rejected
  text is retried on the next run, not by a request. Over the daily budget, or after FAILURES_IN_A_ROW failed
  calls in a row (a dead key, an empty balance), it stops until the next run.
- A request reads the cache; on a miss it gets the card's meaning and advice from the base (source "fallback").
"""
import asyncio
import logging
from datetime import date, timedelta

from app import repo
from app.cards import LANGS
from app.limits import utc_day
from app.reader import check, compose, fallback
from app.reader.engine import Chunk, Finished, run_stream
from app.reader.flow import log_call, over_budget

log = logging.getLogger("arcana.daily")

DAILY_MAX_TOKENS = 2000
FAILURES_IN_A_ROW = 5


def daily_dates(now) -> list[date]:
    """Today first: right after the first start, the texts people see now are written first."""
    today = utc_day(now)
    return [today, today + timedelta(days=1), today - timedelta(days=1)]


def _excerpt(ctx, card_id: str, reversed_: bool, lang: str) -> dict:
    [excerpt] = ctx.cards.excerpts([{"card_id": card_id, "position": "card", "reversed": reversed_}], lang, None)
    return excerpt


def generate_one(ctx, card_id: str, reversed_: bool, lang: str, day: date) -> bool:
    """One model call; the text is cached only if it is complete and passes the live-answer dictionary."""
    prompt = ctx.prompts[("daily", lang)]
    parts, outcome = [], None
    for item in run_stream(ctx.reader, prompt.text, compose.daily_messages(_excerpt(ctx, card_id, reversed_, lang),
                                                                           lang),
                           DAILY_MAX_TOKENS, ctx.settings.first_token_timeout_s):
        if isinstance(item, Chunk):
            parts.append(item.text)
        else:
            outcome = item
    text = "".join(parts).strip()
    usable = (bool(text) and isinstance(outcome, Finished) and outcome.result.stop_reason != "max_tokens"
              and not check.banned_in(text, check.live_terms(ctx.terms, lang), lang))  # no group: strict
    with ctx.db.connect() as conn:
        log_call(conn, ctx, None, "daily", ctx.reader.model, prompt.version, outcome, DAILY_MAX_TOKENS)
        if usable:
            repo.put_daily_cache(conn, {"card_id": card_id, "reversed": reversed_, "lang": lang, "day": day,
                                        "text": text, "model": ctx.reader.model, "prompt_version": prompt.version})
    return usable


def fill_daily_cache(ctx, day: date, card_ids=None) -> dict:
    card_ids = card_ids or ctx.cards.order
    with ctx.db.connect() as conn:
        have = repo.cached_daily_keys(conn, day)
    todo = [(c, r, lang) for c in card_ids for r in (False, True) for lang in LANGS if (c, r, lang) not in have]
    counts = {"written": 0, "failed": 0, "budget": False, "stopped": False}
    in_a_row = 0
    for card_id, reversed_, lang in todo:
        if over_budget(ctx):
            counts["budget"] = True
            break
        ok = generate_one(ctx, card_id, reversed_, lang, day)
        counts["written" if ok else "failed"] += 1
        in_a_row = 0 if ok else in_a_row + 1
        if in_a_row >= FAILURES_IN_A_ROW:
            log.warning("daily cache %s: %s failed calls in a row, stopping until the next run", day, in_a_row)
            counts["stopped"] = True
            break
    if todo:
        log.info("daily cache %s: %s", day, counts)
    return counts


def daily_text(ctx, card_id: str, reversed_: bool, lang: str, day: date) -> dict:
    with ctx.db.connect() as conn:
        cached = repo.get_daily_cache(conn, card_id, reversed_, lang, day)
    if cached:
        return {"text": cached["text"], "source": "cache", "prompt_version": cached["prompt_version"]}
    return {"text": fallback.daily_fallback(_excerpt(ctx, card_id, reversed_, lang)), "source": "fallback",
            "prompt_version": None}


async def daily_loop(ctx, interval_s: float, card_ids=None) -> None:
    while True:
        for day in daily_dates(ctx.clock()):
            try:
                counts = await asyncio.to_thread(fill_daily_cache, ctx, day, card_ids)
            except Exception:  # a failed run must not stop the loop or the API
                log.exception("daily cache run failed")
                continue
            if counts["budget"] or counts["stopped"]:
                break  # the other days would fail the same way
        await asyncio.sleep(interval_s)
