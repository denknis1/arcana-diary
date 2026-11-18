"""Postgres for tests: TEST_DATABASE_URL (a throwaway database!) or a temporary Docker container."""
import os
import shutil
import subprocess
import time
import uuid

import psycopg
import pytest

from app.config import load_settings
from app.db import APP_TABLES, Database, migrate

PG_IMAGE = "postgres:16.10-alpine"


def _docker_problem() -> str | None:
    if shutil.which("docker") is None:
        return "docker is not installed"
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        return "docker daemon is not reachable"
    return None


def _wait_for(url: str, seconds: float = 60.0) -> None:
    deadline = time.monotonic() + seconds
    while True:
        try:
            with psycopg.connect(url, connect_timeout=2) as conn:
                conn.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture(scope="session")
def pg_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return
    problem = _docker_problem()
    if problem:
        pytest.skip(f"Postgres tests skipped: {problem}")
    name = f"arcana-test-pg-{uuid.uuid4().hex[:8]}"
    subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "-e", "POSTGRES_PASSWORD=test",
                    "-e", "POSTGRES_DB=arcana", "-p", "127.0.0.1::5432", PG_IMAGE],
                   check=True, capture_output=True)
    try:
        mapping = subprocess.run(["docker", "port", name, "5432/tcp"], check=True, capture_output=True,
                                 text=True).stdout.split()[0]
        url = f"postgresql://postgres:test@127.0.0.1:{mapping.rsplit(':', 1)[1]}/arcana"
        _wait_for(url)
        yield url
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


@pytest.fixture(scope="session")
def migrated(pg_url) -> Database:
    database = Database(pg_url)
    migrate(database, load_settings({}).migrations_dir)
    return database


@pytest.fixture
def db(migrated) -> Database:
    with migrated.connect() as conn:
        conn.execute("TRUNCATE " + ", ".join(APP_TABLES) + " RESTART IDENTITY CASCADE")
    return migrated



# --- task 8: the API with fakes on the test database ---
from dataclasses import replace as _replace  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.reader.provider import FakeProvider  # noqa: E402
from helpers import T_API, FakeTurnstile, MutableClock  # noqa: E402


def _client(app) -> TestClient:
    return TestClient(app, base_url="https://testserver")  # https: the guest cookie is Secure


def make_api(db, **settings_overrides):
    clock = MutableClock(T_API)
    reader = FakeProvider(model="fake-reader")
    guard = FakeProvider(model="fake-guard")
    turnstile = FakeTurnstile()
    settings = _replace(load_settings({}), database_url=db.url, first_token_timeout_s=0.3, guard_timeout_s=0.5,
                        run_migrations=False, **settings_overrides)
    app = create_app(settings, reader=reader, guard_provider=guard, turnstile=turnstile, clock=clock)
    return SimpleNamespace(app=app, ctx=app.state.ctx, client=_client(app), new_client=lambda: _client(app),
                           clock=clock, reader=reader, guard=guard, turnstile=turnstile, db=db)


@pytest.fixture
def api(db):
    return make_api(db)


@pytest.fixture
def api_factory(db):
    """The same API with other settings, e.g. api_factory(trust_cloudflare=True)."""
    return lambda **overrides: make_api(db, **overrides)
