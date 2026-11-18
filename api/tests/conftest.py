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
