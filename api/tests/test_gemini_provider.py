from types import SimpleNamespace

import httpx2
import pytest
from google.genai import types

from app.reader.gemini_provider import GeminiProvider
from app.reader.provider import ProviderError, ProviderRefusal, ProviderTimeout, StreamResult

SYSTEM = "You are the reader."
MSGS = [{"role": "user", "content": "<reading/>"}, {"role": "assistant", "content": "first"},
        {"role": "user", "content": "<followup/>"}]
SCHEMA = {"type": "object", "properties": {"group": {"type": "string"}}, "required": ["group"]}
USAGE = SimpleNamespace(prompt_token_count=30, candidates_token_count=12, thoughts_token_count=8)


def chunk(text=None, finish=None, usage=None, blocked=None, thought=False):
    parts = [SimpleNamespace(text=text, thought=thought)] if text is not None else []
    candidate = SimpleNamespace(content=SimpleNamespace(parts=parts), finish_reason=finish)
    return SimpleNamespace(candidates=[candidate], usage_metadata=usage,
                           prompt_feedback=SimpleNamespace(block_reason=blocked) if blocked else None)


class FakeModels:
    def __init__(self, chunks=None, response=None, error=None):
        self.chunks, self.response, self.error = chunks or [], response, error
        self.calls = []

    def generate_content_stream(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return iter(self.chunks)

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def provider(models, **kwargs):
    return GeminiProvider("key", "gemini-3.8-flash", client=SimpleNamespace(models=models), **kwargs)


def test_stream_yields_text_then_result_with_thinking_billed_as_output():
    models = FakeModels(chunks=[chunk("Hel"), chunk("lo"), chunk(finish="STOP", usage=USAGE)])
    items = list(provider(models, effort="medium").stream(SYSTEM, MSGS, 500))
    assert items == ["Hel", "lo", StreamResult(30, 20, "end_turn", "gemini-3.8-flash")]
    call = models.calls[0]
    assert call["model"] == "gemini-3.8-flash"
    assert call["contents"] == [{"role": "user", "parts": [{"text": "<reading/>"}]},
                                {"role": "model", "parts": [{"text": "first"}]},
                                {"role": "user", "parts": [{"text": "<followup/>"}]}]
    config = call["config"]
    assert config.system_instruction == SYSTEM and config.max_output_tokens == 500
    assert config.thinking_config.thinking_level == types.ThinkingLevel.MEDIUM


def test_thought_parts_are_not_shown():
    models = FakeModels(chunks=[chunk("plan...", thought=True), chunk("Hi"), chunk(finish="STOP", usage=USAGE)])
    assert list(provider(models).stream(SYSTEM, MSGS, 100))[:-1] == ["Hi"]


@pytest.mark.parametrize("effort, level", [("low", types.ThinkingLevel.LOW), ("high", types.ThinkingLevel.HIGH),
                                           ("xhigh", types.ThinkingLevel.HIGH), ("max", types.ThinkingLevel.HIGH)])
def test_effort_maps_to_thinking_level(effort, level):
    models = FakeModels(chunks=[chunk(finish="STOP", usage=USAGE)])
    list(provider(models, effort=effort).stream(SYSTEM, MSGS, 100))
    assert models.calls[0]["config"].thinking_config.thinking_level == level


def test_no_effort_sends_no_thinking_config():
    models = FakeModels(chunks=[chunk(finish="STOP", usage=USAGE)])
    list(provider(models).stream(SYSTEM, MSGS, 100))
    assert models.calls[0]["config"].thinking_config is None


def test_cut_by_token_limit_is_a_result_not_an_error():
    models = FakeModels(chunks=[chunk("Hel"), chunk(finish=types.FinishReason.MAX_TOKENS, usage=USAGE)])
    assert list(provider(models).stream(SYSTEM, MSGS, 100))[-1].stop_reason == "max_tokens"


@pytest.mark.parametrize("last, category", [
    (chunk(finish=types.FinishReason.SAFETY, usage=USAGE), "safety"),
    (chunk(finish="PROHIBITED_CONTENT", usage=USAGE), "prohibited_content"),
    (chunk(blocked=types.BlockedReason.JAILBREAK, usage=USAGE), "jailbreak"),
])
def test_safety_stops_and_blocked_prompts_are_refusals(last, category):
    with pytest.raises(ProviderRefusal) as exc:
        list(provider(FakeModels(chunks=[last])).stream(SYSTEM, MSGS, 100))
    assert exc.value.result == StreamResult(30, 20, "refusal", "gemini-3.8-flash", category)


def test_timeout_and_other_errors():
    with pytest.raises(ProviderTimeout):
        list(provider(FakeModels(error=httpx2.ReadTimeout("slow"))).stream(SYSTEM, MSGS, 100))
    with pytest.raises(ProviderError) as exc:
        list(provider(FakeModels(error=RuntimeError("boom"))).stream(SYSTEM, MSGS, 100))
    assert not isinstance(exc.value, ProviderTimeout)


def test_complete_json_parses_and_asks_for_json():
    models = FakeModels(response=chunk('{"group": "ok"}', finish="STOP", usage=USAGE))
    data, result = provider(models).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
    assert data == {"group": "ok"} and result == StreamResult(30, 20, "end_turn", "gemini-3.8-flash")
    config = models.calls[0]["config"]
    assert config.response_mime_type == "application/json" and config.response_json_schema == SCHEMA
    assert config.http_options.timeout == 3000 and config.thinking_config.thinking_level == types.ThinkingLevel.LOW


def test_complete_json_without_effort_and_with_long_timeout():
    models = FakeModels(response=chunk('{"group": "ok"}', finish="STOP", usage=USAGE))
    provider(models, json_timeout_s=120.0, json_effort=None).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
    config = models.calls[0]["config"]
    assert config.http_options.timeout == 120000 and config.thinking_config is None


def test_complete_json_failures():
    with pytest.raises(ProviderError) as exc:
        provider(FakeModels(response=chunk('{"gr', finish="MAX_TOKENS", usage=USAGE))).complete_json(
            SYSTEM, MSGS[:1], SCHEMA, 64)
    assert exc.value.result is not None
    with pytest.raises(ProviderError):
        provider(FakeModels(response=chunk("not json", finish="STOP", usage=USAGE))).complete_json(
            SYSTEM, MSGS[:1], SCHEMA, 64)
    with pytest.raises(ProviderError):
        provider(FakeModels(response=chunk(finish="STOP", usage=USAGE))).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
    with pytest.raises(ProviderRefusal):
        provider(FakeModels(response=chunk(finish="SAFETY", usage=USAGE))).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
    with pytest.raises(ProviderTimeout):
        provider(FakeModels(error=httpx2.ReadTimeout("slow"))).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
