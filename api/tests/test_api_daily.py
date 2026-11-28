import uuid
from datetime import date, datetime, timezone

from app.daily import fill_daily_cache
from app.draw import daily_draw
from app.reader import fallback
from helpers import from_ip, guest_headers

MX = "America/Mexico_City"


def daily(api, guest, lang="en", tz=MX, client=None):
    response = (client or api.new_client()).get("/api/daily", params={"lang": lang, "tz": tz},
                                                headers=guest_headers(guest))
    assert response.status_code == 200, response.text
    return response.json()


def twins(order, day):
    """Two guest ids whose card of the day is the same card in the same orientation."""
    seen = {}
    for i in range(1, 5000):
        guest = uuid.UUID(int=i)
        card = daily_draw(str(guest), day, order)
        if card in seen:
            return seen[card], guest
        seen[card] = guest
    raise AssertionError("no two guests share a card")


def prefill(api, guest, day):
    card_id, _ = daily_draw(str(guest), day, api.ctx.cards.order)
    fill_daily_cache(api.ctx, day, [card_id])


def test_daily_text_comes_from_the_cache_all_day(api):
    guest = uuid.uuid4()
    prefill(api, guest, date(2026, 11, 20))
    calls = len(api.reader.stream_calls())
    first = daily(api, guest)
    api.clock.advance(hours=5)  # 23:00 UTC, 17:00 in Mexico City: still the 20th there
    second = daily(api, guest)
    assert first["card"] == second["card"] and first["day"] == second["day"] == "2026-11-20"
    assert (first["source"], second["source"]) == ("cache", "cache") and first["text"] == second["text"]
    assert first["prompt_version"] == "daily.en.v4"
    assert len(api.reader.stream_calls()) == calls  # a request never calls the model


def test_daily_miss_serves_base_meanings_at_once(api):
    guest = uuid.uuid4()
    first = daily(api, guest, lang="es")
    card_id, reversed_ = daily_draw(str(guest), date(2026, 11, 20), api.ctx.cards.order)
    [ex] = api.ctx.cards.excerpts([{"card_id": card_id, "position": "card", "reversed": reversed_}], "es", None)
    assert first["source"] == "fallback" and first["text"] == fallback.daily_fallback(ex)
    assert api.reader.stream_calls() == []


def test_daily_cache_shared_between_guests(api):
    a, b = twins(api.ctx.cards.order, date(2026, 11, 20))
    prefill(api, a, date(2026, 11, 20))
    first, second = daily(api, a), daily(api, b)
    assert first["card"] == second["card"] and first["text"] == second["text"]


def test_daily_new_card_and_text_after_local_midnight(api):
    guest = uuid.uuid4()
    order = api.ctx.cards.order
    api.clock.now = datetime(2026, 11, 21, 5, 30, tzinfo=timezone.utc)  # 23:30 on the 20th in Mexico City
    prefill(api, guest, date(2026, 11, 20))
    before = daily(api, guest)
    api.clock.advance(hours=1)  # 00:30 on the 21st
    after = daily(api, guest)
    assert (before["day"], after["day"]) == ("2026-11-20", "2026-11-21")
    assert (before["card"]["card_id"], before["card"]["reversed"]) == daily_draw(str(guest), date(2026, 11, 20), order)
    assert (after["card"]["card_id"], after["card"]["reversed"]) == daily_draw(str(guest), date(2026, 11, 21), order)
    assert before["source"] == "cache"  # the text follows the local day, not the UTC day
    with api.db.connect() as conn:
        n = conn.execute("SELECT count(*) AS n FROM daily_draws WHERE guest_id = %s", (guest,)).fetchone()["n"]
    assert n == 2


def test_daily_does_not_count_and_new_guests_leave_no_draw(api):
    response = api.client.get("/api/daily", params={"lang": "es", "tz": MX})
    assert response.status_code == 200 and "ad_guest=" in response.headers["set-cookie"]
    assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 2
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM daily_draws").fetchone()["n"] == 0


def test_daily_is_rate_limited_per_address(api):
    client = api.new_client()
    codes = [client.get("/api/daily", params={"lang": "en"}, headers=from_ip("198.51.100.77")).status_code
             for _ in range(31)]
    assert codes == [200] * 30 + [429]
    assert client.get("/api/daily", params={"lang": "en"}, headers=from_ip("198.51.100.77")).json() == {
        "reason": "rate"}
    assert client.get("/api/daily", params={"lang": "en"}, headers=from_ip("198.51.100.78")).status_code == 200


