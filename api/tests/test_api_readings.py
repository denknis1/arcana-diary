import logging
import threading
import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import limits, repo
from app.db import DatabaseUnavailable
from app.config import IP_GUARD_LIMIT, load_settings
from app.main import create_app
from app.reader import fallback, flow
from app.reader.engine import Failed
from app.reader.provider import FakeReply, ProviderError, ProviderRefusal, ProviderTimeout, StreamResult, canned_answer, split_chunks
from app.safety.guard import GuardResult
from helpers import bearer, dump_tables, from_ip, guest_headers, parse_sse, post_reading, stream_sections

MX = "America/Mexico_City"


def create(api, client=None, **body):
    response = post_reading(client or api.client, tz=MX, **body)
    assert response.status_code == 201, response.text
    return response.json()


def stream(api, reading_id, client=None, tz=None):
    response = (client or api.client).get(f"/api/readings/{reading_id}/stream", params={"tz": tz} if tz else None)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return parse_sse(response.text)


def saved(api, reading_id):
    with api.db.connect() as conn:
        return repo.get_reading(conn, uuid.UUID(str(reading_id)), api.clock())


def guest_usage(api) -> int:
    with api.db.connect() as conn:
        row = conn.execute("SELECT coalesce(sum(count), 0) AS n FROM usage WHERE subject LIKE 'guest:%'").fetchone()
    return row["n"]


