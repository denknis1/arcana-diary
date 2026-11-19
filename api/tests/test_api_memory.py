"""Reader memory (spec 4.3 §7, §12): only for a signed-in person, the same topic, at most 5, oldest first, never a
crisis answer, a note or an outcome; a follow-up sees the same block as its reading."""
import re
import uuid
from datetime import timedelta

import pytest

from app import repo
from app.reader.errors import ProviderError, ProviderTimeout
from helpers import bearer, make_reading, parse_sse, post_reading

MX = "America/Mexico_City"
ANA = uuid.UUID("3c4d5e6f-0000-4000-8000-000000000001")
BEN = uuid.UUID("3c4d5e6f-0000-4000-8000-000000000002")
SECRET = "NOTE-7f3a I never told anyone"


def past(api, minutes_ago: int, topic="work", user=ANA, shown="model", note=None, outcome=None,
         guard_group="ok", guard_source="model", question=True) -> dict:
    """An earlier reading of an account, written straight to the database; checked by the guard model unless said
    otherwise (guard_source, migration 003)."""
    reading = make_reading(user_id=user, expires_at=None, now=api.clock() - timedelta(minutes=minutes_ago),
                           topic=topic, question=f"Question {minutes_ago}?" if question else None,
                           guard_group=guard_group, guard_source=guard_source)
    sections = {"headline": f"Headline {minutes_ago}.", "card1": "Card text."}
    with api.db.connect() as conn:
        repo.insert_reading(conn, reading)
        if shown == "crisis":
            repo.save_crisis(conn, reading["id"], "fake-reader", "reader.en.v5")
        elif shown == "model":
            repo.save_answer(conn, reading["id"], {"model": sections, "fallback": None}, "model", "m", "reader.en.v5")
        elif shown == "fallback":
            repo.save_answer(conn, reading["id"], {"model": None, "fallback": sections}, "fallback", "m",
                             "reader.en.v5")
        conn.execute("UPDATE readings SET note = %s, outcome = %s WHERE id = %s", (note, outcome, reading["id"]))
    return reading


def stream_new(api, headers=None, **body) -> tuple[str, str]:
    """Creates and streams a reading; returns its id and the reader's first message."""
    created = post_reading(api.client, headers=headers, tz=MX,
                           **{"kind": "three", "topic": "work", "question": "What now at work?", **body})
    assert created.status_code == 201, created.text
    reading_id = created.json()["id"]
    parse_sse(api.client.get(f"/api/readings/{reading_id}/stream", headers=headers or {}).text)
    return reading_id, api.reader.stream_calls()[-1]["messages"][0]["content"]


def history_of(content: str) -> str:
    return content.split("<reading")[0]


def test_a_signed_in_reading_gets_its_topic_history_oldest_first(api):
    past(api, 300)
    past(api, 200, topic="love")
    past(api, 100, shown="fallback")
    past(api, 50, user=BEN)
    _, content = stream_new(api, headers=bearer(ANA))
    block = history_of(content)
    assert block.startswith("<history>\n") and block.endswith("</history>\n")
    assert block.count("<past ") == 2 and block.index("Question 300?") < block.index("Question 100?")
    assert "<past_headline>Headline 300.</past_headline>" in block and "Headline 100." in block
    assert "Question 200?" not in content and "Question 50?" not in content  # another topic, another account
    assert "What now at work?" not in block  # the current question is not its own history
    assert '<past date="2026-11-20">' in block


def test_at_most_five_and_never_a_crisis_or_an_unanswered_reading(api):
    for minutes in range(10, 80, 10):
        past(api, minutes)
    past(api, 5, shown="crisis")
    past(api, 3, shown=None)
    _, content = stream_new(api, headers=bearer(ANA))
    block = history_of(content)
    assert block.count("<past ") == 5
    assert "Question 50?" in block and "Question 10?" in block and "Question 60?" not in block
    assert "Question 5?" not in block and "Question 3?" not in block


def test_redirected_questions_never_come_back(api):
    """A question the check redirected (health, another person, money) is not replayed by name later."""
    past(api, 40, guard_group="redirect_topic")
    past(api, 30, guard_group="redirect_person")
    past(api, 20, guard_group="redirect_money")
    past(api, 10)
    _, content = stream_new(api, headers=bearer(ANA))
    block = history_of(content)
    assert block.count("<past ") == 1 and "Question 10?" in block
    assert not any(f"Question {m}?" in content for m in (40, 30, 20))


