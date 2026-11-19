"""Spend meter and wrappers for the reader model comparison (spec 2026-11-19 §6–§7).

MeteredProvider records every call (model, purpose, eval item, tokens, cost, timing) into a Meter and refuses a new
call once the meter's ceiling is reached (BudgetExceeded, counted in Meter.refused). The record is written in
`finally`, with the eval item taken when the call started: a stream that the engine gives up on (first-token or
idle timeout) is closed later from its worker thread and is still recorded, as "abandoned". A failed call without
usage costs its upper bound (max_tokens of output, like flow.upper_cost), so the ceiling errs on the safe side.
With a sink, every record is appended to calls.jsonl at once, so a killed run keeps what it paid for.
CachingGuard runs the question check for every question once, before any reader call (prefill), and then serves
all models from that cache. RecordingJudge stands in for the judge while answers are generated: it keeps the
judge's input; the scores come later from the two judges (compare_judges.py).
"""
import json
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import cost_usd
from app.reader.errors import ProviderError, StreamResult
from evals.judge import CRITERIA

NOT_CACHED = ("timeout", "error")  # guard sources that are not a real answer: asked again by prefill
ABANDONED = "abandoned"            # the caller stopped reading the stream before it ended


class BudgetExceeded(Exception):
    """The ceiling (--max-usd) is reached: no new paid call is made."""


@dataclass(frozen=True)
class CallRecord:
    model: str
    purpose: str          # "reader" | "followup" | "daily" | "guard" | "judge" | "json"
    item: str | None      # the eval item (or blind judge id) the call belongs to
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float
    ms_first: int | None
    ms_total: int
    error: str | None = None


class Meter:
    def __init__(self, max_usd: float, spent: float = 0.0, sink: Path | None = None):
        self.max_usd = max_usd
        self.spent = spent
        self.sink = Path(sink) if sink is not None else None
        self.calls: list[CallRecord] = []
        self.item: str | None = None
        self.refused = 0
        self._lock = threading.Lock()

    @property
    def exhausted(self) -> bool:
        return self.spent >= self.max_usd

    def check(self) -> None:
        if self.exhausted:
            with self._lock:
                self.refused += 1
            raise BudgetExceeded(f"spent ${self.spent:.4f} of ${self.max_usd:.2f}")

    def add(self, model: str, purpose: str, result: StreamResult | None, ms_first: int | None, ms_total: int,
            error: str | None = None, item: str | None = None, max_tokens: int | None = None) -> CallRecord:
        tokens_in = result.tokens_in if result else None
        tokens_out = result.tokens_out if result else None
        cost = cost_usd(model, tokens_in, tokens_out)
        if cost is None and error and max_tokens:
            cost = cost_usd(model, 0, max_tokens)  # no usage: the call may have been billed up to max_tokens
        record = CallRecord(model, purpose, item if item is not None else self.item, tokens_in, tokens_out,
                            cost or 0.0, ms_first, ms_total, error)
        with self._lock:
            self.calls.append(record)
            self.spent = round(self.spent + record.cost_usd, 6)
            if self.sink is not None:
                with self.sink.open("a", encoding="utf-8") as sink:
                    sink.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        return record

    def records(self) -> list[dict]:
        return [asdict(call) for call in self.calls]


def purpose_of(messages: list[dict]) -> str:
    """The reader's three uses, told apart by their input (compose.py): a follow-up has earlier turns, the card of
    the day starts with <daily, everything else is a reading."""
    if len(messages) > 1:
        return "followup"
    return "daily" if str(messages[0]["content"]).startswith("<daily") else "reader"


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


class MeteredProvider:
    def __init__(self, inner, meter: Meter, purpose: str | None = None):
        self.inner = inner
        self.meter = meter
        self.purpose = purpose
        self.model = inner.model

    def stream(self, system: str, messages: list[dict], max_tokens: int):
        self.meter.check()
        purpose = self.purpose or purpose_of(messages)
        item = self.meter.item
        started, first, result, error = time.monotonic(), None, None, ABANDONED
        try:
            for piece in self.inner.stream(system, messages, max_tokens):
                if isinstance(piece, StreamResult):
                    result = piece
                elif first is None:
                    first = _ms(started)
                yield piece
            error = None
        except ProviderError as exc:
            result, error = exc.result, type(exc).__name__
            raise
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:  # also on GeneratorExit: the engine stopped reading (timeout), the call was still made
            self.meter.add(self.model, purpose, result, first, _ms(started), error, item=item,
                           max_tokens=max_tokens)

    def complete_json(self, system: str, messages: list[dict], schema: dict, max_tokens: int):
        self.meter.check()
        purpose = self.purpose or "json"
        item = self.meter.item
        started, result, error = time.monotonic(), None, ABANDONED
        try:
            data, result = self.inner.complete_json(system, messages, schema, max_tokens)
            error = None
            return data, result
        except ProviderError as exc:
            result, error = exc.result, type(exc).__name__
            raise
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            self.meter.add(self.model, purpose, result, None, _ms(started), error, item=item, max_tokens=max_tokens)


class CachingGuard:
    """The question check runs once per question, before any reader call, so every model gets the same group
    (spec §5): prefill() asks each distinct question, retrying a timeout or an error, and returns the questions
    that still have no real answer (the run must stop then). classify() serves from the cache; a question that is
    unexpectedly missing is asked then."""

    def __init__(self, guard):
        self.guard = guard
        self.cache: dict[str, object] = {}

    def prefill(self, questions, attempts: int = 3) -> list[str]:
        failed = []
        for question in dict.fromkeys(questions):
            for _ in range(attempts):
                verdict = self.guard.classify(question)
                if getattr(verdict, "source", None) not in NOT_CACHED:
                    self.cache[question] = verdict
                    break
            else:
                failed.append(question)
        return failed

    def classify(self, question: str):
        if question in self.cache:
            return self.cache[question]
        verdict = self.guard.classify(question)
        if getattr(verdict, "source", None) not in NOT_CACHED:
            self.cache[question] = verdict
        return verdict


class RecordingJudge:
    """Stands in for the judge while answers are generated (spec §7): keeps the judge's input, returns zeros that
    the runner replaces with the input itself."""

    model = "pending-judge"

    def __init__(self):
        self.contents: list[str] = []

    def complete_json(self, system: str, messages: list[dict], schema: dict, max_tokens: int):
        self.contents.append(messages[0]["content"])
        return {**{c: 0 for c in CRITERIA}, "note": "pending"}, StreamResult(None, None, "end_turn", self.model)

    def take(self) -> str | None:
        content = self.contents[-1] if self.contents else None
        self.contents.clear()
        return content
