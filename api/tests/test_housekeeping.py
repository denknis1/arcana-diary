import asyncio
import time
import uuid
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import housekeeping, limits, repo
from app.config import load_settings
from app.db import DatabaseUnavailable
from app.housekeeping import (cleanup_loop, delete_expired, free_stale_followups, migrate_until_done,
                               run_background)
from app.main import create_app
from app.reader.provider import FakeProvider
from helpers import T0, make_reading


def count(db, table: str) -> int:
    with db.connect() as conn:
        return conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


def call(created_at, cost=None) -> dict:
    return {"reading_id": None, "purpose": "guard", "model": "m", "prompt_version": "guard.v1",
            "ms_first_token": None, "ms_total": 10, "tokens_in": 1, "tokens_out": 1, "cost_usd": cost,
            "stop_reason": "end_turn", "refusal_category": None, "created_at": created_at}


def test_delete_expired_readings_with_followups(db):
    old, fresh = make_reading(now=T0 - timedelta(days=8)), make_reading(now=T0)
    with db.connect() as conn:
        repo.insert_reading(conn, old)
        repo.insert_reading(conn, fresh)
        repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": old["id"], "n": 1, "question": "Then?",
                                    "created_at": T0 - timedelta(days=8)})
    assert delete_expired(db, T0)["readings"] == 1
    assert count(db, "readings") == 1 and count(db, "followups") == 0


def test_delete_stale_counters_caches_and_old_logs(db):
    today = T0.date()
    with db.connect() as conn:
        for day in (today, today - timedelta(days=3)):
            conn.execute("INSERT INTO usage (subject, day, count) VALUES ('ip:x', %s, 1)", (day,))
            repo.put_daily_cache(conn, {"card_id": "major-18-moon", "reversed": False, "lang": "en", "day": day,
                                        "text": "T.", "model": "m", "prompt_version": "daily.en.v1"})
        repo.record_daily_draw(conn, uuid.uuid4(), today - timedelta(days=8), "major-18-moon", False)
        repo.record_daily_draw(conn, uuid.uuid4(), today, "major-18-moon", False)
        repo.count_guard_event(conn, today - timedelta(days=30), "en", "ok", "model")
        repo.count_guard_event(conn, today - timedelta(days=400), "en", "ok", "model")
        repo.log_llm_call(conn, call(T0))
        repo.log_llm_call(conn, call(T0 - timedelta(days=91)))
    assert delete_expired(db, T0) == {"readings": 0, "usage": 1, "daily_cache": 1, "daily_draws": 1,
                                      "llm_calls": 1, "guard_events": 1, "events": 0, "plus_waitlist": 0, "claim_tokens": 0, "deleted_accounts": 0,
                                      "followup_tombstones": 0}
    assert (count(db, "usage"), count(db, "daily_cache"), count(db, "daily_draws")) == (1, 1, 1)
    assert (count(db, "guard_events"), count(db, "llm_calls")) == (1, 1)


def test_followup_crisis_tombstones_are_deleted_after_one_day(db):
    reading = make_reading(now=T0)
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        for n, age, answer in [(1, timedelta(days=1, minutes=1), {"crisis": True}),   # old tombstone: goes
                               (2, timedelta(hours=23), {"crisis": True}),            # young tombstone: stays
                               (3, timedelta(days=3), {"text": "A."}),                # old real answer: stays
                               (4, timedelta(days=3), {"crisis": False})]:            # not a tombstone: stays
            repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": reading["id"], "n": n, "question": "",
                                        "created_at": T0 - age})
            conn.execute("UPDATE followups SET answer = %s WHERE reading_id = %s AND n = %s",
                         (repo.Jsonb(answer), reading["id"], n))
    assert delete_expired(db, T0)["followup_tombstones"] == 1
    with db.connect() as conn:
        left = sorted(r["n"] for r in conn.execute("SELECT n FROM followups").fetchall())
    assert left == [2, 3, 4]


def test_cleanup_loop_runs_now_and_repeats(db):
    async def scenario():
        with db.connect() as conn:
            repo.insert_reading(conn, make_reading(now=T0 - timedelta(days=8)))
        task = asyncio.create_task(cleanup_loop(db, 0.05, lambda: T0))
        await asyncio.sleep(0.3)
        first = count(db, "readings")
        with db.connect() as conn:
            repo.insert_reading(conn, make_reading(now=T0 - timedelta(days=9)))
        await asyncio.sleep(0.3)
        second = count(db, "readings")
        task.cancel()
        return first, second

    assert asyncio.run(scenario()) == (0, 0)


class FlakyDatabase:
    """The real database, but unreachable for the first `failures` connections (Supabase down at start)."""

    def __init__(self, real, failures: int):
        self.real, self.failures, self.attempts = real, failures, 0

    @contextmanager
    def connect(self):
        self.attempts += 1
        if self.attempts <= self.failures:
            raise DatabaseUnavailable("down")
        with self.real.connect() as conn:
            yield conn