def guard_rows(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT lang, guard_group, source, count FROM guard_events ORDER BY guard_group").fetchall()


def one_card_reply(text: str) -> FakeReply:
    return FakeReply(chunks=split_chunks(text))


def test_create_three_sets_cookie_and_returns_cards(api):
    response = post_reading(api.client, kind="three", tz=MX)
    assert response.status_code == 201
    cookie = response.headers["set-cookie"].lower()
    for part in ("ad_guest=", "httponly", "secure", "samesite=lax", "max-age=31536000"):
        assert part in cookie
    body = response.json()
    assert [c["position"] for c in body["cards"]] == ["past", "present", "path"]
    assert all(c["name"] for c in body["cards"]) and body["verdict"] is None
    assert (body["guard_group"], body["remaining"], body["soft_line"], body["owner"]) == ("ok", 2, None, True)
    assert api.guard.json_calls() == []  # no question, no guard call


def test_api_answers_are_not_cached_or_indexed(api):
    response = post_reading(api.client, kind="one", tz=MX)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert "referrer-policy" not in api.client.get("/health").headers


def test_create_yes_no_has_verdict_from_rule(api):
    body = create(api, kind="yes_no", question="Should I sign up for the pottery class?")
    expected = api.ctx.cards.verdict(body["cards"])
    assert body["verdict"] == {"value": expected, "label": api.ctx.cards.rules["labels"]["en"][expected]}
    assert len(body["cards"]) == 1 and body["cards"][0]["position"] == "card"


@pytest.mark.parametrize("group", ["redirect_topic", "redirect_person"])
def test_yes_no_on_a_closed_topic_has_no_verdict(api, group):
    api.guard.json_replies.append({"group": group, "violence": False})
    body = create(api, kind="yes_no", question="Will she text me back?")
    assert (body["kind"], body["verdict"], body["guard_group"]) == ("yes_no", None, group)
    assert body["soft_line"] == api.ctx.texts["en"]["soft_lines"][group] and len(body["cards"]) == 1
    events = stream(api, body["id"])
    assert "why" not in stream_sections(events)
    assert "<verdict" not in api.reader.stream_calls()[0]["messages"][0]["content"]
    assert saved(api, body["id"])["verdict"] is None


def test_yes_no_on_money_keeps_the_verdict_with_a_disclaimer(api):
    api.guard.json_replies.append({"group": "redirect_money", "violence": False})
    body = create(api, kind="yes_no", question="Should I buy the used car this month?", lang="es")
    assert body["verdict"] is not None and body["soft_line"] == "Esto no es un consejo financiero."
    events = stream(api, body["id"])
    assert "why" in stream_sections(events)
    assert '<verdict value="' in api.reader.stream_calls()[0]["messages"][0]["content"]


def test_card_page_needs_known_card_id(api):
    missing = post_reading(api.client, kind="card_page", tz=MX)
    unknown = post_reading(api.client, kind="card_page", card_id="major-99-nothing", tz=MX)
    stray = post_reading(api.client, kind="one", card_id="major-18-moon", tz=MX)
    assert [r.status_code for r in (missing, unknown, stray)] == [422, 422, 422]
    assert missing.json() == {"reason": "invalid", "fields": ["card_id"]}
    body = create(api, kind="card_page", card_id="major-18-moon")
    assert len(body["cards"]) == 1 and body["source_card_id"] == "major-18-moon"


def test_invalid_input_is_422_with_one_shape(api):
    long_question = post_reading(api.client, question="x" * 501)
    assert long_question.status_code == 422 and long_question.json() == {"reason": "invalid", "fields": ["question"]}
    assert post_reading(api.client, kind="five").json()["fields"] == ["kind"]
    assert post_reading(api.client, lang="fr").status_code == 422
    bad = post_reading(api.client, topic="love", situation="dating")
    assert bad.status_code == 422 and bad.json() == {"reason": "invalid", "fields": ["situation"]}
    assert post_reading(api.client, topic="love", situation="after_breakup", tz=MX).status_code == 201


def test_stream_sends_sections_and_saves_answer(api):
    body = create(api, kind="three", question="How can I settle into my new team?", topic="work")
    events = stream(api, body["id"])
    assert events[0][0] == "meta" and events[0][1]["replay"] is False
    assert events[0][1]["prompt_version"] == "reader.en.v5"
    assert [d["name"] for e, d in events if e == "section"] == ["headline", "card1", "card2", "card3", "synthesis",
                                                                 "step"]
    assert events[-1] == ("done", {"answer_shown": "model"})
    row = saved(api, body["id"])
    assert row["answer_shown"] == "model" and row["answer"]["fallback"] is None
    assert row["answer"]["model"] == stream_sections(events)
    assert (row["model"], row["prompt_version"]) == ("fake-reader", "reader.en.v5")
    [call] = api.reader.stream_calls()
    assert call["system"] == api.ctx.prompts[("reader", "en")].text
    assert '<cards count="3">' in call["messages"][0]["content"]
    with api.db.connect() as conn:
        log_row = conn.execute("SELECT * FROM llm_calls WHERE purpose = 'reader'").fetchone()
    assert log_row["reading_id"] == uuid.UUID(body["id"]) and log_row["tokens_in"] == 120
    assert log_row["prompt_version"] == "reader.en.v5" and log_row["ms_first_token"] is not None
    assert log_row["created_at"] == api.clock()


def test_second_stream_replays_saved_text(api):
    body = create(api)
    first = stream(api, body["id"])
    second = stream(api, body["id"])
    assert second[0][1]["replay"] is True
    assert stream_sections(second) == stream_sections(first)
    assert second[-1] == ("done", {"answer_shown": "model"})
    assert len(api.reader.stream_calls()) == 1


def test_redirect_topic_soft_line(api):
    api.guard.json_replies.append({"group": "redirect_topic", "violence": False})
    body = create(api, question="Will my biopsy results be fine?")
    line = api.ctx.texts["en"]["soft_lines"]["redirect_topic"]
    assert (body["guard_group"], body["soft_line"]) == ("redirect_topic", line)
    events = stream(api, body["id"])
    assert events[0][1]["soft_line"] == line
    assert 'guard_group="redirect_topic"' in api.reader.stream_calls()[0]["messages"][0]["content"]


def test_naming_the_topic_does_not_replace_the_answer(api):
    api.guard.json_replies.append({"group": "redirect_topic", "violence": False})
    text = canned_answer(3, False).replace("The cards may point to a quiet, steady way forward.",
                                           "I can't speak to the pregnancy itself, but the cards can speak to you.")
    api.reader.replies.append(one_card_reply(text))
    body = create(api, question="Am I going to get pregnant this year?")
    events = stream(api, body["id"])
    assert events[-1] == ("done", {"answer_shown": "model"})
    assert not [e for e, _ in events if e in ("replace", "fallback")]


def test_crisis_returns_help_and_stores_nothing(api, caplog):
    question = "Sometimes I want to kill myself. Will it ever change?"
    with caplog.at_level(logging.INFO):
        response = post_reading(api.client, kind="three", question=question, tz=MX, headers={"CF-IPCountry": "US"})
    assert response.status_code == 200
    body = response.json()
    assert body["group"] == "crisis" and body["remaining"] == 3
    assert (body["helplines"]["country"], body["helplines"]["source"]) == ("MX", "timezone")  # CF-* ignored
    assert [line["topic"] for line in body["helplines"]["lines"]] == ["crisis", "violence"]
    assert body["crisis"]["title"] == api.ctx.texts["en"]["crisis"]["title"]
    assert api.guard.json_calls() == [] and api.reader.stream_calls() == []
    dump = dump_tables(api.db)
    assert "kill myself" not in dump and "MX" not in dump
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 0
    assert guard_rows(api) == [{"lang": "en", "guard_group": "crisis", "source": "terms", "count": 1}]
    assert guest_usage(api) == 0
    assert all("kill myself" not in record.getMessage() for record in caplog.records)


def test_crisis_from_guard_model_with_violence_es(api):
    api.guard.json_replies.append({"group": "crisis", "violence": True})
    question = "Mi pareja me controla el celular y me da miedo"
    response = post_reading(api.client, lang="es", kind="one", question=question, tz="Europe/Paris")
    body = response.json()
    assert response.status_code == 200 and body["group"] == "crisis"
    assert body["helplines"]["country"] is None  # a known zone outside our list: the directory only
    assert body["crisis"]["title"] == api.ctx.texts["es"]["crisis"]["title"]
    assert question not in dump_tables(api.db)
    with api.db.connect() as conn:
        call = conn.execute("SELECT * FROM llm_calls").fetchone()
    assert (call["purpose"], call["reading_id"], call["model"]) == ("guard", None, "fake-guard")


def test_crisis_lists_violence_lines_first_when_someone_hurts_the_person(api):
    response = post_reading(api.client, kind="one", question="My husband hits me when he drinks", tz="America/Chicago")
    assert [line["number"] for line in response.json()["helplines"]["lines"]] == ["1-800-799-7233", "988"]


def test_guard_refusal_is_crisis(api):
    api.guard.json_replies.append(ProviderRefusal(StreamResult(40, 0, "refusal", "fake-guard", "general_harms")))
    response = post_reading(api.client, kind="one", question="Something the guard will not touch", tz=MX)
    assert response.status_code == 200 and response.json()["group"] == "crisis"
    assert guard_rows(api) == [{"lang": "en", "guard_group": "crisis", "source": "refusal", "count": 1}]


def test_guard_timeout_reads_and_is_counted(api):
    api.guard.json_replies.append(ProviderTimeout("slow"))
    body = create(api, kind="one", question="What should I keep in mind this week?")
    assert body["guard_group"] == "ok"
    assert guard_rows(api) == [{"lang": "en", "guard_group": "ok", "source": "timeout", "count": 1}]


def test_reader_safety_net_turns_the_reading_into_a_crisis_answer(api):
    api.reader.replies.append(FakeReply(chunks=["[[cri", "sis]]\n", "Please talk to someone."]))
    body = create(api, kind="one", question="Everything feels pointless lately")
    events = stream(api, body["id"], tz=MX)
    assert [e for e, _ in events] == ["meta", "crisis", "done"]
    assert events[1][1]["helplines"]["country"] == "MX" and events[-1][1] == {"answer_shown": "crisis"}
    row = saved(api, body["id"])
    assert (row["question"], row["answer_shown"]) == (None, "crisis")
    assert "pointless" not in dump_tables(api.db)
    assert {"lang": "en", "guard_group": "crisis", "source": "reader", "count": 1} in guard_rows(api)
    owner_view = api.client.get(f"/api/readings/{body['id']}").json()
    assert owner_view["answer_shown"] == "crisis" and owner_view["group"] == "crisis"
    assert api.new_client().get(f"/api/readings/{body['id']}").status_code == 404


def test_crisis_helplines_reach_the_client_even_if_saving_fails(api, monkeypatch):
    def broken(*args, **kwargs):
        raise DatabaseUnavailable("down")
    api.reader.replies.append(FakeReply(chunks=["[[cri", "sis]]\n", "Please talk to someone."]))
    body = create(api, kind="one", question="Everything feels pointless lately")
    monkeypatch.setattr(repo, "save_crisis", broken)
    events = stream(api, body["id"], tz=MX)
    assert [e for e, _ in events] == ["meta", "crisis", "error"]
    assert events[1][1]["helplines"]["country"] == "MX" and events[2][1] == {"reason": "db"}


def test_first_token_timeout_gives_fallback_then_retry_succeeds(api):
    api.reader.replies.append(FakeReply(first_delay=1.0))
    body = create(api, kind="one", question="What should I keep in mind this week?")
    events = stream(api, body["id"])
    assert [e for e, _ in events] == ["meta", "fallback", "done"]
    fb = events[1][1]
    assert fb["reason"] == "timeout" and fb["retry"] is True
    assert fb["sections"]["headline"] == api.ctx.texts["en"]["reader_unavailable"]
    assert events[-1] == ("done", {"answer_shown": "fallback"})
    retry = api.client.post(f"/api/readings/{body['id']}/retry")
    assert retry.status_code == 200
    assert parse_sse(retry.text)[-1] == ("done", {"answer_shown": "model"})
    row = saved(api, body["id"])
    assert row["retries"] == 1 and row["answer_shown"] == "model"
    assert guest_usage(api) == 1


def test_retry_limit_is_two_and_does_not_count(api):
    api.reader.replies.extend([FakeReply(fail_after=0) for _ in range(3)])
    body = create(api, kind="one")
    first = stream(api, body["id"])
    assert first[1][0] == "fallback" and first[1][1]["retry"] is True
    r1 = parse_sse(api.client.post(f"/api/readings/{body['id']}/retry").text)
    assert r1[1][0] == "fallback" and r1[1][1]["retry"] is True
    r2 = parse_sse(api.client.post(f"/api/readings/{body['id']}/retry").text)
    assert r2[1][0] == "fallback" and r2[1][1]["retry"] is False
    third = api.client.post(f"/api/readings/{body['id']}/retry")
    assert third.status_code == 409 and third.json() == {"reason": "retries"}
    assert guest_usage(api) == 1


def test_retry_on_model_answer_is_409(api):
    body = create(api, kind="one")
    stream(api, body["id"])
    response = api.client.post(f"/api/readings/{body['id']}/retry")
    assert response.status_code == 409 and response.json() == {"reason": "not_fallback"}


def test_other_guest_cannot_retry(api):
    api.reader.replies.append(FakeReply(fail_after=0))
    body = create(api, kind="one")
    stream(api, body["id"])
    assert api.new_client().post(f"/api/readings/{body['id']}/retry").status_code == 404


def test_refusal_gives_fallback(api):
    api.reader.replies.append(FakeReply(refuse=True))
    body = create(api, kind="one")
    events = stream(api, body["id"])
    fb = next(d for e, d in events if e == "fallback")
    assert fb["reason"] == "refusal" and events[-1] == ("done", {"answer_shown": "fallback"})
    row = saved(api, body["id"])
    assert row["answer"]["model"] is None and row["answer"]["fallback"] == fb["sections"]
    with api.db.connect() as conn:
        call = conn.execute("SELECT * FROM llm_calls WHERE purpose = 'reader'").fetchone()
    assert (call["stop_reason"], call["refusal_category"], call["tokens_in"]) == ("refusal", "general_harms", 120)


def test_cut_stream_fills_missing_cards(api):
    api.reader.replies.append(FakeReply(fail_after=10))
    body = create(api, kind="three")
    events = stream(api, body["id"])
    [replaced] = [d for e, d in events if e == "replace"]
    assert (replaced["reason"], replaced["retry"]) == ("cut", False)
    sections = replaced["sections"]
    reading = saved(api, body["id"])
    excerpts = api.ctx.cards.excerpts(reading["cards"], "en", None)
    assert sections["headline"] == "The cards may point to a quiet, steady way forward."
    assert sections["card1"] == fallback.card_line(excerpts[0], "en")  # it was cut mid-sentence
    assert sections["card3"] == fallback.card_line(excerpts[2], "en")
    assert events[-1] == ("done", {"answer_shown": "model"})
    assert reading["answer"]["model"] == sections


def test_banned_claim_replaces_answer_and_keeps_both(api):
    text = canned_answer(3, False).replace("The cards may point to a quiet, steady way forward.",
                                           "This will happen for sure.")
    api.reader.replies.append(one_card_reply(text))
    body = create(api, kind="three")
    events = stream(api, body["id"])
    [replaced] = [d for e, d in events if e == "replace"]
    assert (replaced["reason"], replaced["retry"]) == ("banned", True)
    assert replaced["sections"]["headline"] == api.ctx.texts["en"]["reader_unavailable"]
    row = saved(api, body["id"])
    assert row["answer_shown"] == "fallback"
    assert row["answer"]["model"]["headline"] == "This will happen for sure."
    assert row["answer"]["fallback"] == replaced["sections"]
    assert events[-1] == ("done", {"answer_shown": "fallback"})


def test_why_with_verdict_word_is_replaced(api):
    text = canned_answer(1, True).replace("The card shows open hands and a clear road, a sign of easy movement.",
                                          "Yes, the card is bright and open.")
    api.reader.replies.append(one_card_reply(text))
    body = create(api, kind="yes_no", question="Should I start the course?")
    events = stream(api, body["id"])
    [replaced] = [d for e, d in events if e == "replace"]
    assert replaced["reason"] == "why"
    assert replaced["sections"]["why"] == fallback.why_line(api.ctx.cards, body["cards"][0], "en")
    assert replaced["sections"]["headline"] == "The cards may point to a quiet, steady way forward."
    assert saved(api, body["id"])["answer_shown"] == "model"


def test_owner_view_restores_everything(api):
    body = create(api, kind="yes_no", question="Should I call my sister tonight?")
    events = stream(api, body["id"])
    full = api.client.get(f"/api/readings/{body['id']}").json()
    assert full["cards"] == body["cards"] and full["verdict"] == body["verdict"]
    assert full["question"] == "Should I call my sister tonight?" and full["owner"] is True
    assert full["answer"] == stream_sections(events) and full["answer_shown"] == "model"
    assert full["status"] == "done"
    assert (full["followups"], full["followups_left"], full["retries_left"]) == ([], 2, 0)


def test_shared_link_shows_only_cards_and_answer(api):
    body = create(api, kind="three", question="How do I talk to my brother?", topic="love")
    stream(api, body["id"])
    public = api.new_client().get(f"/api/readings/{body['id']}").json()
    assert public["owner"] is False and public["answer"] and public["cards"] == body["cards"]
    for private in ("question", "topic", "situation", "guard_group", "followups", "followups_left", "retries_left"):
        assert private not in public
    assert "brother" not in str(public)


def test_first_stream_only_for_the_owner(api):
    body = create(api, kind="one")
    stranger = api.new_client()
    early = stranger.get(f"/api/readings/{body['id']}/stream")
    assert early.status_code == 403 and early.json() == {"reason": "owner_only"}
    assert api.reader.stream_calls() == []
    assert stranger.get(f"/api/readings/{body['id']}").json()["status"] == "pending"
    stream(api, body["id"])
    replay = stream(api, body["id"], client=stranger)
    assert replay[0][1]["replay"] is True and len(api.reader.stream_calls()) == 1


def test_unknown_or_expired_reading_is_404(api):
    body = create(api, kind="one")
    assert api.client.get(f"/api/readings/{uuid.uuid4()}").status_code == 404
    api.clock.advance(days=8)
    assert api.client.get(f"/api/readings/{body['id']}").json() == {"reason": "not_found"}
    assert api.client.get(f"/api/readings/{body['id']}/stream").status_code == 404


def test_turnstile_after_burst(api):
    ip = from_ip("198.51.100.23")
    codes = [post_reading(api.new_client(), kind="one", tz=MX, headers=ip).status_code for _ in range(6)]
    assert codes == [201] * 5 + [403]
    blocked = post_reading(api.new_client(), kind="one", tz=MX, headers=ip)
    assert blocked.json() == {"reason": "turnstile", "sitekey": ""}
    passed = post_reading(api.new_client(), kind="one", tz=MX, headers=ip, turnstile_token="good-token")
    assert passed.status_code == 201
    assert api.turnstile.calls[-1] == "good-token"


def test_spoofed_cloudflare_headers_are_ignored(api):
    codes = [post_reading(api.new_client(), kind="one", tz=MX,
                          headers={"CF-Connecting-IP": f"203.0.113.{i}"}).status_code for i in range(8)]
    assert codes == [201] * 5 + [403] * 3


def test_trusted_cloudflare_headers_are_used(api_factory):
    api = api_factory(trust_cloudflare=True)
    codes = [post_reading(api.new_client(), kind="one", tz=MX,
                          headers={"CF-Connecting-IP": f"203.0.113.{i}"}).status_code for i in range(8)]
    assert codes == [201] * 8
    crisis = post_reading(api.client, kind="one", question="I want to die", tz=MX, headers={"CF-IPCountry": "ES"})
    assert (crisis.json()["helplines"]["country"], crisis.json()["helplines"]["source"]) == ("ES", "cloudflare")


def test_turnstile_after_ip_daily_threshold(api):
    ip = "198.51.100.42"
    ip_hash = api.ctx.salt.hash_ip(ip, api.clock())
    with api.db.connect() as conn:
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, 20)",
                     (limits.ip_subject(ip_hash), limits.utc_day(api.clock())))
    assert post_reading(api.client, kind="one", tz=MX, headers=from_ip(ip)).status_code == 403
    assert post_reading(api.client, kind="one", tz=MX, headers=from_ip(ip),
                        turnstile_token="good-token").status_code == 201


