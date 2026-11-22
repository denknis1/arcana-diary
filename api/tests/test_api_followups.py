import threading
import uuid
from dataclasses import replace
from datetime import timedelta

import pytest

from app import limits, repo
from app.config import FOLLOWUP_ATTEMPTS, IP_FOLLOWUP_LIMIT
from app.db import DatabaseUnavailable
from app.reader import fallback
from app.reader.followups import stream_followup
from app.reader.provider import FakeReply
from helpers import dump_tables, from_ip, parse_sse, post_reading

MX = "America/Mexico_City"


def ready_reading(api, client=None, **body):
    client = client or api.client
    response = post_reading(client, tz=MX, **body)
    assert response.status_code == 201, response.text
    reading_id = response.json()["id"]
    parse_sse(client.get(f"/api/readings/{reading_id}/stream").text)
    return reading_id


def fin(events):
    """The done event without followup_attempts_left (checked in its own test)."""
    name, data = events[-1]
    return name, {k: v for k, v in data.items() if k != "followup_attempts_left"}


def ask(client, reading_id, question, **extra):
    return client.post(f"/api/readings/{reading_id}/followups", json={"question": question, **extra})


def followups(api, reading_id) -> list[dict]:
    with api.db.connect() as conn:
        return repo.list_followups(conn, uuid.UUID(reading_id))


def test_full_guest_path(api):
    c = api.client
    created = post_reading(c, kind="three", question="How can I settle into my new team?", topic="work", tz=MX)
    assert created.status_code == 201 and created.json()["remaining"] == 2
    reading_id = created.json()["id"]
    assert parse_sse(c.get(f"/api/readings/{reading_id}/stream").text)[-1] == ("done", {"answer_shown": "model"})
    for n in (1, 2):
        followup = ask(c, reading_id, f"What can help me with this, part {n}?")
        assert followup.status_code == 200
        assert followup.headers["content-type"].startswith("text/event-stream")
        assert fin(parse_sse(followup.text)) == ("done", {"answer_shown": "model", "followups_left": 2 - n})
    third = ask(c, reading_id, "And one more thing?", tz=MX)
    assert third.status_code == 402 and third.json() == {"reason": "confirm", "remaining": 2}
    paid = ask(c, reading_id, "And one more thing?", tz=MX, use_reading=True)
    assert fin(parse_sse(paid.text)) == ("done", {"answer_shown": "model", "followups_left": 0, "used_reading": True})
    assert post_reading(c, kind="one", tz=MX).json()["remaining"] == 0
    fourth = ask(c, reading_id, "Anything else?", tz=MX, use_reading=True)
    assert fourth.status_code == 402 and fourth.json() == {"reason": "plus", "remaining": 0}
    reading = post_reading(c, kind="one", tz=MX)
    assert reading.status_code == 429 and reading.json() == {"reason": "limit", "remaining": 0}
    assert c.get("/api/limits", params={"tz": MX}).json()["remaining"] == 0


def test_followup_is_saved_and_restored(api):
    reading_id = ready_reading(api, kind="one", question="What should I focus on?")
    events = parse_sse(ask(api.client, reading_id, "How do I start?").text)
    assert events[0][0] == "meta" and events[0][1]["followup"] == 1
    text = "".join(d["text"] for e, d in events if e == "text").strip()
    full = api.client.get(f"/api/readings/{reading_id}").json()
    assert full["followups"] == [{"n": 1, "question": "How do I start?", "answer": text, "soft_line": None}]
    assert full["followups_left"] == 1
    call = api.reader.stream_calls()[-1]
    assert [m["role"] for m in call["messages"]] == ["user", "assistant", "user"]
    assert call["system"] == api.ctx.prompts[("followup", "en")].text
    assert call["messages"][-1]["content"] == '<followup guard_group="ok">How do I start?</followup>'


def test_followup_crisis_is_not_stored_or_counted(api):
    reading_id = ready_reading(api, kind="one")
    response = ask(api.client, reading_id, "Honestly I want to die.", tz="America/New_York")
    assert response.status_code == 200
    assert response.json()["group"] == "crisis" and response.json()["helplines"]["country"] == "US"
    assert followups(api, reading_id) == []
    assert "want to die" not in dump_tables(api.db)
    second = ask(api.client, reading_id, "What helps me rest?")
    assert fin(parse_sse(second.text)) == ("done", {"answer_shown": "model", "followups_left": 1})


def test_reader_safety_net_in_a_followup(api):
    reading_id = ready_reading(api, kind="one")
    api.reader.replies.append(FakeReply(chunks=["[[crisis]]", "\nPlease talk to someone today."]))
    events = parse_sse(ask(api.client, reading_id, "Nothing matters anymore, right?", tz=MX).text)
    assert [e for e, _ in events] == ["meta", "section", "crisis", "done"]
    assert events[2][1]["helplines"]["country"] == "MX"
    assert fin(events)[1] == {"answer_shown": "crisis", "followups_left": 2}
    [mark] = followups(api, reading_id)  # review I1: a tombstone, not a used follow-up, the question not stored
    assert mark["answer"] == {"crisis": True} and mark["counted"] is False and "Nothing matters" not in dump_tables(api.db)


def test_followup_failure_does_not_use_a_slot(api):
    reading_id = ready_reading(api, kind="one")
    api.reader.replies.append(FakeReply(fail_after=0))
    events = parse_sse(ask(api.client, reading_id, "What now?").text)
    fb = next(d for e, d in events if e == "fallback")
    assert fb["sections"] == {"followup": api.ctx.texts["en"]["followup_unavailable"]}
    assert fin(events) == ("done", {"answer_shown": "fallback", "followups_left": 2})
    assert followups(api, reading_id) == []
    assert fin(parse_sse(ask(api.client, reading_id, "What now?").text))[1]["followups_left"] == 1


