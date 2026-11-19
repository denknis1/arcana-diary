"""Reader model comparison, step 1: answers (spec 2026-11-19 §5–§6). Every run costs money.

  cd ~/arcana-diary && set -a && . deploy/.env && set +a && cd api
  .venv/bin/python -m evals.compare --stage A                                # estimate only, no calls
  .venv/bin/python -m evals.compare --stage A --yes --max-usd 0.2 --limit 1  # smoke run, after the owner's yes
  .venv/bin/python -m evals.compare --stage A --yes --max-usd 5              # the paid run, after the owner's yes

The question check runs first, once per distinct question, before any reader call (CachingGuard.prefill, with
retries); if a question still has no real answer, the run stops before any reader call (exit 5), so every model
gets the same groups. Then every item of compare_set.json runs for each model of the stage in turn, so a stop at
the ceiling leaves comparable results. A model with 3 errors in a row without usage (a refused parameter, a wrong
model id, repeated timeouts) is skipped for the rest of the run. The judges come later (compare_judges.py): here
the judge only records its input (RecordingJudge), which holds no model name; an item without an answer (timeout,
error, refusal, empty) is not graded, it gets "no_answer" with the reason. Each call is appended to calls.jsonl at
once; answers.json and spend.json are rewritten after every item and again when the run ends or fails. A stream
worker still alive 75 s after the end is counted in spend.json "unjoined" (its cost is not recorded).
Output: results/compare-<UTC time>-<stage>/ (not in git); an existing --out folder is refused.
"""
import argparse
import json
import sys
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path

from app.cards import load_cards
from app.config import KEY_NAMES, cost_usd, load_settings, provider_for_model
from app.reader import compose
from app.reader.check import load_reader_terms
from app.reader.providers import make_provider
from app.safety.content import load_all_texts
from app.safety.guard import Guard
from evals.judge import load_judge_prompt
from evals.metering import CachingGuard, Meter, MeteredProvider, RecordingJudge
from evals.run import (EST_TOKENS, EVALS_DIR, load_items, load_jsonl, run_daily_item, run_followup_item, run_item,
                       run_judge_check)

STAGES = {"A": ("claude-haiku-5-5", "gpt-6-luna", "gemini-3.8-flash"),
          "B": ("claude-sonnet-5-5", "gpt-6.2-sol", "gemini-4-argon")}
JUDGE2_MODEL = "gemini-4-argon"
# (in, out) tokens per judge-2 call, upper estimate: the rubric and the answer in, thinking (low) + JSON out
JUDGE2_EST_TOKENS = {"judge": (2200, 1500), "judge_daily": (1200, 1300)}
NO_KEY = 3
STOPPED = 4
GUARD_FAILED = 5
ERRORS_IN_A_ROW = 3


def load_set() -> dict[str, list[dict]]:
    """compare_set.json ids -> the items of the 4.2 eval files, in the set's order."""
    chosen = json.loads((EVALS_DIR / "compare_set.json").read_text(encoding="utf-8"))
    pools = {"questions": [*load_items("en"), *load_items("es")], "injection": load_jsonl("injection.jsonl"),
             "followups": load_jsonl("followups.jsonl"), "daily": load_jsonl("daily.jsonl")}
    out = {}
    for part, ids in chosen.items():
        by_id = {item["id"]: item for item in pools[part]}
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise ValueError(f"compare_set.json: unknown {part} ids {missing}")
        out[part] = [by_id[i] for i in ids]
    return out


def judge2_cost(kind: str, day: date | None = None) -> float:
    """Upper estimate of one judge-2 call; kind "judge" (a reading, a follow-up, a known-bad answer) or
    "judge_daily"."""
    return cost_usd(JUDGE2_MODEL, *JUDGE2_EST_TOKENS[kind], day) or 0.0


def estimate_cost(models, items: dict, guard_model: str = "claude-haiku-5-5", n_judge_check: int = 8,
                  day: date | None = None) -> float:
    """Upper estimate of the whole stage on `day` (default today): answers, the question check once, and judge 2
    (Fable costs no API)."""
    def call(purpose: str, model: str) -> float:
        return cost_usd(model, *EST_TOKENS[purpose], day) or 0.0

    n_read = len(items["questions"]) + len(items["injection"])
    n_fu, n_daily = len(items["followups"]), len(items["daily"])
    guard = (n_read + n_fu) * call("guard", guard_model)
    readers = sum(n_read * call("reader", m) + n_fu * (call("reader", m) + call("followup", m))
                  + n_daily * call("daily", m) for m in models)
    judge = (len(models) * ((n_read + n_fu) * judge2_cost("judge", day) + n_daily * judge2_cost("judge_daily", day))
             + n_judge_check * judge2_cost("judge", day))
    return round(guard + readers + judge, 2)


