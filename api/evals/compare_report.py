"""Reader model comparison, step 3: numbers and the report page in Russian (spec 2026-11-19 §8).

  .venv/bin/python -m evals.compare_report <dir>    # writes <dir>/report.html and <dir>/summary.json

Money comes from the calls actually made (calls.jsonl): a reading = the mean reader call + the mean question check;
a follow-up = the mean follow-up call + the mean question check; the card of the day = the mean daily call. The
second money column uses the announced prices (PRICE_CHANGES) on the same tokens, whatever the date of the run.
Quality counts only the answers every trusted judge scored (merge); "safe <= 2" counts trusted judges only. Answers
without text (no_answer: timeout, error, refusal, empty) are not graded and are counted per reason. The gap to
Claude is Claude's overall minus the model's overall in the same stage; 0 < gap < 0.2 is the §2.6 tuning round,
decided on the unrounded numbers (rounded only for display). A model without a good reader call has no reading,
follow-up, per-1000 or monthly price («—»). A judge that is not counted is labelled with why: it failed the
known-bad check, or its scores are incomplete (merge --allow-incomplete).
"""
import html
import json
import math
import sys
from pathlib import Path
from statistics import mean

from app.config import PRICE_CHANGES, PRICES_PER_MTOK, provider_for_model
from evals.judge import CRITERIA

VISITS = (100, 1000, 10000)
READINGS_PER_VISITOR = 1.5
FOLLOWUPS_PER_VISITOR = 0.5
DAYS = 30
DAILY_TEXTS_PER_DAY = 78 * 2 * 2   # every card, both orientations, EN and ES (app/daily.py fill_daily_cache)
LABELS = {"relevant": "По делу", "specific": "Конкретно", "warm": "Тепло", "safe": "Безопасно"}
TIMEOUTS = ("ProviderTimeout", "abandoned")   # the SDK gave up, or the engine stopped waiting (15 s / 30 s)
READER_PURPOSES = ("reader", "followup", "daily")  # the model's own reader calls, not the guard or judge it may run
TUNING_GAP = 0.2                               # spec §2.6: a cheaper model this close to Claude gets one tuning round
NO_ANSWER = {"timeout": "тайм-аут", "error": "ошибка", "refusal": "отказ",
             "empty": "пусто, тайм-аут или ответ без разделов", "budget": "потолок"}
NOT_COUNTED = {"failed": "не учтён (не прошёл проверку)", "incomplete": "не учтён (оценки неполные)"}
JUDGE_NAMES = {"fable": "Fable 5.2", "gemini": "Gemini 4 Argon"}
CAVEAT = ("Оговорка о судьях: у ChatGPT нет «своего» судьи; Fable 5.2 — модель семейства Claude; судья Gemini 4 Argon "
          "— модель Gemini, а на этапе Б он оценивает и самого себя. Поэтому смотрите и на оценки каждого судьи, и на "
          "расхождения между ними.")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile: the median of [300, 500] is 300, the 95th is 500."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def _means(rows: list[dict], digits: int | None = 2) -> dict:
    return {c: round(mean(r[c] for r in rows), digits) if digits is not None else mean(r[c] for r in rows)
            for c in CRITERIA} if rows else {}


def _status(info: dict) -> str:
    """trusted | failed | incomplete; a scored.json without "status" (before merge knew "incomplete")."""
    return info.get("status") or ("trusted" if info.get("trusted") else "failed")


def _future_cost(call: dict) -> float:
    change = PRICE_CHANGES.get(call["model"])
    if change is None or call["tokens_in"] is None or call["tokens_out"] is None:
        return call["cost_usd"]
    price_in, price_out = change[1]
    return (call["tokens_in"] * price_in + call["tokens_out"] * price_out) / 1_000_000


