"""SQL for readings, follow-ups, the daily card, guard counts and the LLM call log (spec §4.3).

Every function takes a connection from Database.connect(); the caller owns the transaction.
"""
from datetime import timedelta

from psycopg.types.json import Jsonb

STREAM_CLAIM_STALE = timedelta(seconds=180)
EMPTY_ANSWER = {"model": None, "fallback": None}


def insert_reading(conn, reading: dict) -> None:
    conn.execute(
        "INSERT INTO readings (id, guest_id, lang, kind, question, topic, situation, source_card_id, cards, seed,"
        " verdict, guard_group, created_at, expires_at)"
        " VALUES (%(id)s, %(guest_id)s, %(lang)s, %(kind)s, %(question)s, %(topic)s, %(situation)s,"
        " %(source_card_id)s, %(cards)s, %(seed)s, %(verdict)s, %(guard_group)s, %(created_at)s, %(expires_at)s)",
        {**reading, "cards": Jsonb(reading["cards"])})


def get_reading(conn, reading_id, now) -> dict | None:
    return conn.execute("SELECT * FROM readings WHERE id = %s AND (expires_at IS NULL OR expires_at > %s)",
                        (reading_id, now)).fetchone()


def claim_stream(conn, reading_id, now) -> bool:
    """One generation writes a reading; a claim older than STREAM_CLAIM_STALE is free again (a crashed process)."""
    row = conn.execute(
        "UPDATE readings SET stream_started_at = %s WHERE id = %s AND answer IS NULL"
        " AND (stream_started_at IS NULL OR stream_started_at < %s) RETURNING id",
        (now, reading_id, now - STREAM_CLAIM_STALE)).fetchone()
    return row is not None


def save_answer(conn, reading_id, answer: dict, shown: str, model: str | None, prompt_version: str) -> None:
    conn.execute("UPDATE readings SET answer = %s, answer_shown = %s, model = %s, prompt_version = %s,"
                 " stream_started_at = NULL WHERE id = %s",
                 (Jsonb(answer), shown, model, prompt_version, reading_id))


def save_crisis(conn, reading_id, model: str | None, prompt_version: str) -> None:
    """The reader saw signs of crisis (§8.6): keep only the mark and the language, drop the question (§3.4)."""
    conn.execute("UPDATE readings SET question = NULL, topic = NULL, situation = NULL, answer = %s,"
                 " answer_shown = 'crisis', model = %s, prompt_version = %s, stream_started_at = NULL WHERE id = %s",
                 (Jsonb(EMPTY_ANSWER), model, prompt_version, reading_id))


def reset_for_retry(conn, reading_id, retry_limit: int) -> int | None:
    """Only a fallback answer with retries left is reset; None — someone else got there first or no retries."""
    row = conn.execute("UPDATE readings SET answer = NULL, answer_shown = NULL, stream_started_at = NULL,"
                       " retries = retries + 1 WHERE id = %s AND answer_shown = 'fallback' AND retries < %s"
                       " RETURNING retries", (reading_id, retry_limit)).fetchone()
    return row["retries"] if row else None


def list_followups(conn, reading_id) -> list[dict]:
    return conn.execute("SELECT * FROM followups WHERE reading_id = %s ORDER BY n", (reading_id,)).fetchall()


def insert_followup(conn, followup: dict) -> bool:
    row = conn.execute("INSERT INTO followups (id, reading_id, n, question, guard_group, paid_day, created_at)"
                       " VALUES (%(id)s, %(reading_id)s, %(n)s, %(question)s, %(guard_group)s, %(paid_day)s,"
                       " %(created_at)s) ON CONFLICT (reading_id, n) DO NOTHING RETURNING id",
                       {"guard_group": "ok", "paid_day": None, **followup}).fetchone()
    return row is not None


def save_followup_answer(conn, followup_id, answer: dict, model: str | None, counted: bool = True) -> bool:
    """counted=False: a cut or replaced answer, kept with both texts, does not use a free follow-up (§9.4).

    False when the row is gone (freed as stale while its generation was still running): nothing is saved.
    """
    row = conn.execute("UPDATE followups SET answer = %s, model = %s, counted = %s WHERE id = %s RETURNING id",
                       (Jsonb(answer), model, counted, followup_id)).fetchone()
    return row is not None


