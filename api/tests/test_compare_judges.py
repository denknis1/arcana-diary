import json
import random
from pathlib import Path

import pytest

from app.config import cost_usd
from app.reader.provider import FakeProvider, ProviderError
from evals.compare_judges import (BATCH_SIZE, CHECK_MISSED, JUDGE2_MAX_TOKENS, check_fable, export, judge2, merge,
                                  validate_scores)

FOURS = {"relevant": 4, "specific": 4, "warm": 4, "safe": 4, "note": "fine"}
LOW = {"relevant": 1, "specific": 1, "warm": 1, "safe": 1, "note": "bad"}
PER_CALL = cost_usd("gemini-4-argon", 60, 8)  # FakeProvider usage of one judge call (price of the day)


def content(i):
    return f"<category>love</category>\n<reading>q{i}</reading>\n<answer>\nanswer {i}\n</answer>"


class Judge2Fake(FakeProvider):
    """Gives the known-bad answers (contents q900, q901) their low scores, everything else the default."""

    def complete_json(self, system, messages, schema, max_tokens):
        data, result = super().complete_json(system, messages, schema, max_tokens)
        return (LOW if "<reading>q90" in messages[0]["content"] else data), result


@pytest.fixture
def run(tmp_path):
    folder = tmp_path / "run"
    folder.mkdir()
    results = {"model-a": [{"id": f"en-{i:02d}", "lang": "en", "judge_content": content(i)} for i in range(20)],
               "model-b": [{"id": f"en-{i:02d}", "lang": "en", "judge_content": content(100 + i)}
                           for i in range(20)]}
    results["model-b"].append({"id": "en-99", "lang": "en", "group": "crisis"})  # nothing to judge
    checks = [{"id": "bad-01", "criterion": "safe", "max_score": 2, "judge_content": content(900)},
              {"id": "bad-02", "criterion": "warm", "max_score": 2, "judge_content": content(901)}]
    answers = {"stage": "A", "models": ["model-a", "model-b"], "results": results, "judge_check": checks}
    (folder / "answers.json").write_text(json.dumps(answers))
    (folder / "spend.json").write_text(json.dumps({"max_usd": 5.0, "spent": 1.0, "estimate_usd": 3.4,
                                                   "stopped": False, "not_done": []}))
    (folder / "calls.jsonl").write_text("")
    return folder


def key_of(folder):
    return json.loads((folder / "blind-key.json").read_text())


def judging(folder):
    return Path(key_of(folder)["judging_dir"])


def batches(folder):
    return sorted((judging(folder) / "fable").glob("batch-*.jsonl"))


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_fable(folder, score_for):
    items = key_of(folder)["items"]
    for batch in batches(folder):
        scores = [{**score_for(items[line["n"]]), "n": line["n"]} for line in lines(batch)]
        batch.with_suffix(".scores.json").write_text(json.dumps(scores))


def test_export_writes_a_separate_blind_folder(run):
    assert export(run, rng=random.Random(1)) == 0
    blind = judging(run)
    assert blind.parent == run.parent and blind.name.startswith("judging-") and len(blind.name) == len("judging-") + 8
    assert sorted(p.name for p in blind.iterdir()) == ["FABLE-INSTRUCTIONS.md", "fable", "judge-prompt.md"]
    files = batches(run)
    assert len(files) == 2 and all(len(lines(f)) <= BATCH_SIZE for f in files)
    text = "".join(p.read_text() for p in blind.rglob("*") if p.is_file())
    assert "model-a" not in text and "model-b" not in text
    items = key_of(run)["items"]
    assert len(items) == 42 and sum(1 for v in items.values() if v["kind"] == "check") == 2
    assert "You grade one answer" in (blind / "judge-prompt.md").read_text()
    instructions = (blind / "FABLE-INSTRUCTIONS.md").read_text()
    assert "batch-NN.scores.json" in instructions
    named = instructions.replace("fable/", "")  # the only path it names is inside the blind folder
    assert not [w for w in ("answers.json", "blind-key", "..", "results", "/") if w in named]
    with pytest.raises(FileExistsError):
        export(run)  # never overwrite a started judging


def test_validate_scores():
    batch = [{"n": "a"}, {"n": "b"}]
    assert validate_scores(batch, [{**FOURS, "n": "a"}, {**FOURS, "n": "b"}]) == []
    problems = validate_scores(batch, [{**FOURS, "n": "a", "warm": 7}, {**FOURS, "n": "x", "safe": True}])
    assert any("warm=7" in p for p in problems) and any("unknown n 'x'" in p for p in problems)
    assert any("missing n b" in p for p in problems)
    assert validate_scores(batch, {"n": "a"}) == ["not a JSON array"]
    assert any("no note" in p for p in validate_scores(batch[:1], [{**FOURS, "n": "a", "note": " "}]))


def test_check_fable_waits_for_every_batch(run):
    export(run, rng=random.Random(1))
    assert check_fable(run) == 1
    write_fable(run, lambda info: FOURS)
    assert check_fable(run) == 0


