"""Shared helpers for API tests."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_tool(name: str):
    """Import tools/cards/<name>.py by file path (tools/ is not a package)."""
    path = REPO / "tools/cards" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"tools_cards_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- task 3: readings for DB tests ---
import uuid  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

T0 = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def make_reading(**overrides) -> dict:
    now = overrides.pop("now", T0)
    reading = {
        "id": uuid.uuid4(), "guest_id": uuid.uuid4(), "lang": "en", "kind": "three",
        "question": "What should I focus on at work?", "topic": "work", "situation": None, "source_card_id": None,
        "cards": [{"card_id": "major-00-fool", "position": "past", "reversed": False},
                  {"card_id": "major-18-moon", "position": "present", "reversed": True},
                  {"card_id": "cups-02-two", "position": "path", "reversed": False}],
        "seed": "test-seed", "verdict": None, "guard_group": "ok",
        "created_at": now, "expires_at": now + timedelta(days=7),
    }
    reading.update(overrides)
    return reading


# --- task 8: API tests ---
import json  # noqa: E402

T_API = datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)  # 12:00 in Mexico City, 19:00 in Madrid


class MutableClock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)


class FakeTurnstile:
    def __init__(self, valid=("good-token",)):
        self.valid = set(valid)
        self.calls: list[str | None] = []

    def verify(self, token) -> bool:
        self.calls.append(token)
        return token in self.valid


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        lines = block.split("\n")
        name = next(line[len("event: "):] for line in lines if line.startswith("event: "))
        data = json.loads(next(line[len("data: "):] for line in lines if line.startswith("data: ")))
        events.append((name, data))
    return events


def stream_sections(events) -> dict[str, str]:
    """Sections as the site builds them from `text` events."""
    out: dict[str, str] = {}
    for name, data in events:
        if name == "text":
            out[data["name"]] = out.get(data["name"], "") + data["text"]
    return {k: v.strip() for k, v in out.items() if v.strip()}


def post_reading(client, headers=None, **body):
    return client.post("/api/readings", json={"lang": "en", "kind": "three", **body}, headers=headers or {})


def dump_tables(db) -> str:
    from app.db import APP_TABLES
    with db.connect() as conn:
        rows = [r["t"] for table in APP_TABLES
                for r in conn.execute(f"SELECT row_to_json(x)::text AS t FROM {table} x").fetchall()]
    return "\n".join(rows)


def guest_headers(guest_id) -> dict:
    return {"Cookie": f"ad_guest={guest_id}"}


def from_ip(ip: str) -> dict:
    """What Caddy sends: X-Real-IP is always overwritten with the TCP peer address."""
    return {"X-Real-IP": ip}


# --- stage 4.3: signed-in requests (spec 2026-11-19 §12: a local ES256 key, no network) ---
import time  # noqa: E402

import jwt  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from jwt.algorithms import ECAlgorithm  # noqa: E402

AUTH_URL = "https://test-project.supabase.co"
AUTH_ISSUER = f"{AUTH_URL}/auth/v1"
TEST_KID = "test-key-1"
TEST_KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_KEY = ec.generate_private_key(ec.SECP256R1())


def jwk(private_key, kid: str = TEST_KID) -> dict:
    """The public half as Supabase publishes it in its JWKS."""
    return {**ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True), "kid": kid, "alg": "ES256", "use": "sig"}


def jwks(*keys: dict) -> dict:
    return {"keys": list(keys) or [jwk(TEST_KEY)]}


class FakeJwks:
    """Stands in for GET <SUPABASE_URL>/auth/v1/.well-known/jwks.json; fail=True: the keys cannot be reached."""

    def __init__(self, keyset: dict | None = None, fail: bool = False):
        self.keyset = keyset or jwks()
        self.fail = fail
        self.calls = 0

    def __call__(self) -> dict:
        self.calls += 1
        if self.fail:
            raise OSError("no network in tests")
        return self.keyset


def make_token(user_id, email: str | None = "person@example.com", *, key=None, kid: str | None = TEST_KID,
               aud: str = "authenticated", iss: str = AUTH_ISSUER, expires_in: int = 3600, alg: str = "ES256",
               **claims) -> str:
    """A Supabase-like access token signed with the test key (or `key`)."""
    now = int(time.time())
    payload = {"sub": str(user_id), "email": email, "aud": aud, "iss": iss, "iat": now, "exp": now + expires_in,
               "role": "authenticated", **claims}
    return jwt.encode(payload, key or TEST_KEY, algorithm=alg, headers={"kid": kid} if kid else None)


def bearer(user_id, **kwargs) -> dict:
    return {"Authorization": f"Bearer {make_token(user_id, **kwargs)}"}



def supabase_like(url: str) -> bool:
    """Stage 4.3 §10: the fixtures empty every table they use, so a Supabase database is refused by default."""
    lowered = url.lower()
    return "supabase.co" in lowered or "pooler.supabase.com" in lowered