def test_ip_hard_cap_is_not_lifted_by_turnstile(api):
    ip = "198.51.100.60"
    ip_hash = api.ctx.salt.hash_ip(ip, api.clock())
    with api.db.connect() as conn:
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, 60)",
                     (limits.ip_subject(ip_hash), limits.utc_day(api.clock())))
    response = post_reading(api.new_client(), kind="one", tz=MX, headers=from_ip(ip), turnstile_token="good-token")
    assert response.status_code == 429 and response.json() == {"reason": "ip_limit", "remaining": 0}
    assert api.turnstile.calls == []


def test_daily_limit_is_atomic_under_concurrency(api):
    api.guard.json_delay = 0.3  # every request waits in the guard, then all of them race for the 3 slots
    guest = uuid.uuid4()
    start = threading.Barrier(6)
    codes = []

    def worker(i):
        client = api.new_client()
        start.wait()
        response = post_reading(client, kind="one", tz=MX, question=f"What helps me focus, take {i}?",
                                headers={**guest_headers(guest), **from_ip(f"198.51.100.{i}")})
        codes.append(response.status_code)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [201, 201, 201, 429, 429, 429]
    assert guest_usage(api) == 3
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 3


def test_spent_budget_gives_base_meanings(api):
    with api.db.connect() as conn:
        repo.log_llm_call(conn, {"reading_id": None, "purpose": "reader", "model": "claude-haiku-5-5",
                                 "prompt_version": "reader.en.v1", "ms_first_token": 1, "ms_total": 1,
                                 "tokens_in": 1, "tokens_out": 1, "cost_usd": 5.0, "stop_reason": "end_turn",
                                 "refusal_category": None, "created_at": api.clock()})
    body = create(api, kind="one")
    events = stream(api, body["id"])
    fb = next(d for e, d in events if e == "fallback")
    assert fb["reason"] == "budget" and api.reader.stream_calls() == []


