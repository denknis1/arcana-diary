"""Runs a provider stream in a worker thread so the caller can enforce the first-token timeout (§5.1: 15 s)."""
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Iterator

from app.reader.provider import ProviderRefusal, StreamResult

log = logging.getLogger("arcana.reader")
IDLE_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class Chunk:
    text: str


@dataclass(frozen=True)
class Finished:
    result: StreamResult
    ms_first_token: int | None
    ms_total: int


@dataclass(frozen=True)
class Failed:
    reason: str  # "timeout" | "error" | "refusal"
    after_text: bool
    ms_first_token: int | None
    ms_total: int
    result: StreamResult | None = None


def run_stream(provider, system: str, messages: list[dict], max_tokens: int, first_token_timeout: float,
               idle_timeout: float = IDLE_TIMEOUT_S) -> Iterator[Chunk | Finished | Failed]:
    """Chunk… then exactly one Finished or Failed. A late worker is told to stop and its output is dropped."""
    q: queue.Queue = queue.Queue()
    stop = threading.Event()

    def worker() -> None:
        try:
            for item in provider.stream(system, messages, max_tokens):
                if stop.is_set():
                    return
                q.put(("item", item))
            q.put(("end", None))
        except ProviderRefusal as exc:
            q.put(("refusal", exc.result))
        except Exception as exc:  # any provider failure becomes Failed("error")
            q.put(("error", exc))

    threading.Thread(target=worker, daemon=True, name="reader-stream").start()
    started = time.monotonic()
    first: int | None = None
    result: StreamResult | None = None

    def ms() -> int:
        return int((time.monotonic() - started) * 1000)

    try:
        while True:
            wait = first_token_timeout - (time.monotonic() - started) if first is None else idle_timeout
            try:
                kind, item = q.get(timeout=max(wait, 0.001))
            except queue.Empty:
                log.warning("reader stream timeout (%s)", "first token" if first is None else "idle")
                yield Failed("timeout", first is not None, first, ms())
                return
            if kind == "item":
                if isinstance(item, StreamResult):
                    result = item
                elif item:
                    if first is None:
                        first = ms()
                    yield Chunk(item)
            elif kind == "end":
                yield Finished(result or StreamResult(None, None, None, getattr(provider, "model", "")), first, ms())
                return
            elif kind == "refusal":
                yield Failed("refusal", first is not None, first, ms(), item)
                return
            else:
                log.warning("reader stream failed: %s", type(item).__name__)
                yield Failed("error", first is not None, first, ms(), result)
                return
    finally:
        stop.set()
