import json
import threading
from datetime import date

import pytest

from app.reader.provider import FakeProvider, FakeReply, ProviderTimeout
import evals.compare as compare
from evals.compare import GUARD_FAILED, STAGES, STOPPED, _join_new_workers, estimate_cost, load_set, main

GUARD_OK = {"group": "ok", "violence": False}


def fakes(stage="A"):
    return {m: FakeProvider(model=m) for m in STAGES[stage]}


def guard():
    return FakeProvider(model="claude-haiku-5-5", json_default=GUARD_OK)


def read(path):
    return json.loads(path.read_text())


def test_the_set_has_50_items_and_no_crisis():
    items = load_set()
    assert [len(items[k]) for k in ("questions", "injection", "followups", "daily")] == [30, 6, 7, 7]
    assert sum(1 for q in items["questions"] if q["lang"] == "en") == 15
    assert not [i for part in items.values() for i in part if i.get("expect_group") == "crisis"]


def test_estimate_of_stage_a_stays_under_the_five_dollar_ceiling():
    assert 3.3 < estimate_cost(STAGES["A"], load_set(), day=date(2026, 11, 19)) < 3.5
    assert estimate_cost(STAGES["A"], load_set(), day=date(2026, 12, 1)) > 6  # judge 2 doubles from 01.12


def test_without_yes_nothing_is_called(capsys):
    providers = fakes()
    assert main(["--stage", "A"], providers=providers, guard_provider=guard()) == 2
    assert "Estimated cost" in capsys.readouterr().out
    assert all(not p.calls for p in providers.values())


def test_yes_needs_a_ceiling():
    assert main(["--stage", "A", "--yes"], providers=fakes(), guard_provider=guard()) == 2


def test_an_existing_out_folder_is_refused(tmp_path):
    providers, out = fakes(), tmp_path / "run"
    out.mkdir()
    assert main(["--stage", "A", "--yes", "--max-usd", "5", "--out", str(out)], providers=providers,
                guard_provider=guard()) == 2
    assert all(not p.calls for p in providers.values()) and not list(out.iterdir())


def test_a_full_run_writes_blind_judge_inputs_and_the_spend(tmp_path):
    out = tmp_path / "run"
    providers, guard_provider = fakes(), guard()
    assert main(["--stage", "A", "--yes", "--max-usd", "5", "--out", str(out)], providers=providers,
                guard_provider=guard_provider) == 0
    answers = read(out / "answers.json")
    assert answers["models"] == list(STAGES["A"])
    for model in STAGES["A"]:
        results = answers["results"][model]
        assert len(results) == 50 and not [r for r in results if "scores" in r or "no_answer" in r]
        judged = [r for r in results if r.get("judge_content")]
        assert judged and all("<answer>" in r["judge_content"] for r in judged)
        assert not [r for r in judged if any(m in r["judge_content"] for m in STAGES["A"])]
    assert len(answers["judge_check"]) == 9 and all(c["judge_content"] for c in answers["judge_check"])  # + bad-09
    spend = read(out / "spend.json")
    assert spend["stopped"] is False and spend["not_done"] == [] and 0 < spend["spent"] < 5
    assert spend["unjoined"] == 0
    calls = [json.loads(line) for line in (out / "calls.jsonl").read_text().splitlines()]
    assert {"reader", "followup", "daily", "guard"} <= {c["purpose"] for c in calls}
    assert sum(c["cost_usd"] for c in calls) == pytest.approx(spend["spent"])
    guard_calls = guard_provider.json_calls()
    asked = [c["messages"][0]["content"] for c in guard_calls]
    assert len(asked) == len(set(asked)) <= 43  # once per question, not once per model
    first_reader_call = min(i for i, c in enumerate(calls) if c["purpose"] != "guard")
    assert all(c["purpose"] == "guard" for c in calls[:first_reader_call])
    assert len([c for c in calls if c["purpose"] == "guard"]) == len(guard_calls)  # all before any reader call


def test_limit_takes_the_first_items_of_each_part(tmp_path):
    out = tmp_path / "run"
    assert main(["--stage", "A", "--yes", "--max-usd", "5", "--limit", "1", "--out", str(out)], providers=fakes(),
                guard_provider=guard()) == 0
    answers = read(out / "answers.json")
    assert [r["id"] for r in answers["results"]["gpt-6-luna"]] == ["en-01", "inj-en-01", "fu-en-01", "d-en-01"]