def test_migrations_are_retried_until_the_database_is_back(db):
    flaky = FlakyDatabase(db, failures=2)
    applied = asyncio.run(migrate_until_done(flaky, load_settings({}).migrations_dir, retry_s=0.01))
    assert applied == [] and flaky.attempts == 3  # the test database is migrated already


def test_run_background_starts_cleanup_and_the_daily_job(db, monkeypatch):
    started = []

    async def fake_daily(ctx, interval_s, card_ids=None):
        started.append(("daily", interval_s))

    async def fake_cleanup(database, interval_s, clock):
        started.append(("cleanup", interval_s))

    monkeypatch.setattr(housekeeping, "daily_loop", fake_daily)
    monkeypatch.setattr(housekeeping, "cleanup_loop", fake_cleanup)
    settings = replace(load_settings({}), database_url=db.url, cleanup_interval_s=60.0, daily_job_interval_s=900.0)
    asyncio.run(run_background(SimpleNamespace(settings=settings, db=db, clock=lambda: T0)))
    assert started == [("cleanup", 60.0), ("daily", 900.0)]
    started.clear()
    asyncio.run(run_background(SimpleNamespace(settings=replace(settings, daily_job_interval_s=0.0), db=db,
                                               clock=lambda: T0)))
    assert started == [("cleanup", 60.0)]


def test_app_lifespan_starts_and_stops_background_work(db):
    with db.connect() as conn:
        repo.insert_reading(conn, make_reading(now=T0 - timedelta(days=8)))
    settings = replace(load_settings({}), database_url=db.url, cleanup_interval_s=3600, daily_job_interval_s=0)
    app = create_app(settings, reader=FakeProvider(), guard_provider=FakeProvider(), clock=lambda: T0)
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/health").status_code == 200
        task = app.state.background_task
        deadline = time.monotonic() + 3
        while count(db, "readings") and time.monotonic() < deadline:
            time.sleep(0.05)
        assert count(db, "readings") == 0 and not task.done()
    assert task.cancelled()


def usage_count(db, guest_id, day) -> int:
    with db.connect() as conn:
        row = conn.execute("SELECT count FROM usage WHERE subject = %s AND day = %s",
                           (limits.guest_subject(guest_id), day)).fetchone()
    return row["count"] if row else 0


def test_stale_unanswered_followups_are_freed_and_paid_ones_refunded_once(db):
    day = T0.date()
    reading = make_reading(now=T0)
    stale, fresh = T0 - timedelta(seconds=repo.STREAM_CLAIM_STALE.total_seconds() + 5), T0 - timedelta(seconds=10)
    rows = [(1, None, stale, None), (2, day, stale, None), (3, day, fresh, None), (4, day, stale, {"text": "A."})]
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, 3)",
                     (limits.guest_subject(reading["guest_id"]), day))
        for n, paid_day, created_at, answer in rows:
            repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": reading["id"], "n": n, "question": "Then?",
                                        "paid_day": paid_day, "created_at": created_at})
            if answer:
                conn.execute("UPDATE followups SET answer = %s WHERE reading_id = %s AND n = %s",
                             (repo.Jsonb(answer), reading["id"], n))
    assert free_stale_followups(db, T0) == 2
    with db.connect() as conn:
        left = sorted(r["n"] for r in conn.execute("SELECT n FROM followups").fetchall())
    assert left == [3, 4]  # the free and the paid stale ones are gone; the live one and the answered one stay
    assert usage_count(db, reading["guest_id"], day) == 2  # only the paid one gave its reading back
    assert free_stale_followups(db, T0) == 0
    assert usage_count(db, reading["guest_id"], day) == 2


def test_a_non_database_migration_error_is_logged_and_retried(db, caplog):
    class Broken(FlakyDatabase):
        @contextmanager
        def connect(self):
            self.attempts += 1
            if self.attempts <= self.failures:
                raise RuntimeError("malformed DSN")
            with self.real.connect() as conn:
                yield conn

    broken = Broken(db, failures=2)
    with caplog.at_level("ERROR", logger="arcana.housekeeping"):
        applied = asyncio.run(migrate_until_done(broken, load_settings({}).migrations_dir, retry_s=0.01))
    assert applied == [] and broken.attempts == 3
    assert "migrations failed" in caplog.text and "malformed DSN" in caplog.text


def test_a_failing_cleanup_step_does_not_skip_the_other(db, monkeypatch, caplog):
    ran = []

    def boom(database, now):
        raise RuntimeError("delete failed")

    monkeypatch.setattr(housekeeping, "delete_expired", boom)
    monkeypatch.setattr(housekeeping, "free_stale_followups", lambda database, now: ran.append("freed"))

    async def scenario():
        task = asyncio.create_task(cleanup_loop(db, 0.05, lambda: T0))
        await asyncio.sleep(0.2)
        task.cancel()

    asyncio.run(scenario())
    assert "freed" in ran and "delete failed" in caplog.text