def delete_followup(conn, followup_id) -> bool:
    """True when this call deleted the row; False when it was already gone (so nobody refunds twice)."""
    row = conn.execute("DELETE FROM followups WHERE id = %s RETURNING id", (followup_id,)).fetchone()
    return row is not None


def delete_stale_followups(conn, reading_id, before) -> list:
    """A follow-up still without an answer after STREAM_CLAIM_STALE was cut by a crash: free its slot.

    Returns paid_day of every deleted row (None for a free one), so the caller gives paid readings back (§10.1).
    """
    rows = conn.execute("DELETE FROM followups WHERE reading_id = %s AND answer IS NULL AND created_at < %s"
                        " RETURNING paid_day", (reading_id, before)).fetchall()
    return [r["paid_day"] for r in rows]


def delete_all_stale_followups(conn, before) -> list[tuple]:
    """Housekeeping: every unanswered follow-up older than `before` (cut by a restart), across readings.

    Returns (guest_id, paid_day) per deleted row; RETURNING hands each paid row to exactly one caller.
    """
    rows = conn.execute("DELETE FROM followups f USING readings r WHERE r.id = f.reading_id"
                        " AND f.answer IS NULL AND f.created_at < %s RETURNING r.guest_id, f.paid_day",
                        (before,)).fetchall()
    return [(r["guest_id"], r["paid_day"]) for r in rows]


def get_daily_cache(conn, card_id: str, reversed_: bool, lang: str, day) -> dict | None:
    return conn.execute("SELECT * FROM daily_cache WHERE card_id = %s AND reversed = %s AND lang = %s AND day = %s",
                        (card_id, reversed_, lang, day)).fetchone()


def put_daily_cache(conn, row: dict) -> None:
    conn.execute("INSERT INTO daily_cache (card_id, reversed, lang, day, text, model, prompt_version)"
                 " VALUES (%(card_id)s, %(reversed)s, %(lang)s, %(day)s, %(text)s, %(model)s, %(prompt_version)s)"
                 " ON CONFLICT (card_id, reversed, lang, day) DO NOTHING", row)


def cached_daily_keys(conn, day) -> set[tuple[str, bool, str]]:
    rows = conn.execute("SELECT card_id, reversed, lang FROM daily_cache WHERE day = %s", (day,)).fetchall()
    return {(r["card_id"], r["reversed"], r["lang"]) for r in rows}


def record_daily_draw(conn, guest_id, day, card_id: str, reversed_: bool) -> None:
    conn.execute("INSERT INTO daily_draws (guest_id, day, card_id, reversed) VALUES (%s, %s, %s, %s)"
                 " ON CONFLICT (guest_id, day) DO NOTHING", (guest_id, day, card_id, reversed_))


def count_guard_event(conn, day, lang: str, group: str, source: str) -> None:
    conn.execute("INSERT INTO guard_events (day, lang, guard_group, source, count) VALUES (%s, %s, %s, %s, 1)"
                 " ON CONFLICT (day, lang, guard_group, source) DO UPDATE SET count = guard_events.count + 1",
                 (day, lang, group, source))


def log_llm_call(conn, call: dict) -> None:
    conn.execute("INSERT INTO llm_calls (reading_id, purpose, model, prompt_version, ms_first_token, ms_total,"
                 " tokens_in, tokens_out, cost_usd, stop_reason, refusal_category, created_at)"
                 " VALUES (%(reading_id)s, %(purpose)s, %(model)s, %(prompt_version)s, %(ms_first_token)s,"
                 " %(ms_total)s, %(tokens_in)s, %(tokens_out)s, %(cost_usd)s, %(stop_reason)s,"
                 " %(refusal_category)s, %(created_at)s)", call)


def spent_since(conn, since, purpose: str | None = None) -> float:
    """Model spend in USD since a moment: all calls (DAILY_BUDGET_USD, §8.4) or one purpose ("guard":
    GUARD_BUDGET_USD, §9.2); calls without a price count as 0."""
    row = conn.execute("SELECT coalesce(sum(cost_usd), 0) AS usd FROM llm_calls WHERE created_at >= %s"
                       " AND (%s::text IS NULL OR purpose = %s)", (since, purpose, purpose)).fetchone()
    return float(row["usd"])