def test_judge2_needs_yes_grades_the_known_bad_answers_first_and_scores_everything(run):
    export(run, rng=random.Random(1))
    fake = Judge2Fake(model="gemini-4-argon", json_default=FOURS)
    assert judge2(run, yes=False, provider=fake) == 2 and not fake.calls
    assert judge2(run, yes=True, provider=fake) == 0
    assert all("<reading>q90" in c["messages"][0]["content"] for c in fake.calls[:2])
    assert {c["max_tokens"] for c in fake.calls} == {JUDGE2_MAX_TOKENS}
    scores = json.loads((run / "gemini-scores.json").read_text())
    assert len(scores) == 42 and len(fake.calls) == 42
    spend = json.loads((run / "spend.json").read_text())
    assert spend["spent"] == pytest.approx(1.0 + 42 * PER_CALL)
    assert len((run / "calls.jsonl").read_text().splitlines()) == 42
    assert judge2(run, yes=True, provider=fake) == 0 and len(fake.calls) == 42  # nothing left to do


def test_judge2_stops_after_a_missed_known_bad_answer_unless_forced(run, capsys):
    export(run, rng=random.Random(1))
    fake = FakeProvider(model="gemini-4-argon", json_default=FOURS)  # 4 for everything: misses both
    assert judge2(run, yes=True, provider=fake) == CHECK_MISSED
    assert len(fake.calls) == 2 and "bad-01" in capsys.readouterr().err
    assert judge2(run, yes=True, provider=fake) == CHECK_MISSED and len(fake.calls) == 2
    assert judge2(run, yes=True, provider=fake, force=True) == 0 and len(fake.calls) == 42


def test_judge2_stops_after_three_failures_in_a_row(run):
    export(run, rng=random.Random(1))
    fake = Judge2Fake(model="gemini-4-argon", json_default=FOURS,
                      json_replies=[LOW, LOW, FOURS, ProviderError("cut"), {"relevant": 9}, ProviderError("cut")])
    assert judge2(run, yes=True, provider=fake) == 4
    assert len(fake.calls) == 6 and len(json.loads((run / "gemini-scores.json").read_text())) == 3
    spend = json.loads((run / "spend.json").read_text())
    upper = cost_usd("gemini-4-argon", 0, JUDGE2_MAX_TOKENS)  # a failed call without usage
    assert spend["spent"] == pytest.approx(1.0 + 4 * PER_CALL + 2 * upper)


def test_judge2_stops_at_the_ceiling(run):
    export(run, rng=random.Random(1))
    spend = json.loads((run / "spend.json").read_text())
    (run / "spend.json").write_text(json.dumps({**spend, "max_usd": round(1.0 + 5 * PER_CALL, 6)}))
    fake = Judge2Fake(model="gemini-4-argon", json_default=FOURS)
    assert judge2(run, yes=True, provider=fake) == 4
    assert len(json.loads((run / "gemini-scores.json").read_text())) == 5


def test_merge_averages_trusted_judges_and_drops_a_judge_that_misses_a_bad_answer(run):
    export(run, rng=random.Random(1))
    write_fable(run, lambda info: {**FOURS, "safe": 1, "warm": 1} if info["kind"] == "check" else FOURS)
    gemini = {n: {**FOURS, "relevant": 5, "specific": 5, "warm": 5, "safe": 5} for n in key_of(run)["items"]}
    (run / "gemini-scores.json").write_text(json.dumps(gemini))
    assert merge(run) == 0
    scored = json.loads((run / "scored.json").read_text())
    assert scored["judges"]["fable"]["trusted"] is True and scored["judges"]["gemini"]["trusted"] is False
    first = scored["results"]["model-a"][0]
    assert first["scores"]["warm"] == 4 and first["scores_by_judge"]["gemini"]["warm"] == 5
    assert "fable: fine" in first["scores"]["note"]
    assert "scores" not in scored["results"]["model-b"][-1]


def test_merge_averages_two_trusted_judges_only_where_both_scored(run):
    export(run, rng=random.Random(1))
    bad = {**FOURS, "safe": 1, "warm": 1}
    write_fable(run, lambda info: bad if info["kind"] == "check" else FOURS)
    items = key_of(run)["items"]
    gemini = {n: bad if info["kind"] == "check" else {**FOURS, "warm": 5} for n, info in items.items()}
    unscored = next(n for n, info in items.items() if (info["model"], info["id"]) == ("model-a", "en-01"))
    del gemini[unscored]  # judge 2 failed on this answer
    (run / "gemini-scores.json").write_text(json.dumps(gemini))
    merge(run)
    scored = json.loads((run / "scored.json").read_text())
    assert scored["results"]["model-a"][0]["scores"]["warm"] == 4.5
    second = scored["results"]["model-a"][1]
    assert "scores" not in second and list(second["scores_by_judge"]) == ["fable"]
