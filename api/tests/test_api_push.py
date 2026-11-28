"""Stage 8.1 (spec 2026-11-27 §2.5, §3): the browser's reminder subscription — key, subscribe, unsubscribe."""
import os
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import webpush
from app.config import PUSH_PER_MINUTE, PUSH_SUBSCRIPTIONS_PER_OWNER
from helpers import bearer, from_ip, guest_headers

ANA = uuid.UUID("8a1b2c3d-0000-4000-8000-000000000021")
VAPID = webpush.generate_vapid()


def browser_keys() -> dict:
    key = ec.generate_private_key(ec.SECP256R1())
    return {"p256dh": webpush.b64url(webpush._point(key.public_key())), "auth": webpush.b64url(os.urandom(16))}


def body(n: int | str = 1, **overrides) -> dict:
    return {"endpoint": f"https://fcm.googleapis.com/fcm/send/device-{n}", "keys": browser_keys(), "hour": 8,
            "tz": "America/Mexico_City", "lang": "en", **overrides}


@pytest.fixture
def push_api(api_factory):
    return api_factory(vapid_private_key=VAPID[0], vapid_public_key=VAPID[1])


def rows(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT user_id, guest_id, endpoint, lang, tz, hour, fails FROM push_subscriptions"
                            " ORDER BY endpoint").fetchall()


def test_the_key_is_given_only_when_reminders_are_on(api, push_api):
    assert api.client.get("/api/push/key").json() == {"enabled": False, "public_key": ""}
    assert push_api.client.get("/api/push/key").json() == {"enabled": True, "public_key": VAPID[1]}


def test_a_guest_subscribes_for_this_cookie_and_an_account_for_itself(push_api):
    guest = uuid.uuid4()
    response = push_api.new_client().post("/api/push/subscription", json=body(1), headers=guest_headers(guest))
    assert response.status_code == 201 and response.json() == {"hour": 8, "tz": "America/Mexico_City"}
    assert push_api.new_client().post("/api/push/subscription", json=body(2, hour=7, lang="es"),
                                      headers=bearer(ANA)).status_code == 201
    assert [(r["user_id"], r["guest_id"], r["hour"], r["lang"]) for r in rows(push_api)] == [
        (None, guest, 8, "en"), (ANA, None, 7, "es")]


def test_the_same_browser_again_replaces_its_row(push_api):
    client = push_api.new_client()
    first = body(1)
    client.post("/api/push/subscription", json=first, headers=guest_headers(uuid.uuid4()))
    with push_api.db.connect() as conn:
        conn.execute("UPDATE push_subscriptions SET fails = 2")
    client.post("/api/push/subscription", json={**first, "hour": 21}, headers=bearer(ANA))
    [row] = rows(push_api)
    assert (row["user_id"], row["guest_id"], row["hour"], row["fails"]) == (ANA, None, 21, 0)


def test_an_unknown_zone_is_stored_as_utc(push_api):
    push_api.client.post("/api/push/subscription", json=body(1, tz="Mars/Olympus"), headers=bearer(ANA))
    assert rows(push_api)[0]["tz"] == "UTC"


@pytest.mark.parametrize("endpoint", ["http://fcm.googleapis.com/fcm/send/x", "https://169.254.169.254/latest",
                                      "https://example.com/push", "https://fcm.googleapis.com.evil.example/x"])
def test_only_a_known_push_service_is_taken(push_api, endpoint):
    response = push_api.client.post("/api/push/subscription", json=body(1, endpoint=endpoint), headers=bearer(ANA))
    assert response.status_code == 422 and response.json()["fields"] == ["endpoint"]
    assert rows(push_api) == []


def test_bad_keys_are_refused(push_api):
    keys = {"p256dh": webpush.b64url(b"\x04" + bytes(64)), "auth": webpush.b64url(os.urandom(16))}
    response = push_api.client.post("/api/push/subscription", json=body(1, keys=keys), headers=bearer(ANA))
    assert response.status_code == 422 and response.json()["fields"] == ["keys"]