def _missing_keys(settings, models, need_guard: bool) -> list[str]:
    keys = {"claude": settings.anthropic_api_key, "openai": settings.openai_api_key,
            "gemini": settings.google_ai_api_key}
    families = {provider_for_model(m) for m in models} | {"gemini"}  # judge 2 runs on Gemini
    if need_guard:
        families.add("claude")
    return sorted(KEY_NAMES[f] for f in families if not keys[f])


def _questions(items: dict) -> list[str]:
    """Every text the question check sees: the reading questions (not the empty ones) and the follow-ups."""
    return [i["question"] for i in items["questions"] + items["injection"] if i.get("question")] + [
        i["followup"] for i in items["followups"]]


def _no_answer(content: str | None) -> bool:
    """True when the graded answer (between "<answer>\\n" and "\\n</answer>") is empty."""
    if not content or "<answer>\n" not in content:
        return False
    return not content.rsplit("<answer>\n", 1)[1].rsplit("\n</answer>", 1)[0].strip()


def _join_new_workers(before: set, timeout_s: float = 75.0) -> int:
    """A stream the engine gave up on is recorded when its worker ends (MeteredProvider): wait for this run's
    workers (the SDK timeout is 60 s) so their cost reaches spend.json. Returns how many are still alive: their
    calls are lost at exit and missing from spend.json."""
    deadline = time.monotonic() + timeout_s
    mine = [t for t in threading.enumerate() if t.name == "reader-stream" and t not in before]
    for thread in mine:
        thread.join(max(0.0, deadline - time.monotonic()))
    return sum(1 for thread in mine if thread.is_alive())


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None, *, providers: dict | None = None, guard_provider=None) -> int:
    parser = argparse.ArgumentParser(description="Reader model comparison, step 1: answers (costs money)")
    parser.add_argument("--stage", choices=sorted(STAGES), required=True)
    parser.add_argument("--yes", action="store_true", help="the owner approved this stage and its cost")
    parser.add_argument("--max-usd", type=float, default=None, help="hard ceiling for the whole stage")
    parser.add_argument("--limit", type=int, default=None, help="only the first N items of each part (smoke run)")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    settings = load_settings()
    models = STAGES[args.stage]
    items = {part: rows[:args.limit] for part, rows in load_set().items()}
    estimate = estimate_cost(models, items, settings.guard_model)
    print(f"Stage {args.stage}: {', '.join(models)}; {sum(len(v) for v in items.values())} items per model; "
          f"judge 2 {JUDGE2_MODEL}. Estimated cost of the whole stage: ${estimate:.2f} (upper estimate).")
    if not args.yes:
        print("Not running: every run costs money. Re-run with --yes --max-usd N only after the owner's yes.")
        return 2
    if args.max_usd is None:
        print("--max-usd is required with --yes (spec §2.9).", file=sys.stderr)
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or EVALS_DIR / "results" / f"compare-{stamp}-{args.stage}"
    if out.exists():
        print(f"{out} exists: a new run needs a new folder (its spend would be counted from zero). "
              f"Nothing was called.", file=sys.stderr)
        return 2
    if providers is None:
        missing = _missing_keys(settings, models, guard_provider is None)
        if missing:
            print(f"Empty {', '.join(missing)}: load deploy/.env first. Nothing was called.", file=sys.stderr)
            return NO_KEY

    out.mkdir(parents=True)
    meter = Meter(args.max_usd, sink=out / "calls.jsonl")
    readers = {m: MeteredProvider(providers[m] if providers else make_provider(
        m, settings, effort=settings.reader_effort, max_retries=0), meter) for m in models}
    guard_inner = guard_provider or make_provider(settings.guard_model, settings,
                                                  json_timeout_s=settings.guard_timeout_s, max_retries=0)
    prompts = compose.load_prompts()
    guard_prompt = prompts[("guard", None)]
    guard = CachingGuard(Guard(MeteredProvider(guard_inner, meter, "guard"), guard_prompt.text, guard_prompt.version))
    cards, terms, texts = load_cards(settings.content_dir), load_reader_terms(), load_all_texts()
    judge, judge_prompt = RecordingJudge(), load_judge_prompt()
    common = {"cards": cards, "prompts": prompts, "judge_provider": judge, "judge_prompt": judge_prompt,
              "terms": terms, "first_token_timeout_s": settings.first_token_timeout_s}
    runs = [*[(run_item, item) for item in items["questions"] + items["injection"]],
            *[(run_followup_item, item) for item in items["followups"]],
            *[(run_daily_item, item) for item in items["daily"]]]

    results: dict[str, list[dict]] = {m: [] for m in models}
    not_done: list[dict] = []
    skipped: dict[str, str] = {}
    streak = {m: 0 for m in models}
    checks: list[dict] = []
    seen = 0
    workers = set(threading.enumerate())

    unjoined = 0

    def write_spend() -> None:
        _write(out / "spend.json", {"max_usd": args.max_usd, "spent": meter.spent, "estimate_usd": estimate,
                                    "stopped": bool(not_done), "not_done": not_done, "skipped": skipped,
                                    "unjoined": unjoined})

    def write_answers() -> None:
        _write(out / "answers.json", {
            "stage": args.stage, "models": list(models), "reader_effort": settings.reader_effort,
            "prompts": {f"{name}.{lang or 'all'}": p.version for (name, lang), p in prompts.items()},
            "judge_prompt": judge_prompt.version, "results": results, "judge_check": checks})

    def count_errors() -> None:
        """3 calls in a row without usage (an error or an abandoned stream) -> the model is skipped."""
        nonlocal seen
        new, seen = meter.calls[seen:], len(meter.calls)
        for record in new:
            if record.model not in streak or record.purpose == "guard":
                continue
            streak[record.model] = streak[record.model] + 1 if record.error and record.tokens_in is None else 0
            if streak[record.model] >= ERRORS_IN_A_ROW and record.model not in skipped:
                skipped[record.model] = f"{ERRORS_IN_A_ROW} errors in a row without usage (last: {record.error})"
                print(f"{record.model}: {skipped[record.model]}; skipped for the rest of the run", file=sys.stderr)

    try:
        failed = guard.prefill(_questions(items))
        seen = len(meter.calls)
        if failed:
            not_done += [{"model": m, "id": item["id"], "reason": "question check failed"}
                         for _, item in runs for m in models]
            print(f"The question check failed for {len(failed)} question(s) after retries"
                  + (" (the ceiling was reached)" if meter.exhausted else "")
                  + ": no reader was called, every model must get the same groups.", file=sys.stderr)
            return GUARD_FAILED
        for runner, item in runs:
            for model in models:
                if model in skipped or meter.exhausted:
                    not_done.append({"model": model, "id": item["id"],
                                     "reason": f"skipped: {skipped[model]}" if model in skipped else "ceiling"})
                    continue
                meter.item = item["id"]
                refused_before = meter.refused
                kwargs = {**common, "reader": readers[model]}
                if runner is not run_daily_item:
                    kwargs.update(guard=guard, texts=texts)
                result = runner(item, **kwargs)
                content = judge.take()
                count_errors()
                if meter.refused > refused_before:  # the ceiling cut this item short: it does not count
                    not_done.append({"model": model, "id": item["id"], "reason": "ceiling"})
                    continue
                if "scores" in result:
                    del result["scores"]
                    if _no_answer(content):  # nothing to grade: availability, not quality
                        result["no_answer"] = result.get("shown_reason") or result.get("error") or "empty"
                    else:
                        result["judge_content"] = content
                results[model].append(result)
            write_answers()
            write_spend()
        for item in load_jsonl("judge_check.jsonl"):
            run_judge_check(item, cards=cards, judge_provider=judge, judge_prompt=judge_prompt)
            checks.append({"id": item["id"], "criterion": item["criterion"], "max_score": item["max_score"],
                           "judge_content": judge.take()})
    finally:
        unjoined = _join_new_workers(workers)
        if unjoined:
            print(f"{unjoined} abandoned call(s) not recorded: add {unjoined} × the model's upper bound before "
                  f"judge 2", file=sys.stderr)
        write_answers()
        write_spend()
    print(f"Spent ${meter.spent:.4f} of ${args.max_usd:.2f}. "
          + (f"Not done: {len(not_done)} answers (ceiling or skipped model). " if not_done else "")
          + f"Results: {out}")
    return STOPPED if not_done else 0


if __name__ == "__main__":
    sys.exit(main())
