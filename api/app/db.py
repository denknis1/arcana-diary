"""Postgres access: one connection per unit of work, SQL migrations from api/migrations/."""
import logging
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

log = logging.getLogger("arcana.db")

APP_TABLES = ("readings", "followups", "daily_cache", "daily_draws", "usage", "guard_events", "llm_calls",
              "claim_tokens", "profiles", "plus_waitlist", "deleted_accounts")
APP_SEQUENCES = "llm_calls_id_seq"
# Supabase gives these roles to the browser (PostgREST); our tables are for the API only
PUBLIC_ROLES = ("anon", "authenticated")


class DatabaseUnavailable(Exception):
    """The database cannot be reached or is not migrated yet: routes answer 503, nothing is created or counted."""


class Database:
    def __init__(self, url: str, connect_timeout: int = 5):
        self.url = url
        self.connect_timeout = connect_timeout

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        """One transaction: commit on success, rollback on error, then close.

        prepare_threshold=None: no server-side prepared statements (Supabase transaction pooler).
        A missing table means the migrations have not run yet (the database was down at start): also 503.
        """
        if not self.url:
            raise DatabaseUnavailable("DATABASE_URL is not set")
        try:
            conn = psycopg.connect(self.url, connect_timeout=self.connect_timeout, prepare_threshold=None,
                                   row_factory=dict_row)
        except (psycopg.OperationalError, psycopg.ProgrammingError) as exc:  # ProgrammingError: malformed DSN
            raise DatabaseUnavailable(str(exc)) from exc
        try:
            with conn:
                yield conn
        except (psycopg.OperationalError, psycopg.errors.UndefinedTable) as exc:
            raise DatabaseUnavailable(str(exc)) from exc


def split_sql(text: str) -> list[str]:
    """Statements end with ';' at the end of a line; the migrations have no functions or $$ bodies."""
    statements = []
    for chunk in re.split(r";[ \t]*\n", text + "\n"):
        lines = [line for line in chunk.splitlines() if line.strip() and not line.strip().startswith("--")]
        if lines:
            statements.append("\n".join(lines))
    return statements


def migrate(db: Database, migrations_dir: Path) -> list[str]:
    """Apply api/migrations/*.sql in name order, each once; returns the versions applied now.

    Then revokes the rights on our tables from Supabase's browser roles, if they exist (RLS already closes the
    rows); other tables in the schema are left alone.
    """
    applied = []
    with db.connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        conn.execute("ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY")
        done = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(migrations_dir.glob("*.sql")):
            if path.stem in done:
                continue
            for statement in split_sql(path.read_text(encoding="utf-8")):
                conn.execute(statement)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
            applied.append(path.stem)
            log.info("migration applied: %s", path.stem)
        roles = [r["rolname"] for r in conn.execute("SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)",
                                                    (list(PUBLIC_ROLES),))]
        tables = ", ".join(("schema_migrations", *APP_TABLES))
        for role in roles:  # only our tables: later stages may give these roles tables of their own
            conn.execute(f'REVOKE ALL ON TABLE {tables} FROM "{role}"')
            conn.execute(f'REVOKE ALL ON SEQUENCE {APP_SEQUENCES} FROM "{role}"')
    return applied
