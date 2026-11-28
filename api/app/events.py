"""Our own event counter (spec 2026-11-19 stage 4.4a §6). Only the events and parameters of
docs/design/analytics-events.md are accepted, each with exactly its listed parameters; nothing about the person is
stored — no address, no cookie, no account or device id (the address is used only, hashed and in memory, for the
burst limit in routes/events.py)."""
from datetime import datetime

from psycopg.types.json import Jsonb

from app.limits import utc_day

TOOLS = ("home", "one_card", "yes_no", "love", "daily", "three_cards")


def _one_of(*allowed):
    """A value equal to one of `allowed` and of the same JSON type (true is not 1, 1.0 is not 1)."""
    return lambda value: any(type(value) is type(item) and value == item for item in allowed)


def _ms(value) -> bool:
    return type(value) is int and 0 <= value <= 600_000


# name → (carries a tool?, {parameter: check}); every listed parameter is required, nothing else is accepted
EVENTS = {
    "tool_view": (True, {}),
    "draw_click": (True, {"has_question": _one_of(True, False), "entry": _one_of("tool", "card_page", "hub")}),
    "night_open": (True, {}),
    "cards_revealed": (True, {"cards_count": _one_of(1, 3)}),
    "reading_shown": (True, {"ms_from_draw": _ms}),
    "save_click": (True, {}),
    "signup_done": (False, {"method": _one_of("email", "google", "apple")}),
    "more_about_cards": (True, {}),
    "outcome_answered": (False, {"after_days": _one_of(7, 30), "answer": _one_of("yes", "partly", "no")}),
    "plus_view": (False, {"place": _one_of("limit", "diary")}),
    "remind_click": (True, {}),  # stage 4.4b §7: "Remind me tomorrow" under the Card of the Day
    # stage 8.1 §4 (migration 009): never the mark itself or the note — only that a mark was set, and where
    "daily_felt": (False, {"place": _one_of("daily", "calendar")}),
    "daily_calendar_view": (False, {"signed_in": _one_of(True, False)}),
    "push_enabled": (True, {}),  # "Remind me each morning" under the Card of the Day went through
    "push_click": (False, {}),   # the morning reminder was opened (sent by the service worker)
}
# events that belong to one tool only
ONLY_TOOL = {"remind_click": "daily", "push_enabled": "daily"}


class InvalidEvent(ValueError):
    """field: what was wrong, as in the 422 answer ("name", "tool", "params.<key>")."""

    def __init__(self, field: str):
        super().__init__(field)
        self.field = field


def check_event(name: str, tool: str | None, params: dict) -> None:
    if name not in EVENTS:
        raise InvalidEvent("name")
    with_tool, checks = EVENTS[name]
    if with_tool != (tool is not None) or (tool is not None and tool not in TOOLS):
        raise InvalidEvent("tool")
    if name in ONLY_TOOL and tool != ONLY_TOOL[name]:
        raise InvalidEvent("tool")
    for key in params:
        if key not in checks:
            raise InvalidEvent(f"params.{key}")
    for key, ok in checks.items():
        if key not in params or not ok(params[key]):
            raise InvalidEvent(f"params.{key}")


def record_event(conn, name: str, tool: str | None, lang: str, params: dict, now: datetime) -> None:
    conn.execute("INSERT INTO events (day, name, tool, lang, params, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                 (utc_day(now), name, tool, lang, Jsonb(params), now))
