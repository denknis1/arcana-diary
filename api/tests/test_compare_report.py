import json

import pytest

from evals.compare_report import DAILY_TEXTS_PER_DAY, build_summary, main


def call(model, purpose, cost, tokens=(1000, 1000), first=400, total=2000, error=None):
    return {"model": model, "purpose": purpose, "item": "x", "tokens_in": tokens[0], "tokens_out": tokens[1],
            "cost_usd": cost, "ms_first": first, "ms_total": total, "error": error}


def scores(value, safe=4):
    return {"relevant": value, "specific": value, "warm": value, "safe": safe, "note": "n"}


@pytest.fixture
def run(tmp_path):
    folder = tmp_path / "run"
    folder.mkdir()
    results = {
        "claude-haiku-5-5": [
            {"id": "en-01", "lang": "en", "scores": scores(4), "scores_by_judge": {"fable": scores(4)},
             "auto": {"banned": []}, "shown": "model"},
            {"id": "es-01", "lang": "es", "scores": scores(5), "scores_by_judge": {"fable": scores(5, safe=2)},
             "auto": {"banned": ["va a pasar"]}, "shown": "fallback"},
        ],
        "gemini-3.8-flash": [
            {"id": "en-01", "lang": "en", "scores": scores(3), "scores_by_judge": {"fable": scores(3)},
             "auto": {"banned": []}, "shown": "model", "reader_crisis": True},
            {"id": "es-01", "lang": "es", "error": "ProviderError"},
        ],
    }
    scored = {"stage": "A", "models": list(results), "results": results,
              "judges": {"fable": {"trusted": True, "checks": [], "scored": 4},
                         "gemini": {"trusted": False, "checks": [], "scored": 0}}}
    (folder / "scored.json").write_text(json.dumps(scored))
    calls = [call("claude-haiku-5-5", "reader", 0.001, first=300), call("claude-haiku-5-5", "reader", 0.003, first=500),
             call("claude-haiku-5-5", "followup", 0.0007), call("claude-haiku-5-5", "daily", 0.0003),
             call("claude-haiku-5-5", "guard", 0.0002), call("claude-haiku-5-5", "reader", 0.0, error="ProviderError"),
             call("claude-haiku-5-5", "guard", 0.0005, tokens=(None, None), error="ProviderTimeout"),
             call("gemini-3.8-flash", "reader", 0.0045, tokens=(1000, 1000)),
             call("gemini-3.8-flash", "followup", 0.002), call("gemini-3.8-flash", "daily", 0.001),
             call("gemini-4-argon", "judge", 0.01)]
    (folder / "calls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in calls))
    (folder / "spend.json").write_text(json.dumps({"max_usd": 5.0, "spent": 0.0234, "estimate_usd": 2.4,
                                                   "stopped": False, "not_done": []}))
    return folder


def test_quality_safety_and_speed(run):
    s = build_summary(run)
    haiku, flash = s["models"]["claude-haiku-5-5"], s["models"]["gemini-3.8-flash"]
    assert haiku["quality"]["warm"] == 4.5 and haiku["overall"] == pytest.approx(4.38)  # mean of 4.5, 4.5, 4.5, 4.0
    assert haiku["by_lang"]["es"]["warm"] == 5 and haiku["by_judge"]["fable"]["safe"] == 3
    assert haiku["safety"] == {"banned": 1, "safe_low": 1, "fallback": 1, "reader_crisis": 0, "leaks": 0,
                               "errors": 0}
    assert flash["safety"]["errors"] == 1 and flash["safety"]["reader_crisis"] == 1
    assert haiku["speed"]["first_p50"] == 300 and haiku["speed"]["first_p95"] == 500
    assert haiku["speed"]["timeouts"] == 0  # a timeout of the guard (also on Haiku) is not the reader's


def test_money(run):
    s = build_summary(run)
    haiku = s["models"]["claude-haiku-5-5"]["cost"]
    assert haiku["reading"] == pytest.approx(0.002 + 0.0002)    # mean of the two good reader calls + the guard
    assert haiku["followup"] == pytest.approx(0.0007 + 0.0002)
    assert haiku["daily"] == pytest.approx(0.0003)
    assert haiku["per_1000"] == pytest.approx(2.2)
    expected = 30 * (100 * (1.5 * 0.0022 + 0.5 * 0.0009) + DAILY_TEXTS_PER_DAY * 0.0003)
    assert haiku["monthly"]["100"] == pytest.approx(expected)
    flash_now = s["models"]["gemini-3.8-flash"]["cost"]
    flash_later = s["models"]["gemini-3.8-flash"]["cost_future"]
    assert flash_later["reading"] - 0.0002 == pytest.approx((1000 * 1.50 + 1000 * 7.50) / 1e6)
    assert flash_later["reading"] > flash_now["reading"]
    assert s["models"]["claude-haiku-5-5"]["cost_future"] is None   # no announced change
    assert s["spend"]["spent"] == 0.0234 and s["judges"]["gemini"]["trusted"] is False


def test_report_page_is_written(run):
    assert main([str(run)]) == 0
    html = (run / "report.html").read_text()
    assert "<title>" in html and "Качество" in html and "Деньги" in html
    assert "claude-haiku-5-5" in html and "gemini-3.8-flash" in html
    assert "prefers-color-scheme: dark" in html
    assert json.loads((run / "summary.json").read_text())["stage"] == "A"


def test_gap_to_claude_value_disagreements_and_missing_answers(run):
    scored = json.loads((run / "scored.json").read_text())
    scored["models"].append("gpt-6-luna")
    scored["results"]["gpt-6-luna"] = [
        {"id": "en-01", "lang": "en", "scores": scores(4, safe=5), "auto": {"banned": []}, "shown": "model",
         "scores_by_judge": {"fable": scores(4, safe=5), "gemini": scores(2, safe=1)}},  # gemini is not trusted
        {"id": "es-01", "lang": "es", "no_answer": "timeout", "shown": "fallback", "shown_reason": "timeout"},
    ]
    (run / "scored.json").write_text(json.dumps(scored))
    with (run / "calls.jsonl").open("a") as calls:
        calls.write(json.dumps(call("gpt-6-luna", "reader", 0.001)) + "\n")
        calls.write(json.dumps(call("gpt-6-luna", "reader", 0.00005, tokens=(None, None), first=None,
                                    error="abandoned")) + "\n")
    items = {f"n{i}": {"model": "x", "id": "y", "kind": "answer", "batch": 1 + i % 2} for i in range(4)}
    (run / "blind-key.json").write_text(json.dumps({"judging_dir": "/tmp/judging-0", "items": items}))
    s = build_summary(run)
    haiku, flash, luna = (s["models"][m] for m in ("claude-haiku-5-5", "gemini-3.8-flash", "gpt-6-luna"))
    # gaps from the unrounded overalls (4.375 - 3.25, 4.375 - 4.25), rounded for display
    assert haiku["gap_to_claude"] is None and flash["gap_to_claude"] == pytest.approx(1.12)
    assert luna["gap_to_claude"] == pytest.approx(0.12) and luna["tuning_round"] and not flash["tuning_round"]
    assert haiku["quality_per_usd"] == pytest.approx(round(4.38 / 2.2, 2))
    assert (luna["disagree"], luna["disagree_ids"], luna["safety"]["safe_low"]) == (1, ["en-01"], 0)
    assert luna["no_answer"] == {"timeout": 1} and luna["speed"]["timeouts"] == 1
    assert s["fable_batches"] == 2
    assert main([str(run)]) == 0
    html = (run / "report.html").read_text()
    for text in ("Отставание от Claude", "раунд подстройки", "Нет ответа", "тайм-аут", "Качество за доллар",
                 "Расхождения судей", "нет «своего» судьи", "кэшируют", "партий: 2"):
        assert text in html


def test_stopped_line_groups_not_done_by_reason(run):
    spend = {"max_usd": 5.0, "spent": 1.0, "estimate_usd": 2.4, "stopped": True,
             "not_done": [{"model": "a", "id": "1", "reason": "ceiling"}, {"model": "a", "id": "2", "reason": "ceiling"},
                          {"model": "b", "id": "1", "reason": "interrupted"},
                          {"model": "c", "id": "1", "reason": "skipped: no key"},
                          {"model": "c", "id": "2", "reason": "skipped: 400"},
                          {"model": "d", "id": "1", "reason": "question check failed"},
                          {"model": "e", "id": "1", "reason": "weird"}],
             "skipped": {}}
    (run / "spend.json").write_text(json.dumps(spend))
    assert main([str(run)]) == 0
    html = (run / "report.html").read_text()
    assert ("не сделано 7 ответов — потолок: 2, прерван: 1, модель пропущена: 2, "
            "проверка вопроса не удалась: 1, weird: 1") in html



@pytest.mark.parametrize("value, shown", [(3.804, "0.20"), (3.996, "0.00")])
def test_tuning_flag_uses_the_unrounded_gap(run, value, shown):
    scored = json.loads((run / "scored.json").read_text())
    scored["results"]["claude-haiku-5-5"] = [{"id": "en-01", "lang": "en", "scores": scores(4, safe=4)}]
    scored["results"]["gemini-3.8-flash"] = [{"id": "en-01", "lang": "en", "scores": scores(value, safe=value)}]
    (run / "scored.json").write_text(json.dumps(scored))
    flash = build_summary(run)["models"]["gemini-3.8-flash"]
    assert flash["tuning_round"] is True  # a gap of 0.196 / 0.004 is inside (0, 0.2)
    assert f"{flash['gap_to_claude']:.2f}" == shown
    assert main([str(run)]) == 0
    assert f"{shown} — меньше 0.2: раунд подстройки" in (run / "report.html").read_text()


def test_a_model_without_a_good_reader_call_has_no_reading_price(run):
    calls = [json.loads(line) for line in (run / "calls.jsonl").read_text().splitlines()]
    calls = [c for c in calls if not (c["model"] == "gemini-3.8-flash" and c["purpose"] == "reader")]
    calls.append(call("gemini-3.8-flash", "reader", 0.015, tokens=(None, None), error="ProviderError"))
    (run / "calls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in calls))
    s = build_summary(run)
    cost = s["models"]["gemini-3.8-flash"]["cost"]
    assert (cost["reading"], cost["followup"], cost["per_1000"]) == (None, None, None)
    assert set(cost["monthly"].values()) == {None} and cost["daily"] == pytest.approx(0.001)
    assert s["models"]["gemini-3.8-flash"]["quality_per_usd"] is None
    assert main([str(run)]) == 0
    row = next(r.split("</tr>")[0] for r in (run / "report.html").read_text().split("<tr>")
               if "gemini-3.8-flash" in r and "$0.0010" in r)
    assert row.count("—") == 6  # reading, follow-up, 1000 readings, three months; the card of the day stays


def test_report_wording_unjoined_and_judge_labels(run):
    scored = json.loads((run / "scored.json").read_text())
    scored["results"]["gemini-3.8-flash"][1] = {"id": "es-01", "lang": "es", "no_answer": "empty"}
    scored["results"]["claude-haiku-5-5"][0]["scores_by_judge"]["gemini"] = scores(4)
    scored["judges"]["gemini"]["status"] = "incomplete"
    (run / "scored.json").write_text(json.dumps(scored))
    spend = json.loads((run / "spend.json").read_text())
    (run / "spend.json").write_text(json.dumps({**spend, "unjoined": 2}))
    assert main([str(run)]) == 0
    html = (run / "report.html").read_text()
    assert "пусто, тайм-аут или ответ без разделов" in html
    assert "Средние — по оценённым ответам каждой модели; при многих \"нет ответа\" выборка меньше." in html
    assert "Брошенных и не записанных вызовов чтеца: 2" in html
    assert "Месячная сумма уже включает тексты «карты дня»" in html
    judges_part = html.split("<h2>Оценки каждого судьи</h2>")[1].split("<h2>Нет ответа</h2>")[0]
    assert judges_part.count("gemini — не учтён (оценки неполные)") == 1
    disagree_part = judges_part.split("<h2>Расхождения")[1]
    assert "Gemini 4 Argon: не учтён (оценки неполные)" in disagree_part
    scored["judges"]["gemini"]["status"] = "failed"
    (run / "scored.json").write_text(json.dumps(scored))
    main([str(run)])
    html = (run / "report.html").read_text()
    assert "gemini — не учтён (не прошёл проверку)" in html and "Gemini 4 Argon: не учтён (не прошёл проверку)" in html
    del scored["judges"]["gemini"]["status"]  # an older scored.json: untrusted counts as failed
    (run / "scored.json").write_text(json.dumps(scored))
    main([str(run)])
    assert "gemini — не учтён (не прошёл проверку)" in (run / "report.html").read_text()
    assert "Брошенных" in html
