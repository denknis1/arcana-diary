"""GET /api/auth-config (spec 2026-11-22 stage 4.4b §3): the public sign-in settings for the browser."""
import base64
import json

import pytest

from app.config import load_settings
from helpers import AUTH_URL

ANON = "sb_publishable_test-key"  # a made-up public key; the real one is only in deploy/.env
SECRET = "sb_secret_test-key"  # a made-up secret key: it must never reach a browser


def jwt(role: str) -> str:
    """A made-up legacy Supabase key: a JWT whose payload names its role (the signature is not checked here)."""
    def part(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    return f"{part({'alg': 'HS256', 'typ': 'JWT'})}.{part({'iss': 'supabase', 'role': role})}.c2lnbmF0dXJl"


def test_on_with_the_address_and_the_key(api_factory):
    api = api_factory(supabase_anon_key=ANON)
    response = api.client.get("/api/auth-config")
    assert response.status_code == 200
    assert response.json() == {"enabled": True, "supabase_url": AUTH_URL, "anon_key": ANON, "google": False}
    assert response.headers["cache-control"] == "no-store" and "set-cookie" not in response.headers


def test_google_only_when_switched_on(api_factory):
    api = api_factory(supabase_anon_key=ANON, google_signin=True)
    assert api.client.get("/api/auth-config").json()["google"] is True


@pytest.mark.parametrize("overrides", [{}, {"supabase_url": "", "supabase_anon_key": ANON},
                                       {"supabase_url": "", "supabase_anon_key": "", "google_signin": True}])
def test_off_without_the_address_or_the_key(api_factory, overrides):
    api = api_factory(**overrides)
    assert api.client.get("/api/auth-config").json() == {"enabled": False, "supabase_url": "", "anon_key": "",
                                                         "google": False}


def test_a_bad_token_is_refused_here_too(api_factory):
    api = api_factory(supabase_anon_key=ANON)
    response = api.client.get("/api/auth-config", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401 and response.json() == {"reason": "auth"}


def test_the_settings():
    s = load_settings({})
    assert (s.supabase_anon_key, s.google_signin) == ("", False)
    s = load_settings({"SUPABASE_ANON_KEY": f" {ANON} ", "GOOGLE_SIGNIN": "true"})
    assert (s.supabase_anon_key, s.google_signin) == (ANON, True)
    assert load_settings({"GOOGLE_SIGNIN": ""}).google_signin is False


def test_google_signin_other_than_true_is_off_with_a_log_line_never_a_crash(caplog):
    """Fable plan review I12: the settings are read when the API starts; an error here would stop every reading."""
    for wrong in ("yes", "True", "1", "false", " on "):
        caplog.clear()
        with caplog.at_level("WARNING", logger="arcana.config"):
            assert load_settings({"GOOGLE_SIGNIN": wrong}).google_signin is False
        assert f"GOOGLE_SIGNIN={wrong.strip()!r} is not 'true': Continue with Google stays off" in caplog.text


@pytest.mark.parametrize("key", [SECRET, jwt("service_role"), "not.a.jwt", "some-raw-secret-value"])
def test_a_secret_key_is_never_published(key, caplog):
    """Fable plan review I3: GET /api/auth-config shows the key to every visitor, and a secret key passes row level
    security. It is dropped (sign-in stays off) with a log line that never prints the key; the API still starts."""
    with caplog.at_level("ERROR", logger="arcana.config"):
        assert load_settings({"SUPABASE_ANON_KEY": key}).supabase_anon_key == ""
    assert "SUPABASE_ANON_KEY is not the public key" in caplog.text and key not in caplog.text


def test_the_public_keys_are_used(caplog):
    anon = jwt("anon")
    with caplog.at_level("WARNING", logger="arcana.config"):
        assert load_settings({"SUPABASE_ANON_KEY": anon}).supabase_anon_key == anon
        assert load_settings({"SUPABASE_ANON_KEY": ANON}).supabase_anon_key == ANON
    assert caplog.text == ""