def spend_on_guard(api, usd: float) -> None:
    with api.db.connect() as conn:
        repo.log_llm_call(conn, {"reading_id": None, "purpose": "guard", "model": "claude-haiku-5-5",
                                 "prompt_version": "guard.v1", "ms_first_token": None, "ms_total": 1,
                                 "tokens_in": 1, "tokens_out": 1, "cost_usd": usd, "stop_reason": "end_turn",
                                 "refusal_category": None, "created_at": api.clock()})


def test_guard_keeps_working_over_the_daily_budget(api):
    with api.db.connect() as conn:
        repo.log_llm_call(conn, {"reading_id": None, "purpose": "reader", "model": "claude-haiku-5-5",
                                 "prompt_version": "reader.en.v1", "ms_first_token": 1, "ms_total": 1,
                                 "tokens_in": 1, "tokens_out": 1, "cost_usd": 5.0, "stop_reason": "end_turn",
                                 "refusal_category": None, "created_at": api.clock()})
    create(api, kind="one", question="What helps me rest?")
    assert len(api.guard.json_calls()) == 1


def test_over_the_guard_budget_a_question_is_503_and_nothing_is_written(api):
    spend_on_guard(api, 1.0)
    response = post_reading(api.client, kind="one", question="Should I move?", tz=MX)
    assert response.status_code == 503 and response.json() == {"reason": "unavailable"}
    assert api.guard.json_calls() == [] and guest_usage(api) == 0
    assert post_reading(api.client, kind="one", tz=MX).status_code == 201  # no question: no check needed


