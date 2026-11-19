"""Gemini through the official google-genai SDK 2.34.0 (spec 2026-11-19 §4).

stream(): client.models.generate_content_stream(model, contents, config) yields chunks; their text parts (not the
"thought" parts) are the answer; the last chunk with usage_metadata carries the totals. Billed output =
candidates_token_count + thoughts_token_count (thinking is billed as output). Effort -> ThinkingConfig.thinking_level:
low -> LOW, medium -> MEDIUM, high/xhigh/max -> HIGH; no effort -> no thinking config (the model's default).
Finish reasons: STOP -> stop_reason "end_turn"; MAX_TOKENS -> "max_tokens"; a blocked prompt
(prompt_feedback.block_reason) or a refusing finish (SAFETY, PROHIBITED_CONTENT, BLOCKLIST, SPII, RECITATION,
LANGUAGE) -> ProviderRefusal (category = the reason, lower-case); any other finish reason, or none at all (a dropped
stream), -> ProviderError(result) after the text: a cut answer is never taken as complete. The SDK does not retry
by default. An httpx2/httpx
TimeoutException -> ProviderTimeout; any other error -> ProviderError. HttpOptions.timeout is in milliseconds.
The client is created lazily, so building the provider makes no network call.
"""
import json

import httpx
import httpx2
from google import genai
from google.genai import types

from app.reader.errors import ProviderError, ProviderRefusal, ProviderTimeout, StreamResult

_LEVELS = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH", "xhigh": "HIGH", "max": "HIGH"}
_REFUSALS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "LANGUAGE"}
_STOPS = {"STOP": "end_turn", "MAX_TOKENS": "max_tokens"}
_TIMEOUTS = (httpx2.TimeoutException, httpx.TimeoutException)


def _name(value) -> str | None:
    """An SDK enum or a plain string -> its name ("SAFETY")."""
    if value is None:
        return None
    return getattr(value, "value", value)


def _contents(messages: list[dict]) -> list[dict]:
    return [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages]


def _text(chunk) -> str:
    candidates = getattr(chunk, "candidates", None) or []
    content = getattr(candidates[0], "content", None) if candidates else None
    return "".join(p.text for p in (getattr(content, "parts", None) or [])
                   if getattr(p, "text", None) and not getattr(p, "thought", False))


def _finish(chunk) -> str | None:
    candidates = getattr(chunk, "candidates", None) or []
    return _name(getattr(candidates[0], "finish_reason", None)) if candidates else None


def _blocked(chunk) -> str | None:
    feedback = getattr(chunk, "prompt_feedback", None)
    return _name(getattr(feedback, "block_reason", None)) if feedback is not None else None


class GeminiProvider:
    def __init__(self, api_key: str, model: str, client=None, timeout_s: float = 60.0, effort: str | None = None,
                 json_timeout_s: float = 3.0, json_effort: str | None = "low"):
        self.model = model
        self._api_key = api_key
        self._client = client
        self._timeout_s = timeout_s
        self._effort = effort
        self._json_timeout_s = json_timeout_s
        self._json_effort = json_effort

    @property
    def client(self):
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key,
                                        http_options=types.HttpOptions(timeout=int(self._timeout_s * 1000)))
        return self._client

    def _config(self, system: str, max_tokens: int, effort: str | None, **extra) -> types.GenerateContentConfig:
        config = {"system_instruction": system, "max_output_tokens": max_tokens, **extra}
        if effort:
            config["thinking_config"] = {"thinking_level": _LEVELS[effort]}
        return types.GenerateContentConfig(**config)

    def _result(self, usage, finish: str | None, blocked: str | None) -> StreamResult:
        tokens_in = getattr(usage, "prompt_token_count", None) if usage is not None else None
        out = getattr(usage, "candidates_token_count", None) if usage is not None else None
        thoughts = (getattr(usage, "thoughts_token_count", None) or 0) if usage is not None else 0
        tokens_out = None if out is None and not thoughts else (out or 0) + thoughts
        refused = blocked is not None or finish in _REFUSALS
        stop = "refusal" if refused else _STOPS.get(finish)  # None: an unknown finish or none at all
        return StreamResult(tokens_in, tokens_out, stop, self.model, (blocked or finish).lower() if refused else None)

    @staticmethod
    def _check(result: StreamResult, finish: str | None) -> None:
        if result.stop_reason == "refusal":
            raise ProviderRefusal(result)
        if result.stop_reason is None:
            raise ProviderError(f"finish reason {finish or 'missing'}: the answer may be cut", result)

    def stream(self, system: str, messages: list[dict], max_tokens: int):
        usage = finish = blocked = None
        try:
            for chunk in self.client.models.generate_content_stream(
                    model=self.model, contents=_contents(messages),
                    config=self._config(system, max_tokens, self._effort)):
                blocked = _blocked(chunk) or blocked
                finish = _finish(chunk) or finish
                if getattr(chunk, "usage_metadata", None) is not None:
                    usage = chunk.usage_metadata
                text = _text(chunk)
                if text:
                    yield text
        except _TIMEOUTS as exc:
            raise ProviderTimeout(type(exc).__name__) from exc
        except Exception as exc:  # SDK errors (APIError, ClientError, ServerError, ...)
            raise ProviderError(type(exc).__name__) from exc
        result = self._result(usage, finish, blocked)
        self._check(result, finish)
        yield result

    def complete_json(self, system: str, messages: list[dict], schema: dict, max_tokens: int):
        config = self._config(system, max_tokens, self._json_effort, response_mime_type="application/json",
                              response_json_schema=schema,
                              http_options=types.HttpOptions(timeout=int(self._json_timeout_s * 1000)))
        try:
            response = self.client.models.generate_content(model=self.model, contents=_contents(messages),
                                                           config=config)
        except _TIMEOUTS as exc:
            raise ProviderTimeout(type(exc).__name__) from exc
        except Exception as exc:
            raise ProviderError(type(exc).__name__) from exc
        finish = _finish(response)
        result = self._result(getattr(response, "usage_metadata", None), finish, _blocked(response))
        self._check(result, finish)
        if result.stop_reason == "max_tokens":
            raise ProviderError("max_tokens: structured output truncated", result)
        text = _text(response)
        if not text:
            raise ProviderError("no text", result)
        try:
            return json.loads(text), result
        except ValueError as exc:
            raise ProviderError("invalid JSON", result) from exc
