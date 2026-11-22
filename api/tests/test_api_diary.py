"""The diary (spec 4.3 §6, §12): the list and its pages, the outcome, the note (length, stored as sent, never
HTML), delete; someone else's entries are 404."""
import uuid
from datetime import timedelta

from app import repo
from helpers import bearer, make_reading, parse_sse, post_reading

MX = "America/Mexico_City"
ANA = uuid.UUID("2b3c4d5e-0000-4000-8000-000000000001")
BEN = uuid.UUID("2b3c4d5e-0000-4000-8000-000000000002")


def diary(client, user, **params):
    return client.get("/api/diary", params=params, headers=bearer(user))


def patch(client, user, reading_id, **body):
    return client.patch(f"/api/diary/{reading_id}", json=body, headers=bearer(user))


def signed_in_reading(api, user=ANA, **body) -> str:
    api.clock.advance(minutes=1)  # distinct times, and under the burst threshold of one address
    response = post_reading(api.client, headers=bearer(user), tz=MX, **{"kind": "one", **body})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_the_list_is_newest_first_in_pages(api):
    first = signed_in_reading(api, question="How do I settle in?", topic="work")
    parse_sse(api.client.get(f"/api/readings/{first}/stream", headers=bearer(ANA)).text)
    assert api.client.post(f"/api/readings/{first}/followups", json={"question": "And then?"},
                           headers=bearer(ANA)).status_code == 200
    second = signed_in_reading(api)
    third = signed_in_reading(api, kind="three")
    page = diary(api.client, ANA, limit=2).json()
    assert [i["id"] for i in page["items"]] == [third, second]
    assert page["items"][0]["headline"] is None  # not streamed yet
    rest = diary(api.client, ANA, limit=2, before=page["next_before"]).json()
    assert [i["id"] for i in rest["items"]] == [first] and rest["next_before"] is None
    item = rest["items"][0]
    assert (item["question"], item["topic"], item["lang"], item["kind"]) == ("How do I settle in?", "work", "en", "one")
    assert item["headline"] == "The cards may point to a quiet, steady way forward."
    assert (item["answer_shown"], item["outcome"], item["has_note"], item["followups"]) == ("model", None, False, 1)
    assert item["cards"][0]["name"] and item["created_at"].startswith("2026-11-20T18:01:00")


def test_a_crisis_answer_is_listed_without_text(api):
    reading = make_reading(user_id=ANA, expires_at=None, now=api.clock())
    with api.db.connect() as conn:
        repo.insert_reading(conn, reading)
        repo.save_crisis(conn, reading["id"], "fake-reader", "reader.en.v5")
    [item] = diary(api.client, ANA).json()["items"]
    assert (item["question"], item["topic"], item["headline"], item["answer_shown"]) == (None, None, None, "crisis")


def test_only_the_accounts_own_readings_are_listed(api):
    mine = signed_in_reading(api)
    signed_in_reading(api, BEN)
    api.clock.advance(minutes=1)
    assert post_reading(api.client, kind="one", tz=MX).status_code == 201  # a guest reading of the same device
    assert [i["id"] for i in diary(api.client, ANA).json()["items"]] == [mine]
    guest = api.client.get("/api/diary")
    assert guest.status_code == 401 and guest.json() == {"reason": "sign_in"}
    assert diary(api.client, ANA, limit=0).json() == {"reason": "invalid", "fields": ["limit"]}