def test_followup_banned_claim_is_replaced(api):
    reading_id = ready_reading(api, kind="three")
    api.reader.replies.append(FakeReply(chunks=["He feels the same ", "way about you."]))
    events = parse_sse(ask(api.client, reading_id, "Is there hope?").text)
    [replaced] = [d for e, d in events if e == "replace"]
    with api.db.connect() as conn:
        reading = repo.get_reading(conn, uuid.UUID(reading_id), api.clock())
    [row] = followups(api, reading_id)
    expected = fallback.followup_fallback(api.ctx.cards, reading)
    assert replaced == {"sections": {"followup": expected}, "reason": "banned", "retry": False}
    assert fin(events) == ("done", {"answer_shown": "fallback", "followups_left": 2})  # §9.4: no slot used
    assert row["answer"] == {"model": "He feels the same way about you.", "fallback": expected}
    assert row["counted"] is False
    full = api.client.get(f"/api/readings/{reading_id}").json()
    assert full["followups"][0]["answer"] == expected and full["followups_left"] == 2


def test_followup_by_other_guest_is_404(api):
    reading_id = ready_reading(api, kind="one")
    assert ask(api.new_client(), reading_id, "Can I ask too?").status_code == 404


def test_followup_before_answer_is_409(api):
    created = post_reading(api.client, kind="one", tz=MX)
    response = ask(api.client, created.json()["id"], "Too early?")
    assert response.status_code == 409 and response.json() == {"reason": "no_answer"}


def test_no_followup_while_the_base_answer_is_shown(api):
    api.reader.replies.append(FakeReply(fail_after=0))
    reading_id = ready_reading(api, kind="one")
    response = ask(api.client, reading_id, "And now?")
    assert response.status_code == 409 and response.json() == {"reason": "fallback"}


def test_followup_redirect_person_reaches_the_model(api):
    reading_id = ready_reading(api, kind="three", topic="love")
    api.guard.json_replies.append({"group": "redirect_person", "violence": False})
    events = parse_sse(ask(api.client, reading_id, "What does he think about me?").text)
    assert events[0][1]["soft_line"] == api.ctx.texts["en"]["soft_lines"]["redirect_person"]
    last = api.reader.stream_calls()[-1]["messages"][-1]["content"]
    assert last.startswith('<followup guard_group="redirect_person">')


@pytest.mark.parametrize("reading_group, followup_group, shown", [
    ("ok", "ok", "model"), ("redirect_topic", "ok", "fallback"), ("ok", "redirect_person", "fallback"),
])
def test_a_redirect_phrase_in_a_followup_is_judged_by_the_stricter_group(api, reading_group, followup_group, shown):
    """Stage 4.6, Fable I1/I5: an ok follow-up on a reading without an outcome is still checked strictly."""
    if reading_group != "ok":
        api.guard.json_replies.append({"group": reading_group, "violence": False})
    reading_id = ready_reading(api, kind="one", question="Will my scan be clear?")
    if followup_group != "ok":
        api.guard.json_replies.append({"group": followup_group, "violence": False})
    api.reader.replies.append(FakeReply(chunks=["It will happen when the time is right, so rest a little today."]))
    events = parse_sse(ask(api.client, reading_id, "What helps me now?").text)
    assert fin(events)[1]["answer_shown"] == shown


def test_followup_to_a_yes_no_without_verdict_sends_no_verdict(api):
    api.guard.json_replies.append({"group": "redirect_topic", "violence": False})
    reading_id = ready_reading(api, kind="yes_no", question="Will my scan be clear?")
    ask(api.client, reading_id, "How do I stay calm meanwhile?")
    assert "<verdict" not in api.reader.stream_calls()[-1]["messages"][0]["content"]


def test_client_disconnect_keeps_the_followup(api):
    reading_id = ready_reading(api, kind="one")
    with api.db.connect() as conn:
        reading = repo.get_reading(conn, uuid.UUID(reading_id), api.clock())
        followup = {"id": uuid.uuid4(), "reading_id": reading["id"], "n": 1, "question": "How do I begin?",
                    "created_at": api.clock()}
        repo.insert_followup(conn, followup)
    api.reader.replies.append(FakeReply(chunk_delay=0.02))
    events = stream_followup(api.ctx, reading, followup, [], "ok")
    assert next(events).startswith("event: meta")  # the client goes away after the first event
    assert events.join(timeout=10)
    full = api.client.get(f"/api/readings/{reading_id}").json()
    assert [f["n"] for f in full["followups"]] == [1] and full["followups"][0]["answer"]
    assert full["followups_left"] == 1


def test_a_followup_still_writing_blocks_the_next_one(api):
    reading_id = ready_reading(api, kind="one")
    with api.db.connect() as conn:
        repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": uuid.UUID(reading_id), "n": 1,
                                    "question": "First?", "created_at": api.clock()})
    response = ask(api.client, reading_id, "Second?")
    assert response.status_code == 409 and response.json() == {"reason": "busy"}


def test_a_stale_unanswered_followup_frees_its_slot(api):
    reading_id = ready_reading(api, kind="one")
    with api.db.connect() as conn:
        repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": uuid.UUID(reading_id), "n": 1,
                                    "question": "Cut by a restart?", "created_at": api.clock() - timedelta(minutes=5)})
    events = parse_sse(ask(api.client, reading_id, "Can I ask again?").text)
    assert events[0][1]["followup"] == 1 and fin(events)[1]["followups_left"] == 1


def test_followup_over_budget_does_not_use_a_slot(api):
    reading_id = ready_reading(api, kind="one")
    calls = len(api.reader.stream_calls())
    api.ctx.settings = replace(api.ctx.settings, daily_budget_usd=0.0)
    events = parse_sse(ask(api.client, reading_id, "What next?").text)
    assert next(d for e, d in events if e == "fallback")["reason"] == "budget"
    assert len(api.reader.stream_calls()) == calls and followups(api, reading_id) == []


CRISIS = {"group": "crisis", "violence": False}


def set_attempts(api, reading_id, attempts: int) -> None:
    with api.db.connect() as conn:
        conn.execute("UPDATE readings SET followup_attempts = %s WHERE id = %s", (attempts, uuid.UUID(reading_id)))


def attempts_of(api, reading_id) -> int:
    with api.db.connect() as conn:
        return repo.get_reading(conn, uuid.UUID(reading_id), api.clock())["followup_attempts"]


