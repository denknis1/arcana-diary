"""Reader eval run (§5.3, §8.9). Every run costs money: it prints an estimate and refuses to run without --yes and
a hard ceiling --max-usd (stage 4.5, Fable plan review I3): every model call goes through evals.metering, a call
over the ceiling is refused, an item that met a refusal is not counted, and the run stops (exit STOPPED) with what
it spent printed and stored.

Six sets, all written in full in this folder:
- questions.<lang>.jsonl — 60 reader questions per language (guard → reader → judge); the last 10 are yes/no on
  three cards (stage 4.5 §4: "count": 3, and a fixed "seed" where the votes must give yes, no, a tie, …);
- injection.jsonl — 10 attempts to break the reader (guard → reader → judge, plus a leak check);
- followups.jsonl — 10 follow-ups per language (§9.9): reader → guard on the follow-up → follow-up → judge;
- daily.jsonl — 10 card-of-the-day texts per language (§9.9): daily prompt → judge;
- guard.jsonl — 76 questions for the question check only: crisis, look-alike everyday phrases and ambiguous
  stop-phrases that must not give a crisis answer;
- judge_check.jsonl — 10 known-bad answers: the judge must give each one 2 or less on the named criterion,
  otherwise its averages are not trusted and the run fails.
Every result records the guard's source and time, the raw answer and what a person would see after §2.5.
A reader answer of [[crisis]] is recorded (reader_crisis) and not graded: for a crisis question it counts as caught.

The controller runs it only after the owner's explicit yes to the printed cost, with the key from deploy/.env:
  cd ~/arcana-diary && set -a && . deploy/.env && set +a && cd api
  .venv/bin/python -m evals.run                         # estimate only, no calls
  .venv/bin/python -m evals.run --yes --max-usd 3.00     # the paid run, never above $3.00
  .venv/bin/python -m evals.run --kind yes_no --yes --max-usd 1.00   # only the yes/no reader items, the guard set
                                                                      # and the judge check
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.cards import label, load_cards
from app.config import PRICES_PER_MTOK, cost_usd, load_settings
from app.draw import draw_spread
from app.reader import check, compose
from app.reader.check import load_reader_terms
from app.reader.claude import ClaudeProvider
from app.reader.engine import Chunk, Finished, run_stream
from app.reader.finalize import finalize
from app.reader.followups import CRISIS_MARK, FOLLOWUP_MAX_TOKENS
from app.reader.sections import SectionParser
from app.safety.content import load_all_texts
from app.safety.guard import NO_VERDICT_GROUPS, Guard
from evals.judge import auto_checks, judge, load_judge_prompt, summarize, text_checks
from evals.metering import Meter, MeteredProvider

EVALS_DIR = Path(__file__).resolve().parent
# (in, out) tokens per call, upper estimate
EST_TOKENS = {"guard": (700, 300), "reader": (1600, 1500), "judge": (2200, 900), "followup": (2200, 600),
              "daily": (700, 400), "judge_daily": (1200, 700)}
READER_MAX_TOKENS = 4000
DAILY_MAX_TOKENS = 2000
NO_KEY = 3
STOPPED = 4  # the ceiling was reached: the items after it did not run


def load_jsonl(name: str) -> list[dict]:
    path = EVALS_DIR / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_items(lang: str) -> list[dict]:
    return load_jsonl(f"questions.{lang}.jsonl")


def estimate_cost(n_reader: int, n_guard: int, n_judge_check: int, settings, n_followup: int = 0,
                  n_daily: int = 0) -> float:
    def call(purpose: str, model: str) -> float:
        return cost_usd(model, *EST_TOKENS[purpose]) or 0.0

    guard, judge_call = call("guard", settings.guard_model), call("judge", settings.judge_model)
    reader = call("reader", settings.reader_model)
    per_reader_item = guard + reader + judge_call
    per_followup = guard + reader + call("followup", settings.reader_model) + judge_call
    per_daily = call("daily", settings.reader_model) + call("judge_daily", settings.judge_model)
    return round(n_reader * per_reader_item + n_guard * guard + n_judge_check * judge_call
                 + n_followup * per_followup + n_daily * per_daily, 2)


def eval_reading(item: dict, group: str, cards) -> dict:
    """The cards come from the item's own "seed" when it has one, else from its id; "count" — yes/no on three."""
    lang = item["lang"]
    seed = item.get("seed") or f"eval:{item['id']}"
    reading = {"id": item["id"], "lang": lang, "kind": item["kind"], "question": item["question"],
               "topic": item["topic"], "situation": item["situation"], "guard_group": group,
               "cards": draw_spread(seed, item["kind"], cards.order, item.get("count"))}
    with_verdict = item["kind"] == "yes_no" and group not in NO_VERDICT_GROUPS
    reading["verdict"] = cards.verdict(reading["cards"]) if with_verdict else None
    return reading


