"""Stage 4.7: a Spanish section with a gendered form for the reader is rewritten once after the stream (reading,
follow-up, card of the day), with fake providers on the test database."""
import uuid
from datetime import date

import pytest

from app import repo
from app.daily import fill_daily_cache
from app.reader import fallback, flow, rewrite
from app.reader.provider import FakeReply, ProviderError, ProviderTimeout, StreamResult, split_chunks
from helpers import parse_sse, post_reading

MX = "America/Mexico_City"
GENDERED = "La carta habla de una pausa. Hoy estás cansada de cargar con todo y está bien bajar el ritmo."
NEUTRAL = "La carta habla de una pausa. Hoy te sientes sin energía para cargar con todo y está bien bajar el ritmo."
HEADLINE = "Hoy conviene ir con calma."
STEP = "Escribe hoy una cosa pequeña que puedas soltar."


def es_answer(card1: str = GENDERED, why: str | None = None) -> FakeReply:
    text = f"[[headline]]\n{HEADLINE}\n[[card 1]]\n{card1}\n[[step]]\n{STEP}\n"
    if why is not None:
        text += f"[[why]]\n{why}\n"
    return FakeReply(chunks=split_chunks(text))


def create(api, **body):
    response = post_reading(api.client, tz=MX, **body)
    assert response.status_code == 201, response.text
    return response.json()


def stream(api, reading_id):
    return parse_sse(api.client.get(f"/api/readings/{reading_id}/stream").text)


def saved(api, reading_id):
    with api.db.connect() as conn:
        return repo.get_reading(conn, uuid.UUID(str(reading_id)), api.clock())


def rewrite_rows(api) -> list[dict]:
    with api.db.connect() as conn:
        return conn.execute("SELECT * FROM llm_calls WHERE purpose = 'rewrite' ORDER BY id").fetchall()


def es_reading(api, **body):
    return create(api, lang="es", kind="one", question="¿Qué me conviene esta semana?", **body)


# --- the reading ---

def test_a_gendered_section_is_rewritten_saved_and_replaced(api):
    api.reader.replies.append(es_answer())
    api.reader.json_replies.append({"text": NEUTRAL})
    body = es_reading(api)
    events = stream(api, body["id"])
    [call] = api.reader.json_calls()
    assert call["system"] == rewrite.REWRITE_SYSTEM and GENDERED in call["messages"][0]["content"]
    [replaced] = [d for e, d in events if e == "replace"]
    assert replaced == {"sections": {"headline": HEADLINE, "card1": NEUTRAL, "step": STEP}, "reason": "gender",
                        "retry": False}
    names = [e for e, _ in events]
    assert names.index("replace") == len(names) - 2 and events[-1] == ("done", {"answer_shown": "model"})
    row = saved(api, body["id"])
    assert row["answer_shown"] == "model"
    assert row["answer"] == {"model": {"headline": HEADLINE, "card1": NEUTRAL, "step": STEP}, "fallback": None}
    [log_row] = rewrite_rows(api)
    assert log_row["reading_id"] == uuid.UUID(body["id"]) and log_row["model"] == "fake-reader"
    assert (log_row["prompt_version"], log_row["tokens_in"], log_row["stop_reason"]) == (
        rewrite.REWRITE_VERSION, 60, "end_turn")
    # the restored reading and a second stream show the rewritten text
    assert api.client.get(f"/api/readings/{body['id']}").json()["answer"]["card1"] == NEUTRAL
    replay = stream(api, body["id"])
    assert [d["text"] for e, d in replay if e == "text" and d["name"] == "card1"] == [NEUTRAL]


@pytest.mark.parametrize("reply", [
    ProviderTimeout("APITimeoutError"),
    ProviderError("APIConnectionError"),
    {"text": "La carta habla de una pausa. Hoy estás agotada de cargar con todo y está bien bajar el ritmo."},
    {"text": "La carta habla de una pausa. Hoy te sientes sin energía, pero él volverá y está bien bajar el ritmo."},
    {"text": "Pausa."},
    {"group": "ok"},
])
def test_a_failed_or_rejected_rewrite_keeps_the_original(api, reply):
    api.reader.replies.append(es_answer())
    api.reader.json_replies.append(reply)
    body = es_reading(api)
    events = stream(api, body["id"])
    assert len(api.reader.json_calls()) == 1
    assert [e for e, _ in events if e in ("replace", "fallback")] == []
    assert events[-1] == ("done", {"answer_shown": "model"})
    assert saved(api, body["id"])["answer"]["model"]["card1"] == GENDERED
    assert len(rewrite_rows(api)) == 1  # the call is logged even when its text is not taken


def test_a_timed_out_rewrite_is_counted_at_its_max_tokens(api):
    api.reader.replies.append(es_answer())
    api.reader.json_replies.append(ProviderTimeout("APITimeoutError"))
    stream(api, es_reading(api)["id"])
    [row] = rewrite_rows(api)
    assert (row["stop_reason"], row["tokens_out"]) == ("timeout", None)


