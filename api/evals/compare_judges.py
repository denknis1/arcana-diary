"""Reader model comparison, step 2: two blind judges (spec 2026-11-19 §7).

  .venv/bin/python -m evals.compare_judges export <dir>             # blind folder for Fable, blind-key.json
  (the controller gives each batch to one Fable subagent: <blind folder>/FABLE-INSTRUCTIONS.md)
  .venv/bin/python -m evals.compare_judges check-fable <dir>        # every batch scored, every score valid
  .venv/bin/python -m evals.compare_judges judge2 <dir>             # estimate only
  .venv/bin/python -m evals.compare_judges judge2 <dir> --yes       # Gemini 4 Argon via API, within spend.json
  .venv/bin/python -m evals.compare_judges merge <dir>              # scored.json: both judges, checks, averages

<dir> is the run folder of step 1. export writes the judge's files into a separate blind folder next to it,
results/judging-<8 hex>/ (fable/batch-NN.jsonl, judge-prompt.md, FABLE-INSTRUCTIONS.md): no model name, no
answers.json, no key; nothing above it is needed. blind-key.json stays in the run folder:
{"judging_dir": "<absolute path>", "items": {n: {"model", "id", "kind", "batch"}}}. A judge sees only
{"n", "content"}: the judge input recorded in step 1 (category, expected group, reading input, answer).
The 8 known-bad answers are mixed into the Fable batches blind; judge 2 grades them first and stops (exit 6) if it
misses one, unless --force. A judge that does not give one of them its low score is not trusted: its scores are
left out of the averages. judge2 stops after 3 failed calls in a row (exit 4), writes gemini-scores.json after
every answer and spend.json after every call; its calls are appended to calls.jsonl at once. It starts its meter
from the larger of spend.json and the sum of calls.jsonl, plus every stream worker step 1 could not wait for
(spend.json "unjoined", charged once) at the upper bound of the stage's dearest reader. After the known-bad answers
it projects the answers left at the mean cost per judge call so far and stops (exit 8) if that does not fit under
the ceiling, unless --force.
"""
import argparse
import json
import random
import secrets
import sys
from pathlib import Path
from statistics import mean

from app.config import cost_usd, load_settings
from app.reader.providers import make_provider
from evals.compare import JUDGE2_MODEL, NO_KEY, STOPPED, judge2_cost
from evals.judge import CRITERIA, JUDGE_SCHEMA, load_judge_prompt
from evals.metering import BudgetExceeded, Meter, MeteredProvider
from evals.run import READER_MAX_TOKENS

BATCH_SIZE = 25
JUDGES = ("fable", "gemini")
JUDGE2_MAX_TOKENS = 6000   # thinking (low) counts inside the output limit
JUDGE2_EFFORT = "low"
FAILURES_IN_A_ROW = 3
CHECK_MISSED = 6
INCOMPLETE = 7   # merge: a judge's scores are incomplete (see --allow-incomplete)
WONT_FIT = 8     # judge2: the projected cost of the answers left does not fit under the ceiling (see --force)

FABLE_INSTRUCTIONS = """# Judging task

You grade answers written by the tarot reader of Arcana Diary. Everything you need is in this folder; work only
with these files: `judge-prompt.md` (the full grading rubric: follow it exactly, as if it were your system prompt)
and the one `fable/batch-NN.jsonl` named in your task. Do not open, list or search any other file or folder.

Each line of the batch is a JSON object {"n": "<id>", "content": "<judge input>"}. The content holds the question
category, the expected guard group, the reading input and the answer to grade, exactly as the rubric describes.
Grade every line on its own, strictly and consistently, by the rubric only.

Write `fable/batch-NN.scores.json` (the same NN): a JSON array with one object per line of the batch:
{"n": "<id>", "relevant": 1-5, "specific": 1-5, "warm": 1-5, "safe": 1-5, "note": "<one English sentence naming
the main weakness, or none>"}
Integers only, every line of the batch exactly once, nothing else in the file. Then reply with one line: the file
name and the number of objects written.
"""


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _tasks(answers: dict) -> list[dict]:
    """Everything a judge grades: each model's judged answers, then the known-bad answers."""
    tasks = [{"model": model, "id": r["id"], "kind": "answer", "content": r["judge_content"]}
             for model, results in answers["results"].items() for r in results if r.get("judge_content")]
    tasks += [{"model": None, "id": c["id"], "kind": "check", "content": c["judge_content"]}
              for c in answers["judge_check"]]
    return tasks


