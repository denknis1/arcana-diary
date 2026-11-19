"""The account and the Plus waitlist (spec 4.3 §8, §12): profile and consent, the export, deleting at once
(everything gone, the cost log stays), the waitlist and its address limit."""
import uuid
from datetime import timedelta

import pytest

from helpers import bearer, dump_tables, from_ip, parse_sse, post_reading

MX = "America/Mexico_City"
ANA = uuid.UUID("4d5e6f70-0000-4000-8000-000000000001")
BEN = uuid.UUID("4d5e6f70-0000-4000-8000-000000000002")


def count(api, sql: str, *params) -> int:
    with api.db.connect() as conn:
        return conn.execute(sql, params).fetchone()["n"]


def ready(api, user, **body) -> str:
    api.clock.advance(minutes=1)
    created = post_reading(api.client, headers=bearer(user), tz=MX, **{"kind": "one", **body})
    assert created.status_code == 201, created.text
    reading_id = created.json()["id"]
    parse_sse(api.client.get(f"/api/readings/{reading_id}/stream", headers=bearer(user)).text)
    return reading_id


def delete_account(api, user=ANA, **body):
    return api.client.request("DELETE", "/api/account", json=body or None, headers=bearer(user) if user else {})


def test_the_account_needs_a_token(api):
    for method, body in (("GET", None), ("PATCH", {"reminders_consent": True})):
        response = api.client.request(method, "/api/account", json=body)
        assert response.status_code == 401 and response.json() == {"reason": "sign_in"}
    assert api.client.get("/api/account/export").json() == {"reason": "sign_in"}
    assert delete_account(api, None, confirm="DELETE").status_code == 401


def test_the_account_shows_the_email_its_first_day_and_the_limit(api):
    ready(api, ANA)
    body = api.client.get("/api/account", params={"tz": MX}, headers=bearer(ANA, email="Ana@Example.com")).json()
    assert body["email"] == "ana@example.com" and body["created_at"].startswith("2026-11-20T18:01:00")
    assert (body["reminders_consent"], body["consent_at"]) == (False, None)
    assert (body["limit"], body["used"], body["remaining"], body["day"]) == (5, 1, 4, "2026-11-20")
    api.clock.advance(days=1)
    assert api.client.get("/api/account", headers=bearer(ANA)).json()["created_at"] == body["created_at"]


def test_reminders_consent_keeps_its_date(api):
    api.clock.advance(minutes=3)
    on = api.client.patch("/api/account", json={"reminders_consent": True}, headers=bearer(ANA)).json()
    assert on["reminders_consent"] is True and on["consent_at"].startswith("2026-11-20T18:03:00")
    api.clock.advance(minutes=3)
    again = api.client.patch("/api/account", json={"reminders_consent": True}, headers=bearer(ANA)).json()
    assert again["consent_at"] == on["consent_at"]
    off = api.client.patch("/api/account", json={"reminders_consent": False}, headers=bearer(ANA)).json()
    assert (off["reminders_consent"], off["consent_at"]) == (False, None)
    for bad in ({}, {"reminders_consent": "maybe"}, {"reminders_consent": True, "extra": 1}):
        assert api.client.patch("/api/account", json=bad, headers=bearer(ANA)).status_code == 422


def test_the_export_has_every_reading_followup_note_and_outcome(api):
    first = ready(api, ANA, question="How do I settle in?", topic="work")
    assert api.client.post(f"/api/readings/{first}/followups", json={"question": "And then?"},
                           headers=bearer(ANA)).status_code == 200
    api.client.patch(f"/api/diary/{first}", json={"outcome": "yes", "note": "It went well."}, headers=bearer(ANA))
    second = ready(api, ANA)
    ready(api, BEN, question="Not for Ana")
    response = api.client.get("/api/account/export", headers=bearer(ANA))
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="arcana-diary-2026-11-20.json"'
    data = response.json()
    assert data["account"]["email"] == "person@example.com" and data["plus_waitlist"] is None
    assert [r["id"] for r in data["readings"]] == [first, second]
    entry = data["readings"][0]
    assert (entry["question"], entry["topic"], entry["outcome"], entry["note"]) == (
        "How do I settle in?", "work", "yes", "It went well.")
    assert entry["answer"]["headline"] and entry["cards"][0]["name"] and entry["outcome_at"]
    assert [f["question"] for f in entry["followups"]] == ["And then?"] and entry["followups"][0]["answer"]
    assert "Not for Ana" not in response.text


