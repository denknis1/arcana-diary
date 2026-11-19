import json
import time
from types import SimpleNamespace

import pytest

from app.reader.engine import Failed, run_stream
from app.reader.provider import FakeProvider, FakeReply, ProviderError
from evals.metering import BudgetExceeded, CachingGuard, Meter, MeteredProvider, RecordingJudge, purpose_of

READING = [{"role": "user", "content": "<reading kind=\"one\">"}]


def test_meter_counts_cost_and_refuses_over_the_ceiling():
    meter = Meter(0.0001)
    reader = MeteredProvider(FakeProvider(model="claude-haiku-5-5"), meter)
    meter.item = "en-01"
    list(reader.stream("system", READING, 100))  # 120 in / 80 out at 0.10 / 0.50 -> $0.000052
    assert meter.spent == pytest.approx(0.000052)
    record = meter.calls[0]
    assert (record.model, record.purpose, record.item, record.tokens_in, record.tokens_out) == (
        "claude-haiku-5-5", "reader", "en-01", 120, 80)
    assert record.ms_first is not None and record.error is None
    list(reader.stream("system", READING, 100))
    assert meter.exhausted
    with pytest.raises(BudgetExceeded):
        list(reader.stream("system", READING, 100))
    assert meter.refused == 1 and len(meter.calls) == 2
    assert meter.records()[0]["cost_usd"] == pytest.approx(0.000052)


def test_purpose_of_messages():
    assert purpose_of(READING) == "reader"
    assert purpose_of([{"role": "user", "content": '<daily lang="en">'}]) == "daily"
    assert purpose_of([*READING, {"role": "assistant", "content": "a"}, {"role": "user", "content": "q"}]) == "followup"


def test_a_failed_call_without_usage_costs_its_upper_bound():
    meter = Meter(1.0)
    failing = FakeProvider(model="claude-haiku-5-5", replies=[FakeReply(fail_after=1)])
    with pytest.raises(ProviderError):
        list(MeteredProvider(failing, meter).stream("system", READING, 100))
    assert meter.calls[0].error == "ProviderError" and meter.calls[0].tokens_out is None
    assert meter.calls[0].cost_usd == pytest.approx(0.00005)  # 100 output tokens at 0.50


def test_a_stream_abandoned_by_the_engine_is_recorded_for_its_item_at_its_upper_bound():
    meter = Meter(1.0)
    slow = MeteredProvider(FakeProvider(model="claude-haiku-5-5", replies=[FakeReply(first_delay=0.3)]), meter)
    meter.item = "en-01"
    pieces = list(run_stream(slow, "system", READING, 100, first_token_timeout=0.05))
    assert isinstance(pieces[-1], Failed) and pieces[-1].reason == "timeout"
    meter.item = "en-02"  # the run moves on while the abandoned worker is still waiting
    deadline = time.monotonic() + 2.0
    while not meter.calls and time.monotonic() < deadline:  # the worker ends after its first chunk (~0.3 s)
        time.sleep(0.01)
    assert len(meter.calls) == 1
    record = meter.calls[0]
    assert (record.item, record.error, record.tokens_out) == ("en-01", "abandoned", None)
    assert record.cost_usd == pytest.approx(0.00005) and meter.spent == pytest.approx(0.00005)


def test_complete_json_is_metered_with_the_given_purpose():
    meter = Meter(1.0)
    guard = MeteredProvider(FakeProvider(model="claude-haiku-5-5"), meter, "guard")
    data, result = guard.complete_json("system", READING, {}, 50)
    assert data == {"group": "ok", "violence": False} and result.tokens_in == 60
    assert meter.calls[0].purpose == "guard" and meter.spent == pytest.approx(0.00001)


def test_every_record_is_appended_to_the_sink_at_once(tmp_path):
    sink = tmp_path / "calls.jsonl"
    meter = Meter(1.0, sink=sink)
    meter.item = "en-01"
    judge = MeteredProvider(FakeProvider(model="claude-haiku-5-5", json_replies=[ProviderError("cut")]), meter,
                            "judge")
    with pytest.raises(ProviderError):
        judge.complete_json("system", READING, {}, 50)
    judge.complete_json("system", READING, {}, 50)
    lines = [json.loads(line) for line in sink.read_text().splitlines()]
    assert [(r["item"], r["error"]) for r in lines] == [("en-01", "ProviderError"), ("en-01", None)]
    assert lines[0]["cost_usd"] == pytest.approx(0.000025)  # no usage: 50 output tokens at 0.50
    assert meter.spent == pytest.approx(0.000035)


def test_unpriced_models_cost_nothing():
    meter = Meter(1.0)
    list(MeteredProvider(FakeProvider(model="fake-reader"), meter).stream("system", READING, 100))
    assert meter.spent == 0.0 and meter.calls[0].cost_usd == 0.0


def test_caching_guard_prefills_every_question_with_retries_then_serves_the_cache():
    answers = {"q1": ["timeout", "error", "model"], "q2": ["timeout", "error", "timeout"], "q3": ["terms"],
               "q4": ["model"]}
    calls = []

    class Guard:
        def classify(self, question):
            calls.append(question)
            return SimpleNamespace(group="ok", source=answers[question].pop(0))

    guard = CachingGuard(Guard())
    assert guard.prefill(["q1", "q2", "q1", "q3"]) == ["q2"]
    assert calls == ["q1", "q1", "q1", "q2", "q2", "q2", "q3"]
    assert guard.classify("q1").source == "model" and guard.classify("q3").source == "terms"
    assert guard.classify("q4").source == "model"  # not prefilled: asked once, then cached
    assert guard.classify("q4").source == "model" and calls.count("q4") == 1


def test_recording_judge_keeps_the_input_and_returns_pending_scores():
    judge = RecordingJudge()
    data, result = judge.complete_json("rubric", [{"role": "user", "content": "<answer>x</answer>"}], {}, 10)
    assert data == {"relevant": 0, "specific": 0, "warm": 0, "safe": 0, "note": "pending"}
    assert result.tokens_in is None
    assert judge.take() == "<answer>x</answer>"
    assert judge.take() is None


@pytest.mark.parametrize("usage", [(None, None), (None, 900)])
def test_a_finished_call_without_full_usage_costs_its_upper_bound(usage):
    from app.config import cost_usd
    from app.reader.errors import StreamResult
    meter = Meter(1.0)
    result = StreamResult(usage[0], usage[1], "end_turn", "gemini-3.8-flash")
    record = meter.add("gemini-3.8-flash", "reader", result, 10, 20, error=None, max_tokens=4000)
    assert record.error is None
    assert record.cost_usd == pytest.approx(cost_usd("gemini-3.8-flash", 0, 4000)) and record.cost_usd > 0
    assert meter.spent == pytest.approx(record.cost_usd)
