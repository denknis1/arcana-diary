"""Reader provider interface (§2.7) and a fake for tests and keyless local runs."""
import re
import threading
import time
from dataclasses import dataclass
from typing import Iterator, Protocol

from app.reader.errors import ProviderError, ProviderRefusal, ProviderTimeout, StreamResult

__all__ = ["Provider", "FakeProvider", "FakeReply", "ProviderError", "ProviderRefusal", "ProviderTimeout",
           "StreamResult", "canned_answer", "canned_text", "split_chunks"]


class Provider(Protocol):
    model: str

    def stream(self, system: str, messages: list[dict], max_tokens: int) -> Iterator[str | StreamResult]:
        """Text chunks, then exactly one StreamResult as the last item."""
        ...

    def complete_json(self, system: str, messages: list[dict], schema: dict,
                      max_tokens: int) -> tuple[dict, StreamResult]:
        """One structured-output call: the parsed JSON object and its usage."""
        ...


def canned_answer(n_cards: int, why: bool) -> str:
    lines = ["[[headline]]", "The cards may point to a quiet, steady way forward."]
    for i in range(1, n_cards + 1):
        lines += [f"[[card {i}]]", f"Card {i} can suggest a moment to slow down and notice what matters to you. "
                  "It may be worth asking which small choice feels most like your own."]
    if n_cards == 3:
        lines += ["[[synthesis]]", "Together the cards can describe a path from effort toward calmer ground."]
    lines += ["[[step]]", "Write down one small thing you can do this week, then do it."]
    if why:
        lines += ["[[why]]", "The card shows open hands and a clear road, a sign of easy movement."]
    return "\n".join(lines) + "\n"


def canned_text() -> str:
    return ("This card may point to a calm moment for checking in with yourself. It can suggest that one honest, "
            "small step matters more than a big plan. Try writing one sentence about what you want today and keep "
            "it where you can see it.")


def split_chunks(text: str, size: int = 12) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


def _canned_for(messages: list[dict]) -> str:
    first = messages[0]["content"] if messages else ""
    if len(messages) > 1 or first.startswith("<daily"):
        return canned_text()  # a follow-up or the card of the day: plain text
    match = re.search(r'<cards count="(\d)"', first)
    return canned_answer(int(match.group(1)) if match else 1, "<verdict" in first)


@dataclass
class FakeReply:
    chunks: list[str] | None = None  # None: a canned answer that fits the request
    first_delay: float = 0.0
    fail_after: int | None = None    # raise ProviderError before the chunk with this index
    refuse: bool = False
    stop_reason: str = "end_turn"    # "max_tokens": the answer was cut by the token limit
    chunk_delay: float = 0.0         # seconds before each chunk after the first
    tokens_in: int = 120
    tokens_out: int = 80


class FakeProvider:
    """No network. Stream replies are taken from .replies in order; when empty, a canned answer is used."""

    def __init__(self, model: str = "fake-reader", replies: list[FakeReply] | None = None,
                 json_replies: list | None = None, json_default: dict | None = None, json_delay: float = 0.0):
        self.model = model
        self.replies = list(replies or [])
        self.json_replies = list(json_replies or [])
        self.json_default = json_default if json_default is not None else {"group": "ok", "violence": False}
        self.json_delay = json_delay
        self.calls: list[dict] = []
        self._lock = threading.Lock()

    def stream(self, system, messages, max_tokens):
        with self._lock:
            self.calls.append({"kind": "stream", "system": system, "messages": messages, "max_tokens": max_tokens})
            reply = self.replies.pop(0) if self.replies else FakeReply()
        chunks = reply.chunks if reply.chunks is not None else split_chunks(_canned_for(messages))
        if reply.first_delay:
            time.sleep(reply.first_delay)
        for i, chunk in enumerate(chunks):
            if reply.fail_after == i:
                raise ProviderError("fake stream cut")
            if i and reply.chunk_delay:
                time.sleep(reply.chunk_delay)
            yield chunk
        if reply.fail_after is not None and reply.fail_after >= len(chunks):
            raise ProviderError("fake stream cut")
        result = StreamResult(reply.tokens_in, reply.tokens_out, "refusal" if reply.refuse else reply.stop_reason,
                              self.model, "general_harms" if reply.refuse else None)
        if reply.refuse:
            raise ProviderRefusal(result)
        yield result

    def complete_json(self, system, messages, schema, max_tokens):
        with self._lock:
            self.calls.append({"kind": "json", "system": system, "messages": messages, "schema": schema,
                               "max_tokens": max_tokens})
            reply = self.json_replies.pop(0) if self.json_replies else self.json_default
        if self.json_delay:
            time.sleep(self.json_delay)
        if isinstance(reply, Exception):
            raise reply
        return reply, StreamResult(60, 8, "end_turn", self.model)

    def stream_calls(self) -> list[dict]:
        return [c for c in self.calls if c["kind"] == "stream"]

    def json_calls(self) -> list[dict]:
        return [c for c in self.calls if c["kind"] == "json"]