def test_crisis_answers_of_the_check_take_no_attempt(api):
    reading_id = ready_reading(api, kind="one")
    api.guard.json_replies.extend([CRISIS] * 10)
    codes = [ask(api.client, reading_id, "Is any of this even worth it?").status_code for _ in range(10)]
    assert codes == [200] * 10  # stage 4.5 §3: help first; the address cap (40 a day) still bounds them
    assert attempts_of(api, reading_id) == 0 and followups(api, reading_id) == []
    assert len(api.guard.json_calls()) == 10


def test_followup_attempts_are_capped_per_reading(api):
    reading_id = ready_reading(api, kind="one")
    set_attempts(api, reading_id, FOLLOWUP_ATTEMPTS)
    response = ask(api.client, reading_id, "And now?")
    assert response.status_code == 429 and response.json() == {"reason": "attempts"}
    assert len(api.guard.json_calls()) == 1 and followups(api, reading_id) == []  # checked first, then refused
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM llm_calls WHERE purpose = 'guard'").fetchone()["n"] == 1


def test_reader_crisis_and_failures_use_attempts_too(api):
    reading_id = ready_reading(api, kind="one")
    set_attempts(api, reading_id, FOLLOWUP_ATTEMPTS - 4)  # four attempts left
    api.reader.replies.extend([FakeReply(chunks=["[[crisis]]"]), FakeReply(fail_after=0), FakeReply(refuse=True)])
    for _ in range(3):
        ask(api.client, reading_id, "What now?")
    assert fin(parse_sse(ask(api.client, reading_id, "What now?").text))[1]["answer_shown"] == "model"
    response = ask(api.client, reading_id, "One more?")
    assert response.status_code == 429 and response.json() == {"reason": "attempts"}
    assert len(api.reader.stream_calls()) == 5  # the reading and four follow-up attempts


def test_followup_ip_limit(api):
    reading_id = ready_reading(api, kind="one")
    ip_hash = api.ctx.salt.hash_ip("198.51.100.7", api.clock())
    with api.db.connect() as conn:
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, %s)",
                     (limits.followup_ip_subject(ip_hash), limits.utc_day(api.clock()), IP_FOLLOWUP_LIMIT))
    response = api.client.post(f"/api/readings/{reading_id}/followups", json={"question": "What next?"},
                               headers=from_ip("198.51.100.7"))
    assert response.status_code == 429 and response.json() == {"reason": "ip_limit"}
    assert api.guard.json_calls() == []
    assert ask(api.client, reading_id, "What next?").status_code == 200  # another address


def test_followup_over_the_guard_budget_is_503(api):
    reading_id = ready_reading(api, kind="one")
    with api.db.connect() as conn:
        repo.log_llm_call(conn, {"reading_id": None, "purpose": "guard", "model": "claude-haiku-5-5",
                                 "prompt_version": "guard.v1", "ms_first_token": None, "ms_total": 1,
                                 "tokens_in": 1, "tokens_out": 1, "cost_usd": 1.0, "stop_reason": "end_turn",
                                 "refusal_category": None, "created_at": api.clock()})
    response = ask(api.client, reading_id, "What next?")
    assert response.status_code == 503 and response.json() == {"reason": "unavailable"}
    assert api.guard.json_calls() == [] and followups(api, reading_id) == []
    assert attempts_of(api, reading_id) == 0  # м1: a question nobody checked takes no attempt
    crisis = ask(api.client, reading_id, "Honestly I want to die.")  # a stop-phrase still answers
    assert crisis.json()["group"] == "crisis" and attempts_of(api, reading_id) == 0  # stage 4.5 §3


def test_crisis_marker_after_a_preface_or_split_is_caught(api):
    reading_id = ready_reading(api, kind="one")
    chunks = ["I hear how heavy this is.\n", "[", "[cri", "sis]]\nPlease reach out."]
    api.reader.replies.append(FakeReply(chunks=chunks))
    events = parse_sse(ask(api.client, reading_id, "Everything feels too much tonight", tz=MX).text)
    assert [e for e, _ in events] == ["meta", "section", "text", "crisis", "done"]
    assert events[2][1]["text"] == "I hear how heavy this is.\n"
    assert fin(events)[1] == {"answer_shown": "crisis", "followups_left": 2}
    assert [f["answer"] for f in followups(api, reading_id)] == [{"crisis": True}]  # the tombstone (review I1)
    assert "too much tonight" not in dump_tables(api.db)


def test_cut_followup_keeps_both_texts_and_its_slot(api):
    reading_id = ready_reading(api, kind="one")
    api.reader.replies.append(FakeReply(chunks=["Breathe, and take ", "one small"], fail_after=2))
    events = parse_sse(ask(api.client, reading_id, "How do I slow down?").text)
    assert next(d for e, d in events if e == "replace")["reason"] == "cut"
    assert fin(events) == ("done", {"answer_shown": "fallback", "followups_left": 2})
    [row] = followups(api, reading_id)
    assert row["answer"]["model"] == "Breathe, and take one small" and row["counted"] is False
    for n in (1, 2):
        assert fin(parse_sse(ask(api.client, reading_id, f"And then, part {n}?").text))[1]["followups_left"] == 2 - n
    assert ask(api.client, reading_id, "Third?").status_code == 402


def test_money_followup_keeps_its_disclaimer_after_reload(api):
    reading_id = ready_reading(api, kind="one")
    api.guard.json_replies.append({"group": "redirect_money", "violence": False})
    ask(api.client, reading_id, "Should I buy the car now?")
    [shown] = api.client.get(f"/api/readings/{reading_id}").json()["followups"]
    assert shown["soft_line"] == api.ctx.texts["en"]["soft_lines"]["redirect_money"]


def test_blank_followup_question_is_422_with_one_shape(api):
    reading_id = ready_reading(api, kind="one")
    response = ask(api.client, reading_id, "   ")
    assert response.status_code == 422 and response.json() == {"reason": "invalid", "fields": ["question"]}


def test_brackets_in_a_followup_stream_as_usual(api):
    reading_id = ready_reading(api, kind="one")
    api.reader.replies.append(FakeReply(chunks=["Try this [a small step] today. ", "Then rest a little."]))
    events = parse_sse(ask(api.client, reading_id, "How do I begin?").text)
    assert [d["text"] for e, d in events if e == "text"] == ["Try this [a small step] today. ", "Then rest a little."]