def test_outcome_and_note(api):
    reading_id = signed_in_reading(api)
    api.clock.advance(minutes=5)
    body = patch(api.client, ANA, reading_id, outcome="partly", note="Talked to her on Friday.").json()
    assert (body["id"], body["outcome"], body["note"]) == (reading_id, "partly", "Talked to her on Friday.")
    assert body["outcome_at"].startswith("2026-11-20T18:06:00") and body["note_updated_at"] == body["outcome_at"]
    full = api.client.get(f"/api/readings/{reading_id}", headers=bearer(ANA)).json()
    assert (full["outcome"], full["note"], full["in_diary"]) == ("partly", "Talked to her on Friday.", True)
    for client in (api.new_client(), api.client):  # a stranger, and this device without the token
        view = client.get(f"/api/readings/{reading_id}").json()
        assert "note" not in view and "outcome" not in view and "in_diary" not in view
    only_outcome = patch(api.client, ANA, reading_id, outcome=None).json()
    assert (only_outcome["outcome"], only_outcome["outcome_at"], only_outcome["note"]) == (
        None, None, "Talked to her on Friday.")
    cleared = patch(api.client, ANA, reading_id, note="   ").json()
    assert (cleared["note"], cleared["note_updated_at"]) == (None, None)
    assert diary(api.client, ANA).json()["items"][0]["has_note"] is False


def test_the_note_is_at_most_1000_characters_and_kept_as_sent(api):
    reading_id = signed_in_reading(api)
    assert patch(api.client, ANA, reading_id, note="ñ" * 1000).status_code == 200
    too_long = patch(api.client, ANA, reading_id, note="x" * 1001)
    assert too_long.status_code == 422 and too_long.json() == {"reason": "invalid", "fields": ["note"]}
    markup = '<script>alert("hi")</script> & <b>bold</b>'
    response = patch(api.client, ANA, reading_id, note=markup)
    assert response.headers["content-type"] == "application/json"  # JSON only: the site shows it as text
    assert response.json()["note"] == markup
    assert api.client.get(f"/api/readings/{reading_id}", headers=bearer(ANA)).json()["note"] == markup
    for bad in ({"outcome": "maybe"}, {"note": "a\x00b"}, {"mood": "good"}):
        assert patch(api.client, ANA, reading_id, **bad).status_code == 422


def test_someone_elses_or_a_missing_entry_is_404(api):
    reading_id = signed_in_reading(api)
    api.clock.advance(minutes=1)
    guest_reading = post_reading(api.client, kind="one", tz=MX).json()["id"]
    assert patch(api.client, BEN, reading_id, outcome="yes").status_code == 404
    assert patch(api.client, ANA, uuid.uuid4(), outcome="yes").status_code == 404
    assert patch(api.client, ANA, guest_reading, outcome="yes").status_code == 404  # the device's, not the account's
    assert api.client.delete(f"/api/diary/{reading_id}", headers=bearer(BEN)).status_code == 404
    no_account = api.client.patch(f"/api/diary/{reading_id}", json={"outcome": "yes"})
    assert no_account.status_code == 401 and no_account.json() == {"reason": "sign_in"}
    assert patch(api.client, ANA, reading_id).json()["outcome"] is None  # nothing was changed


def test_delete_removes_the_reading_its_followups_and_tokens(api):
    reading_id = signed_in_reading(api)
    parse_sse(api.client.get(f"/api/readings/{reading_id}/stream", headers=bearer(ANA)).text)
    assert api.client.post(f"/api/readings/{reading_id}/followups", json={"question": "And then?"},
                           headers=bearer(ANA)).status_code == 200
    with api.db.connect() as conn:
        conn.execute("INSERT INTO claim_tokens (token_hash, reading_id, created_at, expires_at) VALUES (%s, %s, %s, %s)",
                     ("hash", uuid.UUID(reading_id), api.clock(), api.clock() + timedelta(days=7)))
        calls = conn.execute("SELECT count(*) AS n FROM llm_calls").fetchone()["n"]
    response = api.client.delete(f"/api/diary/{reading_id}", headers=bearer(ANA))
    assert response.status_code == 204 and response.content == b""
    with api.db.connect() as conn:
        left = [conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]
                for t in ("readings", "followups", "claim_tokens", "llm_calls")]
    assert left == [0, 0, 0, calls] and calls >= 2  # the cost log keeps no text and stays
    assert api.client.get(f"/api/readings/{reading_id}").status_code == 404
    assert api.client.delete(f"/api/diary/{reading_id}", headers=bearer(ANA)).status_code == 404


