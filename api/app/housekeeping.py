"""Background work inside the API process (§4.3, §8.8), no separate queue:

- migrations at start, retried every 30 s while the database is unreachable (requests meanwhile get 503);
- the hourly cleanup (CLEANUP_INTERVAL_S): expired guest readings with their follow-ups, expired claim tokens,
  old deleted-account marks, follow-up crisis tombstones older than a day, stale counters and caches, old logs, events older than 13 months, Plus waitlist requests older than 12;
- freeing follow-ups cut by a restart (no answer, stale) and giving paid ones back to their owner;
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
KEEP_EVENTS_DAYS = 396        # 13 months: owner decision 23.11.2026 (stage 4.9)
KEEP_WAITLIST_DAYS = 365      # Plus waitlist requests: 12 months (stage 4.9)
KEEP_TOMBSTONE_DAYS = 1       # follow-up crisis tombstones: owner decision 22.11.2026
KEEP_DELETED_ACCOUNTS_DAYS = 8  # longer than the longest Supabase access token (7 days): stage 4.3 §8
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
            "daily_draws": conn.execute("DELETE FROM daily_draws WHERE day < %s AND user_id IS NULL",
                                        (before(KEEP_DAILY_DRAWS_DAYS),)).rowcount,
            "llm_calls": conn.execute("DELETE FROM llm_calls WHERE created_at < %s",
                                      (now - timedelta(days=KEEP_LLM_CALLS_DAYS),)).rowcount,
            "guard_events": conn.execute("DELETE FROM guard_events WHERE day < %s",
                                         (before(KEEP_GUARD_EVENTS_DAYS),)).rowcount,
            "events": conn.execute("DELETE FROM events WHERE created_at < %s",
                                   (now - timedelta(days=KEEP_EVENTS_DAYS),)).rowcount,
            "plus_waitlist": conn.execute("DELETE FROM plus_waitlist WHERE created_at < %s",
                                          (now - timedelta(days=KEEP_WAITLIST_DAYS),)).rowcount,
            "claim_tokens": conn.execute("DELETE FROM claim_tokens WHERE expires_at <= %s", (now,)).rowcount,
            "deleted_accounts": conn.execute("DELETE FROM deleted_accounts WHERE deleted_at < %s",
                                             (now - timedelta(days=KEEP_DELETED_ACCOUNTS_DAYS),)).rowcount,
            "followup_tombstones": repo.delete_old_tombstones(conn, now - timedelta(days=KEEP_TOMBSTONE_DAYS)),
        }
    log.info("cleanup: %s", counts)
    return counts


def free_stale_followups(db: Database, now: datetime) -> int:
    """Delete unanswered follow-ups older than the stream claim window, across all readings, and give the paid
    ones their reading back. DELETE ... RETURNING makes the refund happen once even next to the route's cleanup."""
    with db.connect() as conn:
        rows = repo.delete_all_stale_followups(conn, now - repo.STREAM_CLAIM_STALE)
        for row in rows:
            if row["paid_day"] is not None:  # back to whoever paid: the account if the reading has one
                limits.give_back_slot(conn, limits.owner_quota(row).subject, row["paid_day"])
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
        except Exception:  # not a connection problem (bad DSN, no rights, broken SQL): say why, keep trying
            log.exception("migrations failed with an unexpected error, retrying in %.0f s", retry_s)
            await asyncio.sleep(retry_s)


async def cleanup_loop(db: Database, interval_s: float, clock) -> None:
    while True:
        now = clock()
        for step in (delete_expired, free_stale_followups):  # separate tries: one failing step skips nothing else
            try:
                await asyncio.to_thread(step, db, now)
            except Exception:  # a failed cleanup must not stop the loop or the API
                log.exception("cleanup step %s failed", step.__name__)
        await asyncio.sleep(interval_s)


async def _logged(name: str, job) -> None:
    """м-п1: a job that dies says so at once; gather alone would report it only after every other job ended, and
    the cleanup never ends. Cancellation (shutdown) passes through."""
    try:
        await job
    except Exception:
        log.exception("background job %s stopped", name)


async def run_background(ctx, migrate_retry_s: float = MIGRATE_RETRY_S) -> None:
    settings = ctx.settings
    if settings.run_migrations:
        await migrate_until_done(ctx.db, settings.migrations_dir, migrate_retry_s)
    jobs = [("cleanup", cleanup_loop(ctx.db, settings.cleanup_interval_s, ctx.clock))]
    if settings.daily_job_interval_s > 0:
        jobs.append(("daily", daily_loop(ctx, settings.daily_job_interval_s)))
    await asyncio.gather(*(_logged(name, job) for name, job in jobs))  # one crashing job does not stop the other