def _money(calls: list[dict], guard_calls: list[dict], cost_of) -> dict:
    def avg(purpose: str, pool: list[dict]) -> float | None:
        values = [cost_of(c) for c in pool if c["purpose"] == purpose and not c["error"]]
        return mean(values) if values else None

    guard, reader, daily = avg("guard", guard_calls) or 0.0, avg("reader", calls), avg("daily", calls) or 0.0
    if reader is None:  # no good reader call (a skipped model): the guard alone is not a reading's price
        return {"reading": None, "followup": None, "daily": daily, "per_1000": None,
                "monthly": {str(v): None for v in VISITS}}
    reading, followup = reader + guard, (avg("followup", calls) or 0.0) + guard
    monthly = {str(v): DAYS * (v * (READINGS_PER_VISITOR * reading + FOLLOWUPS_PER_VISITOR * followup)
                               + DAILY_TEXTS_PER_DAY * daily) for v in VISITS}
    return {"reading": reading, "followup": followup, "daily": daily, "per_1000": reading * 1000,
            "monthly": monthly}


def _disagree(per: dict) -> bool:
    """Two judges more than 1 point apart on any criterion."""
    if len(per) < 2:
        return False
    return any(max(s[c] for s in per.values()) - min(s[c] for s in per.values()) > 1 for c in CRITERIA)


def _model(model: str, results: list[dict], calls: list[dict], guard_calls: list[dict], trusted: set[str]) -> dict:
    scored = [r for r in results if r.get("scores")]
    quality = _means([r["scores"] for r in scored])
    exact = _means([r["scores"] for r in scored], digits=None)
    by_lang = {lang: _means([r["scores"] for r in scored if r["lang"] == lang]) for lang in ("en", "es")}
    judges = sorted({j for r in results for j in r.get("scores_by_judge", {})})
    by_judge = {j: _means([r["scores_by_judge"][j] for r in results if j in r.get("scores_by_judge", {})])
                for j in judges}
    safety = {
        "banned": sum(1 for r in results if r.get("auto", {}).get("banned")),
        "safe_low": sum(1 for r in results if any(s["safe"] <= 2 for j, s in r.get("scores_by_judge", {}).items()
                                                  if j in trusted)),
        "fallback": sum(1 for r in results if r.get("shown") == "fallback"),
        "reader_crisis": sum(1 for r in results if r.get("reader_crisis")),
        "leaks": sum(1 for r in results if r.get("auto", {}).get("leak")),
        "errors": sum(1 for r in results if r.get("error")),
    }
    no_answer: dict[str, int] = {}
    for r in results:
        if r.get("no_answer"):
            no_answer[r["no_answer"]] = no_answer.get(r["no_answer"], 0) + 1
    disagree = [r["id"] for r in results if _disagree(r.get("scores_by_judge", {}))]
    mine = [c for c in calls if c["model"] == model]
    reader = [c for c in mine if c["purpose"] == "reader" and not c["error"]]
    firsts = [c["ms_first"] for c in reader if c["ms_first"] is not None]
    totals = [c["ms_total"] for c in reader]
    speed = {"first_p50": _pct(firsts, 0.5), "first_p95": _pct(firsts, 0.95), "total_p50": _pct(totals, 0.5),
             "total_p95": _pct(totals, 0.95),
             "timeouts": sum(1 for c in mine if c["purpose"] in READER_PURPOSES and c["error"] in TIMEOUTS)}
    return {"quality": quality, "overall": round(mean(quality.values()), 2) if quality else None,
            "overall_exact": mean(exact.values()) if exact else None,
            "by_lang": by_lang, "by_judge": by_judge, "safety": safety, "speed": speed, "no_answer": no_answer,
            "disagree": len(disagree), "disagree_ids": disagree,
            "cost": _money(mine, guard_calls, lambda c: c["cost_usd"]),
            "cost_future": _money(mine, guard_calls, _future_cost) if model in PRICE_CHANGES else None,
            "price": PRICES_PER_MTOK.get(model), "price_change": PRICE_CHANGES.get(model),
            "answers": len(results), "scored": len(scored)}


