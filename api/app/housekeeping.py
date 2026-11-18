"""Background work inside the API process (§4.3, §8.8), no separate queue:

- migrations at start, retried every 30 s while the database is unreachable (requests meanwhile get 503);
- the daily cleanup: expired guest readings with their follow-ups, stale counters and caches, old logs;
- freeing follow-ups cut by a restart (no answer, stale) and giving paid ones back to the guest;
- the card-of-the-day job (app.daily.daily_loop).
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app import limits, repo
from app.daily import daily_loop
from app.db import Database, DatabaseUnavailable, migrate

log = logging.getLogger("arcana.housekeeping")

KEEP_USAGE_DAYS = 2           # address hashes with an old salt link to nothing
KEEP_DAILY_CACHE_DAYS = 2
KEEP_DAILY_DRAWS_DAYS = 7
KEEP_LLM_CALLS_DAYS = 90      # no texts; enough for cost and latency reviews
KEEP_GUARD_EVENTS_DAYS = 365  # counts only
MIGRATE_RETRY_S = 30.0


def delete_expired(db: Database, now: datetime) -> dict[str, int]:
    today = now.astimezone(timezone.utc).date()

    def before(days: int):
        return today - timedelta(days=days)

    with db.connect() as conn:
        counts = {
            "readings": conn.execute("DELETE FROM readings WHERE expires_at IS NOT NULL AND expires_at <= %s",
                                     (now,)).rowcount,
            "usage": conn.execute("DELETE FROM usage WHERE day < %s", (before(KEEP_USAGE_DAYS),)).rowcount,
            "daily_cache": conn.execute("DELETE FROM daily_cache WHERE day < %s",
                                        (before(KEEP_DAILY_CACHE_DAYS),)).rowcount,
            "daily_draws": conn.execute("DELETE FROM daily_draws WHERE day < %s",
                                        (before(KEEP_DAILY_DRAWS_DAYS),)).rowcount,
            "llm_calls": conn.execute("DELETE FROM llm_calls WHERE created_at < %s",
                                      (now - timedelta(days=KEEP_LLM_CALLS_DAYS),)).rowcount,
            "guard_events": conn.execute("DELETE FROM guard_events WHERE day < %s",
                                         (before(KEEP_GUARD_EVENTS_DAYS),)).rowcount,
        }
    log.info("cleanup: %s", counts)
    return counts


def free_stale_followups(db: Database, now: datetime) -> int:
    """Delete unanswered follow-ups older than the stream claim window, across all readings, and give the paid
    ones their reading back. DELETE ... RETURNING makes the refund happen once even next to the route's cleanup."""
    with db.connect() as conn:
        rows = repo.delete_all_stale_followups(conn, now - repo.STREAM_CLAIM_STALE)
        for guest_id, paid_day in rows:
            if paid_day is not None:
                limits.give_back_slot(conn, limits.guest_subject(guest_id), paid_day)
    if rows:
        log.info("cleanup: freed %d stale follow-ups", len(rows))
    return len(rows)


async def migrate_until_done(db: Database, migrations_dir, retry_s: float = MIGRATE_RETRY_S) -> list[str]:
    while True:
        try:
            return await asyncio.to_thread(migrate, db, migrations_dir)
        except DatabaseUnavailable as exc:
            log.error("migrations waiting for the database: %s", exc)
            await asyncio.sleep(retry_s)


async def cleanup_loop(db: Database, interval_s: float, clock) -> None:
    while True:
        try:
            now = clock()
            await asyncio.to_thread(delete_expired, db, now)
            await asyncio.to_thread(free_stale_followups, db, now)
        except Exception:  # a failed cleanup must not stop the loop or the API
            log.exception("cleanup failed")
        await asyncio.sleep(interval_s)


async def run_background(ctx, migrate_retry_s: float = MIGRATE_RETRY_S) -> None:
    settings = ctx.settings
    if settings.run_migrations:
        await migrate_until_done(ctx.db, settings.migrations_dir, migrate_retry_s)
    jobs = [cleanup_loop(ctx.db, settings.cleanup_interval_s, ctx.clock)]
    if settings.daily_job_interval_s > 0:
        jobs.append(daily_loop(ctx, settings.daily_job_interval_s))
    await asyncio.gather(*jobs)