def test_a_stop_phrase_does_not_query_the_budget(api, monkeypatch):
    calls = []
    monkeypatch.setattr(flow, "guard_over_budget", lambda ctx: calls.append(1) or False)
    response = post_reading(api.client, kind="one", question="I want to die", tz=MX)
    assert response.status_code == 200 and response.json()["group"] == "crisis" and calls == []
    post_reading(api.client, kind="one", question="Should I move?", tz=MX)
    assert calls == [1]


def test_over_the_guard_budget_an_ambiguous_phrase_is_crisis(api):
    spend_on_guard(api, 1.0)
    response = post_reading(api.client, kind="one", question="Will I hurt myself if I go back to my ex?", tz=MX)
    assert response.status_code == 200 and response.json()["group"] == "crisis"
    assert api.guard.json_calls() == []
    assert guard_rows(api) == [{"lang": "en", "guard_group": "crisis", "source": "budget", "count": 1}]


def test_a_cut_call_counts_its_upper_price(api):
    with api.db.connect() as conn:
        flow.log_call(conn, api.ctx, None, "reader", "claude-haiku-5-5", "reader.en.v1",
                      Failed("timeout", False, None, 15000), flow.READER_MAX_TOKENS)
        flow.record_guard(conn, api.ctx, GuardResult("ok", "timeout", False, "claude-haiku-5-5", 3000), "en",
                          limits.utc_day(api.clock()), None)
        costs = [float(r["cost_usd"]) for r in conn.execute("SELECT cost_usd FROM llm_calls ORDER BY id")]
    assert costs == [0.002, 0.000512]


def test_a_call_that_never_reached_the_model_costs_nothing(api):
    with api.db.connect() as conn:
        flow.log_call(conn, api.ctx, None, "reader", "claude-haiku-5-5", "reader.en.v1",
                      Failed("error", False, None, 40), flow.READER_MAX_TOKENS)
        flow.record_guard(conn, api.ctx, GuardResult("ok", "error", False, "claude-haiku-5-5", 40), "en",
                          limits.utc_day(api.clock()), None)
        costs = [r["cost_usd"] for r in conn.execute("SELECT cost_usd FROM llm_calls ORDER BY id")]
    assert costs == [None, None]
    assert flow.guard_over_budget(api.ctx) is False


def test_database_down_is_503():
    settings = replace(load_settings({}), database_url="postgresql://nobody@127.0.0.1:1/none", run_migrations=False)
    client = TestClient(create_app(settings), base_url="https://testserver")
    response = post_reading(client, kind="one", tz=MX)
    assert response.status_code == 503 and response.json() == {"reason": "db"}
    assert client.get(f"/api/readings/{uuid.uuid4()}").status_code == 503
    assert client.get("/health").json() == {"status": "ok"}


def test_llm_cost_logged_for_priced_model(api):
    api.reader.model = "claude-haiku-5-5"
    body = create(api, kind="one")
    stream(api, body["id"])
    with api.db.connect() as conn:
        call = conn.execute("SELECT * FROM llm_calls WHERE purpose = 'reader'").fetchone()
    assert call["model"] == "claude-haiku-5-5" and float(call["cost_usd"]) == 0.000052


def test_stream_in_progress_returns_error_event(api):
    body = create(api, kind="one")
    with api.db.connect() as conn:
        assert repo.claim_stream(conn, uuid.UUID(body["id"]), api.clock())
    assert stream(api, body["id"]) == [("error", {"reason": "in_progress"})]
    assert api.client.get(f"/api/readings/{body['id']}").json()["status"] == "streaming"


