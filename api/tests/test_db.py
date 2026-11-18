import uuid
from datetime import date, timedelta

import psycopg
import pytest

from app import repo
from app.config import load_settings
from app.db import APP_TABLES, Database, DatabaseUnavailable, migrate, split_sql
from helpers import T0, make_reading

MIGRATIONS = load_settings({}).migrations_dir


@pytest.fixture
def fresh_db(pg_url):
    name = f"mig_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(pg_url, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {name}")
    yield Database(pg_url.rsplit("/", 1)[0] + "/" + name)
    with psycopg.connect(pg_url, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE {name} WITH (FORCE)")


def test_split_sql():
    text = "-- comment\nCREATE TABLE a (x int);\n\nCREATE TABLE b (\n  y int -- inline\n);\n"
    assert split_sql(text) == ["CREATE TABLE a (x int)", "CREATE TABLE b (\n  y int -- inline\n)"]


def test_migrate_creates_tables_with_rls_and_no_policies(fresh_db):
    assert migrate(fresh_db, MIGRATIONS) == ["001_init"]
    with fresh_db.connect() as conn:
        rows = conn.execute("SELECT relname, relrowsecurity FROM pg_class"
                            " WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'").fetchall()
        policies = conn.execute("SELECT count(*) AS n FROM pg_policies WHERE schemaname = 'public'").fetchone()
    tables = {r["relname"]: r["relrowsecurity"] for r in rows}
    assert set(tables) == set(APP_TABLES) | {"schema_migrations"}
    assert all(tables.values())
    assert policies["n"] == 0


def test_migrate_revokes_supabase_browser_roles(fresh_db):
    with psycopg.connect(fresh_db.url, autocommit=True) as conn:
        for role in ("anon", "authenticated"):
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                conn.execute(f"CREATE ROLE {role}")
            conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {role}")
    migrate(fresh_db, MIGRATIONS)
    with fresh_db.connect() as conn:
        rows = conn.execute("SELECT has_table_privilege('anon', 'public.readings', 'SELECT') AS a,"
                            " has_table_privilege('authenticated', 'public.llm_calls', 'INSERT') AS b").fetchone()
    assert rows == {"a": False, "b": False}


def test_migrate_leaves_other_tables_alone(fresh_db):
    with psycopg.connect(fresh_db.url, autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'anon'").fetchone():
            conn.execute("CREATE ROLE anon")
        conn.execute("CREATE TABLE later_stage (x int)")
        conn.execute("GRANT SELECT ON later_stage TO anon")
    migrate(fresh_db, MIGRATIONS)
    with fresh_db.connect() as conn:
        row = conn.execute("SELECT has_table_privilege('anon', 'public.later_stage', 'SELECT') AS other,"
                           " has_table_privilege('anon', 'public.schema_migrations', 'SELECT') AS ours").fetchone()
    assert row == {"other": True, "ours": False}


def test_unmigrated_table_is_unavailable(fresh_db):
    with pytest.raises(DatabaseUnavailable):
        with fresh_db.connect() as conn:
            conn.execute("SELECT * FROM readings")


def test_migrate_is_idempotent(fresh_db):
    migrate(fresh_db, MIGRATIONS)
    assert migrate(fresh_db, MIGRATIONS) == []


def test_indexes_exist(fresh_db):
    migrate(fresh_db, MIGRATIONS)
    with fresh_db.connect() as conn:
        names = {r["indexname"] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")}
    assert {"readings_guest_created_idx", "readings_expires_idx", "usage_day_idx", "llm_calls_created_idx"} <= names


def test_unreachable_database_raises():
    with pytest.raises(DatabaseUnavailable):
        with Database("postgresql://nobody@127.0.0.1:1/none", connect_timeout=1).connect():
            pass


def test_empty_url_raises():
    with pytest.raises(DatabaseUnavailable):
        with Database("").connect():
            pass


def test_reading_roundtrip(db):
    reading = make_reading()
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        got = repo.get_reading(conn, reading["id"], T0)
    assert got["cards"] == reading["cards"]
    assert got["guest_id"] == reading["guest_id"]
    assert got["answer"] is None and got["answer_shown"] is None and got["retries"] == 0


def test_expired_reading_hidden(db):
    reading = make_reading()
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        assert repo.get_reading(conn, reading["id"], T0 + timedelta(days=8)) is None


def test_claim_stream_once(db):
    reading = make_reading()
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        assert repo.claim_stream(conn, reading["id"], T0) is True
        assert repo.claim_stream(conn, reading["id"], T0 + timedelta(seconds=120)) is False
        assert repo.claim_stream(conn, reading["id"], T0 + timedelta(seconds=300)) is True


def test_save_answer_and_retry(db):
    reading = make_reading()
    answer = {"model": None, "fallback": {"headline": "x"}}
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        repo.save_answer(conn, reading["id"], answer, "fallback", "fake-reader", "reader.en.v1")
        saved = repo.get_reading(conn, reading["id"], T0)
        assert saved["answer"] == answer and saved["answer_shown"] == "fallback"
        assert repo.claim_stream(conn, reading["id"], T0) is False
        assert repo.reset_for_retry(conn, reading["id"], 2) == 1
        assert repo.reset_for_retry(conn, reading["id"], 2) is None  # no longer a fallback: a second retry loses
        again = repo.get_reading(conn, reading["id"], T0)
    assert again["answer"] is None and again["answer_shown"] is None and again["retries"] == 1


def test_save_crisis_drops_the_question(db):
    reading = make_reading(topic="love", situation="after_breakup")
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        repo.save_crisis(conn, reading["id"], "fake-reader", "reader.en.v1")
        saved = repo.get_reading(conn, reading["id"], T0)
    assert (saved["question"], saved["topic"], saved["situation"], saved["answer_shown"]) == (None, None, None,
                                                                                               "crisis")


def test_verdict_only_for_allowed_groups(db):
    one = [{"card_id": "major-18-moon", "position": "card", "reversed": False}]
    with db.connect() as conn:
        repo.insert_reading(conn, make_reading(kind="yes_no", cards=one, verdict="no", guard_group="redirect_money"))
    for bad in (make_reading(kind="yes_no", cards=one, verdict="no", guard_group="redirect_topic"),
                make_reading(kind="one", cards=one, verdict="yes")):
        with pytest.raises(psycopg.errors.CheckViolation):
            with db.connect() as conn:
                repo.insert_reading(conn, bad)


def test_followups_unique_n(db):
    reading = make_reading()
    first = {"id": uuid.uuid4(), "reading_id": reading["id"], "n": 1, "question": "And then?", "created_at": T0}
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        assert repo.insert_followup(conn, first) is True
        assert repo.insert_followup(conn, {**first, "id": uuid.uuid4()}) is False
        repo.save_followup_answer(conn, first["id"], {"model": "Text.", "fallback": None}, "fake-reader")
        rows = repo.list_followups(conn, reading["id"])
        repo.delete_followup(conn, first["id"])
        assert repo.list_followups(conn, reading["id"]) == []
    assert [(r["n"], r["answer"]) for r in rows] == [(1, {"model": "Text.", "fallback": None})]
    assert (rows[0]["guard_group"], rows[0]["counted"]) == ("ok", True)


def test_followup_keeps_its_group_and_an_uncounted_answer(db):
    reading = make_reading()
    followup = {"id": uuid.uuid4(), "reading_id": reading["id"], "n": 8, "question": "Should I buy it?",
                "guard_group": "redirect_money", "paid_day": date(2026, 11, 20), "created_at": T0}
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        repo.insert_followup(conn, followup)
        repo.save_followup_answer(conn, followup["id"], {"model": "Cut sh", "fallback": "Base."}, "fake-reader",
                                  counted=False)
        [row] = repo.list_followups(conn, reading["id"])
        attempts = repo.get_reading(conn, reading["id"], T0)["followup_attempts"]
    assert (row["guard_group"], row["counted"], row["answer"]["fallback"], row["paid_day"], attempts) == (
        "redirect_money", False, "Base.", date(2026, 11, 20), 0)
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.connect() as conn:
            repo.insert_followup(conn, {**followup, "id": uuid.uuid4(), "n": 9})


def test_stale_unanswered_followups_are_freed(db):
    reading = make_reading()
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        for n, answer, paid_day in ((1, {"model": "Done.", "fallback": None}, None), (2, None, None),
                                    (3, None, date(2026, 11, 20))):
            fid = uuid.uuid4()
            repo.insert_followup(conn, {"id": fid, "reading_id": reading["id"], "n": n, "question": "Q?",
                                        "paid_day": paid_day, "created_at": T0})
            if answer:
                repo.save_followup_answer(conn, fid, answer, "fake-reader")
        assert repo.delete_stale_followups(conn, reading["id"], T0) == []
        assert set(repo.delete_stale_followups(conn, reading["id"], T0 + timedelta(seconds=181))) == {
            None, date(2026, 11, 20)}
        assert [r["n"] for r in repo.list_followups(conn, reading["id"])] == [1]


def test_daily_cache_first_write_wins(db):
    row = {"card_id": "major-18-moon", "reversed": False, "lang": "es", "day": date(2026, 11, 20),
           "text": "Primero.", "model": "fake-reader", "prompt_version": "daily.es.v1"}
    with db.connect() as conn:
        repo.put_daily_cache(conn, row)
        repo.put_daily_cache(conn, {**row, "text": "Segundo."})
        got = repo.get_daily_cache(conn, "major-18-moon", False, "es", date(2026, 11, 20))
        assert repo.get_daily_cache(conn, "major-18-moon", True, "es", date(2026, 11, 20)) is None
        keys = repo.cached_daily_keys(conn, date(2026, 11, 20))
    assert got["text"] == "Primero."
    assert keys == {("major-18-moon", False, "es")}


def test_daily_draw_once_per_day(db):
    guest = uuid.uuid4()
    with db.connect() as conn:
        repo.record_daily_draw(conn, guest, date(2026, 11, 20), "major-18-moon", True)
        repo.record_daily_draw(conn, guest, date(2026, 11, 20), "major-18-moon", True)
        n = conn.execute("SELECT count(*) AS n FROM daily_draws").fetchone()["n"]
    assert n == 1


def test_guard_events_count_without_text(db):
    with db.connect() as conn:
        repo.count_guard_event(conn, date(2026, 11, 20), "es", "crisis", "terms")
        repo.count_guard_event(conn, date(2026, 11, 20), "es", "crisis", "terms")
        repo.count_guard_event(conn, date(2026, 11, 20), "es", "ok", "timeout")
        rows = conn.execute("SELECT * FROM guard_events ORDER BY guard_group").fetchall()
    assert rows == [{"day": date(2026, 11, 20), "lang": "es", "guard_group": "crisis", "source": "terms", "count": 2},
                    {"day": date(2026, 11, 20), "lang": "es", "guard_group": "ok", "source": "timeout", "count": 1}]


def test_log_llm_call_and_spend(db):
    call = {"reading_id": None, "purpose": "guard", "model": "claude-haiku-5-5", "prompt_version": "guard.v1",
            "ms_first_token": None, "ms_total": 420, "tokens_in": 60, "tokens_out": 8, "cost_usd": 0.00001,
            "stop_reason": "end_turn", "refusal_category": None, "created_at": T0}
    with db.connect() as conn:
        repo.log_llm_call(conn, call)
        repo.log_llm_call(conn, {**call, "cost_usd": 1.5, "created_at": T0 - timedelta(days=1)})
        repo.log_llm_call(conn, {**call, "cost_usd": None, "stop_reason": "refusal", "refusal_category": "bio"})
        row = conn.execute("SELECT * FROM llm_calls ORDER BY id").fetchone()
        assert repo.spent_since(conn, T0 - timedelta(hours=1)) == pytest.approx(0.00001)
        assert repo.spent_since(conn, T0 - timedelta(days=2)) == pytest.approx(1.50001)
        repo.log_llm_call(conn, {**call, "purpose": "reader", "cost_usd": 0.002})
        assert repo.spent_since(conn, T0 - timedelta(hours=1)) == pytest.approx(0.00201)
        assert repo.spent_since(conn, T0 - timedelta(hours=1), "guard") == pytest.approx(0.00001)
    assert row["purpose"] == "guard" and row["ms_total"] == 420 and float(row["cost_usd"]) == 0.00001


def test_check_constraint_rejects_bad_kind(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.connect() as conn:
            repo.insert_reading(conn, make_reading(kind="five"))
