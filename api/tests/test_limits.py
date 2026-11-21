import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import Response
from starlette.requests import Request

from app import limits, repo
from app.limits import (BurstCounter, DailySalt, LimitReached, client_country, client_ip, give_back_slot,
                        guest_from_request, guest_quota, guest_subject, ip_blocked, ip_key, ip_subject, local_day,
                        needs_turnstile,
                        parse_guest_id, remaining, resolve_tz, set_guest_cookie, take_followup_attempt,
                        take_reading_slots, take_slot, used)
from helpers import make_reading

GID = uuid.UUID("6f1c2a54-0c1e-4c8e-9a51-2a8f8d1e7b10")
DAY = date(2026, 11, 20)


def make_request(headers: dict[str, str] | None = None, client=("203.0.113.9", 5000)) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "client": client,
                    "query_string": b""})


@pytest.mark.parametrize("value, expected", [(str(GID), GID), ("garbage", None), ("", None), (None, None)])
def test_parse_guest_id(value, expected):
    assert parse_guest_id(value) == expected


def test_guest_cookie_attributes():
    response = Response()
    set_guest_cookie(response, GID)
    header = response.headers["set-cookie"].lower()
    assert header.startswith(f"ad_guest={GID}")
    for part in ("httponly", "secure", "samesite=lax", "max-age=31536000", "path=/"):
        assert part in header


def test_guest_from_request():
    assert guest_from_request(make_request({"cookie": f"ad_guest={GID}"})) == (GID, False)
    new_id, is_new = guest_from_request(make_request())
    assert is_new and isinstance(new_id, uuid.UUID) and new_id != GID


@pytest.mark.parametrize("name, expected", [
    ("America/Mexico_City", "America/Mexico_City"), ("Europe/Madrid", "Europe/Madrid"), ("Mars/Olympus", "UTC"),
    ("America/Buenos_Aires", "America/Argentina/Buenos_Aires"), ("", "UTC"), (None, "UTC"), ("../../etc/passwd", "UTC"),
    ("/etc/passwd", "UTC"),
])
def test_resolve_tz(name, expected):
    assert resolve_tz(name).key == expected


def test_local_day_follows_timezone():
    now = datetime(2026, 11, 21, 5, 30, tzinfo=timezone.utc)
    assert local_day(resolve_tz("America/Mexico_City"), now) == date(2026, 11, 20)
    assert local_day(resolve_tz("Europe/Madrid"), now) == date(2026, 11, 21)
    assert local_day(resolve_tz(None), now) == date(2026, 11, 21)


@pytest.mark.parametrize("hits, ip_count, expected", [(5, 19, False), (6, 0, True), (1, 20, True), (1, 19, False)])
def test_needs_turnstile(hits, ip_count, expected):
    assert needs_turnstile(hits, ip_count) is expected


def test_ip_hard_cap():
    assert limits.IP_HARD_LIMIT == 60
    assert (ip_blocked(59), ip_blocked(60)) == (False, True)


def test_daily_salt_hash():
    salt = DailySalt()
    now = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
    h = salt.hash_ip("198.51.100.4", now)
    assert len(h) == 64 and "198.51.100.4" not in h
    assert salt.hash_ip("198.51.100.4", now + timedelta(hours=5)) == h
    assert salt.hash_ip("198.51.100.5", now) != h


def test_daily_salt_changes_at_utc_midnight():
    salt = DailySalt()
    day1 = datetime(2026, 11, 20, 23, 59, tzinfo=timezone.utc)
    h1 = salt.hash_ip("198.51.100.4", day1)
    old = salt._salt
    h2 = salt.hash_ip("198.51.100.4", day1 + timedelta(minutes=2))
    assert h2 != h1 and salt._salt != old


@pytest.mark.parametrize("ip, expected", [
    ("198.51.100.4", "198.51.100.4"),
    ("2001:db8:abcd:12:1:2:3:4", "2001:db8:abcd:12::/64"),
    ("2001:db8:abcd:12:ffff::9", "2001:db8:abcd:12::/64"),
    ("unknown", "unknown"),
    ("::ffff:203.0.113.9", "203.0.113.9"),
    ("fe80::1%eth0", "fe80::/64"),
    ("2001:db8:abcd:12:1:2:3:4%en0", "2001:db8:abcd:12::/64"),
])
def test_ip_key(ip, expected):
    assert ip_key(ip) == expected