def test_deleting_the_account_removes_everything_at_once(api, caplog):
    first = ready(api, ANA)
    assert api.client.post(f"/api/readings/{first}/followups", json={"question": "And then?"},
                           headers=bearer(ANA)).status_code == 200
    api.client.patch("/api/account", json={"reminders_consent": True}, headers=bearer(ANA))
    assert api.client.post("/api/plus/waitlist", json={"lang": "en"}, headers=bearer(ANA)).status_code == 200
    bens = ready(api, BEN)
    api.clock.advance(minutes=1)
    guest = post_reading(api.client, kind="one", tz=MX).json()["id"]
    with api.db.connect() as conn:
        conn.execute("INSERT INTO claim_tokens (token_hash, reading_id, created_at, expires_at) VALUES (%s, %s, %s, %s)",
                     ("hash", uuid.UUID(first), api.clock(), api.clock() + timedelta(days=7)))
    calls = count(api, "SELECT count(*) AS n FROM llm_calls")
    wrong = delete_account(api, confirm="delete")
    assert wrong.status_code == 422 and wrong.json() == {"reason": "invalid", "fields": ["confirm"]}
    assert delete_account(api).status_code == 422
    with caplog.at_level("ERROR", logger="arcana.account"):
        response = delete_account(api, confirm="DELETE")
    assert response.status_code == 200 and response.json() == {"deleted": True}
    assert "Supabase user was not deleted" in caplog.text  # SUPABASE_URL is set, the test database has no auth
    assert count(api, "SELECT count(*) AS n FROM deleted_accounts WHERE user_id = %s", ANA) == 1
    assert count(api, "SELECT count(*) AS n FROM readings WHERE user_id = %s", ANA) == 0
    for table in ("followups", "claim_tokens", "plus_waitlist"):
        assert count(api, f"SELECT count(*) AS n FROM {table}") == 0
    assert count(api, "SELECT count(*) AS n FROM profiles WHERE user_id = %s", ANA) == 0
    assert count(api, "SELECT count(*) AS n FROM llm_calls") == calls >= 3  # the cost log has no text and stays
    with api.db.connect() as conn:
        left = {str(r["id"]) for r in conn.execute("SELECT id FROM readings").fetchall()}
    assert left == {bens, guest}
    assert api.client.get("/api/diary", headers=bearer(ANA)).json()["items"] == []


@pytest.fixture
def auth_schema(db):
    """Supabase's auth.users as far as the API touches it; the test database has no auth schema otherwise."""
    with db.connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS auth")
        conn.execute("CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY, email text)")
    yield
    with db.connect() as conn:
        conn.execute("DROP SCHEMA auth CASCADE")


def test_deleting_the_account_deletes_the_supabase_user_too(api, auth_schema, caplog):
    with api.db.connect() as conn:
        conn.execute("INSERT INTO auth.users (id, email) VALUES (%s, 'a@example.com'), (%s, 'b@example.com')",
                     (ANA, BEN))
    with caplog.at_level("ERROR", logger="arcana.account"):
        assert delete_account(api, confirm="DELETE").status_code == 200
    with api.db.connect() as conn:
        assert [r["id"] for r in conn.execute("SELECT id FROM auth.users").fetchall()] == [BEN]
    assert "Supabase user was not deleted" not in caplog.text


def test_a_token_that_outlives_its_account_writes_nothing(api):
    """Fable I2: a Supabase token stays valid until its exp; after DELETE /api/account it can write nothing."""
    ready(api, ANA)
    assert delete_account(api, confirm="DELETE").status_code == 200
    before = dump_tables(api.db)
    api.clock.advance(minutes=1)
    for response in (post_reading(api.client, headers=bearer(ANA), kind="one", tz=MX),
                     api.client.get("/api/account", headers=bearer(ANA)),
                     api.client.post("/api/account/claim", headers=bearer(ANA)),
                     api.client.post("/api/plus/waitlist", json={"lang": "en"}, headers=bearer(ANA))):
        assert response.status_code == 401 and response.json() == {"reason": "auth"}
    assert dump_tables(api.db) == before
    assert api.guard.json_calls() == []


def join(client, headers=None, **body):
    return client.post("/api/plus/waitlist", json={"lang": "en", **body}, headers=headers or {})


def waitlist(api) -> list[tuple]:
    with api.db.connect() as conn:
        rows = conn.execute("SELECT email, lang, user_id FROM plus_waitlist ORDER BY email").fetchall()
    return [(r["email"], r["lang"], r["user_id"]) for r in rows]


def test_the_waitlist_takes_a_guest_email_once(api):
    assert join(api.client, email=" Ana@Example.com ").json() == {"ok": True}
    assert join(api.client, email="ana@example.com", lang="es").json() == {"ok": True}  # a repeat is no error
    assert waitlist(api) == [("ana@example.com", "en", None)]


def test_signed_in_the_waitlist_uses_the_tokens_email(api):
    join(api.client, headers=bearer(ANA, email="ana@example.com"), email="someone@else.com")
    join(api.client, email="ben@example.com", lang="es")
    join(api.client, headers=bearer(BEN, email="ben@example.com"))  # links the account to the guest entry
    assert waitlist(api) == [("ana@example.com", "en", ANA), ("ben@example.com", "es", BEN)]