def build_summary(folder: Path) -> dict:
    folder = Path(folder)
    scored = _read(folder / "scored.json")
    calls = [json.loads(line) for line in (folder / "calls.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    guard_calls = [c for c in calls if c["purpose"] == "guard"]
    judges = scored.get("judges", {})
    trusted = {j for j, info in judges.items() if info["trusted"]}
    models = {m: _model(m, scored["results"][m], calls, guard_calls, trusted) for m in scored["models"]}
    claude = next((m for m in models if provider_for_model(m) == "claude"), None)
    for m, s in models.items():
        per_1000 = s["cost"]["per_1000"]
        s["quality_per_usd"] = round(s["overall"] / per_1000, 2) if s["overall"] is not None and per_1000 else None
        base = models[claude]["overall_exact"] if claude else None
        gap = (base - s["overall_exact"] if m != claude and base is not None and s["overall_exact"] is not None
               else None)
        s["gap_to_claude"] = round(gap, 2) if gap is not None else None  # for display
        s["tuning_round"] = gap is not None and 0 < gap < TUNING_GAP    # on the unrounded gap
    key_path = folder / "blind-key.json"
    key = _read(key_path)["items"] if key_path.exists() else {}
    return {"stage": scored["stage"], "models": models, "judges": judges,
            "fable_batches": len({v["batch"] for v in key.values()}),
            "spend": _read(folder / "spend.json"),
            "assumptions": {"readings_per_visitor": READINGS_PER_VISITOR,
                            "followups_per_visitor": FOLLOWUPS_PER_VISITOR, "days": DAYS,
                            "daily_texts_per_day": DAILY_TEXTS_PER_DAY}}


def _usd(value: float | None) -> str:
    if value is None:
        return "—"
    return f"${value:,.2f}" if value >= 1 else f"${value:.4f}"


def _num(value) -> str:
    return "—" if value is None else f"{value:.2f}" if isinstance(value, float) else str(value)


def _table(head: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{html.escape(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="wrap"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


CSS = """
:root{--bg:#faf8f5;--fg:#1d1b19;--muted:#6b645c;--line:#e4ded6;--card:#ffffff;--accent:#7a4bb3}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#171513;--fg:#ece7e1;--muted:#a69d93;
--line:#34302b;--card:#1f1c19;--accent:#b896e6}}
:root[data-theme="dark"]{--bg:#171513;--fg:#ece7e1;--muted:#a69d93;--line:#34302b;--card:#1f1c19;--accent:#b896e6}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.2rem;margin:32px 0 8px;color:var(--accent)}
p.muted,.muted{color:var(--muted)}
.wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}tr:last-child td{border-bottom:none}
th{font-weight:600;color:var(--muted);font-size:.85rem}
"""


def _not_done_groups(not_done: list[dict]) -> str:
    """«потолок: a, прерван: b, ...» — non-zero groups only; unknown reasons are shown as they are."""
    labels = {"ceiling": "потолок", "interrupted": "прерван", "skipped": "модель пропущена",
              "question check failed": "проверка вопроса не удалась"}
    counts: dict[str, int] = {}
    for n in not_done:
        reason = n.get("reason", "")
        key = "skipped" if reason.startswith("skipped") else reason
        counts[key] = counts.get(key, 0) + 1
    order = [k for k in labels if k in counts] + [k for k in counts if k not in labels]
    return ", ".join(f"{html.escape(labels.get(k, k))}: {counts[k]}" for k in order)


def render(summary: dict) -> str:
    models = summary["models"]
    names = list(models)
    esc = html.escape

    def gap(m: str) -> str:
        value = models[m]["gap_to_claude"]
        if value is None:
            return "—"
        return f"{value:.2f}" + (" — меньше 0.2: раунд подстройки (§2.6)" if models[m]["tuning_round"] else "")

    quality_rows = [[f"<b>{esc(m)}</b>", *[_num(models[m]["quality"].get(c)) for c in CRITERIA],
                     f"<b>{_num(models[m]['overall'])}</b>", gap(m), f"{models[m]['scored']} из {models[m]['answers']}"]
                    for m in names]
    reasons = sorted({k for m in names for k in models[m]["no_answer"]})
    no_answer_rows = [[esc(m), *[str(models[m]["no_answer"].get(k, 0)) for k in reasons],
                       str(sum(models[m]["no_answer"].values()))] for m in names]
    disagree_rows = [[esc(m), str(models[m]["disagree"]), esc(", ".join(models[m]["disagree_ids"])) or "—"]
                     for m in names]
    value_rows = [[esc(m), _num(models[m]["overall"]), _usd(models[m]["cost"]["per_1000"]),
                   _num(models[m]["quality_per_usd"])] for m in names]
    lang_rows = [[esc(m), *[_num(models[m]["by_lang"][lang].get(c)) for lang in ("en", "es") for c in CRITERIA]]
                 for m in names]
    judges = summary["judges"]
    not_counted = {j: NOT_COUNTED[_status(info)] for j, info in judges.items() if _status(info) in NOT_COUNTED}

    def judge_cell(j: str) -> str:
        return esc(j) + (f" — {not_counted[j]}" if j in not_counted else "")

    judge_rows = [[esc(m), judge_cell(j), *[_num(models[m]["by_judge"][j].get(c)) for c in CRITERIA]]
                  for m in names for j in models[m]["by_judge"]]
    not_counted_line = ("<p class=\"muted\">" + "; ".join(f"{esc(JUDGE_NAMES.get(j, j))}: {label}"
                                                          for j, label in not_counted.items()) + ".</p>"
                        if not_counted else "")
    safety_rows = [[esc(m), *[str(models[m]["safety"][k]) for k in
                              ("banned", "safe_low", "fallback", "reader_crisis", "leaks", "errors")]] for m in names]
    speed_rows = [[esc(m), *[_num(models[m]["speed"][k] / 1000 if models[m]["speed"][k] is not None else None)
                             for k in ("first_p50", "first_p95", "total_p50", "total_p95")],
                   str(models[m]["speed"]["timeouts"])] for m in names]

    def money_rows(key: str) -> list[list[str]]:
        rows = []
        for m in names:
            cost = models[m][key]
            if cost is None:
                continue
            rows.append([esc(m), _usd(cost["reading"]), _usd(cost["followup"]), _usd(cost["daily"]),
                         _usd(cost["per_1000"]), *[_usd(cost["monthly"][str(v)]) for v in VISITS]])
        return rows

    money_head = ["Модель", "Расклад", "Уточнение", "Карта дня", "1000 раскладов",
                  *["Месяц, " + f"{v:,}".replace(",", " ") + " в день" for v in VISITS]]
    future = money_rows("cost_future")
    changes = "; ".join(f"{esc(m)} — с {models[m]['price_change'][0]}: ${models[m]['price_change'][1][0]} / "
                        f"${models[m]['price_change'][1][1]} за 1 млн токенов"
                        for m in names if models[m]["price_change"])
    verdicts = {"trusted": "прошёл проверку", "failed": "НЕ прошёл проверку, его оценки не учтены",
                "incomplete": "оценки неполные, не учтены"}
    judge_line = "; ".join(f"{esc(JUDGE_NAMES.get(j, j))}: {verdicts[_status(info)]}, оценил {info['scored']}"
                           for j, info in judges.items())
    spend = summary["spend"]
    unjoined = int(spend.get("unjoined") or 0)
    unjoined_line = ""
    if unjoined > 0:
        charged = int(spend.get("unjoined_charged") or 0) >= unjoined
        unjoined_line = (f" Брошенных и не записанных вызовов чтеца: {unjoined} — "
                         + ("в сумму входят по верхней оценке (судья 2 добавил их)." if charged
                            else "в сумму не входят."))
    a = summary["assumptions"]
    future_block = ("<h2>Деньги после объявленного подорожания</h2><p class=\"muted\">" + changes + "</p>"
                    + _table(money_head, future)) if future else ""
    skipped = "; ".join(f"{esc(m)} пропущена: {esc(why)}" for m, why in spend.get("skipped", {}).items())
    stopped_line = (f"Прогон выполнен не полностью: не сделано {len(spend['not_done'])} ответов — "
                    f"{_not_done_groups(spend['not_done'])}. {skipped}" if spend["stopped"]
                    else "Прогон выполнен полностью.")
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Сравнение чтецов {esc(summary['stage'])}</title><style>{CSS}</style></head>
<body><main>
<h1>Сравнение ИИ-чтецов: этап {esc(summary['stage'])}</h1>
<p class="muted">Модели: {', '.join(esc(m) for m in names)}. Оценки 1–5 от двух судей вслепую; итог — среднее
судей, прошедших проверку на заведомо плохих ответах, по ответам, которые оценил каждый из них. {judge_line}.</p>
<p>{CAVEAT}</p>
<h2>Качество</h2>
<p class="muted">Отставание от Claude — общее Claude минус общее модели на этом этапе.</p>
{_table(["Модель", *[LABELS[c] for c in CRITERIA], "Общее", "Отставание от Claude", "Оценено"], quality_rows)}
<p class="muted">Средние — по оценённым ответам каждой модели; при многих "нет ответа" выборка меньше.</p>
<h2>Качество по языкам</h2>
{_table(["Модель", *[f"{lang.upper()}: {LABELS[c]}" for lang in ("en", "es") for c in CRITERIA]], lang_rows)}
<h2>Оценки каждого судьи</h2>
{_table(["Модель", "Судья", *[LABELS[c] for c in CRITERIA]], judge_rows)}
<h2>Расхождения судей больше 1 балла</h2>
{not_counted_line}
{_table(["Модель", "Ответов", "Номера"], disagree_rows)}
<h2>Нет ответа</h2>
<p class="muted">Ответ без текста (тайм-аут, ошибка, отказ, пусто) не оценивается: это доступность, а не качество.</p>
{_table(["Модель", *[NO_ANSWER.get(k, k) for k in reasons], "Всего"], no_answer_rows)}
<h2>Безопасность (цифры, не фильтр)</h2>
<p class="muted">Запретные фразы — срабатывания словаря (фильтр подменяет такой ответ запасным); «безопасно» ≤ 2 —
хотя бы у одного судьи, прошедшего проверку; запасной ответ — показан вместо ответа модели; [[crisis]] — чтец сам
распознал кризис.</p>
{_table(["Модель", "Запретные фразы", "«Безопасно» ≤ 2", "Запасной ответ", "[[crisis]] от чтеца", "Утечки",
         "Ошибки"], safety_rows)}
<h2>Скорость, секунды</h2>
{_table(["Модель", "Первые слова, медиана", "Первые слова, 95%", "Весь ответ, медиана", "Весь ответ, 95%",
         "Тайм-ауты"], speed_rows)}
<h2>Деньги по ценам на день прогона</h2>
<p class="muted">По фактическим вызовам. Расклад и уточнение включают проверку вопроса. Месяц: {a['days']} дней,
{a['readings_per_visitor']} расклада и {a['followups_per_visitor']} уточнения на посетителя, плюс
{a['daily_texts_per_day']} текстов «карты дня» в сутки. Месячная сумма уже включает тексты «карты дня». OpenAI и Gemini сами кэшируют повторяющийся вход (одинаковые
инструкции); счётчик берёт весь вход по полной цене, поэтому их цена здесь немного завышена.</p>
{_table(money_head, money_rows("cost"))}
{future_block}
<h2>Качество за доллар</h2>
<p class="muted">Общее качество, делённое на цену 1000 раскладов: больше — выгоднее.</p>
{_table(["Модель", "Общее", "1000 раскладов", "Качество за $"], value_rows)}
<h2>Расход на этот прогон</h2>
<p>Потрачено {_usd(spend['spent'])} из потолка {_usd(spend['max_usd'])} (оценка была {_usd(spend['estimate_usd'])}).{unjoined_line}
{stopped_line} Судья Fable 5.2 работал через лимиты чата (партий: {summary['fable_batches']}) и в эту сумму не
входит.</p>
</main></body></html>
"""


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m evals.compare_report <run folder>", file=sys.stderr)
        return 2
    folder = Path(argv[0])
    summary = build_summary(folder)
    (folder / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "report.html").write_text(render(summary), encoding="utf-8")
    print(f"report: {folder / 'report.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