def test_one_background_job_crashing_does_not_stop_the_other(db, monkeypatch, caplog):
    finished = []

    async def crashing_daily(ctx, interval_s, card_ids=None):
        raise RuntimeError("daily crashed")

    async def fake_cleanup(database, interval_s, clock):
        await asyncio.sleep(0.1)
        finished.append("cleanup")

    monkeypatch.setattr(housekeeping, "daily_loop", crashing_daily)
    monkeypatch.setattr(housekeeping, "cleanup_loop", fake_cleanup)
    settings = replace(load_settings({}), database_url=db.url, cleanup_interval_s=60.0, daily_job_interval_s=900.0)
    asyncio.run(run_background(SimpleNamespace(settings=settings, db=db, clock=lambda: T0)))
    assert finished == ["cleanup"] and "daily crashed" in caplog.text



# --- stage 4.3 §10 ---
import contextlib  # noqa: E402


def test_expired_claim_tokens_are_deleted(db):
    reading = make_reading(now=T0)
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        for name, expires_at in (("old", T0 - timedelta(seconds=1)), ("live", T0 + timedelta(days=1))):
            conn.execute("INSERT INTO claim_tokens (token_hash, reading_id, created_at, expires_at)"
                         " VALUES (%s, %s, %s, %s)", (name, reading["id"], T0 - timedelta(days=6), expires_at))
    assert delete_expired(db, T0)["claim_tokens"] == 1
    with db.connect() as conn:
        assert [r["token_hash"] for r in conn.execute("SELECT token_hash FROM claim_tokens").fetchall()] == ["live"]


def test_deleted_accounts_are_forgotten_after_eight_days(db):
    old, recent = uuid.uuid4(), uuid.uuid4()
    with db.connect() as conn:
        conn.execute("INSERT INTO deleted_accounts (user_id, deleted_at) VALUES (%s, %s), (%s, %s)",
                     (old, T0 - timedelta(days=8, minutes=1), recent, T0 - timedelta(days=7)))
    assert delete_expired(db, T0)["deleted_accounts"] == 1
    with db.connect() as conn:
        assert [r["user_id"] for r in conn.execute("SELECT user_id FROM deleted_accounts").fetchall()] == [recent]


def test_account_readings_survive_the_cleanup(db):
    """Stage 4.3 §4.3: a reading in an account has no expiry; only the old guest reading goes."""
    old = T0 - timedelta(days=400)
    mine = make_reading(now=old, user_id=uuid.uuid4(), expires_at=None)
    guest = make_reading(now=old)
    with db.connect() as conn:
        repo.insert_reading(conn, mine)
        repo.insert_reading(conn, guest)
    assert delete_expired(db, T0)["readings"] == 1
    with db.connect() as conn:
        assert [r["id"] for r in conn.execute("SELECT id FROM readings").fetchall()] == [mine["id"]]


def test_a_crashed_background_job_is_logged_at_once(db, monkeypatch, caplog):
    async def crashing_daily(ctx, interval_s, card_ids=None):
        raise RuntimeError("daily crashed")

    async def endless_cleanup(database, interval_s, clock):
        await asyncio.sleep(3600)

    monkeypatch.setattr(housekeeping, "daily_loop", crashing_daily)
    monkeypatch.setattr(housekeeping, "cleanup_loop", endless_cleanup)
    settings = replace(load_settings({}), database_url=db.url, run_migrations=False, daily_job_interval_s=900.0)

    async def scenario():
        task = asyncio.create_task(run_background(SimpleNamespace(settings=settings, db=db, clock=lambda: T0)))
        await asyncio.sleep(0.2)
        logged = "background job daily stopped" in caplog.text and "daily crashed" in caplog.text
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return logged, task.cancelled()

    with caplog.at_level("ERROR", logger="arcana.housekeeping"):
        assert asyncio.run(scenario()) == (True, True)


def test_delete_old_events_and_waitlist(db):
    with db.connect() as conn:
        for created in (T0, T0 - timedelta(days=400)):
            conn.execute("INSERT INTO events (day, name, tool, lang, created_at) VALUES (%s, 'tool_view', 'home', 'en', %s)",
                         (created.date(), created))
        for email, created in (("new@example.com", T0 - timedelta(days=300)), ("old@example.com", T0 - timedelta(days=370))):
            conn.execute("INSERT INTO plus_waitlist (email, lang, created_at) VALUES (%s, 'en', %s)", (email, created))
    counts = delete_expired(db, T0)
    assert (counts["events"], counts["plus_waitlist"]) == (1, 1)
    assert (count(db, "events"), count(db, "plus_waitlist")) == (1, 1)
