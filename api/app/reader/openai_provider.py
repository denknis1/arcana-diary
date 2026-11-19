"""ChatGPT through the official openai SDK 3.46.0, Responses API (spec 2026-11-19 §4).

stream(): client.responses.stream(...) yields events; "response.output_text.delta" carries the text. The stream
ends with one terminal event that carries the whole response (status, usage, output): "response.completed",
"response.incomplete" or "response.failed". It is taken from the loop: the SDK's get_final_response() raises
unless the stream ended with response.completed, which would turn a cut or filtered answer into a plain error and
lose its usage. No terminal event -> ProviderError. Usage: input_tokens / output_tokens (reasoning tokens are part
of output_tokens and billed as output). status "incomplete" with reason "max_output_tokens" -> stop_reason
"max_tokens"; a "refusal" content part or reason "content_filter" -> ProviderRefusal; status "failed" ->
ProviderError with the usage. store=False: OpenAI keeps no copy of the conversation. openai.APITimeoutError ->
ProviderTimeout; any other SDK error -> ProviderError. The client is created lazily, so building the provider makes
no network call.
"""
import json

import openai

from app.reader.errors import ProviderError, ProviderRefusal, ProviderTimeout, StreamResult

TERMINAL_EVENTS = ("response.completed", "response.incomplete", "response.failed")


def _refused(response) -> bool:
    details = getattr(response, "incomplete_details", None)
    if details is not None and getattr(details, "reason", None) == "content_filter":
        return True
    for item in getattr(response, "output", None) or []:
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "refusal":
                return True
    return False


def _stop_reason(response) -> str:
    status = getattr(response, "status", None)
    if status == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
        return "max_tokens" if reason == "max_output_tokens" else (reason or "incomplete")
    return status if status in ("failed", "cancelled") else "end_turn"


class OpenAIProvider:
    def __init__(self, api_key: str, model: str, client=None, timeout_s: float = 60.0, max_retries: int = 1,
                 effort: str | None = None, json_timeout_s: float = 3.0, json_effort: str | None = "low"):
        self.model = model
        self._api_key = api_key
        self._client = client
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._effort = effort
        self._json_timeout_s = json_timeout_s
        self._json_effort = json_effort

    @property
    def client(self):
        if self._client is None:
            self._client = openai.OpenAI(api_key=self._api_key, timeout=self._timeout_s,
                                         max_retries=self._max_retries)
        return self._client

    def _result(self, response) -> StreamResult:
        usage = getattr(response, "usage", None)
        refused = _refused(response)
        return StreamResult(getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None),
                            "refusal" if refused else _stop_reason(response), self.model,
                            "content_filter" if refused else None)

    def _params(self, system: str, messages: list[dict], max_tokens: int, effort: str | None) -> dict:
        params = {"model": self.model, "instructions": system,
                  "input": [{"role": m["role"], "content": m["content"]} for m in messages],
                  "max_output_tokens": max_tokens, "store": False}
        if effort:
            params["reasoning"] = {"effort": effort}
        return params

    def stream(self, system: str, messages: list[dict], max_tokens: int):
        final = None
        try:
            with self.client.responses.stream(**self._params(system, messages, max_tokens, self._effort)) as stream:
                for event in stream:
                    kind = getattr(event, "type", None)
                    if kind == "response.output_text.delta" and event.delta:
                        yield event.delta
                    elif kind in TERMINAL_EVENTS:
                        final = event.response
        except openai.APITimeoutError as exc:
            raise ProviderTimeout("APITimeoutError") from exc
        except Exception as exc:  # SDK errors (APIStatusError, APIConnectionError, ...)
            raise ProviderError(type(exc).__name__) from exc
        if final is None:
            raise ProviderError("stream ended without a terminal event")
        result = self._result(final)
        if result.stop_reason == "refusal":
            raise ProviderRefusal(result)
        if result.stop_reason in ("failed", "cancelled"):
            raise ProviderError(f"response {result.stop_reason}", result)
        yield result

    def complete_json(self, system: str, messages: list[dict], schema: dict, max_tokens: int):
        params = self._params(system, messages, max_tokens, self._json_effort)
        params["text"] = {"format": {"type": "json_schema", "name": "result", "schema": schema, "strict": True}}
        try:
            response = self.client.with_options(timeout=self._json_timeout_s, max_retries=0).responses.create(
                **params)
        except openai.APITimeoutError as exc:
            raise ProviderTimeout("APITimeoutError") from exc
        except Exception as exc:
            raise ProviderError(type(exc).__name__) from exc
        result = self._result(response)
        if result.stop_reason == "refusal":
            raise ProviderRefusal(result)
        if result.stop_reason != "end_turn":
            raise ProviderError(f"{result.stop_reason}: no complete structured output", result)
        text = getattr(response, "output_text", "") or ""
        if not text:
            raise ProviderError("no text", result)
        try:
            return json.loads(text), result
        except ValueError as exc:
            raise ProviderError("invalid JSON", result) from exc
