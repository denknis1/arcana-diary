import uuid
from datetime import date, timedelta

import psycopg
import pytest
from psycopg.types.json import Jsonb

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
    assert migrate(fresh_db, MIGRATIONS) == ["001_init", "002_accounts", "003_guard_source", "004_events",
                                           "005_request_ids", "006_rewrite_purpose"]
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
                            " has_table_privilege('authenticated', 'public.llm_calls', 'INSERT') AS b,"
                            " has_table_privilege('anon', 'public.profiles', 'SELECT') AS c,"
                            " has_table_privilege('authenticated', 'public.claim_tokens', 'SELECT') AS d,"
                            " has_table_privilege('anon', 'public.plus_waitlist', 'INSERT') AS e,"
                            " has_table_privilege('authenticated', 'public.deleted_accounts', 'SELECT') AS f,"
                            " has_table_privilege('anon', 'public.events', 'INSERT') AS g,"
                            " has_table_privilege('authenticated', 'public.events', 'SELECT') AS h"
                            ).fetchone()
    assert rows == {"a": False, "b": False, "c": False, "d": False, "e": False, "f": False, "g": False, "h": False}


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


def test_a_missing_column_is_unavailable_too(db):
    """Final review Minor 2: new code on a database whose migration is not finished yet answers 503, not 500."""
    with pytest.raises(DatabaseUnavailable):
        with db.connect() as conn:
            conn.execute("SELECT no_such_column FROM readings")


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
        assert repo.save_followup_answer(conn, first["id"], {"model": "Text.", "fallback": None}, "fake-reader") is True
        rows = repo.list_followups(conn, reading["id"])
        assert repo.delete_followup(conn, first["id"]) is True
        assert repo.delete_followup(conn, first["id"]) is False  # already gone: nobody refunds twice
        assert repo.save_followup_answer(conn, first["id"], {"model": "Late.", "fallback": None}, "fake-reader") is False
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


def test_malformed_dsn_is_database_unavailable():
    import pytest as _pytest
    from app.db import Database, DatabaseUnavailable
    with _pytest.raises(DatabaseUnavailable):
        with Database("postgresql://[bad").connect():
            pass



# --- stage 4.3: migration 002 (spec 2026-11-19 §9) ---

def apply_up_to(db, *versions: str) -> None:
    """The database as an earlier stage left it: these migrations applied by hand, in order."""
    with db.connect() as conn:
        conn.execute("CREATE TABLE schema_migrations ("
                     "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        for version in versions:
            for statement in split_sql((MIGRATIONS / f"{version}.sql").read_text(encoding="utf-8")):
                conn.execute(statement)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))


def insert_001_reading(conn, reading: dict) -> None:
    """A reading with the 001 columns only, as the code of stage 4.2 wrote it."""
    conn.execute("INSERT INTO readings (id, guest_id, lang, kind, question, topic, cards, seed, guard_group,"
                 " created_at, expires_at) VALUES (%(id)s, %(guest_id)s, %(lang)s, %(kind)s, %(question)s, %(topic)s,"
                 " %(cards)s, %(seed)s, %(guard_group)s, %(created_at)s, %(expires_at)s)",
                 {**reading, "cards": Jsonb(reading["cards"])})


def test_002_applies_over_001_and_keeps_the_readings(fresh_db):
    reading = make_reading()
    apply_up_to(fresh_db, "001_init")  # stage 4.2: 001 applied, a guest reading in it
    with fresh_db.connect() as conn:
        insert_001_reading(conn, reading)
    assert migrate(fresh_db, MIGRATIONS) == ["002_accounts", "003_guard_source", "004_events", "005_request_ids",
                                             "006_rewrite_purpose"]
    with fresh_db.connect() as conn:
        row = conn.execute("SELECT user_id, outcome, outcome_at, note, note_updated_at FROM readings WHERE id = %s",
                           (reading["id"],)).fetchone()
    assert row == {"user_id": None, "outcome": None, "outcome_at": None, "note": None, "note_updated_at": None}