def reading_input(reading: dict, cards) -> str:
    verdict_label = label(reading["verdict"], reading["lang"], cards.rules) if reading["verdict"] else None
    return compose.reading_input(reading, cards.excerpts(reading["cards"], reading["lang"], reading["topic"]),
                                 verdict_label, compose.card_votes(reading, cards))


def read_sections(reader, prompt, reading: dict, user_input: str, first_token_timeout_s: float):
    parser, outcome = SectionParser(), None
    for piece in run_stream(reader, prompt.text, [{"role": "user", "content": user_input}], READER_MAX_TOKENS,
                            first_token_timeout_s):
        if isinstance(piece, Chunk):
            parser.feed(piece.text)
        else:
            outcome = piece
    parser.finish()
    return parser.sections(), parser.seen, outcome


def read_text(reader, prompt, messages: list[dict], max_tokens: int, first_token_timeout_s: float):
    parts, outcome = [], None
    for piece in run_stream(reader, prompt.text, messages, max_tokens, first_token_timeout_s):
        if isinstance(piece, Chunk):
            parts.append(piece.text)
        else:
            outcome = piece
    return "".join(parts).strip(), outcome


def run_item(item: dict, *, cards, prompts, guard, reader, judge_provider, judge_prompt, terms, texts,
             first_token_timeout_s: float) -> dict:
    lang = item["lang"]
    result = {"id": item["id"], "lang": lang, "category": item["category"], "expect_group": item["expect_group"]}
    try:
        if item["question"]:
            verdict = guard.classify(item["question"])
            group = verdict.group
            result.update({"guard_source": verdict.source, "guard_ms": verdict.ms_total})
        else:
            group = "ok"
        result["group"] = group
        if group == "crisis":
            result["auto"] = auto_checks(item, group, None, terms[lang], False)
            return result
        reading = eval_reading(item, group, cards)
        user_input = reading_input(reading, cards)
        sections, seen, outcome = read_sections(reader, prompts[("reader", lang)], reading, user_input,
                                                first_token_timeout_s)
        final = finalize(reading, sections, seen, outcome, cards, terms[lang], texts[lang]["reader_unavailable"])
        result.update({"sections": sections, "shown": final.shown, "shown_reason": final.reason,
                       "shown_sections": final.sections, "reader_crisis": final.shown == "crisis"})
        if final.shown == "crisis":
            result["auto"] = auto_checks(item, group, None, terms[lang], False, reader_crisis=True)
            return result
        result["auto"] = auto_checks(item, group, sections, terms[lang], reading["verdict"] is not None)
        result["scores"] = judge(judge_provider, judge_prompt, item, user_input, compose.answer_text(sections))
    except Exception as exc:  # one failed item must not stop a paid run; it is counted as an error
        result["error"] = type(exc).__name__
    return result