def test_signed_in_without_an_email_in_the_token_the_body_is_not_used(api):
    """Final review M3: the e-mail of a signed-in person comes only from the token; without one — 422, no row."""
    for email in (None, ""):
        response = join(api.client, headers=bearer(ANA, email=email), email="someone@else.com")
        assert response.status_code == 422 and response.json() == {"reason": "invalid", "fields": ["email"]}
    assert waitlist(api) == []


def test_the_waitlist_rejects_bad_emails(api):
    for bad in ({"email": "not-an-email"}, {}, {"email": "a@b"}, {"email": "x" * 250 + "@b.co"}):
        response = join(api.client, **bad)
        assert response.status_code == 422 and response.json() == {"reason": "invalid", "fields": ["email"]}
    assert join(api.client, email="a@b.co", lang="fr").status_code == 422
    assert waitlist(api) == []


def test_the_waitlist_takes_five_a_day_from_one_address(api):
    here, there = from_ip("198.51.100.7"), from_ip("198.51.100.8")
    statuses = [join(api.client, headers=here, email=f"p{i}@example.com").status_code for i in range(6)]
    assert statuses == [200, 200, 200, 200, 200, 429]
    assert join(api.client, headers=here, email="p9@example.com").json() == {"reason": "ip_limit"}
    assert join(api.client, headers=there, email="p9@example.com").status_code == 200
    assert len(waitlist(api)) == 6


def test_the_account_lock_is_taken_before_the_deleted_check(api, monkeypatch):
    """R4: delete_account and the signed-in insert of a reading take the advisory lock on the account id first, so
    a delete and a create cannot interleave (a reading written after the delete's DELETE would survive)."""
    from app import account_repo
    events = []
    real_lock, real_refuse = account_repo.lock_account, account_repo.refuse_deleted
    monkeypatch.setattr(account_repo, "lock_account", lambda conn, user_id: (events.append(("lock", user_id)),
                                                                              real_lock(conn, user_id))[1])
    monkeypatch.setattr(account_repo, "refuse_deleted", lambda conn, user_id: (events.append(("refuse", user_id)),
                                                                                real_refuse(conn, user_id))[1])
    api.clock.advance(minutes=1)
    assert post_reading(api.client, headers=bearer(ANA), kind="one", tz=MX).status_code == 201
    assert events[-2:] == [("lock", ANA), ("refuse", ANA)]
    events.clear()
    assert delete_account(api, confirm="DELETE").status_code == 200
    assert events == [("lock", ANA), ("refuse", ANA)]


def test_the_lock_makes_a_delete_wait_for_a_creating_transaction(api):
    """R4 with two real connections: while another transaction holds the account's lock, delete waits for it."""
    import threading
    done = threading.Event()
    with api.db.connect() as holder:
        holder.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (str(ANA),))
        worker = threading.Thread(target=lambda: (delete_account(api, confirm="DELETE"), done.set()))
        worker.start()
        assert not done.wait(1.0)
    worker.join(10)
    assert done.is_set()



def test_claim_and_the_waitlist_take_the_lock_before_the_deleted_check(api, monkeypatch):
    """Review fix: ensure_profile (claim, consent, account) and the signed-in waitlist lock, then refuse."""
    from app import account_repo
    events = []
    real_lock, real_refuse = account_repo.lock_account, account_repo.refuse_deleted
    monkeypatch.setattr(account_repo, "lock_account", lambda conn, user_id: (events.append("lock"),
                                                                              real_lock(conn, user_id))[1])
    monkeypatch.setattr(account_repo, "refuse_deleted", lambda conn, user_id: (events.append("refuse"),
                                                                                real_refuse(conn, user_id))[1])
    assert api.client.post("/api/account/claim", headers=bearer(ANA)).status_code == 200
    assert events == ["lock", "refuse"]
    events.clear()
    assert join(api.client, headers=bearer(ANA)).status_code == 200
    assert events == ["lock", "refuse"]


def test_a_claim_waits_for_a_delete_in_progress(api):
    """Two real connections: while another transaction holds the account's lock, a claim waits for it."""
    import threading
    done = threading.Event()
    with api.db.connect() as holder:
        holder.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (str(ANA),))
        worker = threading.Thread(target=lambda: (api.client.post("/api/account/claim", headers=bearer(ANA)),
                                                  done.set()))
        worker.start()
        assert not done.wait(1.0)
    worker.join(10)
    assert done.is_set()


def test_a_repeated_delete_is_refused_and_logs_no_false_error(api, caplog):
    assert delete_account(api, confirm="DELETE").status_code == 200
    caplog.clear()
    with caplog.at_level("ERROR", logger="arcana.account"):
        again = delete_account(api, confirm="DELETE")
    assert again.status_code == 401 and again.json() == {"reason": "auth"}
    assert caplog.text == ""