def test_003_applies_over_002_and_leaves_the_old_rows_without_a_source(fresh_db):
    """Final review I2: a nullable column without a default (no table rewrite on the live database); rows made
    before it keep NULL, which the reader memory reads as "not checked"."""
    reading = make_reading()
    apply_up_to(fresh_db, "001_init", "002_accounts")  # the live database after stage 4.3's first deploy
    with fresh_db.connect() as conn:
        insert_001_reading(conn, reading)
    assert migrate(fresh_db, MIGRATIONS) == ["003_guard_source", "004_events", "005_request_ids", "006_rewrite_purpose"]
    with fresh_db.connect() as conn:
        column = conn.execute("SELECT is_nullable, column_default FROM information_schema.columns"
                              " WHERE table_name = 'readings' AND column_name = 'guard_source'").fetchone()
        row = conn.execute("SELECT guard_group, guard_source FROM readings WHERE id = %s",
                           (reading["id"],)).fetchone()
    assert column == {"is_nullable": "YES", "column_default": None}
    assert row == {"guard_group": "ok", "guard_source": None}


def test_002_indexes(db):
    with db.connect() as conn:
        names = {r["indexname"] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")}
    assert {"readings_user_created_idx", "claim_tokens_reading_idx", "claim_tokens_expires_idx",
            "plus_waitlist_user_idx"} <= names


def test_reading_keeps_its_account_and_diary_fields(db):
    user = uuid.uuid4()
    reading = make_reading(user_id=user, expires_at=None)
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        conn.execute("UPDATE readings SET outcome = 'partly', note = %s WHERE id = %s", ("x" * 1000, reading["id"]))
        saved = repo.get_reading(conn, reading["id"], T0 + timedelta(days=365))
    assert (saved["user_id"], saved["expires_at"], saved["outcome"], len(saved["note"])) == (user, None, "partly",
                                                                                            1000)


@pytest.mark.parametrize("sql", [
    "UPDATE readings SET outcome = 'maybe'",
    "UPDATE readings SET note = repeat('x', 1001)",
    "INSERT INTO plus_waitlist (email, lang, created_at) VALUES ('Person@Example.com', 'en', now())",
    "INSERT INTO plus_waitlist (email, lang, created_at) VALUES ('person@example.com', 'fr', now())",
])
def test_002_checks(db, sql):
    with db.connect() as conn:
        repo.insert_reading(conn, make_reading())
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.connect() as conn:
            conn.execute(sql)


def test_claim_tokens_go_with_their_reading(db):
    reading = make_reading()
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        conn.execute("INSERT INTO claim_tokens (token_hash, reading_id, created_at, expires_at)"
                     " VALUES ('hash', %s, %s, %s)", (reading["id"], T0, T0 + timedelta(days=7)))
        conn.execute("DELETE FROM readings WHERE id = %s", (reading["id"],))
        left = conn.execute("SELECT count(*) AS n FROM claim_tokens").fetchone()["n"]
    assert left == 0



# --- stage 4.3 §10: the tests never empty a Supabase database by mistake ---
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

from helpers import supabase_like  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]


def test_supabase_like_urls():
    assert supabase_like("postgresql://postgres.abc:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres")
    assert supabase_like("postgresql://postgres:pw@db.abcdefgh.SUPABASE.co:5432/postgres")
    assert not supabase_like("postgresql://postgres:test@127.0.0.1:55432/arcana")


def test_the_tests_refuse_a_supabase_database():
    """A separate pytest run that stops before connecting. hostaddr=127.0.0.1 and port 1: even without the guard
    the run would only knock on a closed local port — no name lookup, nothing goes over the network."""
    env = {k: v for k, v in os.environ.items() if k != "TEST_DATABASE_ALLOW_SUPABASE"}
    env["TEST_DATABASE_URL"] = ("postgresql://postgres.abc:pw@aws-0-eu-central-1.pooler.supabase.com:1/postgres"
                                "?hostaddr=127.0.0.1&connect_timeout=2")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/test_db.py::test_reading_roundtrip"], cwd=API_DIR, env=env, capture_output=True,
                            text=True, timeout=120)
    assert result.returncode == 4, result.stdout + result.stderr
    assert "looks like a Supabase database" in result.stdout + result.stderr



# --- stage 4.4a: migration 004 (spec 2026-11-19 §6) ---