def test_followups_left_never_exceeds_the_attempts_left(api):
    reading_id = ready_reading(api, kind="one")
    for attempts, left in ((FOLLOWUP_ATTEMPTS - 1, 1), (FOLLOWUP_ATTEMPTS, 0)):
        set_attempts(api, reading_id, attempts)
        assert api.client.get(f"/api/readings/{reading_id}").json()["followups_left"] == left


# --- §10.1: after two free follow-ups each one uses a reading of the guest's day ---

def guest_used(api, reading_id) -> int:
    with api.db.connect() as conn:
        guest = repo.get_reading(conn, uuid.UUID(reading_id), api.clock())["guest_id"]
        return limits.used(conn, limits.guest_subject(guest), limits.local_day(limits.resolve_tz(MX), api.clock()))


def free_used(api, reading_id, client=None) -> None:
    for n in (1, 2):
        events = parse_sse(ask(client or api.client, reading_id, f"What helps, part {n}?", tz=MX).text)
        assert fin(events)[1]["followups_left"] == 2 - n


def test_third_followup_without_confirmation_is_402_and_takes_no_reading_or_attempt(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    guard_calls = len(api.guard.json_calls())
    response = ask(api.client, reading_id, "And one more?", tz=MX)
    assert response.status_code == 402 and response.json() == {"reason": "confirm", "remaining": 2}
    assert (guest_used(api, reading_id), attempts_of(api, reading_id)) == (1, 2)
    # stage 4.5 §3: the question is checked before the 402, so a crisis question gets help instead
    assert len(api.guard.json_calls()) == guard_calls + 1 and len(followups(api, reading_id)) == 2


def test_confirmed_followup_uses_a_reading(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    events = parse_sse(ask(api.client, reading_id, "And one more?", tz=MX, use_reading=True).text)
    assert events[0][1]["paid"] is True and events[0][1]["followup"] == 3
    assert fin(events) == ("done", {"answer_shown": "model", "followups_left": 0, "used_reading": True})
    assert guest_used(api, reading_id) == 2
    assert api.client.get("/api/limits", params={"tz": MX}).json()["remaining"] == 1
    row = followups(api, reading_id)[-1]
    assert (row["n"], row["counted"], row["paid_day"]) == (3, True, limits.local_day(limits.resolve_tz(MX),
                                                                                    api.clock()))
    again = ask(api.client, reading_id, "And another?", tz=MX)
    assert again.status_code == 402 and again.json() == {"reason": "confirm", "remaining": 1}


def test_no_readings_left_is_402_plus(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    for _ in range(2):
        assert post_reading(api.client, kind="one", tz=MX).status_code == 201
    for extra in ({}, {"use_reading": True}):
        response = ask(api.client, reading_id, "And one more?", tz=MX, **extra)
        assert response.status_code == 402 and response.json() == {"reason": "plus", "remaining": 0}
    assert attempts_of(api, reading_id) == 2 and guest_used(api, reading_id) == 3


@pytest.mark.parametrize("reply, reason", [
    (FakeReply(fail_after=0), "error"),
    (FakeReply(chunks=["Breathe, and take ", "one small"], fail_after=2), "cut"),
    (FakeReply(chunks=["He feels the same ", "way about you."]), "banned"),
])
def test_failed_paid_followup_gives_the_reading_back(api, reply, reason):
    reading_id = ready_reading(api, kind="three")
    free_used(api, reading_id)
    api.reader.replies.append(reply)
    events = parse_sse(ask(api.client, reading_id, "And one more?", tz=MX, use_reading=True).text)
    assert next(d for e, d in events if e in ("fallback", "replace"))["reason"] == reason
    assert fin(events) == ("done", {"answer_shown": "fallback", "followups_left": 0, "used_reading": False})
    assert guest_used(api, reading_id) == 1


def test_crisis_of_the_question_check_uses_no_reading(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    api.guard.json_replies.append(CRISIS)
    response = ask(api.client, reading_id, "Is any of this even worth it?", tz=MX, use_reading=True)
    assert response.status_code == 200 and response.json()["group"] == "crisis"
    assert guest_used(api, reading_id) == 1 and len(followups(api, reading_id)) == 2


def test_reader_crisis_marker_uses_the_paid_reading(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    api.reader.replies.append(FakeReply(chunks=["[[crisis]]"]))
    events = parse_sse(ask(api.client, reading_id, "Nothing matters anymore, right?", tz=MX, use_reading=True).text)
    assert fin(events) == ("done", {"answer_shown": "crisis", "followups_left": 0, "used_reading": True})
    assert guest_used(api, reading_id) == 2 and len(followups(api, reading_id)) == 3  # the third is the tombstone


def test_a_stale_paid_followup_gives_its_reading_back(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    day = limits.local_day(limits.resolve_tz(MX), api.clock())
    with api.db.connect() as conn:
        reading = repo.get_reading(conn, uuid.UUID(reading_id), api.clock())
        repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": reading["id"], "n": 3, "question": "Cut?",
                                    "paid_day": day, "created_at": api.clock() - timedelta(minutes=5)})
        limits.take_slot(conn, limits.guest_subject(reading["guest_id"]), day, limits.DAILY_LIMIT)
    assert guest_used(api, reading_id) == 2
    response = ask(api.client, reading_id, "Can I ask again?", tz=MX)
    assert response.json() == {"reason": "confirm", "remaining": 2} and guest_used(api, reading_id) == 1


def test_paid_followups_at_once_cannot_overspend_the_day(api):
    first, second = ready_reading(api, kind="one"), ready_reading(api, kind="one")
    free_used(api, first)
    free_used(api, second)
    api.guard.json_delay = 0.3  # all three requests wait in the guard, then race for the last reading
    start = threading.Barrier(3)
    codes = []

    def worker(action):
        start.wait()
        codes.append(action().status_code)

    actions = [lambda: ask(api.client, first, "One more?", tz=MX, use_reading=True),
               lambda: ask(api.client, second, "One more?", tz=MX, use_reading=True),
               lambda: post_reading(api.client, kind="one", tz=MX, question="What helps me focus?")]
    threads = [threading.Thread(target=worker, args=(a,)) for a in actions]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len([c for c in codes if c in (200, 201)]) == 1 and len(codes) == 3
    assert guest_used(api, first) == 3
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM followups WHERE paid_day IS NOT NULL").fetchone()["n"] + \
            conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 3


# --- Fable plan check: attempts before confirm, attempts_left in done, м10 stale deletion during a live stream ---

def test_exhausted_attempts_answer_429_before_the_confirm_question(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    set_attempts(api, reading_id, FOLLOWUP_ATTEMPTS)
    for extra in ({}, {"use_reading": True}):
        response = ask(api.client, reading_id, "And one more?", tz=MX, **extra)
        assert response.status_code == 429 and response.json() == {"reason": "attempts"}
    assert guest_used(api, reading_id) == 1


def test_done_carries_the_attempts_left(api):
    reading_id = ready_reading(api, kind="one")
    first = parse_sse(ask(api.client, reading_id, "How do I start?").text)[-1][1]
    assert (first["followups_left"], first["followup_attempts_left"]) == (1, FOLLOWUP_ATTEMPTS - 1)
    set_attempts(api, reading_id, FOLLOWUP_ATTEMPTS - 2)  # two attempts left, one free follow-up left
    second = parse_sse(ask(api.client, reading_id, "And then?").text)[-1][1]
    assert (second["followups_left"], second["followup_attempts_left"]) == (0, 1)
    third = parse_sse(ask(api.client, reading_id, "More?", tz=MX, use_reading=True).text)[-1][1]
    assert (third["followups_left"], third["followup_attempts_left"]) == (0, 0)


def slow_paid_followup(api, reply):
    """A paid follow-up whose generation is still running while the clock moves past the stale limit."""
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    day = limits.local_day(limits.resolve_tz(MX), api.clock())
    with api.db.connect() as conn:
        reading = repo.get_reading(conn, uuid.UUID(reading_id), api.clock())
        followup = {"id": uuid.uuid4(), "reading_id": reading["id"], "n": 3, "question": "Slow?", "paid_day": day,
                    "created_at": api.clock()}
        repo.insert_followup(conn, followup)
        limits.take_slot(conn, limits.guest_subject(reading["guest_id"]), day, limits.DAILY_LIMIT)
        previous = repo.list_followups(conn, reading["id"])[:2]
    assert guest_used(api, reading_id) == 2
    api.reader.replies.append(reply)
    events = stream_followup(api.ctx, reading, {**followup, "attempts": 3}, previous, "ok")
    assert next(events).startswith("event: meta")
    return reading_id, events


def test_stale_deletion_during_a_slow_stream_refunds_once_and_a_cut_does_not_refund_again(api):
    reply = FakeReply(chunks=["Breathe, ", "and take ", "one small ", "step now"], fail_after=3, chunk_delay=0.15)
    reading_id, events = slow_paid_followup(api, reply)
    api.clock.advance(seconds=181)
    again = ask(api.client, reading_id, "Can I ask again?", tz=MX)
    assert again.json() == {"reason": "confirm", "remaining": 2} and guest_used(api, reading_id) == 1
    assert events.join(timeout=10)
    assert guest_used(api, reading_id) == 1  # no second refund
    assert len(followups(api, reading_id)) == 2


def test_stale_deletion_during_a_slow_stream_then_a_successful_end_saves_and_charges_nothing(api):
    reply = FakeReply(chunks=["Breathe, ", "and take ", "one small ", "step now."], chunk_delay=0.15)
    reading_id, events = slow_paid_followup(api, reply)
    api.clock.advance(seconds=181)
    assert ask(api.client, reading_id, "Can I ask again?", tz=MX).status_code == 402
    rest = list(events)
    assert events.join(timeout=10)
    # the person who was still watching sees the answer, told that no reading was used; it is not stored
    assert parse_sse("".join(rest))[-1][1]["used_reading"] is False
    assert guest_used(api, reading_id) == 1 and len(followups(api, reading_id)) == 2


def test_crisis_marker_still_sends_helplines_when_saving_fails(api, monkeypatch):
    reading_id = ready_reading(api, kind="one")
    api.reader.replies.append(FakeReply(chunks=["[[crisis]]"]))

    def broken(*args, **kwargs):
        raise DatabaseUnavailable("down")

    monkeypatch.setattr(repo, "tombstone_followup", broken)
    events = parse_sse(ask(api.client, reading_id, "Nothing matters anymore, right?", tz=MX).text)
    names = [e for e, _ in events]
    assert names[-2:] == ["crisis", "error"] and events[-2][1]["helplines"]["country"] == "MX"


def test_nul_in_a_followup_question_is_422_before_any_guard_call_or_attempt(api):
    reading_id = ready_reading(api, kind="one")
    guard_calls = len(api.guard.calls)
    response = ask(api.client, reading_id, "And then\x00 what?")
    assert response.status_code == 422 and response.json() == {"reason": "invalid", "fields": ["question"]}
    assert followups(api, reading_id) == []
    with api.db.connect() as conn:
        assert repo.get_reading(conn, uuid.UUID(reading_id), api.clock())["followup_attempts"] == 0
    assert len(api.guard.calls) == guard_calls


# --- stage 4.5 §3 and §5: help before attempts and 402; a follow-up number never repeats ---

def test_crisis_at_exhausted_attempts_gets_the_crisis_answer(api):
    reading_id = ready_reading(api, kind="one")
    set_attempts(api, reading_id, FOLLOWUP_ATTEMPTS)
    response = ask(api.client, reading_id, "Honestly I want to die.", tz=MX)
    assert response.status_code == 200 and response.json()["group"] == "crisis"
    api.guard.json_replies.append(CRISIS)
    response = ask(api.client, reading_id, "Is any of this even worth it?", tz=MX)
    assert response.status_code == 200 and response.json()["group"] == "crisis"
    assert attempts_of(api, reading_id) == FOLLOWUP_ATTEMPTS


@pytest.mark.parametrize("readings_left", [2, 0])  # 402 confirm, 402 plus
def test_crisis_where_a_402_would_come_gets_the_crisis_answer(api, readings_left):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    for _ in range(2 - readings_left):
        assert post_reading(api.client, kind="one", tz=MX).status_code == 201
    response = ask(api.client, reading_id, "Honestly I want to die.", tz=MX)
    assert response.status_code == 200 and response.json()["group"] == "crisis"
    assert attempts_of(api, reading_id) == 2 and guest_used(api, reading_id) == 3 - readings_left


def test_a_followup_number_is_never_used_twice(api):
    reading_id = ready_reading(api, kind="one")
    api.reader.replies.append(FakeReply(fail_after=0))  # the first follow-up fails and is deleted
    assert fin(parse_sse(ask(api.client, reading_id, "What now?").text))[1]["answer_shown"] == "fallback"
    events = parse_sse(ask(api.client, reading_id, "And now?").text)
    assert events[0][1]["followup"] == 2  # the attempt count, not "the highest saved number + 1"
    assert [f["n"] for f in api.client.get(f"/api/readings/{reading_id}").json()["followups"]] == [2]


def test_two_followups_at_once_make_one(api):
    reading_id = ready_reading(api, kind="one")
    api.guard.json_delay = 0.3  # both wait in the question check, then race for the reading's row
    start = threading.Barrier(2)
    codes = []

    def worker(i):
        start.wait()
        codes.append(ask(api.client, reading_id, f"Part {i}?").status_code)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [200, 409]
    assert len(followups(api, reading_id)) == 1 and attempts_of(api, reading_id) == 1


def test_a_free_followup_written_meanwhile_in_another_tab_is_counted(api, monkeypatch):
    """Fable plan review I1: the free-or-paid decision is taken again from the list read under the reading's lock,
    not from the one read before the question check."""
    reading_id = ready_reading(api, kind="one")
    assert fin(parse_sse(ask(api.client, reading_id, "First?").text))[1]["followups_left"] == 1
    check = api.guard.complete_json

    def another_tab_answers_meanwhile(*args, **kwargs):
        with api.db.connect() as conn:
            fid = uuid.uuid4()
            repo.insert_followup(conn, {"id": fid, "reading_id": uuid.UUID(reading_id), "n": 7, "question": "Other?",
                                        "created_at": api.clock()})
            repo.save_followup_answer(conn, fid, {"model": "Done.", "fallback": None}, "fake-reader")
        return check(*args, **kwargs)

    monkeypatch.setattr(api.guard, "complete_json", another_tab_answers_meanwhile)
    response = ask(api.client, reading_id, "Second?")
    assert response.status_code == 409 and response.json() == {"reason": "busy"}
    assert len(followups(api, reading_id)) == 2 and attempts_of(api, reading_id) == 1  # the attempt rolled back
    monkeypatch.setattr(api.guard, "complete_json", check)
    again = ask(api.client, reading_id, "Second?", tz=MX)
    assert again.status_code == 402 and again.json()["reason"] == "confirm"


# --- stage 4.5 §5: one request, one follow-up ---

def test_the_same_number_replays_the_saved_followup(api):
    reading_id = ready_reading(api, kind="one")
    number = str(uuid.uuid4())
    first = parse_sse(ask(api.client, reading_id, "How do I start?", request_id=number).text)
    calls, guard_calls = len(api.reader.stream_calls()), len(api.guard.json_calls())
    again = parse_sse(ask(api.client, reading_id, "How do I start?", request_id=number).text)
    assert [e for e, _ in again] == ["meta", "section", "text", "done"]
    assert again[0][1] == {"reading_id": reading_id, "followup": 1, "replay": True, "paid": False,
                           "prompt_version": None, "soft_line": None}
    text = "".join(d["text"] for e, d in first if e == "text").strip()
    assert again[2][1] == {"name": "followup", "text": text}
    assert again[-1] == ("done", {"answer_shown": "model", "followups_left": 1,
                                  "followup_attempts_left": FOLLOWUP_ATTEMPTS - 1})
    assert (len(api.reader.stream_calls()), len(api.guard.json_calls())) == (calls, guard_calls)
    assert attempts_of(api, reading_id) == 1 and len(followups(api, reading_id)) == 1
    assert followups(api, reading_id)[0]["request_id"] == uuid.UUID(number)


def test_the_same_number_replays_a_replaced_answer_as_replaced(api):
    reading_id = ready_reading(api, kind="three")
    number = str(uuid.uuid4())
    api.reader.replies.append(FakeReply(chunks=["He feels the same ", "way about you."]))
    ask(api.client, reading_id, "Is there hope?", request_id=number)
    again = parse_sse(ask(api.client, reading_id, "Is there hope?", request_id=number).text)
    [replaced] = [d for e, d in again if e == "replace"]
    assert replaced["reason"] == "saved" and replaced["sections"]["followup"] == followups(api, reading_id)[0][
        "answer"]["fallback"]
    assert fin(again) == ("done", {"answer_shown": "fallback", "followups_left": 2})


def test_the_same_number_of_a_paid_followup_uses_no_second_reading(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    number = str(uuid.uuid4())
    ask(api.client, reading_id, "And one more?", tz=MX, use_reading=True, request_id=number)
    assert guest_used(api, reading_id) == 2
    again = parse_sse(ask(api.client, reading_id, "And one more?", tz=MX, use_reading=True, request_id=number).text)
    assert again[0][1]["paid"] is True
    assert fin(again) == ("done", {"answer_shown": "model", "followups_left": 0, "used_reading": True})
    assert guest_used(api, reading_id) == 2 and attempts_of(api, reading_id) == 3


def test_the_same_number_while_it_is_written_says_in_progress(api):
    reading_id = ready_reading(api, kind="one")
    number = uuid.uuid4()
    with api.db.connect() as conn:
        repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": uuid.UUID(reading_id), "n": 1,
                                    "question": "First?", "request_id": number, "created_at": api.clock()})
    events = parse_sse(ask(api.client, reading_id, "First?", request_id=str(number)).text)
    assert [e for e, _ in events] == ["meta", "error"]
    assert events[0][1]["followup"] == 1 and events[1][1] == {"reason": "in_progress"}
    assert api.guard.json_calls() == [] and attempts_of(api, reading_id) == 0
    other = ask(api.client, reading_id, "Second?", request_id=str(uuid.uuid4()))
    assert other.status_code == 409 and other.json() == {"reason": "busy"}  # still one at a time


def test_a_number_belongs_to_its_reading(api):
    first, second = ready_reading(api, kind="one"), ready_reading(api, kind="one")
    number = str(uuid.uuid4())
    ask(api.client, first, "How do I start?", request_id=number)
    events = parse_sse(ask(api.client, second, "How do I start?", request_id=number).text)
    assert events[0][1]["replay"] is False and len(followups(api, second)) == 1


def test_a_followup_number_must_be_a_uuid(api):
    reading_id = ready_reading(api, kind="one")
    response = ask(api.client, reading_id, "How do I start?", request_id="ask-1")
    assert response.status_code == 422 and response.json() == {"reason": "invalid", "fields": ["request_id"]}


# --- stage 4.5 review (fix wave) ---

def test_the_same_number_after_a_reader_crisis_replays_the_crisis_and_takes_nothing(api):
    reading_id = ready_reading(api, kind="one")
    number = str(uuid.uuid4())
    api.reader.replies.append(FakeReply(chunks=["[[crisis]]", "\nPlease talk to someone today."]))
    live = parse_sse(ask(api.client, reading_id, "Nothing matters anymore, right?", tz=MX, request_id=number).text)
    calls, guard_calls, attempts = len(api.reader.stream_calls()), len(api.guard.json_calls()), attempts_of(
        api, reading_id)
    again = parse_sse(ask(api.client, reading_id, "Nothing matters anymore, right?", tz=MX, request_id=number).text)
    assert [e for e, _ in live] == ["meta", "section", "crisis", "done"]
    assert [e for e, _ in again] == ["meta", "section", "crisis", "done"]
    assert again[0][1]["replay"] is True and again[0][1]["followup"] == 1
    assert again[2][1] == live[2][1] and again[2][1]["helplines"]["country"] == "MX"
    assert fin(again) == ("done", {"answer_shown": "crisis", "followups_left": 2})
    assert (len(api.reader.stream_calls()), len(api.guard.json_calls()), attempts_of(api, reading_id)) == (
        calls, guard_calls, attempts)
    assert len(followups(api, reading_id)) == 1


def test_the_tombstone_is_no_answer_and_no_used_free_followup(api):
    reading_id = ready_reading(api, kind="one")
    api.reader.replies.append(FakeReply(chunks=["[[crisis]]"]))
    ask(api.client, reading_id, "Nothing matters anymore, right?", tz=MX)
    full = api.client.get(f"/api/readings/{reading_id}").json()
    assert full["followups"] == [] and full["followups_left"] == 2
    first = parse_sse(ask(api.client, reading_id, "What helps me rest?").text)
    assert fin(first) == ("done", {"answer_shown": "model", "followups_left": 1})
    full = api.client.get(f"/api/readings/{reading_id}").json()
    assert [f["n"] for f in full["followups"]] == [2] and full["followups_left"] == 1
    # the reader's memory of earlier follow-ups holds the answered one only, not the tombstone
    parse_sse(ask(api.client, reading_id, "And then?").text)
    earlier = [m for m in api.reader.stream_calls()[-1]["messages"] if "What helps me rest?" in str(m["content"])]
    assert len(earlier) >= 1 and "Nothing matters" not in str(api.reader.stream_calls()[-1]["messages"])


def test_the_same_number_after_a_paid_reader_crisis_uses_no_second_reading(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    number = str(uuid.uuid4())
    api.reader.replies.append(FakeReply(chunks=["[[crisis]]"]))
    ask(api.client, reading_id, "Nothing matters anymore, right?", tz=MX, use_reading=True, request_id=number)
    calls = len(api.reader.stream_calls())
    again = parse_sse(ask(api.client, reading_id, "Nothing matters anymore, right?", tz=MX, use_reading=True,
                          request_id=number).text)
    assert [e for e, _ in again] == ["meta", "section", "crisis", "done"] and again[0][1]["paid"] is True
    assert fin(again) == ("done", {"answer_shown": "crisis", "followups_left": 0, "used_reading": True})
    assert guest_used(api, reading_id) == 2 and attempts_of(api, reading_id) == 3
    assert len(api.reader.stream_calls()) == calls and len(followups(api, reading_id)) == 3


def test_a_twin_inserted_during_the_question_check_is_replayed_in_the_lock(api, monkeypatch):
    """Review M1: the Repeated branch under the reading's lock."""
    reading_id = ready_reading(api, kind="one")
    number = uuid.uuid4()
    check = api.guard.complete_json

    def twin_answers_meanwhile(*args, **kwargs):
        with api.db.connect() as conn:
            fid = uuid.uuid4()
            conn.execute("UPDATE readings SET followup_attempts = 1 WHERE id = %s", (uuid.UUID(reading_id),))
            repo.insert_followup(conn, {"id": fid, "reading_id": uuid.UUID(reading_id), "n": 1, "question": "Q?",
                                        "request_id": number, "created_at": api.clock()})
            repo.save_followup_answer(conn, fid, {"model": "Done.", "fallback": None}, "fake-reader")
        return check(*args, **kwargs)

    monkeypatch.setattr(api.guard, "complete_json", twin_answers_meanwhile)
    events = parse_sse(ask(api.client, reading_id, "Q?", request_id=str(number)).text)
    assert events[0][0] == "meta" and events[0][1]["replay"] is True and events[0][1]["followup"] == 1
    assert events[2] == ("text", {"name": "followup", "text": "Done."})
    assert attempts_of(api, reading_id) == 1 and len(followups(api, reading_id)) == 1


def test_a_twin_that_took_the_last_attempt_is_replayed_not_429(api, monkeypatch):
    """Review M2: the refusal caused by the twin itself shows the twin's follow-up."""
    reading_id = ready_reading(api, kind="one")
    number = uuid.uuid4()
    check = api.guard.complete_json

    def twin_takes_the_last_attempt(*args, **kwargs):
        with api.db.connect() as conn:
            fid = uuid.uuid4()
            conn.execute("UPDATE readings SET followup_attempts = %s WHERE id = %s",
                         (FOLLOWUP_ATTEMPTS, uuid.UUID(reading_id)))
            repo.insert_followup(conn, {"id": fid, "reading_id": uuid.UUID(reading_id), "n": FOLLOWUP_ATTEMPTS,
                                        "question": "Q?", "request_id": number, "created_at": api.clock()})
            repo.save_followup_answer(conn, fid, {"model": "Done.", "fallback": None}, "fake-reader")
        return check(*args, **kwargs)

    monkeypatch.setattr(api.guard, "complete_json", twin_takes_the_last_attempt)
    response = ask(api.client, reading_id, "Q?", request_id=str(number))
    assert response.status_code == 200
    events = parse_sse(response.text)
    assert events[0][1]["replay"] is True and events[0][1]["followup"] == FOLLOWUP_ATTEMPTS
    assert attempts_of(api, reading_id) == FOLLOWUP_ATTEMPTS
    other = ask(api.client, reading_id, "Q?", request_id=str(uuid.uuid4()))  # another number still gets the 429
    assert other.status_code == 429 and other.json() == {"reason": "attempts"}


def test_a_twin_that_took_the_last_reading_is_replayed_not_402_plus(api, monkeypatch):
    """Final review: twin_or on the 402 plus refusal shows the twin's follow-up; another number still gets 402."""
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    number = uuid.uuid4()
    day = limits.local_day(limits.resolve_tz(MX), api.clock())
    check = api.guard.complete_json

    def twin_takes_the_last_reading(*args, **kwargs):
        with api.db.connect() as conn:
            reading = repo.get_reading(conn, uuid.UUID(reading_id), api.clock())
            fid = uuid.uuid4()
            repo.insert_followup(conn, {"id": fid, "reading_id": reading["id"], "n": 3, "question": "Q?",
                                        "paid_day": day, "request_id": number, "created_at": api.clock()})
            repo.save_followup_answer(conn, fid, {"model": "Done.", "fallback": None}, "fake-reader")
            while limits.take_slot(conn, limits.guest_subject(reading["guest_id"]), day, limits.DAILY_LIMIT):
                pass
        return check(*args, **kwargs)

    monkeypatch.setattr(api.guard, "complete_json", twin_takes_the_last_reading)
    response = ask(api.client, reading_id, "Q?", tz=MX, use_reading=True, request_id=str(number))
    assert response.status_code == 200
    events = parse_sse(response.text)
    assert events[0][1]["replay"] is True and events[0][1]["followup"] == 3 and events[0][1]["paid"] is True
    other = ask(api.client, reading_id, "Q?", tz=MX, use_reading=True, request_id=str(uuid.uuid4()))
    assert other.status_code == 402 and other.json() == {"reason": "plus", "remaining": 0}


def test_a_stop_phrase_gets_help_when_the_address_has_no_slot_left(api):
    """Final review (Task 3): at the address cap a stop-phrase still answers with the crisis (no model call, no
    attempt, no reading); any other question is 429 ip_limit."""
    reading_id = ready_reading(api, kind="one")
    ip_hash = api.ctx.salt.hash_ip("198.51.100.7", api.clock())
    with api.db.connect() as conn:
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, %s)",
                     (limits.followup_ip_subject(ip_hash), limits.utc_day(api.clock()), IP_FOLLOWUP_LIMIT))
    url = f"/api/readings/{reading_id}/followups"
    crisis = api.client.post(url, json={"question": "I want to die"}, headers=from_ip("198.51.100.7"))
    assert crisis.status_code == 200 and crisis.json()["group"] == "crisis" and crisis.json()["helplines"]
    assert api.guard.json_calls() == [] and attempts_of(api, reading_id) == 0 and followups(api, reading_id) == []
    plain = api.client.post(url, json={"question": "What next?"}, headers=from_ip("198.51.100.7"))
    assert plain.status_code == 429 and plain.json() == {"reason": "ip_limit"}
    assert api.guard.json_calls() == []


def test_a_crisis_question_repeated_with_one_number_gets_the_crisis_both_times(api):
    reading_id = ready_reading(api, kind="one")
    number = str(uuid.uuid4())
    api.guard.json_replies.extend([CRISIS] * 2)
    codes = [ask(api.client, reading_id, "Is any of this even worth it?", request_id=number) for _ in range(2)]
    assert [c.status_code for c in codes] == [200, 200] and all(c.json()["group"] == "crisis" for c in codes)
    assert attempts_of(api, reading_id) == 0 and followups(api, reading_id) == []


def test_a_confirmed_repeat_of_a_402_with_the_same_number_is_a_normal_paid_followup(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    number = str(uuid.uuid4())
    refused = ask(api.client, reading_id, "And one more?", tz=MX, request_id=number)
    assert refused.status_code == 402 and refused.json()["reason"] == "confirm"
    events = parse_sse(ask(api.client, reading_id, "And one more?", tz=MX, use_reading=True, request_id=number).text)
    assert events[0][1]["replay"] is False and events[0][1]["paid"] is True
    assert fin(events) == ("done", {"answer_shown": "model", "followups_left": 0, "used_reading": True})
    assert guest_used(api, reading_id) == 2  # the reading and the one paid follow-up


def test_the_same_number_of_a_paid_followup_still_written_says_in_progress(api):
    reading_id = ready_reading(api, kind="one")
    free_used(api, reading_id)
    number = uuid.uuid4()
    with api.db.connect() as conn:
        repo.insert_followup(conn, {"id": uuid.uuid4(), "reading_id": uuid.UUID(reading_id), "n": 3,
                                    "question": "And one more?", "request_id": number, "created_at": api.clock(),
                                    "paid_day": limits.local_day(limits.resolve_tz(MX), api.clock())})
    attempts, used, guard_calls = attempts_of(api, reading_id), guest_used(api, reading_id), len(api.guard.json_calls())
    events = parse_sse(ask(api.client, reading_id, "And one more?", tz=MX, use_reading=True,
                           request_id=str(number)).text)
    assert [e for e, _ in events] == ["meta", "error"] and events[0][1]["paid"] is True
    assert events[1][1] == {"reason": "in_progress"}
    assert (attempts_of(api, reading_id), guest_used(api, reading_id), len(api.guard.json_calls())) == (
        attempts, used, guard_calls)