def test_english_never_calls(api):
    api.reader.replies.append(FakeReply(chunks=split_chunks(
        f"[[headline]]\nA calm day.\n[[card 1]]\nYou feel tired today. {GENDERED}\n[[step]]\nWrite one line.\n")))
    body = create(api, lang="en", kind="one", question="What should I focus on?")
    events = stream(api, body["id"])
    assert api.reader.json_calls() == [] and rewrite_rows(api) == []
    assert [e for e, _ in events if e == "replace"] == []


def test_a_neutral_spanish_answer_makes_no_call(api):
    api.reader.replies.append(es_answer(card1=NEUTRAL))
    stream(api, es_reading(api)["id"])
    assert api.reader.json_calls() == [] and rewrite_rows(api) == []


def test_over_the_daily_budget_nothing_is_rewritten(api, monkeypatch):
    answers = iter([False])  # the reading itself still fits; the budget is spent when the rewrite would start
    monkeypatch.setattr(flow, "over_budget", lambda ctx: next(answers, True))
    api.reader.replies.append(es_answer())
    api.reader.json_replies.append({"text": NEUTRAL})
    body = es_reading(api)
    events = stream(api, body["id"])
    assert api.reader.json_calls() == [] and rewrite_rows(api) == []
    assert saved(api, body["id"])["answer"]["model"]["card1"] == GENDERED
    assert [e for e, _ in events if e == "replace"] == []


def test_a_line_from_the_card_base_is_never_rewritten(api, monkeypatch):
    # finalize replaces a why with a verdict word by the fixed line; that line is ours even if it had a hit
    monkeypatch.setattr(fallback, "reading_why", lambda base, reading: "Estás lista, dice la carta.")
    api.reader.replies.append(es_answer(why="Sí, la carta muestra un camino abierto."))
    api.reader.json_replies.append({"text": NEUTRAL})
    body = create(api, lang="es", kind="yes_no", question="¿Debo empezar el curso?")
    assert body["verdict"] is not None
    events = stream(api, body["id"])
    [call] = api.reader.json_calls()
    assert GENDERED in call["messages"][0]["content"]  # card1 only
    [replaced] = [d for e, d in events if e == "replace"]
    assert replaced["reason"] == "why"  # finalize's own reason stays
    assert replaced["sections"]["why"] == "Estás lista, dice la carta." and replaced["sections"]["card1"] == NEUTRAL
    assert saved(api, body["id"])["answer"]["model"]["card1"] == NEUTRAL


def test_a_banned_answer_shows_the_base_and_is_not_rewritten(api):
    api.reader.replies.append(es_answer(card1="Hoy estás cansada, pero él volverá y todo cambiará."))
    body = es_reading(api)
    events = stream(api, body["id"])
    assert api.reader.json_calls() == []
    assert [d["reason"] for e, d in events if e == "replace"] == ["banned"]


def test_several_sections_are_rewritten_at_once(api):
    headline = "Hoy estás lista para bajar el ritmo."
    api.reader.replies.append(FakeReply(chunks=split_chunks(
        f"[[headline]]\n{headline}\n[[card 1]]\n{GENDERED}\n[[step]]\n{STEP}\n")))
    new_headline = "Hoy tienes lo necesario para bajar el ritmo."
    asked = []

    def complete_json(system, messages, schema, max_tokens):  # the calls run in parallel: answer by content
        content = messages[0]["content"]
        asked.append(content)
        return {"text": new_headline if headline in content else NEUTRAL}, StreamResult(60, 8, "end_turn", "m")

    api.reader.complete_json = complete_json
    body = es_reading(api)
    events = stream(api, body["id"])
    assert len(asked) == 2 and len(rewrite_rows(api)) == 2
    [replaced] = [d for e, d in events if e == "replace"]
    assert replaced["sections"] == {"headline": new_headline, "card1": NEUTRAL, "step": STEP}


# --- the follow-up ---

def ready_es_reading(api) -> str:
    body = es_reading(api)
    parse_sse(api.client.get(f"/api/readings/{body['id']}/stream").text)
    return body["id"]


FOLLOWUP = ("Es normal que hoy te sientas inquieta con esta pregunta. La carta pide una pausa antes de decidir: "
            "mira qué parte depende de ti y escríbela en una línea.")
FOLLOWUP_NEUTRAL = ("Es normal que hoy esta pregunta te quite la calma. La carta pide una pausa antes de decidir: "
                    "mira qué parte depende de ti y escríbela en una línea.")