def test_client_disconnect_does_not_lose_the_answer(api):
    api.reader.replies.append(FakeReply(chunk_delay=0.02))
    body = create(api, kind="three")
    events = flow.stream_reading(api.ctx, saved(api, body["id"]))
    assert next(events).startswith("event: meta") and next(events).startswith("event: section")
    # the client goes away here: nobody reads `events` any more
    assert api.client.get(f"/api/readings/{body['id']}").json()["status"] == "streaming"
    assert events.join(timeout=10)
    full = api.client.get(f"/api/readings/{body['id']}").json()
    assert full["status"] == "done" and full["answer_shown"] == "model"
    assert set(full["answer"]) == {"headline", "card1", "card2", "card3", "synthesis", "step"}


def test_log_lines_have_no_question_text(api, caplog):
    with caplog.at_level(logging.INFO):
        body = create(api, kind="three", question="How do I handle the move to Monterrey?")
        stream(api, body["id"])
    messages = [record.getMessage() for record in caplog.records]
    assert any(m.startswith("llm_call purpose=reader") for m in messages)
    assert all("Monterrey" not in m for m in messages)


CRISIS = {"group": "crisis", "violence": False}


def test_question_checks_are_capped_per_address(api):
    ip = "198.51.100.77"
    ip_hash = api.ctx.salt.hash_ip(ip, api.clock())
    with api.db.connect() as conn:
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, %s)",
                     (limits.guard_ip_subject(ip_hash), limits.utc_day(api.clock()), IP_GUARD_LIMIT - 1))
    api.guard.json_replies.append(CRISIS)
    ask = dict(kind="one", tz=MX, headers=from_ip(ip), turnstile_token="good-token")
    sixtieth = post_reading(api.client, question="Is there any way out of this?", **ask)
    assert sixtieth.status_code == 200 and sixtieth.json()["group"] == "crisis"
    assert len(api.guard.json_calls()) == 1
    sixty_first = post_reading(api.client, question="Is there any way out of this?", **ask)
    assert sixty_first.status_code == 503 and sixty_first.json() == {"reason": "unavailable"}
    stop_phrase = post_reading(api.client, question="I want to die", **ask)
    assert stop_phrase.status_code == 200 and stop_phrase.json()["group"] == "crisis"
    assert post_reading(api.client, **ask).status_code == 201  # no question: no check needed
    assert len(api.guard.json_calls()) == 1 and guest_usage(api) == 1
    other = post_reading(api.new_client(), question="Should I move?", kind="one", tz=MX,
                         headers=from_ip("198.51.100.78"))
    assert other.status_code == 201 and len(api.guard.json_calls()) == 2


def test_crisis_answers_from_one_address_lead_to_turnstile(api):
    ip = from_ip("198.51.100.88")
    api.guard.json_default = CRISIS
    codes = []
    for _ in range(limits.IP_DAILY_THRESHOLD):
        response = post_reading(api.client, kind="one", tz=MX, question="Is there any way out?", headers=ip)
        codes.append(response.status_code)
        api.clock.advance(seconds=13)  # slower than the burst threshold
    assert codes == [200] * limits.IP_DAILY_THRESHOLD and guest_usage(api) == 0
    blocked = post_reading(api.client, kind="one", tz=MX, question="Is there any way out?", headers=ip)
    assert blocked.status_code == 403 and blocked.json()["reason"] == "turnstile"
    assert len(api.guard.json_calls()) == limits.IP_DAILY_THRESHOLD  # Turnstile comes before the guard call
    passed = post_reading(api.client, kind="one", tz=MX, question="Is there any way out?", headers=ip,
                          turnstile_token="good-token")
    assert passed.status_code == 200 and len(api.guard.json_calls()) == limits.IP_DAILY_THRESHOLD + 1


def test_stop_phrases_do_not_take_the_question_check_slot(api):
    ip = "198.51.100.99"
    ip_hash = api.ctx.salt.hash_ip(ip, api.clock())
    for _ in range(21):
        response = post_reading(api.client, kind="one", tz=MX, question="I want to die", headers=from_ip(ip))
        assert response.status_code == 200 and response.json()["group"] == "crisis"
        api.clock.advance(seconds=13)  # slower than the burst threshold
    assert api.guard.json_calls() == []
    with api.db.connect() as conn:
        assert limits.used(conn, limits.guard_ip_subject(ip_hash), limits.utc_day(api.clock())) == 0


def test_guard_answer_that_is_unusable_still_costs_something(api):
    api.guard.model = "claude-haiku-5-5"
    cut = StreamResult(60, 1024, "max_tokens", "claude-haiku-5-5")
    silent = StreamResult(None, None, None, "claude-haiku-5-5")  # answered, but no usage came back
    api.guard.json_replies.extend([ProviderError("max_tokens: structured output truncated", cut),
                                   ProviderError("no text block", silent),
                                   ProviderError("APIConnectionError")])
    for i in range(3):
        body = create(api, kind="one", question=f"What helps me rest, attempt {i}?")
        assert body["guard_group"] == "ok"
        api.clock.advance(seconds=13)
    with api.db.connect() as conn:
        costs = [r["cost_usd"] for r in conn.execute("SELECT cost_usd FROM llm_calls WHERE purpose = 'guard' "
                                                     "ORDER BY id")]
    assert [float(c) if c is not None else None for c in costs] == [0.000518, 0.000512, None]
    assert guard_rows(api) == [{"lang": "en", "guard_group": "ok", "source": "error", "count": 3}]