def test_004_applies_over_003(fresh_db):
    apply_up_to(fresh_db, "001_init", "002_accounts", "003_guard_source")  # the live database after stage 4.3
    assert migrate(fresh_db, MIGRATIONS) == ["004_events", "005_request_ids", "006_rewrite_purpose"]
    with fresh_db.connect() as conn:
        security = conn.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'events'").fetchone()
        names = {r["indexname"] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'events'")}
    assert security == {"relrowsecurity": True}
    assert "events_day_name_idx" in names


@pytest.mark.parametrize("sql", [
    "INSERT INTO events (day, name, lang, created_at) VALUES ('2026-11-20', 'page_view', 'en', now())",
    "INSERT INTO events (day, name, tool, lang, created_at) VALUES ('2026-11-20', 'tool_view', 'diary', 'en', now())",
    "INSERT INTO events (day, name, lang, created_at) VALUES ('2026-11-20', 'tool_view', 'fr', now())",
])
def test_004_checks(db, sql):
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.connect() as conn:
            conn.execute(sql)


# --- stage 4.5: migration 005 (spec 2026-11-20 §5) ---

def test_005_applies_over_004_and_leaves_the_old_rows_without_a_number(fresh_db):
    reading = make_reading()
    apply_up_to(fresh_db, "001_init", "002_accounts", "003_guard_source", "004_events")  # the live database
    with fresh_db.connect() as conn:
        insert_001_reading(conn, reading)
        conn.execute("INSERT INTO followups (id, reading_id, n, question, created_at) VALUES (%s, %s, 1, 'Q?', %s)",
                     (uuid.uuid4(), reading["id"], T0))
    assert migrate(fresh_db, MIGRATIONS) == ["005_request_ids", "006_rewrite_purpose"]
    with fresh_db.connect() as conn:
        columns = conn.execute("SELECT table_name, is_nullable, column_default FROM information_schema.columns"
                               " WHERE column_name = 'request_id' ORDER BY table_name").fetchall()
        names = {r["indexname"] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")}
        old = conn.execute("SELECT request_id FROM readings WHERE id = %s", (reading["id"],)).fetchone()
    assert columns == [{"table_name": t, "is_nullable": "YES", "column_default": None}
                       for t in ("followups", "readings")]
    assert {"readings_user_request_idx", "readings_guest_request_idx", "followups_reading_request_key"} <= names
    assert old == {"request_id": None}


def test_a_request_number_is_unique_per_owner(db):
    number, guest, user = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    first = make_reading(guest_id=guest, request_id=number)
    with db.connect() as conn:
        assert repo.insert_reading(conn, first) is True
        assert repo.insert_reading(conn, make_reading(guest_id=guest, request_id=number)) is False
        assert repo.insert_reading(conn, make_reading(request_id=number)) is True  # another device
        assert repo.insert_reading(conn, make_reading(guest_id=guest, user_id=user, request_id=number)) is True
        assert repo.insert_reading(conn, make_reading(user_id=user, request_id=number)) is False  # same account
        assert repo.insert_reading(conn, make_reading(guest_id=guest)) is True  # no number: never a conflict
        assert repo.insert_reading(conn, make_reading(guest_id=guest)) is True
        found = repo.find_reading_by_request(conn, number, None, guest, T0)
        assert found["id"] == first["id"]
        assert repo.find_reading_by_request(conn, number, None, uuid.uuid4(), T0) is None
        assert repo.find_reading_by_request(conn, number, user, guest, T0)["user_id"] == user
        assert repo.find_reading_by_request(conn, number, uuid.uuid4(), guest, T0) is None
        assert repo.find_reading_by_request(conn, number, None, guest, T0 + timedelta(days=8)) is None  # expired


def test_a_guest_lookup_never_finds_a_signed_in_reading_with_the_same_guest_id(db):
    number, guest, user = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with db.connect() as conn:  # the device drew while signed in: the reading belongs to the account
        repo.insert_reading(conn, make_reading(guest_id=guest, user_id=user, request_id=number))
        assert repo.find_reading_by_request(conn, number, None, guest, T0) is None
        assert repo.find_reading_by_request(conn, number, user, guest, T0) is not None


def test_a_follow_up_number_is_unique_per_reading(db):
    reading, other = make_reading(), make_reading()
    number = uuid.uuid4()
    first = {"id": uuid.uuid4(), "reading_id": reading["id"], "n": 1, "question": "And then?", "created_at": T0,
             "request_id": number}
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        repo.insert_reading(conn, other)
        assert repo.insert_followup(conn, first) is True
        assert repo.insert_followup(conn, {**first, "id": uuid.uuid4(), "n": 2}) is False  # the same number
        assert repo.insert_followup(conn, {**first, "id": uuid.uuid4(), "reading_id": other["id"]}) is True
        assert repo.insert_followup(conn, {**first, "id": uuid.uuid4(), "n": 2, "request_id": None}) is True
        rows = repo.list_followups(conn, reading["id"])
    assert [(r["n"], r["request_id"]) for r in rows] == [(1, number), (2, None)]