def test_ipv4_mapped_key_equals_plain_ipv4():
    assert ip_key("::ffff:203.0.113.9") == ip_key("203.0.113.9") == "203.0.113.9"


def test_different_mapped_addresses_get_different_keys():
    assert ip_key("::ffff:203.0.113.9") != ip_key("::ffff:203.0.113.10")
    salt = DailySalt()
    now = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
    assert salt.hash_ip("::ffff:203.0.113.9", now) != salt.hash_ip("::ffff:203.0.113.10", now)


def test_ipv6_addresses_in_one_64_share_a_hash():
    salt = DailySalt()
    now = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
    assert salt.hash_ip("2001:db8:abcd:12::1", now) == salt.hash_ip("2001:db8:abcd:12:9::2", now)
    assert salt.hash_ip("2001:db8:abcd:12::1", now) != salt.hash_ip("2001:db8:abcd:13::1", now)


def test_burst_window():
    burst = BurstCounter()
    t = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
    assert [burst.hit("a", t + timedelta(seconds=i)) for i in range(6)] == [1, 2, 3, 4, 5, 6]
    assert burst.hit("a", t + timedelta(seconds=62)) == 4


def test_burst_keys_independent():
    burst = BurstCounter()
    t = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
    burst.hit("a", t)
    burst.hit("a", t)
    assert burst.hit("b", t) == 1


def test_burst_drops_many_distinct_keys_older_than_window():
    burst = BurstCounter()
    t = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
    for i in range(20_000):
        burst.hit(f"attacker-{i}", t)
    assert burst.hit("fresh", t + timedelta(seconds=61)) == 1
    assert len(burst._hits) == 1


def test_burst_prunes_at_most_once_per_window(monkeypatch):
    burst = BurstCounter()
    calls = []
    original = BurstCounter._prune

    def counting(self, now_ts):
        calls.append(now_ts)
        return original(self, now_ts)

    monkeypatch.setattr(BurstCounter, "_prune", counting)
    t = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
    for i in range(20_000):
        burst.hit(f"attacker-{i}", t + timedelta(seconds=i / 1000))  # all within one 60 s window
    assert len(calls) <= 1


SPOOF = {"cf-connecting-ip": "198.51.100.7", "cf-ipcountry": "MX", "x-forwarded-for": "10.0.0.1"}


@pytest.mark.parametrize("headers, trust, expected", [
    (SPOOF, False, "203.0.113.9"),
    ({**SPOOF, "x-real-ip": "198.51.100.8"}, False, "198.51.100.8"),
    ({**SPOOF, "x-real-ip": "198.51.100.8"}, True, "198.51.100.7"),
    ({"x-real-ip": "198.51.100.8"}, True, "198.51.100.8"),
    ({}, False, "203.0.113.9"),
])
def test_client_ip(headers, trust, expected):
    assert client_ip(make_request(headers), trust) == expected


@pytest.mark.parametrize("headers, trust, expected", [
    ({"cf-ipcountry": "mx"}, True, "MX"), ({"cf-ipcountry": "mx"}, False, None), ({"cf-ipcountry": "XX1"}, True, None),
    ({"cf-ipcountry": "XX"}, True, None), ({"cf-ipcountry": "t1"}, True, None),
    ({}, True, None),
])
def test_client_country(headers, trust, expected):
    assert client_country(make_request(headers), trust) == expected


def test_take_slot_stops_at_limit(db):
    with db.connect() as conn:
        assert [take_slot(conn, "guest:x", DAY, 3) for _ in range(4)] == [1, 2, 3, None]
        assert used(conn, "guest:x", DAY) == 3


def test_take_slot_is_atomic_under_concurrency(db):
    start = threading.Barrier(8)
    results = []

    def worker():
        start.wait()
        with db.connect() as conn:
            got = take_slot(conn, "guest:race", DAY, 3)
            time.sleep(0.1)  # hold the transaction open so the others really overlap
        results.append(got)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(r for r in results if r is not None) == [1, 2, 3]
    assert results.count(None) == 5
    with db.connect() as conn:
        assert used(conn, "guest:race", DAY) == 3


