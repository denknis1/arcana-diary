"""Stage 8.1 (spec 2026-11-27 §2.2-§2.4, §3, §4): the calendar of the Card of the Day and the evening mark."""
import uuid
from datetime import date, datetime, timezone

import pytest

from app import repo
from app.daily import fill_daily_cache
from app.draw import daily_draw
from app.reader import fallback
from helpers import bearer, dump_tables, guest_headers

MX = "America/Mexico_City"
ANA = uuid.UUID("8a1b2c3d-0000-4000-8000-000000000011")
BEN = uuid.UUID("8a1b2c3d-0000-4000-8000-000000000012")


def open_card(api, user=None, guest=None, lang="en"):
    headers = bearer(user) if user else guest_headers(guest)
    response = api.new_client().get("/api/daily", params={"lang": lang, "tz": MX}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def calendar(api, user=None, guest=None, **params):
    headers = bearer(user) if user else (guest_headers(guest) if guest else {})
    return api.new_client().get("/api/daily/calendar", params={"lang": "en", "tz": MX, **params}, headers=headers)


def mark(api, user, day, body):
    return api.new_client().put(f"/api/daily/{day}", json=body, headers=bearer(user) if user else {})


def days_in_a_row(api, n, **who):
    for i in range(n):
        if i:
            api.clock.advance(days=1)
        open_card(api, **who)


def test_the_month_has_each_day_with_its_card_text_mark_and_note(api):
    days_in_a_row(api, 3, user=ANA)  # the 20th, 21st, 22nd of November in Mexico City
    assert mark(api, ANA, "2026-11-21", {"felt": "partly", "note": "Kept the word: patience."}).status_code == 200
    body = calendar(api, user=ANA, month="2026-11").json()
    assert (body["guest"], body["month"], body["months"], body["locked"]) == (False, "2026-11", ["2026-10", "2026-11"],
                                                                            False)
    assert (body["today"], body["streak"], body["best_streak"]) == ("2026-11-22", 3, 3)
    assert [d["day"] for d in body["days"]] == ["2026-11-20", "2026-11-21", "2026-11-22"]
    second = body["days"][1]
    card_id, reversed_ = daily_draw(str(ANA), date(2026, 11, 21), api.ctx.cards.order)
    assert second["card"] == {"card_id": card_id, "name": api.ctx.cards.name(card_id, "en"), "reversed": reversed_}
    assert (second["felt"], second["note"]) == ("partly", "Kept the word: patience.")
    assert body["days"][0]["felt"] is None and body["days"][0]["note"] is None


def test_a_days_text_is_the_cached_one_then_the_card_base(api):
    open_card(api, user=ANA)
    card_id, reversed_ = daily_draw(str(ANA), date(2026, 11, 20), api.ctx.cards.order)
    [first] = calendar(api, user=ANA).json()["days"]
    [ex] = api.ctx.cards.excerpts([{"card_id": card_id, "position": "card", "reversed": reversed_}], "en", None)
    assert (first["source"], first["text"]) == ("fallback", fallback.daily_fallback(ex))
    fill_daily_cache(api.ctx, date(2026, 11, 20), [card_id])
    [cached] = calendar(api, user=ANA).json()["days"]
    assert cached["source"] == "cache" and cached["text"] != first["text"]


def test_the_month_defaults_to_this_one_and_the_free_calendar_is_two_months(api):
    open_card(api, user=ANA)
    assert calendar(api, user=ANA).json()["month"] == "2026-11"
    october = calendar(api, user=ANA, month="2026-10").json()
    assert (october["locked"], october["days"]) == (False, [])
    september = calendar(api, user=ANA, month="2026-09").json()
    assert (september["locked"], september["days"], september["streak"]) == (True, [], 1)  # kept, for Plus


def test_an_old_month_is_kept_but_locked(api):
    api.clock.now = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)
    open_card(api, user=ANA)
    api.clock.now = datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)
    assert calendar(api, user=ANA, month="2026-08").json()["locked"] is True
    with api.db.connect() as conn:
        assert repo.draw_days(conn, ANA, None) == [date(2026, 8, 10)]