def test_owner_view_shows_follow_up_attempts_left(api):
    body = create(api, kind="one")
    stream(api, body["id"])
    assert api.client.get(f"/api/readings/{body['id']}").json()["followup_attempts_left"] == 8
    for used, left in ((3, 5), (8, 0)):
        with api.db.connect() as conn:
            conn.execute("UPDATE readings SET followup_attempts = %s WHERE id = %s", (used, body["id"]))
        assert api.client.get(f"/api/readings/{body['id']}").json()["followup_attempts_left"] == left
    assert "followup_attempts_left" not in api.new_client().get(f"/api/readings/{body['id']}").json()


def test_nul_in_a_question_is_422_before_any_guard_call_or_slot(api):
    response = post_reading(api.client, question="Will it work\x00 out?", tz=MX)
    assert response.status_code == 422 and response.json() == {"reason": "invalid", "fields": ["question"]}
    assert api.guard.calls == [] and api.reader.calls == []
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM usage").fetchone()["n"] == 0
        assert conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 0



# --- stage 4.3 §10 (м-н8): a database failure during a generation frees its stream claim at once ---

def test_a_database_failure_after_the_claim_frees_it(api, monkeypatch):
    body = create(api, kind="one")

    def down(ctx):
        raise DatabaseUnavailable("down")

    monkeypatch.setattr(flow, "over_budget", down)
    assert stream(api, body["id"]) == [("error", {"reason": "db"})]
    assert saved(api, body["id"])["stream_started_at"] is None
    monkeypatch.undo()
    assert stream(api, body["id"])[-1] == ("done", {"answer_shown": "model"})  # no 180 s of "in_progress"


def test_a_failed_save_frees_the_claim(api, monkeypatch):
    body = create(api, kind="one")

    def down(*args, **kwargs):
        raise DatabaseUnavailable("down")

    monkeypatch.setattr(repo, "save_answer", down)
    assert stream(api, body["id"])[-1] == ("error", {"reason": "db"})
    row = saved(api, body["id"])
    assert row["answer"] is None and row["stream_started_at"] is None


# --- stage 4.5 §3: help first, then the limit ---

def use_up_the_day(api, client=None, headers=None):
    for _ in range(3):
        assert post_reading(client or api.client, kind="one", tz=MX, headers=headers).status_code == 201


def guard_calls_logged(api) -> int:
    with api.db.connect() as conn:
        return conn.execute("SELECT count(*) AS n FROM llm_calls WHERE purpose = 'guard'").fetchone()["n"]


def test_a_stop_phrase_at_the_daily_limit_gets_the_crisis_answer(api):
    use_up_the_day(api)
    response = post_reading(api.client, kind="one", tz=MX, question="I want to die")
    assert response.status_code == 200
    body = response.json()
    assert (body["group"], body["remaining"]) == ("crisis", 0)
    assert api.guard.json_calls() == [] and guest_usage(api) == 3
    assert guard_rows(api) == [{"lang": "en", "guard_group": "crisis", "source": "terms", "count": 1}]


def test_a_crisis_found_by_the_check_model_at_the_daily_limit_gets_the_crisis_answer(api):
    use_up_the_day(api)
    api.guard.json_replies.append(CRISIS)
    response = post_reading(api.client, kind="three", tz=MX, question="Is there any way out of this?")
    assert response.status_code == 200 and response.json()["group"] == "crisis"
    assert len(api.guard.json_calls()) == 1 and guard_calls_logged(api) == 1
    with api.db.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"] == 3


def test_an_ordinary_question_at_the_daily_limit_is_checked_then_refused(api):
    use_up_the_day(api)
    response = post_reading(api.client, kind="one", tz=MX, question="Should I take the pottery class?")
    assert response.status_code == 429 and response.json() == {"reason": "limit", "remaining": 0}
    assert len(api.guard.json_calls()) == 1  # the check first; its call is logged for the guard budget
    assert guard_calls_logged(api) == 1 and guest_usage(api) == 3
    with api.db.connect() as conn:  # ...for no reading: none is made
        assert conn.execute("SELECT reading_id FROM llm_calls WHERE purpose = 'guard'").fetchone()["reading_id"] is None
    assert guard_rows(api) == [{"lang": "en", "guard_group": "ok", "source": "model", "count": 1}]
    assert post_reading(api.client, kind="one", tz=MX).json() == {"reason": "limit", "remaining": 0}
    assert len(api.guard.json_calls()) == 1  # no question: nothing to check


def test_the_address_cap_still_comes_before_the_question_check(api):
    ip = "198.51.100.123"
    ip_hash = api.ctx.salt.hash_ip(ip, api.clock())
    with api.db.connect() as conn:
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, 60)",
                     (limits.ip_subject(ip_hash), limits.utc_day(api.clock())))
    response = post_reading(api.client, kind="one", tz=MX, question="I want to die", headers=from_ip(ip))
    assert response.status_code == 429 and response.json() == {"reason": "ip_limit", "remaining": 0}
    assert guard_rows(api) == []


def test_at_the_daily_limit_a_question_nobody_can_check_is_429_limit(api):
    """Fable plan review I6(b): over the guard's budget, or with the address's checks used, a question only the
    model can check cannot get a reading anyway — the limit answers, not "unavailable" (below the limit: 503)."""
    use_up_the_day(api)
    with api.db.connect() as conn:
        repo.log_llm_call(conn, {"reading_id": None, "purpose": "guard", "model": "claude-haiku-5-5",
                                 "prompt_version": "guard.v1", "ms_first_token": None, "ms_total": 1,
                                 "tokens_in": 1, "tokens_out": 1, "cost_usd": 1.0, "stop_reason": "end_turn",
                                 "refusal_category": None, "created_at": api.clock()})
    over_budget = post_reading(api.client, kind="one", tz=MX, question="Should I take the pottery class?")
    assert over_budget.status_code == 429 and over_budget.json() == {"reason": "limit", "remaining": 0}
    crisis = post_reading(api.client, kind="one", tz=MX, question="I want to die")  # a stop-phrase still helps
    assert crisis.status_code == 200 and crisis.json()["group"] == "crisis"
    below = post_reading(api.new_client(), kind="one", tz=MX, question="Should I take the pottery class?",
                         headers=from_ip("198.51.100.150"))  # another device and address
    assert below.status_code == 503 and below.json() == {"reason": "unavailable"}
    assert api.guard.json_calls() == []


