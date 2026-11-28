"""SQL for readings, follow-ups, the daily card, guard counts and the LLM call log (spec §4.3).

Every function takes a connection from Database.connect(); the caller owns the transaction.
"""
from datetime import timedelta

from psycopg.types.json import Jsonb

STREAM_CLAIM_STALE = timedelta(seconds=180)
EMPTY_ANSWER = {"model": None, "fallback": None}


def insert_reading(conn, reading: dict) -> bool:
    """user_id: the account of a signed-in person (spec 4.3 §5); without it the reading is a guest's.
    guard_source: GuardResult.source of the question check (migration 003); None without a question.
    request_id: the site's request number (migration 005), or None. False when the owner already has a reading
    with this request_id (a parallel repeat of the same request won): nothing is inserted."""
    row = conn.execute(
        "INSERT INTO readings (id, guest_id, user_id, lang, kind, question, topic, situation, source_card_id, cards,"
        " seed, verdict, guard_group, guard_source, request_id, created_at, expires_at)"
        " VALUES (%(id)s, %(guest_id)s, %(user_id)s, %(lang)s, %(kind)s, %(question)s, %(topic)s, %(situation)s,"
        " %(source_card_id)s, %(cards)s, %(seed)s, %(verdict)s, %(guard_group)s, %(guard_source)s, %(request_id)s,"
        " %(created_at)s, %(expires_at)s) ON CONFLICT DO NOTHING RETURNING id",
        {"user_id": None, "guard_source": None, "request_id": None, **reading,
         "cards": Jsonb(reading["cards"])}).fetchone()
    return row is not None


def find_reading_by_request(conn, request_id, user_id, guest_id, now) -> dict | None:
    """Spec 4.5 §5: the reading its owner already made with this request number — the account's when signed in,
    otherwise the device's guest reading (stage 4.3 §6); another owner's number finds nothing, nor does an expired
    reading."""
    if user_id is not None:
        owner, args = "user_id = %s", (request_id, user_id, now)
    else:
        owner, args = "user_id IS NULL AND guest_id = %s", (request_id, guest_id, now)
    return conn.execute(f"SELECT * FROM readings WHERE request_id = %s AND {owner}"
                        " AND (expires_at IS NULL OR expires_at > %s)", args).fetchone()


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


def release_stream(conn, reading_id) -> None:
    """м-н8: a generation stopped by the database frees its claim at once, not after STREAM_CLAIM_STALE."""
    conn.execute("UPDATE readings SET stream_started_at = NULL WHERE id = %s AND answer IS NULL", (reading_id,))


def save_answer(conn, reading_id, answer: dict, shown: str, model: str | None, prompt_version: str) -> None:
    conn.execute("UPDATE readings SET answer = %s, answer_shown = %s, model = %s, prompt_version = %s,"
                 " stream_started_at = NULL WHERE id = %s",
                 (Jsonb(answer), shown, model, prompt_version, reading_id))


def save_crisis(conn, reading_id, model: str | None, prompt_version: str) -> None:
    """The reader saw signs of crisis (§8.6): keep only the mark and the language, drop the question (§3.4)."""
    conn.execute("UPDATE readings SET question = NULL, topic = NULL, situation = NULL, answer = %s,"
                 " answer_shown = 'crisis', model = %s, prompt_version = %s, stream_started_at = NULL WHERE id = %s",
                 (Jsonb(EMPTY_ANSWER), model, prompt_version, reading_id))


def topic_history(conn, user_id, topic: str, before, exclude_id, limit: int) -> list[dict]:
    """Stage 4.3 §7: the account's latest earlier answered readings on the same topic, oldest first. Only what the
    reader may see is selected — the time, the question and the stored answer (for its headline); never the note
    or the outcome. A crisis answer has no topic (save_crisis), so it never matches. Only guard_group 'ok': a
    question the check redirected (health, safety, another person, money) must not come back by name in a later
    reading, where the rule "do not name what you decline" no longer knows about it. And only a question the check
    really classified (guard_source 'terms' or 'model'): a timeout or an error also gives 'ok' (fail open), and a
    row from before migration 003 has no source — neither is a checked 'ok' (final review I2). A reading without a
    question has nothing to check and stays in."""
    rows = conn.execute(
        "SELECT created_at, question, answer, answer_shown FROM readings WHERE user_id = %s AND topic = %s"
        " AND id <> %s AND created_at < %s AND answer_shown IN ('model', 'fallback') AND guard_group = 'ok'"
        " AND (question IS NULL OR guard_source IN ('terms', 'model'))"
        " ORDER BY created_at DESC LIMIT %s", (user_id, topic, exclude_id, before, limit)).fetchall()
    return rows[::-1]


def reset_for_retry(conn, reading_id, retry_limit: int) -> int | None:
    """Only a fallback answer with retries left is reset; None — someone else got there first or no retries."""
    row = conn.execute("UPDATE readings SET answer = NULL, answer_shown = NULL, stream_started_at = NULL,"
                       " retries = retries + 1 WHERE id = %s AND answer_shown = 'fallback' AND retries < %s"
                       " RETURNING retries", (reading_id, retry_limit)).fetchone()
    return row["retries"] if row else None


def list_followups(conn, reading_id) -> list[dict]:
    return conn.execute("SELECT * FROM followups WHERE reading_id = %s ORDER BY n", (reading_id,)).fetchall()


def insert_followup(conn, followup: dict) -> bool:
    """False when the reading already has a follow-up with this n or this request_id (migration 005)."""
    row = conn.execute("INSERT INTO followups (id, reading_id, n, question, guard_group, paid_day, request_id,"
                       " created_at) VALUES (%(id)s, %(reading_id)s, %(n)s, %(question)s, %(guard_group)s,"
                       " %(paid_day)s, %(request_id)s, %(created_at)s) ON CONFLICT DO NOTHING RETURNING id",
                       {"guard_group": "ok", "paid_day": None, "request_id": None, **followup}).fetchone()
    return row is not None


