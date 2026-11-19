"""Streaming parser of section markers (§2.2). A marker starts a line: [[headline]], [[card 1]] … [[why]], and
[[crisis]] — the reader's safety net (§8.6). Markdown decoration around it (**, ##) is ignored, and text may follow
the marker on the same line. The exception is [[crisis]]: it is recognised anywhere in the text (inline, split
across chunks), and its characters are never emitted as text.

Text is emitted as soon as it cannot be the start of a marker; a line that already started as text never becomes
a marker. Text before the first marker goes to "headline".
"""
import re
from dataclasses import dataclass

SECTION_ORDER = ("headline", "card1", "card2", "card3", "synthesis", "step", "why")
_NAMES = r"(headline|card\s*[123]|synthesis|step|why|crisis)"
_MARKER = re.compile(r"^\s*[#*_]*\s*\[\[\s*" + _NAMES + r"\s*\]\][*_]*[ \t]*(.*)$", re.IGNORECASE | re.DOTALL)
_PARTIAL = re.compile(r"^\s*[#*_]*\s*(\[(\[[a-z0-9 ]*(\](\][*_ \t\r]*)?)?)?)?$", re.IGNORECASE)
_CRISIS = re.compile(r"\[\[\s*crisis\s*\]\]", re.IGNORECASE)
# a suffix that may still grow into [[crisis]]: held back until the next chunk
_CRISIS_PARTIAL = re.compile(r"\[(?:\[[ \t\r]*(?:c(?:r(?:i(?:s(?:i(?:s[ \t\r]*\]?)?)?)?)?)?)?)?\Z", re.IGNORECASE)


@dataclass(frozen=True)
class Event:
    kind: str  # "section" | "text"
    name: str
    text: str = ""


def required_sections(kind: str, with_why: bool) -> list[str]:
    """with_why: the reading has a verdict (yes/no, and not a redirect_topic / redirect_person question)."""
    n = 3 if kind == "three" else 1
    names = ["headline"] + [f"card{i}" for i in range(1, n + 1)]
    if n == 3:
        names.append("synthesis")
    names.append("step")
    if with_why:
        names.append("why")
    return names


class SectionParser:
    def __init__(self):
        self.current: str | None = None
        self.seen: list[str] = []  # section names in the order they started
        self._parts: dict[str, list[str]] = {}
        self._buf = ""
        self._line_started = False  # part of the current line was already emitted as text
        self._tail = ""  # a possible start of an inline [[crisis]] held back from the text

    def feed(self, chunk: str) -> list[Event]:
        self._buf += chunk
        events: list[Event] = []
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            events += self._line(line + "\n")
        if self._buf and not self._line_started:
            match = _MARKER.match(self._buf)
            if match and match.group(2).strip():
                events += self._start(match.group(1)) + self._text(match.group(2))
                self._buf, self._line_started = "", True
            elif not _PARTIAL.match(self._buf):
                events += self._text(self._buf)
                self._buf, self._line_started = "", True
        elif self._buf:
            events += self._text(self._buf)
            self._buf = ""
        return events

    def finish(self) -> list[Event]:
        events = self._line(self._buf) if self._buf else []
        self._buf = ""
        tail, self._tail = self._tail, ""
        return events + self._emit(tail)

    def sections(self) -> dict[str, str]:
        out = {}
        for name, parts in self._parts.items():
            text = "".join(parts).strip()
            if text:
                out[name] = text
        return out

    def _start(self, raw_name: str) -> list[Event]:
        self.current = re.sub(r"\s+", "", raw_name.lower())
        self._parts.setdefault(self.current, [])
        self.seen.append(self.current)
        return [Event("section", self.current)]

    def _line(self, line: str) -> list[Event]:
        started, self._line_started = self._line_started, False
        match = None if started else _MARKER.match(line)
        if match:
            rest = match.group(2)
            return self._start(match.group(1)) + (self._text(rest) if rest.strip() else [])
        return self._text(line)

    def _text(self, text: str) -> list[Event]:
        """Text with the crisis marker taken out wherever it is; a possible start of it waits for the next chunk."""
        text = self._tail + text
        self._tail = ""
        events: list[Event] = []
        while (match := _CRISIS.search(text)):
            events += self._emit(text[:match.start()]) + self._start("crisis")
            text = text[match.end():]
        partial = _CRISIS_PARTIAL.search(text)
        if partial:
            self._tail, text = partial.group(0), text[:partial.start()]
        return events + self._emit(text)

    def _emit(self, text: str) -> list[Event]:
        if not text:
            return []
        events = []
        if self.current is None:
            if not text.strip():
                return []
            events += self._start("headline")
        self._parts[self.current].append(text)
        events.append(Event("text", self.current, text))
        return events