def test_take_reading_slots_counts_guest_and_address(db):
    other = uuid.uuid4()
    with db.connect() as conn:
        assert take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", DAY) == 1
        assert take_reading_slots(conn, guest_quota(other), DAY, "hash-1", DAY) == 1
        assert used(conn, guest_subject(GID), DAY) == 1
        assert used(conn, ip_subject("hash-1"), DAY) == 2


def test_guest_limit_raises(db):
    with db.connect() as conn:
        for _ in range(3):
            take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", DAY)
        with pytest.raises(LimitReached) as info:
            take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", DAY)
    assert info.value.reason == "limit"


def test_ip_limit_rolls_back_the_guest_slot(db):
    with db.connect() as conn:
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, 60)", (ip_subject("hash-1"), DAY))
    with pytest.raises(LimitReached) as info:
        with db.connect() as conn:
            take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", DAY)
    assert info.value.reason == "ip_limit"
    with db.connect() as conn:
        assert used(conn, guest_subject(GID), DAY) == 0


def test_remaining_and_midnight_reset(db):
    with db.connect() as conn:
        for _ in range(3):
            take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", date(2026, 11, 21))
        assert remaining(conn, guest_quota(GID), DAY) == 0
        assert remaining(conn, guest_quota(GID), date(2026, 11, 21)) == limits.DAILY_LIMIT


def test_followup_attempts_stop_at_eight_per_reading(db):
    reading, other = make_reading(), make_reading()
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
        repo.insert_reading(conn, other)
        assert [take_followup_attempt(conn, reading["id"]) for _ in range(8)] == list(range(1, 9))
        with pytest.raises(LimitReached) as info:
            take_followup_attempt(conn, reading["id"])
        assert take_followup_attempt(conn, other["id"]) == 1
        assert used(conn, limits.followup_ip_subject("hash-1"), DAY) == 0  # the address slot is the route's
    assert info.value.reason == "attempts"


def test_a_rolled_back_attempt_is_given_back(db):
    reading = make_reading()
    with db.connect() as conn:
        repo.insert_reading(conn, reading)
    with pytest.raises(LimitReached):
        with db.connect() as conn:
            assert take_followup_attempt(conn, reading["id"]) == 1
            raise LimitReached("limit")  # e.g. the paid reading went to a parallel request
    with db.connect() as conn:
        assert repo.get_reading(conn, reading["id"], reading["created_at"])["followup_attempts"] == 0
        assert take_followup_attempt(conn, reading["id"]) == 1


def test_give_back_slot_never_goes_below_zero(db):
    with db.connect() as conn:
        for _ in range(3):
            take_reading_slots(conn, guest_quota(GID), DAY, "hash-1", DAY)
        give_back_slot(conn, guest_subject(GID), DAY)
        assert remaining(conn, guest_quota(GID), DAY) == 1
        for _ in range(3):
            give_back_slot(conn, guest_subject(GID), DAY)
        give_back_slot(conn, guest_subject(uuid.uuid4()), DAY)  # no row: nothing to give back
        assert used(conn, guest_subject(GID), DAY) == 0


def test_question_checks_are_counted_apart():
    assert limits.guard_ip_subject("hash-1") == "ipg:hash-1"
    assert len({limits.guard_ip_subject("h"), limits.followup_ip_subject("h"), ip_subject("h")}) == 3



# --- stage 4.3 §5: the guest's 3 or the account's 5 ---

def test_quotas():
    user = uuid.uuid4()
    assert guest_quota(GID) == limits.Quota(f"guest:{GID}", 3)
    assert limits.user_quota(user) == limits.Quota(f"user:{user}", 5)
    assert limits.owner_quota({"guest_id": GID, "user_id": None}) == guest_quota(GID)
    assert limits.owner_quota({"guest_id": GID, "user_id": user}) == limits.user_quota(user)


def test_an_account_takes_five_a_day(db):
    quota = limits.user_quota(uuid.uuid4())
    with db.connect() as conn:
        assert [take_reading_slots(conn, quota, DAY, "hash-1", DAY) for _ in range(5)] == [1, 2, 3, 4, 5]
        with pytest.raises(LimitReached):
            take_reading_slots(conn, quota, DAY, "hash-1", DAY)
        assert remaining(conn, quota, DAY) == 0 and used(conn, ip_subject("hash-1"), DAY) == 5
