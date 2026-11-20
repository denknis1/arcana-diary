"""POST /api/events (spec 2026-11-19 stage 4.4a §6): only the events and parameters of
docs/design/analytics-events.md, nothing about the person, a burst limit per address."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.config import EVENTS_PER_MINUTE
from app.routes import events as events_route
from helpers import from_ip, guest_headers

VALID = [
    {"name": "tool_view", "tool": "home", "lang": "en", "params": {}},
    {"name": "draw_click", "tool": "yes_no", "lang": "es", "params": {"has_question": True, "entry": "tool"}},
    {"name": "draw_click", "tool": "one_card", "lang": "en", "params": {"has_question": False, "entry": "card_page"}},
    {"name": "night_open", "tool": "love", "lang": "en", "params": {}},
    {"name": "cards_revealed", "tool": "home", "lang": "en", "params": {"cards_count": 3}},
    {"name": "reading_shown", "tool": "one_card", "lang": "es", "params": {"ms_from_draw": 5400}},
    {"name": "save_click", "tool": "home", "lang": "en", "params": {}},
    {"name": "signup_done", "lang": "en", "params": {"method": "email"}},
    {"name": "more_about_cards", "tool": "yes_no", "lang": "en", "params": {}},
    {"name": "outcome_answered", "lang": "es", "params": {"after_days": 7, "answer": "partly"}},
    {"name": "plus_view", "lang": "en", "params": {"place": "limit"}},
    {"name": "tool_view", "tool": "daily", "lang": "es"},
]

INVALID = [
    ({"name": "page_view", "tool": "home", "lang": "en"}, "name"),
    ({"name": "tool_view", "lang": "en"}, "tool"),
    ({"name": "tool_view", "tool": "diary", "lang": "en"}, "tool"),
    ({"name": "plus_view", "tool": "home", "lang": "en", "params": {"place": "limit"}}, "tool"),
    ({"name": "tool_view", "tool": "home", "lang": "en", "params": {"question": "Will he call?"}}, "params.question"),
    ({"name": "draw_click", "tool": "home", "lang": "en", "params": {"has_question": True}}, "params.entry"),
    ({"name": "draw_click", "tool": "home", "lang": "en", "params": {"has_question": "yes", "entry": "tool"}},
     "params.has_question"),
    ({"name": "cards_revealed", "tool": "home", "lang": "en", "params": {"cards_count": True}}, "params.cards_count"),
    ({"name": "cards_revealed", "tool": "home", "lang": "en", "params": {"cards_count": 2}}, "params.cards_count"),
    ({"name": "reading_shown", "tool": "home", "lang": "en", "params": {"ms_from_draw": -1}}, "params.ms_from_draw"),
    ({"name": "reading_shown", "tool": "home", "lang": "en", "params": {"ms_from_draw": 1.5}}, "params.ms_from_draw"),
    ({"name": "outcome_answered", "lang": "en", "params": {"after_days": 14, "answer": "yes"}}, "params.after_days"),
]


def rows(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT * FROM events ORDER BY created_at, name").fetchall()


@pytest.mark.parametrize("body", VALID, ids=[f"{b['name']}-{i}" for i, b in enumerate(VALID)])
def test_a_listed_event_is_stored(api, body):
    response = api.client.post("/api/events", json=body)
    assert response.status_code == 204 and response.content == b""
    [row] = rows(api)
    assert (row["name"], row["tool"], row["lang"], row["params"]) == (body["name"], body.get("tool"), body["lang"],
                                                                      body.get("params", {}))
    assert row["day"].isoformat() == "2026-11-20"


@pytest.mark.parametrize("body,field", INVALID, ids=[f for _, f in INVALID])
def test_anything_else_is_refused_and_not_stored(api, body, field):
    response = api.client.post("/api/events", json=body)
    assert response.status_code == 422
    assert response.json() == {"reason": "invalid", "fields": [field]}
    assert rows(api) == []


def test_a_wrong_language_is_refused(api):
    response = api.client.post("/api/events", json={"name": "tool_view", "tool": "home", "lang": "fr"})
    assert response.status_code == 422 and rows(api) == []


def test_no_address_cookie_or_id_is_kept(api):
    headers = {**from_ip("203.0.113.77"), **guest_headers("4d5e6f70-0000-4000-8000-0000000000aa")}
    response = api.client.post("/api/events", json=VALID[1], headers=headers)
    assert response.status_code == 204
    assert "set-cookie" not in response.headers
    with api.db.connect() as conn:
        columns = [r["column_name"] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'events' ORDER BY ordinal_position")]
        dump = conn.execute("SELECT row_to_json(e)::text AS t FROM events e").fetchone()["t"]
    assert columns == ["id", "day", "name", "tool", "lang", "params", "created_at"]
    assert "203.0.113" not in dump and "4d5e6f70" not in dump


def test_a_new_visitor_gets_no_guest_cookie(api):
    response = api.client.post("/api/events", json=VALID[0])
    assert response.status_code == 204 and "set-cookie" not in response.headers


def test_a_burst_from_one_address_is_cut(api):
    here, there = from_ip("198.51.100.7"), from_ip("198.51.100.8")
    statuses = [api.client.post("/api/events", json=VALID[0], headers=here).status_code
                for _ in range(EVENTS_PER_MINUTE + 1)]
    assert statuses == [204] * EVENTS_PER_MINUTE + [429]
    assert api.client.post("/api/events", json=VALID[0], headers=here).json() == {"reason": "rate"}
    assert api.client.post("/api/events", json=VALID[0], headers=there).status_code == 204
    api.clock.advance(seconds=61)
    assert api.client.post("/api/events", json=VALID[0], headers=here).status_code == 204
    assert len(rows(api)) == EVENTS_PER_MINUTE + 2


def test_a_flood_from_many_addresses_is_cut(api, monkeypatch):
    monkeypatch.setattr(events_route, "EVENTS_GLOBAL_PER_MINUTE", 3)
    statuses = [api.client.post("/api/events", json=VALID[0], headers=from_ip(f"198.51.100.{i}")).status_code
                for i in range(5)]
    assert statuses == [204, 204, 204, 429, 429]
    assert len(rows(api)) == 3


def test_a_bad_token_is_refused_before_anything(api):
    response = api.client.post("/api/events", json=VALID[0], headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401 and rows(api) == []


def test_the_funnel_query_of_the_readme_counts_the_steps(api):
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    sql = readme.split("## Счётчик событий (этап 4.4а)", 1)[1].split("```sql\n", 1)[1].split("```", 1)[0]
    assert api.client.post("/api/events", json=VALID[0]).status_code == 204  # the closed stage: not counted
    api.clock.now = datetime(2026, 12, 15, 18, 0, tzinfo=timezone.utc)
    for body in (VALID[0], VALID[0], {**VALID[1], "tool": "home"}, VALID[4],
                 {"name": "reading_shown", "tool": "home", "lang": "en", "params": {"ms_from_draw": 900}},
                 {"name": "draw_click", "tool": "home", "lang": "en", "params": {"has_question": False, "entry": "tool"}}):
        assert api.client.post("/api/events", json=body).status_code == 204
    with api.db.connect() as conn:
        rows = conn.execute(sql, {"day_from": "2026-11-01", "day_to": "2026-12-31"}).fetchall()
    assert [(r["tool"], r["lang"], r["views"], r["draws"], r["shown"], r["saves"], float(r["shown_pct"])) for r in rows] == [
        ("home", "en", 2, 1, 1, 0, 100.0), ("home", "es", 0, 1, 0, 0, 0.0)]
