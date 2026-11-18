from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.reader.claude import ClaudeProvider
from app.reader.provider import ProviderError, ProviderRefusal, ProviderTimeout, StreamResult

SYSTEM = "You are the reader."
MSGS = [{"role": "user", "content": "<reading/>"}]


def message(stop_reason="end_turn", content=None, tokens=(30, 12), category=None):
    details = SimpleNamespace(category=category, explanation="") if stop_reason == "refusal" else None
    return SimpleNamespace(stop_reason=stop_reason, content=content, stop_details=details,
                           usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]))


def sdk_timeout():
    return anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))


class FakeStream:
    def __init__(self, chunks, final):
        self.chunks, self.final = chunks, final

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        return iter(self.chunks)

    def get_final_message(self):
        return self.final


class FakeMessages:
    def __init__(self, stream=None, create=None, error=None):
        self._stream, self._create, self._error = stream, create, error
        self.calls = []

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._stream

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._create


class FakeClient:
    def __init__(self, messages):
        self.messages = messages
        self.options = None

    def with_options(self, **kwargs):
        self.options = kwargs
        return self


def test_stream_yields_text_then_result_with_only_documented_params():
    msgs = FakeMessages(stream=FakeStream(["Hel", "lo"], message()))
    provider = ClaudeProvider("key", "claude-haiku-5-5", client=FakeClient(msgs), effort="medium")
    assert list(provider.stream(SYSTEM, MSGS, 4000)) == ["Hel", "lo", StreamResult(30, 12, "end_turn",
                                                                                   "claude-haiku-5-5")]
    # no temperature / top_p / top_k / thinking: adaptive thinking is the default; effort is explicit
    assert msgs.calls == [{"model": "claude-haiku-5-5", "max_tokens": 4000, "system": SYSTEM, "messages": MSGS,
                           "output_config": {"effort": "medium"}}]


def test_stream_without_effort_sends_no_output_config():
    msgs = FakeMessages(stream=FakeStream(["Hi"], message()))
    list(ClaudeProvider("key", "claude-haiku-5-5", client=FakeClient(msgs)).stream(SYSTEM, MSGS, 100))
    assert "output_config" not in msgs.calls[0]


def test_stream_refusal_is_an_error_with_category():
    msgs = FakeMessages(stream=FakeStream(["Partial"], message(stop_reason="refusal", category="general_harms")))
    gen = ClaudeProvider("key", "claude-haiku-5-5", client=FakeClient(msgs)).stream(SYSTEM, MSGS, 4000)
    assert next(gen) == "Partial"
    with pytest.raises(ProviderRefusal) as info:
        next(gen)
    assert (info.value.result.stop_reason, info.value.result.refusal_category) == ("refusal", "general_harms")


def test_sdk_timeout_becomes_provider_timeout():
    client = FakeClient(FakeMessages(error=sdk_timeout()))
    provider = ClaudeProvider("key", "claude-haiku-5-5", client=client)
    with pytest.raises(ProviderTimeout):
        list(provider.stream(SYSTEM, MSGS, 4000))
    with pytest.raises(ProviderTimeout):
        provider.complete_json(SYSTEM, MSGS, {}, 1024)


def test_sdk_exception_becomes_provider_error():
    client = FakeClient(FakeMessages(error=RuntimeError("APIConnectionError")))
    with pytest.raises(ProviderError):
        list(ClaudeProvider("key", "claude-haiku-5-5", client=client).stream(SYSTEM, MSGS, 4000))


def test_complete_json_reads_the_text_block():
    content = [SimpleNamespace(type="thinking", thinking=""),
               SimpleNamespace(type="text", text='{"group": "redirect_person"}')]
    msgs = FakeMessages(create=message(content=content))
    client = FakeClient(msgs)
    schema = {"type": "object"}
    data, usage = ClaudeProvider("key", "claude-haiku-5-5", client=client).complete_json(SYSTEM, MSGS, schema, 1024)
    assert data == {"group": "redirect_person"}
    assert usage == StreamResult(30, 12, "end_turn", "claude-haiku-5-5")
    assert client.options == {"timeout": 3.0, "max_retries": 0}
    assert msgs.calls == [{"model": "claude-haiku-5-5", "max_tokens": 1024, "system": SYSTEM, "messages": MSGS,
                           "output_config": {"format": {"type": "json_schema", "schema": schema},
                                             "effort": "low"}}]


def test_complete_json_refusal_checked_before_content():
    msgs = FakeMessages(create=message(stop_reason="refusal", content=None))
    with pytest.raises(ProviderRefusal):
        ClaudeProvider("key", "claude-haiku-5-5", client=FakeClient(msgs)).complete_json(SYSTEM, MSGS, {}, 1024)


def test_complete_json_max_tokens_is_an_error():
    msgs = FakeMessages(create=message(stop_reason="max_tokens", content=[SimpleNamespace(type="text", text='{"gr')]))
    with pytest.raises(ProviderError) as info:
        ClaudeProvider("key", "claude-haiku-5-5", client=FakeClient(msgs)).complete_json(SYSTEM, MSGS, {}, 1024)
    assert info.value.result == StreamResult(30, 12, "max_tokens", "claude-haiku-5-5")


def test_complete_json_invalid_json_is_an_error():
    msgs = FakeMessages(create=message(content=[SimpleNamespace(type="text", text="not json")]))
    with pytest.raises(ProviderError) as info:
        ClaudeProvider("key", "claude-haiku-5-5", client=FakeClient(msgs)).complete_json(SYSTEM, MSGS, {}, 1024)
    assert info.value.result == StreamResult(30, 12, "end_turn", "claude-haiku-5-5")


def test_complete_json_without_a_text_block_is_an_error_that_keeps_usage():
    msgs = FakeMessages(create=message(content=[SimpleNamespace(type="thinking", thinking="")]))
    with pytest.raises(ProviderError) as info:
        ClaudeProvider("key", "claude-haiku-5-5", client=FakeClient(msgs)).complete_json(SYSTEM, MSGS, {}, 1024)
    assert info.value.result == StreamResult(30, 12, "end_turn", "claude-haiku-5-5")


def test_judge_style_call_without_effort():
    msgs = FakeMessages(create=message(content=[SimpleNamespace(type="text", text="{}")]))
    client = FakeClient(msgs)
    provider = ClaudeProvider("key", "claude-sonnet-5-5", client=client, json_timeout_s=60.0, json_effort=None)
    provider.complete_json(SYSTEM, MSGS, {"type": "object"}, 2000)
    assert "effort" not in msgs.calls[0]["output_config"] and client.options["timeout"] == 60.0


def test_client_is_created_lazily():
    assert ClaudeProvider("", "claude-haiku-5-5")._client is None
