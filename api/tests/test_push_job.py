"""Stage 8.1 (spec 2026-11-27 §2.5, §3): the morning reminder job — its hour, once a day, not when the card is open,
what the message says, and what a failed delivery does."""
import asyncio
import json
import os
import uuid
from dataclasses import replace
from datetime import date, datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import housekeeping, repo, webpush
from app.config import load_settings
from app.housekeeping import run_background
from app.push import due_day, send_due
from test_webpush import decrypt

VAPID = webpush.generate_vapid()
MX = "America/Mexico_City"
EIGHT_THIRTY_MX = datetime(2026, 11, 20, 14, 30, tzinfo=timezone.utc)  # 08:30 in Mexico City


class FakePost:
    def __init__(self, *statuses):
        self.statuses = list(statuses)
        self.calls: list[tuple[str, dict, bytes]] = []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, body))
        status = self.statuses.pop(0) if self.statuses else 201
        if isinstance(status, Exception):
            raise status
        return status


@pytest.fixture
def push_api(api_factory):
    api = api_factory(vapid_private_key=VAPID[0], vapid_public_key=VAPID[1])
    api.clock.now = EIGHT_THIRTY_MX
    return api


def subscribe(api, *, user_id=None, guest_id=None, hour=8, tz=MX, lang="en"):
    key = ec.generate_private_key(ec.SECP256R1())
    auth = webpush.b64url(os.urandom(16))
    endpoint = f"https://fcm.googleapis.com/fcm/send/{uuid.uuid4()}"
    if user_id is None and guest_id is None:
        guest_id = uuid.uuid4()
    with api.db.connect() as conn:
        repo.upsert_push(conn, {"user_id": user_id, "guest_id": guest_id, "endpoint": endpoint,
                                "p256dh": webpush.b64url(webpush._point(key.public_key())), "auth": auth,
                                "lang": lang, "tz": tz, "hour": hour, "now": api.clock()})
    return SimpleNamespace(key=key, auth=auth, endpoint=endpoint, guest_id=guest_id, user_id=user_id)


def run(api, post):
    return send_due(api.ctx, api.clock(), post=post)


def subs(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT fails, last_sent_day FROM push_subscriptions").fetchall()


def test_the_hour_is_the_subscribers_own():
    sub = {"tz": MX, "hour": 8, "last_sent_day": None}
    assert due_day(sub, datetime(2026, 11, 20, 13, 59, tzinfo=timezone.utc)) is None  # 07:59 there
    assert due_day(sub, EIGHT_THIRTY_MX) == date(2026, 11, 20)
    assert due_day(sub, datetime(2026, 11, 20, 16, 0, tzinfo=timezone.utc)) is None  # 10:00: the window is over
    assert due_day({**sub, "last_sent_day": date(2026, 11, 20)}, EIGHT_THIRTY_MX) is None
    assert due_day({**sub, "tz": "Europe/Madrid", "hour": 15}, EIGHT_THIRTY_MX) == date(2026, 11, 20)  # 15:30


def test_one_reminder_a_day_that_names_no_card(push_api):
    sub = subscribe(push_api, lang="es")
    post = FakePost()
    assert run(push_api, post) == {"sent": 1, "skipped": 0, "failed": 0, "deleted": 0}
    assert run(push_api, post)["sent"] == 0  # the next run of the same day
    [(url, headers, body)] = post.calls
    assert url == sub.endpoint and headers["Authorization"].startswith("vapid t=")
    assert json.loads(decrypt(body, sub.key, sub.auth)) == {"lang": "es"}  # only the language, never the card
    assert subs(push_api) == [{"fails": 0, "last_sent_day": date(2026, 11, 20)}]
    push_api.clock.advance(days=1)
    assert run(push_api, post)["sent"] == 1


def test_no_reminder_when_the_card_is_already_open(push_api):
    sub = subscribe(push_api)
    with push_api.db.connect() as conn:
        repo.record_daily_draw(conn, sub.guest_id, date(2026, 11, 20), "major-18-moon", False)
    post = FakePost()
    assert run(push_api, post)["skipped"] == 1 and post.calls == []
    assert run(push_api, post)["skipped"] == 0  # the day is marked: not looked at again


def test_an_accounts_open_card_counts_on_any_device(push_api):
    user = uuid.uuid4()
    subscribe(push_api, user_id=user)
    with push_api.db.connect() as conn:
        repo.account_daily_draw(conn, user, date(2026, 11, 20), "major-18-moon", False)
    assert run(push_api, FakePost())["skipped"] == 1


def test_a_gone_subscription_is_deleted_at_once(push_api):
    subscribe(push_api)
    assert run(push_api, FakePost(410))["deleted"] == 1 and subs(push_api) == []


def test_three_failures_in_a_row_delete_and_a_success_resets(push_api):
    subscribe(push_api)
    post = FakePost(500, httpx.ConnectError("down"), 201, 503, 429, 500)
    for expected in (1, 2, 0, 1, 2):
        run(push_api, post)
        assert subs(push_api)[0]["fails"] == expected
        push_api.clock.advance(days=1)
    assert run(push_api, post)["deleted"] == 1 and subs(push_api) == []


def test_a_refused_vapid_key_is_logged_and_never_counted(push_api, caplog):
    subscribe(push_api)
    with caplog.at_level("ERROR", logger="arcana.push"):
        for _ in range(4):
            run(push_api, FakePost(403))
            push_api.clock.advance(days=1)
    assert subs(push_api)[0]["fails"] == 0 and "VAPID" in caplog.text


def test_without_keys_nothing_is_sent(api):
    api.clock.now = EIGHT_THIRTY_MX
    subscribe(api)
    post = FakePost()
    assert run(api, post) == {"sent": 0, "skipped": 0, "failed": 0, "deleted": 0} and post.calls == []


def test_the_job_starts_only_with_keys(db, monkeypatch):
    started = []

    async def fake(*args, **kwargs):
        started.append(args[-1] if args else None)

    async def fake_push(ctx, interval_s):
        started.append(("push", interval_s))

    monkeypatch.setattr(housekeeping, "daily_loop", fake)
    monkeypatch.setattr(housekeeping, "cleanup_loop", fake)
    monkeypatch.setattr(housekeeping, "push_loop", fake_push)
    settings = replace(load_settings({}), database_url=db.url, run_migrations=False, daily_job_interval_s=0.0)
    keys = webpush.load_vapid(*VAPID)
    asyncio.run(run_background(SimpleNamespace(settings=settings, db=db, clock=lambda: EIGHT_THIRTY_MX, vapid=keys)))
    assert ("push", 600.0) in started
    started.clear()
    asyncio.run(run_background(SimpleNamespace(settings=settings, db=db, clock=lambda: EIGHT_THIRTY_MX, vapid=None)))
    assert all(not (isinstance(s, tuple) and s[0] == "push") for s in started)
