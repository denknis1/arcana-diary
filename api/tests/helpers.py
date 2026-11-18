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