def test_daily_lang_is_required(api):
    assert api.client.get("/api/daily").status_code == 422
    assert api.client.get("/api/daily", params={"lang": "fr"}).status_code == 422


# --- stage 8.1: the card by account, streaks, the mark (spec 2026-11-27 §2, §3) ---

import psycopg  # noqa: E402
import pytest  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.db import Database, split_sql  # noqa: E402
from conftest import make_api  # noqa: E402
from helpers import bearer  # noqa: E402

ANA = uuid.UUID("8a1b2c3d-0000-4000-8000-000000000001")


def signed_in(api, user, client=None, lang="en"):
    response = (client or api.new_client()).get("/api/daily", params={"lang": lang, "tz": MX}, headers=bearer(user))
    assert response.status_code == 200, response.text
    return response.json()


def test_signed_in_the_card_is_the_accounts_on_every_device(api):
    phone, laptop = signed_in(api, ANA), signed_in(api, ANA)  # two clients: two guest cookies
    expected = daily_draw(str(ANA), date(2026, 11, 20), api.ctx.cards.order)
    assert (phone["card"]["card_id"], phone["card"]["reversed"]) == expected
    assert phone["card"] == laptop["card"] and phone["mark"] == {"felt": None, "note": None}
    with api.db.connect() as conn:
        rows = conn.execute("SELECT guest_id, user_id FROM daily_draws").fetchall()
    assert rows == [{"guest_id": None, "user_id": ANA}]  # an account row keeps no device


def test_a_guest_streak_counts_days_in_a_row_and_a_missed_day_starts_again(api):
    guest = uuid.uuid4()
    seen = []
    for step in (0, 1, 1, 2, 1):  # the 20th, 21st, 22nd, a missed 23rd, the 24th, 25th
        api.clock.advance(days=step)
        seen.append((daily(api, guest)["streak"], daily(api, guest)["best_streak"]))
    assert seen == [(1, 1), (2, 2), (3, 3), (1, 3), (2, 3)]


def test_a_new_guest_gets_day_one_and_no_mark(api):
    body = api.client.get("/api/daily", params={"lang": "en", "tz": MX}).json()
    assert (body["streak"], body["best_streak"], body["mark"]) == (1, 1, None)


def test_a_returning_guest_has_no_mark(api):
    assert daily(api, uuid.uuid4())["mark"] is None


def test_the_account_streak_spans_devices(api):
    signed_in(api, ANA)
    api.clock.advance(days=1)
    assert signed_in(api, ANA)["streak"] == 2


def test_a_deleted_account_gets_no_card(api):
    assert api.client.request("DELETE", "/api/account", json={"confirm": "DELETE"}, headers=bearer(ANA)).status_code == 200
    response = api.new_client().get("/api/daily", params={"lang": "en", "tz": MX}, headers=bearer(ANA))
    assert response.status_code == 401
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM daily_draws").fetchone()["n"] == 0


@pytest.fixture
def db_before_009(pg_url):
    """The live database before stage 8.1: migrations 001-008 only."""
    name = f"pre009_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(pg_url, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {name}")
    database = Database(pg_url.rsplit("/", 1)[0] + "/" + name)
    migrations = load_settings({}).migrations_dir
    with database.connect() as conn:
        for path in sorted(migrations.glob("00[1-8]_*.sql")):
            for statement in split_sql(path.read_text(encoding="utf-8")):
                conn.execute(statement)
    yield database
    with psycopg.connect(pg_url, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE {name} WITH (FORCE)")


def test_before_009_the_card_answers_503_not_500(db_before_009):
    """The review of 008: new code on a database whose migration has not run yet answers 503 (the site then shows
    the card from the card base), never 500."""
    api = make_api(db_before_009)
    guest = api.new_client().get("/api/daily", params={"lang": "en", "tz": MX}, headers=guest_headers(uuid.uuid4()))
    account = api.new_client().get("/api/daily", params={"lang": "en", "tz": MX}, headers=bearer(ANA))
    assert (guest.status_code, guest.json()) == (503, {"reason": "db"})
    assert (account.status_code, account.json()) == (503, {"reason": "db"})
