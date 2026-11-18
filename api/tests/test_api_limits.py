from datetime import datetime, timezone

from helpers import post_reading

MX = "America/Mexico_City"


def test_limits_endpoint_new_guest(api):
    response = api.client.get("/api/limits", params={"tz": MX})
    assert response.json() == {"limit": 3, "used": 0, "remaining": 3, "day": "2026-11-20"}
    assert "ad_guest=" in response.headers["set-cookie"]


def test_limit_resets_at_local_midnight(api):
    api.clock.now = datetime(2026, 11, 21, 5, 30, tzinfo=timezone.utc)  # 23:30 on the 20th in Mexico City
    for _ in range(3):
        assert post_reading(api.client, kind="one", tz=MX).status_code == 201
    assert post_reading(api.client, kind="one", tz=MX).status_code == 429
    api.clock.advance(minutes=40)  # 00:10 on the 21st
    assert post_reading(api.client, kind="one", tz=MX).status_code == 201
    assert api.client.get("/api/limits", params={"tz": MX}).json() == {"limit": 3, "used": 1, "remaining": 2,
                                                                       "day": "2026-11-21"}


def test_limit_day_depends_on_tz(api):
    api.clock.now = datetime(2026, 11, 21, 5, 30, tzinfo=timezone.utc)
    for _ in range(3):
        post_reading(api.client, kind="one", tz=MX)
    assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 0
    assert api.client.get("/api/limits", params={"tz": "Asia/Tokyo"}).json() == {"limit": 3, "used": 0,
                                                                                 "remaining": 3, "day": "2026-11-21"}


def test_invalid_tz_uses_utc(api):
    api.clock.now = datetime(2026, 11, 21, 5, 30, tzinfo=timezone.utc)
    assert post_reading(api.client, kind="one", tz="Mars/Olympus").status_code == 201
    assert api.client.get("/api/limits", params={"tz": "UTC"}).json()["used"] == 1
    assert api.client.get("/api/limits", params={"tz": MX}).json()["used"] == 0


def test_crisis_does_not_use_the_limit(api):
    response = post_reading(api.client, kind="one", question="I want to end my life", tz=MX)
    assert response.status_code == 200 and response.json()["remaining"] == 3
    assert api.client.get("/api/limits", params={"tz": MX}).json()["used"] == 0