# --- stage 4.4b §5 (owner decision 9): the free diary lists the 10 newest readings ---

def insert_entries(api, n: int, user=ANA) -> list[str]:
    """n readings of the account, an hour apart; ids oldest first."""
    ids = []
    with api.db.connect() as conn:
        for i in range(n):
            reading = make_reading(user_id=user, expires_at=None, now=api.clock() - timedelta(hours=n - i))
            repo.insert_reading(conn, reading)
            ids.append(str(reading["id"]))
    return ids


def test_the_free_diary_lists_the_ten_newest_and_counts_the_hidden(api):
    ids = insert_entries(api, 12)
    body = diary(api.client, ANA).json()
    assert [i["id"] for i in body["items"]] == ids[::-1][:10]
    assert (body["hidden_count"], body["next_before"]) == (2, None)


def test_pages_stop_at_the_tenth_entry(api):
    newest = insert_entries(api, 12)[::-1]
    first = diary(api.client, ANA, limit=4).json()
    second = diary(api.client, ANA, limit=4, before=first["next_before"]).json()
    third = diary(api.client, ANA, limit=4, before=second["next_before"]).json()
    assert [i["id"] for i in first["items"] + second["items"] + third["items"]] == newest[:10]
    assert third["next_before"] is None and len(third["items"]) == 2
    assert [p["hidden_count"] for p in (first, second, third)] == [2, 2, 2]
    beyond = diary(api.client, ANA, before=third["items"][-1]["created_at"]).json()  # older than the 10th: hidden
    assert beyond == {"items": [], "next_before": None, "hidden_count": 2}


def test_ten_or_fewer_hide_nothing(api):
    insert_entries(api, 10)
    body = diary(api.client, ANA).json()
    assert (len(body["items"]), body["hidden_count"], body["next_before"]) == (10, 0, None)
    assert diary(api.client, BEN).json() == {"items": [], "next_before": None, "hidden_count": 0}


def test_a_hidden_entry_still_opens_by_its_link_and_is_exported(api):
    oldest = insert_entries(api, 11)[0]
    assert oldest not in [i["id"] for i in diary(api.client, ANA).json()["items"]]
    view = api.client.get(f"/api/readings/{oldest}", headers=bearer(ANA))
    assert view.status_code == 200 and view.json()["in_diary"] is True
    assert view.json()["created_at"].startswith("2026-11-20T07:00:00")  # T_API − 11 h
    assert len(api.client.get("/api/account/export", headers=bearer(ANA)).json()["readings"]) == 11


def test_deleting_a_listed_entry_brings_the_next_older_one_in(api):
    ids = insert_entries(api, 11)
    assert api.client.delete(f"/api/diary/{ids[-1]}", headers=bearer(ANA)).status_code == 204
    body = diary(api.client, ANA).json()
    assert [i["id"] for i in body["items"]] == ids[:10][::-1]
    assert body["hidden_count"] == 0


def test_the_view_of_someone_else_has_no_date_of_the_diary(api):
    reading_id = insert_entries(api, 1)[0]
    view = api.new_client().get(f"/api/readings/{reading_id}").json()
    assert "created_at" not in view and "in_diary" not in view


def test_a_fallback_answer_lists_no_headline(api):
    """Walk-through 22.11.2026: a fallback's first line is the site's notice ("The reader is unavailable…"), not a
    headline of this reading; the list shows the question and the cards only. The entry itself is unchanged."""
    reading = make_reading(user_id=ANA, expires_at=None, now=api.clock())
    notice = {"headline": "The reader is unavailable right now.", "card1": "Meaning."}
    with api.db.connect() as conn:
        repo.insert_reading(conn, reading)
        repo.save_answer(conn, reading["id"], {"model": {"headline": "Model line."}, "fallback": notice}, "fallback",
                         "m", "reader.en.v7")
    [item] = diary(api.client, ANA).json()["items"]
    assert (item["headline"], item["answer_shown"]) == (None, "fallback")
