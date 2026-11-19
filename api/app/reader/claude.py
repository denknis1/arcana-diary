"""Claude through the official anthropic SDK (claude-api docs, python: README, streaming.md, tool-use.md →
Structured Outputs; shared/model-migration.md → Migrating to Claude Haiku 5.5).

Haiku 5.5: adaptive thinking is on by default; effort is set explicitly in output_config (reader: READER_EFFORT,
default "medium"; question guard: "low"); temperature, top_p and top_k are never sent. stop_reason == "refusal"
is raised as ProviderRefusal (with stop_details.category) and checked before any content is read.
anthropic.APITimeoutError becomes ProviderTimeout. The SDK runs on httpx2; nothing from httpx is passed to it.
"""
import json

import anthropic

from app.reader.errors import ProviderError, ProviderRefusal, ProviderTimeout, StreamResult


def _category(message) -> str | None:
    details = getattr(message, "stop_details", None)
    return getattr(details, "category", None) if details else None


class ClaudeProvider:
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
            self._client = anthropic.Anthropic(api_key=self._api_key, timeout=self._timeout_s,
                                               max_retries=self._max_retries)
        return self._client

    def _result(self, message) -> StreamResult:
        return StreamResult(message.usage.input_tokens, message.usage.output_tokens, message.stop_reason,
                            self.model, _category(message) if message.stop_reason == "refusal" else None)

    def stream(self, system: str, messages: list[dict], max_tokens: int):
        params = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": messages}
        if self._effort:
            params["output_config"] = {"effort": self._effort}
        try:
            with self.client.messages.stream(**params) as stream:
                for text in stream.text_stream:
                    yield text
                final = stream.get_final_message()
        except anthropic.APITimeoutError as exc:
            raise ProviderTimeout("APITimeoutError") from exc
        except Exception as exc:  # SDK errors (APIStatusError, APIConnectionError, ...)
            raise ProviderError(type(exc).__name__) from exc
        result = self._result(final)
        if final.stop_reason == "refusal":
            raise ProviderRefusal(result)
        yield result

    def complete_json(self, system: str, messages: list[dict], schema: dict, max_tokens: int):
        output_config: dict = {"format": {"type": "json_schema", "schema": schema}}
        if self._json_effort:
            output_config["effort"] = self._json_effort
        try:
            response = self.client.with_options(timeout=self._json_timeout_s, max_retries=0).messages.create(
                model=self.model, max_tokens=max_tokens, system=system, messages=messages,
                output_config=output_config)
        except anthropic.APITimeoutError as exc:
            raise ProviderTimeout("APITimeoutError") from exc
        except Exception as exc:
            raise ProviderError(type(exc).__name__) from exc
        result = self._result(response)
        if response.stop_reason == "refusal":
            raise ProviderRefusal(result)
        if response.stop_reason == "max_tokens":
            raise ProviderError("max_tokens: structured output truncated", result)
        text = next((block.text for block in response.content if block.type == "text"), None)
        if text is None:
            raise ProviderError("no text block", result)
        try:
            return json.loads(text), result
        except ValueError as exc:
            raise ProviderError("invalid JSON", result) from exc