def test_a_gendered_followup_is_rewritten_saved_and_replaced(api):
    reading_id = ready_es_reading(api)
    api.reader.replies.append(FakeReply(chunks=split_chunks(FOLLOWUP)))
    api.reader.json_replies.append({"text": FOLLOWUP_NEUTRAL})
    events = parse_sse(api.client.post(f"/api/readings/{reading_id}/followups",
                                       json={"question": "¿Y cómo empiezo?"}).text)
    [replaced] = [d for e, d in events if e == "replace"]
    assert replaced == {"sections": {"followup": FOLLOWUP_NEUTRAL}, "reason": "gender", "retry": False}
    assert events[-1][0] == "done" and events[-1][1]["answer_shown"] == "model"
    assert events[-1][1]["followups_left"] == 1  # it still uses a free slot like any model answer
    with api.db.connect() as conn:
        [row] = repo.list_followups(conn, uuid.UUID(reading_id))
    assert row["answer"] == {"model": FOLLOWUP_NEUTRAL, "fallback": None} and row["counted"] is True
    full = api.client.get(f"/api/readings/{reading_id}").json()
    assert full["followups"][0]["answer"] == FOLLOWUP_NEUTRAL
    [log_row] = rewrite_rows(api)
    assert log_row["reading_id"] == uuid.UUID(reading_id)


def test_a_failed_followup_rewrite_keeps_the_text(api):
    reading_id = ready_es_reading(api)
    api.reader.replies.append(FakeReply(chunks=split_chunks(FOLLOWUP)))
    api.reader.json_replies.append(ProviderTimeout("APITimeoutError"))
    events = parse_sse(api.client.post(f"/api/readings/{reading_id}/followups",
                                       json={"question": "¿Y cómo empiezo?"}).text)
    assert [e for e, _ in events if e == "replace"] == []
    assert events[-1][1]["answer_shown"] == "model"
    with api.db.connect() as conn:
        [row] = repo.list_followups(conn, uuid.UUID(reading_id))
    assert row["answer"]["model"] == FOLLOWUP
    assert len(rewrite_rows(api)) == 1


def test_an_english_followup_never_calls(api):
    body = create(api, lang="en", kind="one", question="What should I focus on?")
    parse_sse(api.client.get(f"/api/readings/{body['id']}/stream").text)
    api.reader.replies.append(FakeReply(chunks=split_chunks(f"You may feel tired. {FOLLOWUP}")))
    parse_sse(api.client.post(f"/api/readings/{body['id']}/followups", json={"question": "And then?"}).text)
    assert api.reader.json_calls() == []


# --- the card of the day ---

DAY = date(2026, 11, 20)
DAILY = ("Hoy la Luna pide calma. Si te sientes perdida, no hace falta correr: mira lo que ya sabes, deja lo demás "
         "para después y da un paso pequeño que te deje respirar.")
DAILY_NEUTRAL = ("Hoy la Luna pide calma. Si te falta el rumbo, no hace falta correr: mira lo que ya sabes, deja lo "
                 "demás para después y da un paso pequeño que te deje respirar.")


def daily_texts(api) -> dict:
    with api.db.connect() as conn:
        rows = conn.execute("SELECT reversed, lang, text FROM daily_cache ORDER BY reversed, lang").fetchall()
    return {(r["reversed"], r["lang"]): r["text"] for r in rows}


def test_a_gendered_card_of_the_day_is_rewritten_before_it_is_cached(api):
    # the run's order: (False, en), (False, es), (True, en), (True, es)
    api.reader.replies.extend([FakeReply(), FakeReply(chunks=[DAILY]), FakeReply(), FakeReply(chunks=[DAILY])])
    api.reader.json_replies.extend([{"text": DAILY_NEUTRAL}, ProviderError("APIConnectionError")])
    assert fill_daily_cache(api.ctx, DAY, ("major-18-moon",))["written"] == 4
    texts = daily_texts(api)
    assert texts[(False, "es")] == DAILY_NEUTRAL
    assert texts[(True, "es")] == DAILY  # a failed rewrite caches the text as written
    rows = rewrite_rows(api)
    assert len(rows) == 2 and {r["reading_id"] for r in rows} == {None}
    assert len(api.reader.json_calls()) == 2  # only the Spanish texts with a hit


def test_the_card_of_the_day_over_budget_is_not_rewritten(api, monkeypatch):
    monkeypatch.setattr(flow, "over_budget", lambda ctx: True)  # fill_daily_cache has its own name: it still runs
    api.reader.replies.extend([FakeReply(), FakeReply(chunks=[DAILY])])
    fill_daily_cache(api.ctx, DAY, ("major-18-moon",))
    assert api.reader.json_calls() == [] and daily_texts(api)[(False, "es")] == DAILY


def test_a_rewrite_whose_log_fails_still_gives_the_answer(api, monkeypatch):
    # e.g. migration 006 not applied yet: the CHECK rejects purpose 'rewrite'
    real = flow.log_call

    def log_call(conn, ctx, reading_id, purpose, *args, **kwargs):
        if purpose == "rewrite":
            raise RuntimeError("check constraint")
        return real(conn, ctx, reading_id, purpose, *args, **kwargs)

    monkeypatch.setattr(flow, "log_call", log_call)
    api.reader.replies.append(es_answer())
    api.reader.json_replies.append({"text": NEUTRAL})
    body = es_reading(api)
    events = stream(api, body["id"])
    assert events[-1] == ("done", {"answer_shown": "model"})
    assert saved(api, body["id"])["answer"]["model"]["card1"] == NEUTRAL