def run_followup_item(item: dict, *, cards, prompts, guard, reader, judge_provider, judge_prompt, terms, texts,
                      first_token_timeout_s: float) -> dict:
    """The reading's first answer, then the follow-up exactly as the API sends it (§2.3); the follow-up question
    goes through the guard, the reading question is an ok question."""
    lang = item["lang"]
    result = {"id": item["id"], "lang": lang, "category": item["category"], "expect_group": item["expect_group"]}
    try:
        verdict = guard.classify(item["followup"])
        group = verdict.group
        result.update({"group": group, "guard_source": verdict.source, "guard_ms": verdict.ms_total})
        if group == "crisis":
            result["auto"] = text_checks(item, group, None, terms[lang], check.FOLLOWUP_WORDS)
            return result
        reading = eval_reading(item, "ok", cards)
        user_input = reading_input(reading, cards)
        sections, seen, outcome = read_sections(reader, prompts[("reader", lang)], reading, user_input,
                                                first_token_timeout_s)
        first = finalize(reading, sections, seen, outcome, cards, terms[lang], texts[lang]["reader_unavailable"])
        if first.sections is None:
            raise RuntimeError("the first answer is a crisis answer")
        first_answer = compose.answer_text(first.sections)
        excerpts = cards.excerpts(reading["cards"], lang, reading["topic"])
        messages = compose.followup_messages(reading, excerpts, None, first_answer, [], item["followup"], group)
        text, outcome = read_text(reader, prompts[("followup", lang)], messages, FOLLOWUP_MAX_TOKENS,
                                  first_token_timeout_s)
        crisis = bool(CRISIS_MARK.search(text))
        result.update({"answer": text, "reader_crisis": crisis})
        result["auto"] = text_checks(item, group, None if crisis else text, terms[lang], check.FOLLOWUP_WORDS,
                                     reader_crisis=crisis)
        if not crisis:
            context = (f"{user_input}\n<first_answer>\n{first_answer}\n</first_answer>\n"
                       f"<followup>{item['followup']}</followup>")
            result["scores"] = judge(judge_provider, judge_prompt, item, context, text)
    except Exception as exc:  # one failed item must not stop a paid run; it is counted as an error
        result["error"] = type(exc).__name__
    return result


def run_daily_item(item: dict, *, cards, prompts, reader, judge_provider, judge_prompt, terms,
                   first_token_timeout_s: float) -> dict:
    """One card-of-the-day text as the background job writes it (§2.6); "shown" is what the cache would keep."""
    lang = item["lang"]
    result = {"id": item["id"], "lang": lang, "category": item["category"], "expect_group": "ok", "group": "ok"}
    try:
        [excerpt] = cards.excerpts([{"card_id": item["card_id"], "position": "card", "reversed": item["reversed"]}],
                                   lang, None)
        messages = compose.daily_messages(excerpt, lang)
        text, outcome = read_text(reader, prompts[("daily", lang)], messages, DAILY_MAX_TOKENS,
                                  first_token_timeout_s)
        auto = text_checks(item, "ok", text, terms[lang], check.DAILY_WORDS)
        usable = (bool(text) and isinstance(outcome, Finished) and outcome.result.stop_reason != "max_tokens"
                  and not auto["banned"])
        result.update({"answer": text, "shown": "model" if usable else "fallback", "auto": auto})
        result["scores"] = judge(judge_provider, judge_prompt, item, messages[0]["content"], text)
    except Exception as exc:
        result["error"] = type(exc).__name__
    return result


def run_guard_item(item: dict, guard) -> dict:
    result = {"id": item["id"], "lang": item["lang"], "expect_group": item["expect_group"], "note": item["note"]}
    try:
        verdict = guard.classify(item["question"])
        result.update({"group": verdict.group, "guard_source": verdict.source, "guard_ms": verdict.ms_total})
    except Exception as exc:
        result["error"] = type(exc).__name__
    return result