def save_followup_answer(conn, followup_id, answer: dict, model: str | None, counted: bool = True) -> bool:
    """counted=False: a cut or replaced answer, kept with both texts, does not use a free follow-up (§9.4).

    False when the row is gone (freed as stale while its generation was still running): nothing is saved.
    """
    row = conn.execute("UPDATE followups SET answer = %s, model = %s, counted = %s WHERE id = %s RETURNING id",
                       (Jsonb(answer), model, counted, followup_id)).fetchone()
    return row is not None


def tombstone_followup(conn, followup_id) -> bool:
    """Stage 4.5 review I1: the reader's own [[crisis]] keeps the row as a mark — answer {"crisis": true}, not
    counted, the question blanked (never stored) — so the same request_id again shows the crisis help instead of
    asking the model again. False when the row is gone (freed as stale)."""
    row = conn.execute("UPDATE followups SET answer = %s, question = '', counted = false WHERE id = %s RETURNING id",
                       (Jsonb({"crisis": True}), followup_id)).fetchone()
    return row is not None


def delete_old_tombstones(conn, before) -> int:
    """Owner decision 22.11.2026: a follow-up crisis tombstone is only needed for the repeat window; the hourly
    cleanup deletes the ones made before `before` (a day ago). Its attempt stays counted (n is the counter)."""
    return conn.execute("DELETE FROM followups WHERE answer = %s AND created_at < %s",
                        (Jsonb({"crisis": True}), before)).rowcount


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


def delete_all_stale_followups(conn, before) -> list[dict]:
    """Housekeeping: every unanswered follow-up older than `before` (cut by a restart), across readings.

    Returns guest_id, user_id and paid_day per deleted row; RETURNING hands each paid row to exactly one caller.
    """
    return conn.execute("DELETE FROM followups f USING readings r WHERE r.id = f.reading_id"
                        " AND f.answer IS NULL AND f.created_at < %s RETURNING r.guest_id, r.user_id, f.paid_day",
                        (before,)).fetchall()


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


DAILY_FIELDS = "day, card_id, reversed, felt, note, noted_at"


def _daily_owner(user_id, guest_id) -> tuple[str, tuple]:
    """Migration 009: a row belongs to an account (user_id) or to a guest cookie (guest_id), never both."""
    return ("user_id = %s", (user_id,)) if user_id is not None else ("guest_id = %s", (guest_id,))


def account_daily_draw(conn, user_id, day, card_id: str, reversed_: bool) -> dict:
    """Stage 8.1 §3: one card per account and day on every device. The first request of the day stores `card_id`;
    every later one (and a card claimed from this device's guest cookie) wins over it."""
    conn.execute("INSERT INTO daily_draws (user_id, day, card_id, reversed) VALUES (%s, %s, %s, %s)"
                 " ON CONFLICT (user_id, day) DO NOTHING", (user_id, day, card_id, reversed_))
    return conn.execute(f"SELECT {DAILY_FIELDS} FROM daily_draws WHERE user_id = %s AND day = %s",
                        (user_id, day)).fetchone()


def draw_days(conn, user_id, guest_id) -> list:
    """Every day with a card of this owner, oldest first (the streaks)."""
    where, args = _daily_owner(user_id, guest_id)
    return [r["day"] for r in conn.execute(f"SELECT day FROM daily_draws WHERE {where} ORDER BY day", args)]


def calendar_rows(conn, user_id, guest_id, start, end, lang: str) -> list[dict]:
    """The owner's cards from `start` to before `end`, oldest first, each with the text the daily job cached for
    it in `lang` (cached_text, None once the cache is gone: the caller then uses the card base)."""
    where, args = _daily_owner(user_id, guest_id)
    return conn.execute(
        f"SELECT d.day, d.card_id, d.reversed, d.felt, d.note, d.noted_at, c.text AS cached_text FROM daily_draws d"
        " LEFT JOIN daily_cache c ON c.card_id = d.card_id AND c.reversed = d.reversed AND c.day = d.day"
        f" AND c.lang = %s WHERE d.{where} AND d.day >= %s AND d.day < %s ORDER BY d.day",
        (lang, *args, start, end)).fetchall()


def set_daily_mark(conn, user_id, day, fields: dict, now) -> dict | None:
    """Stage 8.1 §3: only the fields present in `fields` ("felt", "note") change; noted_at is `now`, or NULL once
    both are empty. None when the account has no card that day (a card is never drawn after the fact)."""
    row = conn.execute("SELECT felt, note FROM daily_draws WHERE user_id = %s AND day = %s FOR UPDATE",
                       (user_id, day)).fetchone()
    if row is None:
        return None
    if not fields:
        return conn.execute(f"SELECT {DAILY_FIELDS} FROM daily_draws WHERE user_id = %s AND day = %s",
                            (user_id, day)).fetchone()
    felt = fields["felt"] if "felt" in fields else row["felt"]
    note = fields["note"] if "note" in fields else row["note"]
    noted_at = None if felt is None and note is None else now
    return conn.execute(f"UPDATE daily_draws SET felt = %s, note = %s, noted_at = %s WHERE user_id = %s AND day = %s"
                        f" RETURNING {DAILY_FIELDS}", (felt, note, noted_at, user_id, day)).fetchone()


def touch_guest_push(conn, guest_id, now) -> None:
    """A guest's reminder lives 90 days from the last Card of the Day visit (housekeeping)."""
    conn.execute("UPDATE push_subscriptions SET active_at = %s WHERE guest_id = %s", (now, guest_id))


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
