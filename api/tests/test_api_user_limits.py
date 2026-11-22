"""Daily limits with accounts (spec 4.3 §5, stage 4.4b §2): a guest has 2 per device, a signed-in person 3 per
account on every device; a paid follow-up uses a slot of the reading's owner and gives it back there."""
import threading
import uuid
from datetime import timedelta

from app import limits, repo
from app.housekeeping import free_stale_followups
from app.reader.provider import FakeReply
from helpers import bearer, make_reading, parse_sse, post_reading

MX = "America/Mexico_City"
USER = uuid.UUID("5e0a6b7c-8d9e-4f01-a2b3-c4d5e6f7a8b9")


def used(api, subject: str) -> int:
    with api.db.connect() as conn:
        return limits.used(conn, subject, limits.local_day(limits.resolve_tz(MX), api.clock()))


def guest_rows(api) -> int:
    with api.db.connect() as conn:
        return conn.execute("SELECT count(*) AS n FROM usage WHERE subject LIKE 'guest:%'").fetchone()["n"]


def test_a_guest_has_two(api):
    assert [post_reading(api.client, kind="one", tz=MX).json()["remaining"] for _ in range(2)] == [1, 0]
    assert post_reading(api.client, kind="one", tz=MX).json() == {"reason": "limit", "remaining": 0}


def test_signed_in_has_three_per_account_on_every_device(api):
    phone, laptop = api.new_client(), api.new_client()
    token = bearer(USER)
    remaining = []
    for client in (phone, laptop, phone):
        api.clock.advance(minutes=1)  # one address: stay under the burst threshold (Turnstile after 5 a minute)
        remaining.append(post_reading(client, headers=token, kind="one", tz=MX).json()["remaining"])
    assert remaining == [2, 1, 0]
    api.clock.advance(minutes=1)
    fourth = post_reading(laptop, headers=token, kind="one", tz=MX)
    assert fourth.status_code == 429 and fourth.json() == {"reason": "limit", "remaining": 0}
    assert laptop.get("/api/limits", params={"tz": MX}, headers=token).json() == {
        "limit": 3, "used": 3, "remaining": 0, "day": "2026-11-20"}
    assert guest_rows(api) == 0
    assert laptop.get("/api/limits", params={"tz": MX}).json()["remaining"] == 2  # the device as a guest
    api.clock.advance(minutes=1)
    assert post_reading(laptop, kind="one", tz=MX).status_code == 201


def test_an_account_reading_is_kept_and_a_guest_reading_expires(api):
    mine = uuid.UUID(post_reading(api.client, headers=bearer(USER), kind="one", tz=MX).json()["id"])
    guest = uuid.UUID(post_reading(api.new_client(), kind="one", tz=MX).json()["id"])
    with api.db.connect() as conn:
        rows = {r["id"]: r for r in conn.execute("SELECT id, user_id, expires_at FROM readings").fetchall()}
    assert (rows[mine]["user_id"], rows[mine]["expires_at"]) == (USER, None)
    assert (rows[guest]["user_id"], rows[guest]["expires_at"]) == (None, api.clock() + timedelta(days=7))


def test_guest_slots_stay_with_the_guest_after_sign_in(api):
    for _ in range(2):
        post_reading(api.client, kind="one", tz=MX)
    assert post_reading(api.client, kind="one", tz=MX).status_code == 429
    signed_in = post_reading(api.client, headers=bearer(USER), kind="one", tz=MX)
    assert signed_in.status_code == 201 and signed_in.json()["remaining"] == 2
    assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 0


def test_a_crisis_answer_shows_what_the_account_has_left(api):
    post_reading(api.client, headers=bearer(USER), kind="one", tz=MX)
    response = post_reading(api.client, headers=bearer(USER), kind="one", question="I want to end my life", tz=MX)
    assert response.status_code == 200 and response.json()["remaining"] == 2
    assert used(api, limits.user_subject(USER)) == 1


def ask(client, reading_id, question="And one more?", **extra):
    return client.post(f"/api/readings/{reading_id}/followups", headers=bearer(USER),
                       json={"question": question, "tz": MX, **extra})


def account_reading_with_free_followups_used(client) -> str:
    created = post_reading(client, headers=bearer(USER), kind="one", tz=MX)
    reading_id = created.json()["id"]
    parse_sse(client.get(f"/api/readings/{reading_id}/stream", headers=bearer(USER)).text)
    for n in (1, 2):
        assert ask(client, reading_id, f"What helps, part {n}?").status_code == 200
    return reading_id


def test_a_paid_followup_uses_the_account_slot_from_any_device(api):
    reading_id = account_reading_with_free_followups_used(api.new_client())
    laptop = api.new_client()
    confirm = ask(laptop, reading_id)
    assert confirm.status_code == 402 and confirm.json() == {"reason": "confirm", "remaining": 2}
    events = parse_sse(ask(laptop, reading_id, use_reading=True).text)
    assert events[-1][1]["used_reading"] is True
    assert used(api, limits.user_subject(USER)) == 2 and guest_rows(api) == 0


def test_a_failed_paid_followup_gives_the_account_slot_back(api):
    reading_id = account_reading_with_free_followups_used(api.client)
    api.reader.replies.append(FakeReply(fail_after=0))
    events = parse_sse(ask(api.client, reading_id, use_reading=True).text)
    assert events[-1][1]["used_reading"] is False
    assert used(api, limits.user_subject(USER)) == 1


def test_a_stale_paid_followup_refunds_the_account(api):
    reading = make_reading(user_id=USER, expires_at=None, now=api.clock())
    day = limits.local_day(limits.resolve_tz(MX), api.clock())
    with api.db.connect() as conn:
        repo.insert_reading(conn, reading)
        limits.take_slot(conn, limits.user_subject(USER), day, limits.USER_DAILY_LIMIT)
        repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": reading["id"], "n": 3, "question": "Cut?",
                                    "paid_day": day, "created_at": api.clock() - timedelta(minutes=5)})
    assert free_stale_followups(api.db, api.clock()) == 1
    assert used(api, limits.user_subject(USER)) == 0 and guest_rows(api) == 0


# --- Fable plan review M5: the three-way race for the last reading of the day, with an account ---

def test_paid_followups_of_an_account_at_once_cannot_overspend_the_day(api):
    """test_api_followups.py races two requests since a guest has only two readings a day; the account's three keep
    the three-way race: two paid follow-ups and a new reading, from three devices, for the account's last reading."""
    first = account_reading_with_free_followups_used(api.new_client())
    second = account_reading_with_free_followups_used(api.new_client())  # two of the account's three are used
    api.guard.json_delay = 0.3  # all three requests wait in the guard, then race for the last reading
    start = threading.Barrier(3)
    codes = []

    def worker(action):
        start.wait()
        codes.append(action().status_code)

    actions = [lambda: ask(api.new_client(), first, use_reading=True),
               lambda: ask(api.new_client(), second, use_reading=True),
               lambda: post_reading(api.new_client(), headers=bearer(USER), kind="one", tz=MX,
                                    question="What helps me focus?")]
    threads = [threading.Thread(target=worker, args=(a,)) for a in actions]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len([c for c in codes if c in (200, 201)]) == 1 and len(codes) == 3
    assert used(api, limits.user_subject(USER)) == 3
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM followups WHERE paid_day IS NOT NULL").fetchone()["n"] + \
            conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 3