# --- stage 4.5 §5: one request, one reading ---

def reading_count(api) -> int:
    with api.db.connect() as conn:
        return conn.execute("SELECT count(*) AS n FROM readings").fetchone()["n"]


def test_the_same_request_number_returns_the_same_reading(api):
    number = str(uuid.uuid4())
    ask = dict(kind="three", tz=MX, question="How can I settle into my new team?", request_id=number)
    first = post_reading(api.client, **ask)
    again = post_reading(api.client, **ask)
    assert (first.status_code, again.status_code) == (201, 201)
    assert again.json() == first.json() and first.json()["remaining"] == 2
    assert (reading_count(api), guest_usage(api), len(api.guard.json_calls())) == (1, 1, 1)
    assert saved(api, first.json()["id"])["request_id"] == uuid.UUID(number)


def test_a_repeat_of_the_last_reading_of_the_day_is_not_refused(api):
    use_up_the_day(api)
    with api.db.connect() as conn:  # the third reading was made with a number
        conn.execute("UPDATE readings SET request_id = %s WHERE id = (SELECT id FROM readings LIMIT 1)",
                     (uuid.UUID("00000000-0000-4000-8000-000000000003"),))
    again = post_reading(api.client, kind="one", tz=MX, request_id="00000000-0000-4000-8000-000000000003")
    assert again.status_code == 201 and again.json()["remaining"] == 0
    assert (reading_count(api), guest_usage(api)) == (3, 3)


def test_another_owners_number_finds_nothing(api):
    number = str(uuid.uuid4())
    mine = create(api, kind="one", request_id=number)
    other = create(api, client=api.new_client(), kind="one", request_id=number)
    assert other["id"] != mine["id"] and reading_count(api) == 2


def test_an_account_finds_its_reading_from_any_device(api):
    user, number = uuid.uuid4(), str(uuid.uuid4())
    phone, laptop = api.new_client(), api.new_client()
    first = post_reading(phone, kind="one", tz=MX, request_id=number, headers=bearer(user))
    again = post_reading(laptop, kind="one", tz=MX, request_id=number, headers=bearer(user))
    as_guest = post_reading(phone, kind="one", tz=MX, request_id=number)
    assert again.json()["id"] == first.json()["id"] and again.json()["remaining"] == 4
    assert as_guest.json()["id"] != first.json()["id"]  # the device's guest is another owner


def test_without_a_number_every_request_is_a_new_reading(api):
    first, second = create(api, kind="one"), create(api, kind="one")
    assert first["id"] != second["id"] and guest_usage(api) == 2


def test_a_request_number_must_be_a_uuid(api):
    response = post_reading(api.client, kind="one", tz=MX, request_id="draw-1")
    assert response.status_code == 422 and response.json() == {"reason": "invalid", "fields": ["request_id"]}


def test_two_requests_with_one_number_at_once_make_one_reading(api):
    api.guard.json_delay = 0.3  # both wait in the question check, then race to insert
    guest, number = uuid.uuid4(), str(uuid.uuid4())
    start = threading.Barrier(2)
    answers = []

    def worker():
        client = api.new_client()
        start.wait()
        answers.append(post_reading(client, kind="one", tz=MX, question="What helps me focus?", request_id=number,
                                    headers=guest_headers(guest)))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [a.status_code for a in answers] == [201, 201]
    assert answers[0].json()["id"] == answers[1].json()["id"]
    assert (reading_count(api), guest_usage(api)) == (1, 1)  # the loser's slot rolled back with its insert


def test_a_repeat_is_found_before_the_address_cap_and_turnstile(api):
    """Fable plan review I6(a): a repeat takes nothing, and a Turnstile token works once — so the lookup comes
    before both (owner decision 21.11.2026)."""
    ip = "198.51.100.160"
    ip_hash = api.ctx.salt.hash_ip(ip, api.clock())
    number = str(uuid.uuid4())
    with api.db.connect() as conn:  # from here on the address needs Turnstile
        conn.execute("INSERT INTO usage (subject, day, count) VALUES (%s, %s, %s)",
                     (limits.ip_subject(ip_hash), limits.utc_day(api.clock()), limits.IP_DAILY_THRESHOLD))
    ask = dict(kind="one", tz=MX, request_id=number, headers=from_ip(ip))
    first = post_reading(api.client, turnstile_token="good-token", **ask)
    assert first.status_code == 201
    without_token = post_reading(api.client, **ask)
    assert without_token.status_code == 201 and without_token.json()["id"] == first.json()["id"]
    with api.db.connect() as conn:  # and now the address is at its hard cap
        conn.execute("UPDATE usage SET count = 60 WHERE subject = %s", (limits.ip_subject(ip_hash),))
    capped = post_reading(api.client, **ask)
    assert capped.status_code == 201 and capped.json()["id"] == first.json()["id"]
    assert post_reading(api.client, kind="one", tz=MX, headers=from_ip(ip)).json() == {"reason": "ip_limit",
                                                                                         "remaining": 0}
    assert api.turnstile.calls == ["good-token"] and reading_count(api) == 1


def test_a_number_of_an_expired_reading_is_409(api):
    number = uuid.uuid4()
    create(api, kind="one")
    with api.db.connect() as conn:  # expired, and not purged yet
        conn.execute("UPDATE readings SET request_id = %s, expires_at = %s", (number, api.clock()))
    response = post_reading(api.client, kind="one", tz=MX, request_id=str(number))
    assert response.status_code == 409 and response.json() == {"reason": "request_id"}
    assert guest_usage(api) == 1 and reading_count(api) == 1  # the new insert and its slot rolled back