def _key(folder: Path) -> dict:
    return _read(Path(folder) / "blind-key.json")


def _batches(judging: Path) -> list[Path]:
    return sorted((Path(judging) / "fable").glob("batch-*.jsonl"))


def export(folder: Path, rng: random.Random | None = None) -> int:
    folder = Path(folder)
    if (folder / "blind-key.json").exists():
        raise FileExistsError(f"{folder / 'blind-key.json'}: judging has started, never export twice")
    tasks = _tasks(_read(folder / "answers.json"))
    rng = rng or random.Random(secrets.randbits(64))
    rng.shuffle(tasks)
    judging = (folder.parent / f"judging-{secrets.token_hex(4)}").resolve()
    fable = judging / "fable"
    fable.mkdir(parents=True, exist_ok=False)
    items: dict[str, dict] = {}
    for b, start in enumerate(range(0, len(tasks), BATCH_SIZE), 1):
        rows = []
        for task in tasks[start:start + BATCH_SIZE]:
            n = f"{rng.getrandbits(32):08x}"
            while n in items:
                n = f"{rng.getrandbits(32):08x}"
            items[n] = {"model": task["model"], "id": task["id"], "kind": task["kind"], "batch": b}
            rows.append(json.dumps({"n": n, "content": task["content"]}, ensure_ascii=False))
        (fable / f"batch-{b:02d}.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (judging / "judge-prompt.md").write_text(load_judge_prompt().text, encoding="utf-8")
    (judging / "FABLE-INSTRUCTIONS.md").write_text(FABLE_INSTRUCTIONS, encoding="utf-8")
    _write(folder / "blind-key.json", {"judging_dir": str(judging), "items": items})
    print(f"{len(tasks)} answers in {len(_batches(judging))} batches. Blind folder for Fable: {judging}")
    return 0


def _valid(entry: dict) -> list[str]:
    problems = []
    for c in CRITERIA:
        value = entry.get(c)
        if not (isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5):
            problems.append(f"{entry.get('n')}: {c}={value!r}")
    note = entry.get("note")
    if not isinstance(note, str) or not note.strip():
        problems.append(f"{entry.get('n')}: no note")
    return problems


def validate_scores(lines: list[dict], scores) -> list[str]:
    if not isinstance(scores, list):
        return ["not a JSON array"]
    wanted, seen, problems = {line["n"] for line in lines}, set(), []
    for entry in scores:
        n = entry.get("n") if isinstance(entry, dict) else None
        if n not in wanted:
            problems.append(f"unknown n {n!r}")
            continue
        if n in seen:
            problems.append(f"n {n} twice")
        seen.add(n)
        problems += _valid(entry)
    problems += [f"missing n {n}" for n in sorted(wanted - seen)]
    return problems


def check_fable(folder: Path) -> int:
    bad = 0
    for batch in _batches(_key(folder)["judging_dir"]):
        scores_path = batch.with_suffix(".scores.json")
        if not scores_path.exists():
            print(f"{batch.name}: no scores yet")
            bad += 1
            continue
        try:
            scores = _read(scores_path)
        except ValueError:
            print(f"{scores_path.name}: invalid JSON")
            bad += 1
            continue
        problems = validate_scores(_lines(batch), scores)
        if problems:
            print(f"{scores_path.name}: " + "; ".join(problems[:10]))
            bad += 1
    print("all Fable batches scored" if not bad else f"{bad} batch(es) to (re)do")
    return 0 if not bad else 1


def _missed_checks(key: dict, answers: dict, scores: dict) -> list[str]:
    """Known-bad answers that the judge did not grade, or graded above their max_score on their criterion."""
    by_id = {c["id"]: c for c in answers["judge_check"]}
    missed = []
    for n, info in key["items"].items():
        if info["kind"] == "check":
            check, s = by_id[info["id"]], scores.get(n)
            if s is None or s[check["criterion"]] > check["max_score"]:
                missed.append(check["id"])
    return sorted(missed)


def _calls(folder: Path) -> list[dict]:
    path = Path(folder) / "calls.jsonl"
    return _lines(path) if path.exists() else []


def _start(spend: dict, calls: list[dict], models: list[str]) -> tuple[float, str]:
    """Where judge 2's meter starts: the larger of spend.json and the sum of calls.jsonl (after a hard kill
    spend.json can lag), plus the stream workers step 1 could not wait for ("unjoined", not yet charged) at the
    upper bound of the stage's dearest reader call. Returns the start and a line saying what was added."""
    recorded = round(sum(c.get("cost_usd") or 0.0 for c in calls), 6)
    base = max(spend["spent"], recorded)
    unjoined = int(spend.get("unjoined") or 0) - int(spend.get("unjoined_charged") or 0)
    bound = max((cost_usd(m, 0, READER_MAX_TOKENS) or 0.0 for m in models), default=0.0)
    added = max(0, unjoined) * bound
    line = (f"Meter starts at ${base + added:.4f}: spend.json ${spend['spent']:.4f}, calls.jsonl ${recorded:.4f}"
            + (f", + {unjoined} unrecorded abandoned call(s) × ${bound:.4f} = ${added:.4f}" if unjoined > 0 else "")
            + ".")
    return round(base + added, 6), line


def judge2(folder: Path, yes: bool, provider=None, force: bool = False) -> int:
    folder = Path(folder)
    key, answers = _key(folder), _read(folder / "answers.json")
    items = key["items"]
    tasks = [line for batch in _batches(key["judging_dir"]) for line in _lines(batch)]
    out_path = folder / "gemini-scores.json"
    done = _read(out_path) if out_path.exists() else {}
    todo = sorted((t for t in tasks if t["n"] not in done), key=lambda t: items[t["n"]]["kind"] != "check")
    estimate = sum(judge2_cost("judge_daily" if items[t["n"]]["id"].startswith("d-") else "judge") for t in todo)
    spend = _read(folder / "spend.json")
    print(f"{len(todo)} answers for {JUDGE2_MODEL} (the {sum(1 for t in todo if items[t['n']]['kind'] == 'check')} "
          f"known-bad ones first); estimated ${estimate:.2f}; spent so far ${spend['spent']:.2f} of "
          f"${spend['max_usd']:.2f}.")
    calls = _calls(folder)
    start, start_line = _start(spend, calls, answers.get("models", []))
    print(start_line)
    if not yes:
        print("Not running: every call costs money. Re-run with --yes only after the owner's yes.")
        return 2
    if provider is None:
        settings = load_settings()
        if not settings.google_ai_api_key:
            print("Empty GOOGLE_AI_API_KEY: load deploy/.env first. Nothing was called.", file=sys.stderr)
            return NO_KEY
        provider = make_provider(JUDGE2_MODEL, settings, json_timeout_s=120.0, json_effort=JUDGE2_EFFORT,
                                 max_retries=0)
    if spend.get("unjoined"):
        spend["unjoined_charged"] = spend["unjoined"]  # counted in the start, never again
    prior = [c.get("cost_usd") or 0.0 for c in calls if c.get("purpose") == "judge"]
    meter = Meter(spend["max_usd"], start, sink=folder / "calls.jsonl")
    judge = MeteredProvider(provider, meter, "judge")
    prompt = load_judge_prompt()
    code, failures, checked = None, 0, False

    def save_spend() -> None:
        spend["spent"] = meter.spent
        _write(folder / "spend.json", spend)

    try:
        for task in todo:
            if not checked and items[task["n"]]["kind"] != "check":
                checked = True
                missed = _missed_checks(key, answers, done)
                if missed and not force:
                    print(f"Judge 2 missed known-bad answers {missed}: it would not be trusted. Stopped before the "
                          f"answers; --force grades them anyway.", file=sys.stderr)
                    code = CHECK_MISSED
                    break
                costs = prior + [r.cost_usd for r in meter.calls]
                if costs:
                    left_now = sum(1 for t in todo if t["n"] not in done)
                    projected, room = mean(costs) * left_now, spend["max_usd"] - meter.spent
                    print(f"Projection: {left_now} answers left × ${mean(costs):.4f} per call = ${projected:.2f}; "
                          f"${room:.2f} left under the ceiling.", file=sys.stderr)
                    if projected > room and not force:
                        print("It will not fit under the ceiling: stopped before the answers; --force grades them "
                              "anyway, up to the ceiling.", file=sys.stderr)
                        code = WONT_FIT
                        break
            if meter.exhausted:
                break
            meter.item = task["n"]
            try:
                data, _ = judge.complete_json(prompt.text, [{"role": "user", "content": task["content"]}],
                                              JUDGE_SCHEMA, JUDGE2_MAX_TOKENS)
                entry = {**{c: data.get(c) for c in CRITERIA}, "note": str(data.get("note", "")) or "none"}
                problems = _valid(entry)
            except BudgetExceeded:
                break
            except Exception as exc:  # one failed answer must not stop the run; it is asked again next time
                problems = [type(exc).__name__]
            finally:
                save_spend()
            if problems:
                failures += 1
                print(f"{task['n']}: {problems[0]}", file=sys.stderr)
                if failures >= FAILURES_IN_A_ROW:
                    print(f"{FAILURES_IN_A_ROW} failed calls in a row: stopped.", file=sys.stderr)
                    code = STOPPED
                    break
                continue
            failures = 0
            done[task["n"]] = entry
            _write(out_path, done)
    finally:
        save_spend()
    left = len(tasks) - len(done)
    print(f"Gemini scored {len(done)} of {len(tasks)}; spent ${meter.spent:.4f} of ${spend['max_usd']:.2f}.")
    if code is not None:
        return code
    return 0 if left == 0 else STOPPED


def _fable_scores(judging: Path) -> dict[str, dict]:
    scores = {}
    for batch in _batches(judging):
        path = batch.with_suffix(".scores.json")
        if path.exists():
            for entry in _read(path):
                if isinstance(entry, dict) and entry.get("n") and not _valid(entry):
                    scores[entry["n"]] = {c: entry[c] for c in (*CRITERIA, "note")}
    return scores


def merge(folder: Path) -> int:
    folder = Path(folder)
    answers, key = _read(folder / "answers.json"), _key(folder)
    items = key["items"]
    gemini_path = folder / "gemini-scores.json"
    judges = {"fable": _fable_scores(key["judging_dir"]), "gemini": _read(gemini_path) if gemini_path.exists() else {}}
    check_by_id = {c["id"]: c for c in answers["judge_check"]}
    checks: dict[str, list[dict]] = {j: [] for j in JUDGES}
    for n, info in items.items():
        if info["kind"] != "check":
            continue
        check = check_by_id[info["id"]]
        for j in JUDGES:
            s = judges[j].get(n)
            checks[j].append({"id": check["id"], "criterion": check["criterion"], "scored": s is not None,
                              "caught": s is not None and s[check["criterion"]] <= check["max_score"]})
    trusted = [j for j in JUDGES if checks[j] and all(c["caught"] for c in checks[j])]
    lookup = {(info["model"], info["id"]): n for n, info in items.items() if info["kind"] == "answer"}
    for model, results in answers["results"].items():
        for r in results:
            n = lookup.get((model, r["id"]))
            if n is None:
                continue
            per = {j: judges[j][n] for j in JUDGES if n in judges[j]}
            r["scores_by_judge"] = per
            if trusted and all(j in per for j in trusted):  # every trusted judge, or the answer is not averaged
                r["scores"] = {c: round(mean(per[j][c] for j in trusted), 2) for c in CRITERIA}
                r["scores"]["note"] = " | ".join(f"{j}: {s['note']}" for j, s in per.items())
    answers["judges"] = {j: {"trusted": j in trusted, "checks": checks[j], "scored": len(judges[j])} for j in JUDGES}
    _write(folder / "scored.json", answers)
    print(f"scored.json written; trusted judges: {trusted or 'none'}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Reader model comparison, step 2: blind judges")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("export", "check-fable", "merge"):
        sub.add_parser(name).add_argument("folder", type=Path)
    j2 = sub.add_parser("judge2")
    j2.add_argument("folder", type=Path)
    j2.add_argument("--yes", action="store_true", help="the owner approved this cost")
    j2.add_argument("--force", action="store_true",
                    help="grade the answers even after a missed known-bad answer or a projection over the ceiling")
    args = parser.parse_args(argv)
    if args.command == "export":
        return export(args.folder)
    if args.command == "check-fable":
        return check_fable(args.folder)
    if args.command == "judge2":
        return judge2(args.folder, args.yes, force=args.force)
    return merge(args.folder)


if __name__ == "__main__":
    sys.exit(main())