@pytest.mark.parametrize("month", ["2026-13", "11-2026", "2026-1", "x", "0000-01", "9999-12", "2025-12", "2101-01", "２０２６-11", "٢٠٢٦-11"])
def test_a_bad_month_is_422(api, month):
    response = calendar(api, user=ANA, month=month)
    assert response.status_code == 422 and response.json()["fields"] == ["month"]


def test_the_most_frequent_card_needs_two(api):
    open_card(api, user=ANA)
    assert calendar(api, user=ANA).json()["top_card"] is None
    card_id, reversed_ = daily_draw(str(ANA), date(2026, 11, 20), api.ctx.cards.order)
    with api.db.connect() as conn:
        conn.execute("INSERT INTO daily_draws (user_id, day, card_id, reversed) VALUES (%s, %s, %s, %s)",
                     (ANA, date(2026, 11, 3), card_id, not reversed_))
    top = calendar(api, user=ANA).json()["top_card"]
    assert top == {"card_id": card_id, "name": api.ctx.cards.name(card_id, "en"), "count": 2}


def test_a_guest_sees_the_last_seven_days_without_marks(api):
    guest = uuid.uuid4()
    days_in_a_row(api, 9, guest=guest)  # the 20th to the 28th
    body = calendar(api, guest=guest, month="2026-10").json()  # the month is ignored for a guest
    assert (body["guest"], body["today"], body["streak"], body["best_streak"]) == (True, "2026-11-28", 9, 9)
    assert [d["day"] for d in body["days"]] == [f"2026-11-{n}" for n in range(22, 29)]
    assert all(set(d) == {"day", "card", "text", "source"} for d in body["days"])


def test_a_new_guest_has_an_empty_calendar_and_gets_the_cookie(api):
    response = calendar(api)
    assert response.status_code == 200 and response.json()["days"] == [] and "ad_guest=" in response.headers["set-cookie"]


def test_the_mark_sets_changes_and_clears(api):
    open_card(api, user=ANA)
    first = mark(api, ANA, "2026-11-20", {"felt": "yes"}).json()
    assert (first["felt"], first["note"]) == ("yes", None) and first["noted_at"]
    both = mark(api, ANA, "2026-11-20", {"note": "  The talk went well.  "}).json()
    assert (both["felt"], both["note"]) == ("yes", "  The talk went well.  ")  # stored exactly as sent
    cleared = mark(api, ANA, "2026-11-20", {"felt": None, "note": "   "}).json()
    assert (cleared["felt"], cleared["note"], cleared["noted_at"]) == (None, None, None)
    unchanged = mark(api, ANA, "2026-11-20", {}).json()
    assert (unchanged["felt"], unchanged["note"]) == (None, None)


def test_the_mark_needs_an_account_and_a_card_that_day(api):
    guest = uuid.uuid4()
    open_card(api, guest=guest)
    assert mark(api, None, "2026-11-20", {"felt": "yes"}).json() == {"reason": "sign_in"}
    open_card(api, user=ANA)
    assert mark(api, ANA, "2026-11-19", {"felt": "yes"}).status_code == 404  # no card that day
    assert mark(api, BEN, "2026-11-20", {"felt": "yes"}).status_code == 404  # another account's day
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM daily_draws WHERE user_id = %s", (BEN,)).fetchone()["n"] == 0


@pytest.mark.parametrize("body, field", [
    ({"felt": "maybe"}, "felt"),
    ({"note": "x" * 281}, "note"),
    ({"note": "a\x00b"}, "note"),
    ({"felt": "yes", "mood": "fine"}, "mood"),
])
def test_a_bad_mark_is_422(api, body, field):
    open_card(api, user=ANA)
    response = mark(api, ANA, "2026-11-20", body)
    assert response.status_code == 422 and response.json()["fields"] == [field]


def test_a_note_of_280_characters_fits_and_is_never_in_an_event_or_a_model_call(api):
    open_card(api, user=ANA)
    note = "é" * 280
    assert mark(api, ANA, "2026-11-20", {"note": note}).status_code == 200
    with api.db.connect() as conn:
        events = conn.execute("SELECT count(*) AS n FROM events").fetchone()["n"]
    assert events == 0 and api.reader.stream_calls() == []
    assert note in dump_tables(api.db)  # only in daily_draws