def test_answers_are_written_after_every_item_so_an_interrupt_keeps_them(tmp_path, monkeypatch):
    out, real, seen, on_disk = tmp_path / "run", compare.run_item, [], []

    def interrupted(item, **kwargs):
        seen.append(item["id"])
        if len(set(seen)) == 2:  # the second item: what is on disk now, then Ctrl-C
            on_disk.append(read(out / "answers.json"))
            raise KeyboardInterrupt
        return real(item, **kwargs)

    monkeypatch.setattr(compare, "run_item", interrupted)
    with pytest.raises(KeyboardInterrupt):
        main(["--stage", "A", "--yes", "--max-usd", "5", "--out", str(out)], providers=fakes(),
             guard_provider=guard())
    first_only = {m: ["en-01"] for m in STAGES["A"]}
    assert {m: [r["id"] for r in rs] for m, rs in on_disk[0]["results"].items()} == first_only
    assert {m: [r["id"] for r in rs] for m, rs in read(out / "answers.json")["results"].items()} == first_only
    spend = read(out / "spend.json")
    assert spend["spent"] > 0 and spend["stopped"] is True
    assert len(spend["not_done"]) == 3 * 49 and {n["reason"] for n in spend["not_done"]} == {"interrupted"}
    assert {(n["model"], n["id"]) for n in spend["not_done"]}.isdisjoint(
        {(m, "en-01") for m in STAGES["A"]})


@pytest.mark.parametrize("flag,value", [("--max-usd", "nan"), ("--max-usd", "inf"), ("--max-usd", "0"),
                                        ("--max-usd", "-1"), ("--limit", "0"), ("--limit", "-1")])
def test_bad_ceiling_or_limit_is_refused(tmp_path, flag, value):
    providers, guard_provider = fakes(), guard()
    argv = ["--stage", "A", "--yes", "--out", str(tmp_path / "run")]
    if flag == "--limit":
        argv += ["--max-usd", "5"]
    assert main([*argv, flag, value], providers=providers, guard_provider=guard_provider) == 2
    assert all(not p.calls for p in providers.values()) and not guard_provider.calls
    assert not (tmp_path / "run").exists()


def test_join_new_workers_counts_the_workers_still_alive():
    before, release = set(threading.enumerate()), threading.Event()
    worker = threading.Thread(target=release.wait, name="reader-stream", daemon=True)
    worker.start()
    assert _join_new_workers(before, timeout_s=0.05) == 1
    release.set()
    assert _join_new_workers(before, timeout_s=2.0) == 0


def test_the_ceiling_stops_the_run_and_lists_what_is_not_done(tmp_path):
    out = tmp_path / "run"
    code = main(["--stage", "A", "--yes", "--max-usd", "0.0006", "--out", str(out)], providers=fakes(),
                guard_provider=guard())
    assert code == STOPPED
    spend = read(out / "spend.json")
    assert spend["stopped"] is True and len(spend["not_done"]) == 49 * 3
    assert {n["reason"] for n in spend["not_done"]} == {"ceiling"}
    answers = read(out / "answers.json")
    assert [len(answers["results"][m]) for m in STAGES["A"]] == [1, 1, 1]


def test_a_failed_question_check_stops_before_any_reader_call(tmp_path):
    out = tmp_path / "run"
    providers = fakes()
    slow_guard = FakeProvider(model="claude-haiku-5-5", json_default=ProviderTimeout("slow"))
    assert main(["--stage", "A", "--yes", "--max-usd", "5", "--out", str(out)], providers=providers,
                guard_provider=slow_guard) == GUARD_FAILED
    assert all(not p.calls for p in providers.values())
    spend = read(out / "spend.json")
    assert spend["spent"] > 0 and len(spend["not_done"]) == 50 * 3  # the timed-out checks cost their upper bound
    assert len(slow_guard.json_calls()) % 3 == 0  # every question asked three times
    assert read(out / "answers.json")["results"] == {m: [] for m in STAGES["A"]}


def test_a_model_failing_without_usage_is_skipped_and_its_answers_are_not_graded(tmp_path):
    out = tmp_path / "run"
    providers = fakes()
    providers["gpt-6-luna"] = FakeProvider(model="gpt-6-luna", replies=[FakeReply(fail_after=0)] * 50)
    assert main(["--stage", "A", "--yes", "--max-usd", "5", "--out", str(out)], providers=providers,
                guard_provider=guard()) == STOPPED
    answers, spend = read(out / "answers.json"), read(out / "spend.json")
    failed = answers["results"]["gpt-6-luna"]
    assert len(failed) == 3 and len(providers["gpt-6-luna"].calls) == 3
    assert all(r["no_answer"] == "error" and "judge_content" not in r for r in failed)
    assert "3 errors in a row" in spend["skipped"]["gpt-6-luna"]
    assert len(spend["not_done"]) == 47 and all(n["model"] == "gpt-6-luna" for n in spend["not_done"])
    assert len(answers["results"]["claude-haiku-5-5"]) == 50


def test_missing_keys_stop_before_any_call(monkeypatch, capsys):
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_AI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert main(["--stage", "A", "--yes", "--max-usd", "5"]) == 3
    assert "OPENAI_API_KEY" in capsys.readouterr().err