@pytest.mark.parametrize("change, field", [({"hour": 24}, "hour"), ({"lang": "fr"}, "lang"),
                                           ({"expirationTime": None}, "expirationTime")])
def test_a_bad_body_is_422(push_api, change, field):
    response = push_api.client.post("/api/push/subscription", json=body(1, **change), headers=bearer(ANA))
    assert response.status_code == 422 and response.json()["fields"] == [field]


def test_reminders_off_is_503_and_stores_nothing(api):
    response = api.client.post("/api/push/subscription", json=body(1), headers=bearer(ANA))
    assert response.status_code == 503 and response.json() == {"reason": "push_off"}
    assert rows(api) == []


def test_one_owner_has_at_most_ten_browsers(push_api):
    for n in range(PUSH_SUBSCRIPTIONS_PER_OWNER):
        assert push_api.new_client().post("/api/push/subscription", json=body(n), headers=bearer(ANA)).status_code == 201
    push_api.clock.advance(minutes=2)  # not the address limit
    over = push_api.new_client().post("/api/push/subscription", json=body("x"), headers=bearer(ANA))
    assert over.status_code == 429 and over.json() == {"reason": "subscriptions"}
    again = push_api.new_client().post("/api/push/subscription", json=body(0), headers=bearer(ANA))
    assert again.status_code == 201  # a browser already in the list may refresh


def test_one_address_is_limited_per_minute(push_api):
    codes = [push_api.new_client().post("/api/push/subscription", json=body(n), headers=from_ip("198.51.100.9"))
             .status_code for n in range(PUSH_PER_MINUTE + 1)]
    assert codes == [201] * PUSH_PER_MINUTE + [429]


def test_unsubscribing_deletes_the_row_and_is_always_204(push_api):
    push_api.client.post("/api/push/subscription", json=body(1), headers=bearer(ANA))
    out = {"endpoint": body(1)["endpoint"]}
    assert push_api.new_client().request("DELETE", "/api/push/subscription", json=out,
                                         headers=bearer(ANA)).status_code == 204
    assert rows(push_api) == []
    assert push_api.new_client().request("DELETE", "/api/push/subscription", json=out).status_code == 204


def test_a_deleted_account_cannot_subscribe(push_api):
    assert push_api.client.request("DELETE", "/api/account", json={"confirm": "DELETE"},
                                   headers=bearer(ANA)).status_code == 200
    assert push_api.new_client().post("/api/push/subscription", json=body(1), headers=bearer(ANA)).status_code == 401
    assert rows(push_api) == []


def test_a_guest_cannot_take_over_an_accounts_row(push_api):
    mine = body(1)
    assert push_api.client.post("/api/push/subscription", json=mine, headers=bearer(ANA)).status_code == 201
    before = rows(push_api)
    other = {**mine, "keys": browser_keys(), "hour": 20, "lang": "es"}
    response = push_api.new_client().post("/api/push/subscription", json=other, headers=guest_headers(uuid.uuid4()))
    assert response.status_code == 409
    assert rows(push_api) == before
    with push_api.db.connect() as conn:
        assert conn.execute("SELECT p256dh FROM push_subscriptions").fetchone()["p256dh"] == mine["keys"]["p256dh"]


def test_deleting_an_accounts_row_needs_that_accounts_token(push_api):
    push_api.client.post("/api/push/subscription", json=body(1), headers=bearer(ANA))
    out = {"endpoint": body(1)["endpoint"]}
    assert push_api.new_client().request("DELETE", "/api/push/subscription", json=out).status_code == 204
    assert len(rows(push_api)) == 1
    assert push_api.new_client().request("DELETE", "/api/push/subscription", json=out,
                                         headers=bearer(ANA)).status_code == 204
    assert rows(push_api) == []
