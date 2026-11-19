"""Who is asking, through the API (spec 4.3 §3, §6): a guest by cookie, an account by token, 401 and 503; a
reading in an account belongs to that account only (owner decision 19.11.2026)."""
import uuid

from fastapi.routing import APIRoute

from app import repo
from helpers import FakeJwks, bearer, dump_tables, guest_headers, make_reading, parse_sse, post_reading

MX = "America/Mexico_City"
USER = uuid.UUID("0b8f9a52-3c1d-4e2f-9a6b-7c8d9e0f1a2b")


def account_reading(api, **overrides) -> dict:
    reading = make_reading(user_id=USER, expires_at=None, now=api.clock(), **overrides)
    with api.db.connect() as conn:
        repo.insert_reading(conn, reading)
    return reading


def test_no_header_and_the_stage_password_are_guests(api):
    assert api.client.get("/api/limits", params={"tz": MX}).json()["limit"] == 3
    stage = {"Authorization": "Basic YXJjYW5hOnNlY3JldA=="}  # Caddy's stage password passes through to the API
    assert post_reading(api.client, headers=stage, kind="one", tz=MX).status_code == 201
    assert api.jwks.calls == 0


def test_a_bad_or_expired_token_is_401_and_changes_nothing(api):
    for headers in (bearer(USER, expires_in=-120), {"Authorization": "Bearer not-a-token"}, bearer(USER, aud="anon"),
                    bearer(USER, is_anonymous=True), {"Authorization": "Bearer "}):
        response = post_reading(api.client, headers=headers, kind="one", tz=MX)
        assert response.status_code == 401 and response.json() == {"reason": "auth"}
        assert response.headers["www-authenticate"] == "Bearer"
        assert "set-cookie" not in response.headers
    assert dump_tables(api.db) == ""
    assert api.guard.json_calls() == []


def test_every_api_route_checks_a_bearer_token_first(api):
    """Every /api/* route, the card of the day included, answers a bad token with 401 — before it reads the body
    or the query, so nothing can pass as a guest with a made-up token."""
    bad = {"Authorization": "Bearer not-a-token"}
    checked = []
    for route in api.app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        path = route.path.replace("{reading_id}", str(uuid.uuid4()))
        for method in sorted(route.methods):
            response = api.client.request(method, path, headers=bad, json={})
            assert (method, route.path, response.status_code) == (method, route.path, 401)
            checked.append((method, route.path))
    assert ("GET", "/api/daily") in checked and len(checked) >= 7
    assert dump_tables(api.db) == ""


def test_sign_in_off_refuses_every_token(api_factory):
    api = api_factory(supabase_url="")
    assert api.ctx.auth is None
    path = f"/api/readings/{uuid.uuid4()}"
    response = api.client.get(path, headers=bearer(USER))
    assert response.status_code == 401 and response.json() == {"reason": "auth"}
    assert api.client.get(path).status_code == 404  # without a token: a guest, as before


def test_unreachable_keys_are_503_and_guests_do_not_need_them(api_factory):
    api = api_factory(jwks=FakeJwks(fail=True))
    path = f"/api/readings/{uuid.uuid4()}"
    response = api.client.get(path, headers=bearer(USER))
    assert response.status_code == 503 and response.json() == {"reason": "auth_unavailable"}
    assert api.client.get(path).status_code == 404
    assert post_reading(api.client, kind="one", tz=MX).status_code == 201


def test_an_account_reading_is_owned_by_its_account_only(api):
    device = uuid.uuid4()
    reading = account_reading(api, guest_id=device)
    path = f"/api/readings/{reading['id']}"
    assert api.new_client().get(path, headers=bearer(USER)).json()["owner"] is True
    for headers in (guest_headers(device), bearer(uuid.uuid4()), {}):  # the device that made it is a link now
        view = api.new_client().get(path, headers=headers).json()
        assert view["owner"] is False and "question" not in view and "note" not in view
    guest = make_reading(guest_id=device, now=api.clock())
    with api.db.connect() as conn:
        repo.insert_reading(conn, guest)
    assert api.new_client().get(f"/api/readings/{guest['id']}", headers=guest_headers(device)).json()["owner"] is True


def test_the_account_streams_and_follows_up_from_another_device(api):
    device = uuid.uuid4()
    reading = account_reading(api, guest_id=device, kind="one",
                              cards=[{"card_id": "major-18-moon", "position": "card", "reversed": False}])
    path = f"/api/readings/{reading['id']}"
    for headers in ({}, guest_headers(device)):
        stranger = api.new_client().get(f"{path}/stream", headers=headers)
        assert stranger.status_code == 403 and stranger.json() == {"reason": "owner_only"}
    events = parse_sse(api.new_client().get(f"{path}/stream", headers=bearer(USER)).text)
    assert events[-1] == ("done", {"answer_shown": "model"})
    for headers in (bearer(uuid.uuid4()), guest_headers(device)):
        other = api.new_client().post(f"{path}/followups", json={"question": "And then?"}, headers=headers)
        assert other.status_code == 404
    mine = api.new_client().post(f"{path}/followups", json={"question": "And then?"}, headers=bearer(USER))
    assert mine.status_code == 200 and parse_sse(mine.text)[-1][1]["answer_shown"] == "model"
    assert api.new_client().post(f"{path}/retry", headers=bearer(uuid.uuid4())).status_code == 404
    retry = api.new_client().post(f"{path}/retry", headers=bearer(USER))
    assert retry.status_code == 409 and retry.json() == {"reason": "not_fallback"}