def test_notes_and_outcomes_never_reach_a_model(api):
    past(api, 60, note=SECRET, outcome="yes")
    reading_id, content = stream_new(api, headers=bearer(ANA))
    assert "Question 60?" in content
    assert set(re.findall(r"<(\w+)", history_of(content))) == {"history", "past", "past_question", "past_headline"}
    patched = api.client.patch(f"/api/diary/{reading_id}", json={"note": SECRET, "outcome": "no"},
                               headers=bearer(ANA))
    assert patched.status_code == 200
    followup = api.client.post(f"/api/readings/{reading_id}/followups", json={"question": "And then?"},
                               headers=bearer(ANA))
    assert followup.status_code == 200
    sent = [m["content"] for call in api.reader.stream_calls() for m in call["messages"]]
    sent += [m["content"] for call in api.guard.json_calls() for m in call["messages"]]
    assert sent and not any("NOTE-7f3a" in text for text in sent)


def test_a_followup_sees_the_same_history_as_its_reading(api):
    past(api, 60)
    reading_id, content = stream_new(api, headers=bearer(ANA))
    response = api.client.post(f"/api/readings/{reading_id}/followups", json={"question": "And then?"},
                               headers=bearer(ANA))
    assert response.status_code == 200
    call = api.reader.stream_calls()[-1]
    assert call["system"] == api.ctx.prompts[("followup", "en")].text
    assert call["messages"][0]["content"] == content and "<history>" in content


def test_a_guest_reading_gets_no_history(api):
    past(api, 60)  # the account has history, but this reading is a guest's
    _, content = stream_new(api)
    assert "<history>" not in content and content.startswith("<reading")


def test_a_reading_without_a_topic_gets_no_history(api):
    past(api, 60)
    _, content = stream_new(api, headers=bearer(ANA), topic=None)
    assert "<history>" not in content


# --- final review I2: a question whose check failed open is not a checked 'ok' ---

@pytest.mark.parametrize("failure", [ProviderTimeout("slow"), ProviderError("down")], ids=["timeout", "error"])
def test_a_question_the_guard_could_not_check_never_comes_back(api, failure):
    """The guard timed out or failed: the reading is made (fail open, group 'ok'), but its question is not
    replayed by name in a later reading's history."""
    api.guard.json_replies.append(failure)
    unchecked, _ = stream_new(api, headers=bearer(ANA), question="Is my sister seriously ill?")
    with api.db.connect() as conn:
        row = conn.execute("SELECT guard_group, guard_source FROM readings WHERE id = %s",
                           (uuid.UUID(unchecked),)).fetchone()
    source = "timeout" if isinstance(failure, ProviderTimeout) else "error"
    assert row == {"guard_group": "ok", "guard_source": source}
    api.clock.advance(minutes=5)  # history takes only earlier readings
    _, content = stream_new(api, headers=bearer(ANA))
    assert "<history>" not in content and "sister" not in content


def test_a_question_the_guard_model_checked_comes_back(api):
    checked, _ = stream_new(api, headers=bearer(ANA), question="Will the new project go well?")
    with api.db.connect() as conn:
        assert conn.execute("SELECT guard_source FROM readings WHERE id = %s",
                            (uuid.UUID(checked),)).fetchone()["guard_source"] == "model"
    api.clock.advance(minutes=5)
    _, content = stream_new(api, headers=bearer(ANA))
    assert "<past_question>Will the new project go well?</past_question>" in history_of(content)


def test_a_reading_without_a_question_still_counts_and_an_unchecked_old_one_does_not(api):
    """No question: no check, no guard_source — its headline still serves as history. A row from before
    migration 003 has a question but no guard_source: left out."""
    past(api, 30, question=False, guard_source=None)
    past(api, 20, guard_source=None)
    reading_id, content = stream_new(api, headers=bearer(ANA), question=None)
    block = history_of(content)
    assert block.count("<past ") == 1 and "Headline 30." in block and "Question 20?" not in content
    with api.db.connect() as conn:
        assert conn.execute("SELECT guard_source FROM readings WHERE id = %s",
                            (uuid.UUID(reading_id),)).fetchone()["guard_source"] is None
