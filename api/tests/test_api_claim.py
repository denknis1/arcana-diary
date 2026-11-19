"""Moving guest readings into an account (spec 4.3 §4, §12): from this device, by token from another device, a
made-up token, a used one, an expired one, a reading that already has an account."""
import uuid
from datetime import timedelta

from app import account_repo
from helpers import bearer, dump_tables, post_reading

MX = "America/Mexico_City"
ANA = uuid.UUID("1a2b3c4d-0000-4000-8000-000000000001")
BEN = uuid.UUID("1a2b3c4d-0000-4000-8000-000000000002")


def reading_row(api, reading_id) -> dict:
    with api.db.connect() as conn:
        return conn.execute("SELECT user_id, expires_at FROM readings WHERE id = %s",
                            (uuid.UUID(str(reading_id)),)).fetchone()


def new_reading(client) -> str:
    response = post_reading(client, kind="one", tz=MX)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def claim(client, user, tokens=None):
    return client.post("/api/account/claim", headers=bearer(user),
                       json=None if tokens is None else {"tokens": tokens})


def claim_token(client, reading_id, headers=None):
    return client.post(f"/api/readings/{reading_id}/claim-token", headers=headers or {})


def test_signing_in_moves_this_devices_guest_readings(api):
    first, second = new_reading(api.client), new_reading(api.client)
    stranger = new_reading(api.new_client())
    response = claim(api.client, ANA)
    assert response.status_code == 200 and sorted(response.json()["claimed"]) == sorted([first, second])
    assert reading_row(api, first) == {"user_id": ANA, "expires_at": None}
    assert reading_row(api, stranger)["user_id"] is None
    assert api.client.get(f"/api/readings/{first}", headers=bearer(ANA)).json()["owner"] is True
    assert api.client.get(f"/api/readings/{first}").json()["owner"] is False  # the cookie alone: a shared link now
    with api.db.connect() as conn:  # §4.4: the slots the guests used stay with the guests
        counts = {r["subject"]: r["count"] for r in conn.execute("SELECT subject, count FROM usage"
                                                                 " WHERE subject NOT LIKE 'ip%'").fetchall()}
    assert sorted(counts.values()) == [1, 2] and all(s.startswith("guest:") for s in counts)
    assert claim(api.client, ANA).json() == {"claimed": []}


def test_an_expired_guest_reading_is_not_moved(api):
    old = new_reading(api.client)
    api.clock.advance(days=7, minutes=1)
    assert claim(api.client, ANA).json() == {"claimed": []}
    assert reading_row(api, old)["user_id"] is None


def test_a_token_moves_the_reading_from_another_device(api):
    reading_id = new_reading(api.client)
    response = claim_token(api.client, reading_id)
    assert response.status_code == 201
    token = response.json()["token"]
    assert response.json()["expires_at"].startswith("2026-11-27T18:00:00")
    laptop = api.new_client()
    assert claim(laptop, ANA, [token]).json() == {"claimed": [reading_id]}
    assert reading_row(api, reading_id) == {"user_id": ANA, "expires_at": None}
    assert laptop.get(f"/api/readings/{reading_id}", headers=bearer(ANA)).json()["owner"] is True
    dump = dump_tables(api.db)
    assert token not in dump and account_repo.token_hash(token) in dump  # only the hash is stored


def test_a_used_token_is_skipped(api):
    reading_id = new_reading(api.client)
    token = claim_token(api.client, reading_id).json()["token"]
    assert claim(api.new_client(), ANA, [token]).json() == {"claimed": [reading_id]}
    assert claim(api.new_client(), BEN, [token]).json() == {"claimed": []}
    assert reading_row(api, reading_id)["user_id"] == ANA


def test_made_up_and_expired_tokens_are_skipped(api):
    reading_id = new_reading(api.client)
    token = claim_token(api.client, reading_id).json()["token"]
    with api.db.connect() as conn:
        conn.execute("UPDATE claim_tokens SET expires_at = %s", (api.clock() - timedelta(seconds=1),))
    response = claim(api.new_client(), ANA, [token, "made-up-token"])
    assert response.status_code == 200 and response.json() == {"claimed": []}
    assert reading_row(api, reading_id)["user_id"] is None


def test_a_reading_of_another_account_never_moves(api):
    reading_id = new_reading(api.client)
    token = claim_token(api.client, reading_id).json()["token"]
    assert claim(api.client, ANA).json() == {"claimed": [reading_id]}  # saved from its own device first
    assert claim(api.new_client(), BEN, [token]).json() == {"claimed": []}
    assert reading_row(api, reading_id)["user_id"] == ANA
    with api.db.connect() as conn:  # the token is used up all the same
        assert conn.execute("SELECT used_at FROM claim_tokens").fetchone()["used_at"] == api.clock()


def test_only_the_device_that_made_it_gets_a_token(api):
    reading_id = new_reading(api.client)
    assert claim_token(api.new_client(), reading_id).status_code == 404
    assert claim_token(api.new_client(), reading_id, bearer(ANA)).status_code == 404
    assert claim_token(api.client, uuid.uuid4()).status_code == 404
    claim(api.client, ANA)
    taken = claim_token(api.client, reading_id)
    assert taken.status_code == 409 and taken.json() == {"reason": "in_diary"}


def test_live_tokens_per_reading_are_capped(api):
    reading_id = new_reading(api.client)
    statuses = [claim_token(api.client, reading_id).status_code for _ in range(6)]
    assert statuses == [201, 201, 201, 201, 201, 429]
    assert claim_token(api.client, reading_id).json() == {"reason": "tokens"}


def test_claim_needs_an_account_and_a_short_list(api):
    response = api.client.post("/api/account/claim", json={"tokens": []})
    assert response.status_code == 401 and response.json() == {"reason": "sign_in"}
    too_many = claim(api.client, ANA, ["t"] * 21)
    assert too_many.status_code == 422 and too_many.json() == {"reason": "invalid", "fields": ["tokens"]}


def test_a_device_without_a_cookie_moves_nothing_and_gets_no_cookie(api):
    new_reading(api.client)
    response = claim(api.new_client(), ANA)
    assert response.json() == {"claimed": []} and "set-cookie" not in response.headers
    with api.db.connect() as conn:
        assert conn.execute("SELECT user_id FROM profiles").fetchone()["user_id"] == ANA