def run_judge_check(item: dict, *, cards, judge_provider, judge_prompt) -> dict:
    result = {"id": item["id"], "lang": item["lang"], "criterion": item["criterion"], "max_score": item["max_score"]}
    try:
        reading = eval_reading(item, item["expect_group"], cards)
        scores = judge(judge_provider, judge_prompt, item, reading_input(reading, cards), item["answer"])
        result.update({"scores": scores, "caught": scores[item["criterion"]] <= item["max_score"]})
    except Exception as exc:
        result.update({"error": type(exc).__name__, "caught": False})
    return result


def main(argv=None, *, reader=None, guard_provider=None, judge_provider=None) -> int:
    parser = argparse.ArgumentParser(description="Arcana Diary reader evals (each run costs money)")
    parser.add_argument("--lang", choices=["en", "es", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None, help="only the first N items of each set per language")
    parser.add_argument("--kind", choices=["one", "three", "yes_no"], default=None,
                        help="only reader items of this kind; skips the follow-up and daily sets")
    parser.add_argument("--yes", action="store_true", help="the owner has approved this run and its cost")
    parser.add_argument("--max-usd", type=float, default=None, help="hard ceiling of this run, required with --yes")
    parser.add_argument("--out", type=Path, default=EVALS_DIR / "results")
    args = parser.parse_args(argv)
    settings = load_settings()
    langs = ("en", "es") if args.lang == "all" else (args.lang,)

    def per_lang(rows):
        return [row for lang in langs for row in [r for r in rows if r["lang"] == lang][: args.limit]]

    items = per_lang([*load_items("en"), *load_items("es")]) + per_lang(load_jsonl("injection.jsonl"))
    followup_items = per_lang(load_jsonl("followups.jsonl"))
    daily_items = per_lang(load_jsonl("daily.jsonl"))
    if args.kind:
        items = [item for item in items if item["kind"] == args.kind]
        followup_items, daily_items = [], []
    guard_items = per_lang(load_jsonl("guard.jsonl"))
    judge_items = per_lang(load_jsonl("judge_check.jsonl"))
    estimate = estimate_cost(len(items), len(guard_items), len(judge_items), settings, len(followup_items),
                             len(daily_items))
    print(f"Items: {len(items)} reader, {len(followup_items)} follow-up, {len(daily_items)} daily, "
          f"{len(guard_items)} guard-only, {len(judge_items)} judge check. "
          f"Models: reader {settings.reader_model} (effort {settings.reader_effort}), guard {settings.guard_model}, "
          f"judge {settings.judge_model}.")
    print(f"Estimated cost: ${estimate:.2f} (upper estimate).")
    if not args.yes:
        print("Not running: every run costs money. Re-run with --yes --max-usd N only after the owner has approved "
              "this cost.")
        return 2
    if args.max_usd is None or not math.isfinite(args.max_usd) or args.max_usd <= 0:
        print("--max-usd N (a number above 0) is required with --yes. Nothing was called.", file=sys.stderr)
        return 2
    if estimate > args.max_usd:
        print(f"The estimate ${estimate:.2f} is above the ceiling ${args.max_usd:.2f}. Nothing was called.",
              file=sys.stderr)
        return 2
    key = settings.anthropic_api_key
    if not key and None in (reader, guard_provider, judge_provider):
        print("ANTHROPIC_API_KEY is empty: load it first (set -a && . deploy/.env && set +a). Nothing was called.",
              file=sys.stderr)
        return NO_KEY
    reader = reader or ClaudeProvider(key, settings.reader_model, effort=settings.reader_effort)
    guard_provider = guard_provider or ClaudeProvider(key, settings.guard_model,
                                                      json_timeout_s=settings.guard_timeout_s)
    judge_provider = judge_provider or ClaudeProvider(key, settings.judge_model, json_timeout_s=60.0, json_effort=None)
    unpriced = [f"{role} model {model}" for role, model in (("reader", reader.model), ("guard", guard_provider.model),
                                                            ("judge", judge_provider.model))
                if model not in PRICES_PER_MTOK]
    if unpriced:  # a model without a price row would be metered as $0 and could never reach the ceiling
        print(f"The {', '.join(unpriced)} has no price in PRICES_PER_MTOK (app/config.py): the ceiling would not "
              f"work. Add a price row first. Nothing was called.", file=sys.stderr)
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args.out.mkdir(parents=True, exist_ok=True)
    # every call is appended at once, so what a crashed run spent is not lost (stage 4.5, Fable re-check R2)
    meter = Meter(args.max_usd, sink=args.out / f"calls-{stamp}.jsonl")
    reader = MeteredProvider(reader, meter)
    guard_provider = MeteredProvider(guard_provider, meter, "guard")
    judge_provider = MeteredProvider(judge_provider, meter, "judge")
    prompts = compose.load_prompts()
    guard_prompt = prompts[("guard", None)]
    guard = Guard(guard_provider, guard_prompt.text, guard_prompt.version)
    cards = load_cards(settings.content_dir)
    terms, texts, judge_prompt = load_reader_terms(), load_all_texts(), load_judge_prompt()
    common = {"cards": cards, "prompts": prompts, "reader": reader, "judge_provider": judge_provider,
              "judge_prompt": judge_prompt, "terms": terms, "first_token_timeout_s": settings.first_token_timeout_s}
    not_done: list[str] = []

    def metered(runs) -> list[dict]:
        """Each item while the ceiling holds. The guard and the reader engine turn a refused call into a fallback
        and run_item into an error, so an item that met a refusal is dropped, not graded."""
        out = []
        for item, run in runs:
            if meter.exhausted:
                not_done.append(item["id"])
                continue
            meter.item, refused_before = item["id"], meter.refused
            result = run(item)
            if meter.refused > refused_before:
                not_done.append(item["id"])
            else:
                out.append(result)
        return out

    judge_check = metered((item, lambda i: run_judge_check(i, cards=cards, judge_provider=judge_provider,
                                                           judge_prompt=judge_prompt)) for item in judge_items)
    results = metered((item, lambda i: run_item(i, guard=guard, texts=texts, **common)) for item in items)
    results += metered((item, lambda i: run_followup_item(i, guard=guard, texts=texts, **common))
                       for item in followup_items)
    results += metered((item, lambda i: run_daily_item(i, **common)) for item in daily_items)
    guard_results = metered((item, lambda i: run_guard_item(i, guard)) for item in guard_items)
    summary = summarize(results, guard_results, judge_check)
    path = args.out / f"run-{stamp}.json"
    report = {
        "estimate_usd": estimate, "max_usd": args.max_usd, "spent_usd": meter.spent, "not_done": not_done,
        "models": {"reader": reader.model, "guard": guard_provider.model, "judge": judge_provider.model},
        "reader_effort": settings.reader_effort,
        "prompts": {f"{name}.{lang or 'all'}": p.version for (name, lang), p in prompts.items()},
        "judge_prompt": judge_prompt.version, "summary": summary, "judge_check": judge_check, "results": results,
        "guard_results": guard_results,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    judge_ok = summary.get("judge_check", {}).get("passed", True)
    if not judge_ok:
        print("The judge missed known-bad answers: its averages are not trusted -> FAIL")
    for lang in langs:
        s = summary.get(lang)
        if s:
            print(f"{lang}: means {s['means']}, safety violations {s['safety_violations']}, "
                  f"guard missed crisis {s['guard']['missed_crisis']}, false crisis {s['guard']['false_crisis']}, "
                  f"guard sources {s['guard']['sources']}, errors {s['errors']} -> {'PASS' if s['passed'] else 'FAIL'}")
    print(f"Spent ${meter.spent:.4f} of ${args.max_usd:.2f}.")
    print(f"Results: {path}")
    if not_done:
        print(f"Stopped at the ceiling: {len(not_done)} items did not run (first: {not_done[0]}) -> NOT A RESULT")
        return STOPPED
    passed = judge_ok and all(summary[lang]["passed"] for lang in langs if lang in summary)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
