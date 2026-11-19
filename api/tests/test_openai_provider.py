from types import SimpleNamespace

import httpx2
import openai
import pytest

from app.reader.openai_provider import OpenAIProvider
from app.reader.provider import ProviderError, ProviderRefusal, ProviderTimeout, StreamResult

SYSTEM = "You are the reader."
MSGS = [{"role": "user", "content": "<reading/>"}, {"role": "assistant", "content": "first"},
        {"role": "user", "content": "<followup/>"}]
SCHEMA = {"type": "object", "properties": {"group": {"type": "string"}}, "required": ["group"],
          "additionalProperties": False}


def ev(type_, delta=None, response=None):
    return SimpleNamespace(type=type_, delta=delta, response=response)


def response(status="completed", reason=None, tokens=(30, 12), refusal=False, text="Hello"):
    part = SimpleNamespace(type="refusal", refusal="no") if refusal else SimpleNamespace(type="output_text", text=text)
    return SimpleNamespace(status=status, incomplete_details=SimpleNamespace(reason=reason) if reason else None,
                           usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]),
                           output=[SimpleNamespace(type="message", content=[part])],
                           output_text="" if refusal else text)


def end(final):
    """The terminal event the SDK sends last: response.completed, response.incomplete or response.failed."""
    kind = {"completed": "response.completed", "incomplete": "response.incomplete"}.get(final.status,
                                                                                         "response.failed")
    return ev(kind, response=final)


def sdk_timeout():
    return openai.APITimeoutError(request=httpx2.Request("POST", "https://api.openai.com/v1/responses"))


class FakeStream:
    """Like the SDK's ResponseStream: get_final_response() works only after a response.completed event."""

    def __init__(self, events):
        self.events = events

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(self.events)

    def get_final_response(self):
        done = [e for e in self.events if e.type == "response.completed"]
        if not done:
            raise RuntimeError("Didn't receive a `response.completed` event.")
        return done[-1].response


class FakeResponses:
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
    def __init__(self, responses):
        self.responses = responses
        self.options = []

    def with_options(self, **kwargs):
        self.options.append(kwargs)
        return self


def provider(responses, **kwargs):
    return OpenAIProvider("key", "gpt-6-luna", client=FakeClient(responses), **kwargs)


def test_stream_yields_text_then_result_and_sends_the_conversation():
    events = [ev("response.created"), ev("response.output_text.delta", "Hel"), ev("response.output_text.delta", "lo"),
              end(response())]
    responses = FakeResponses(stream=FakeStream(events))
    items = list(provider(responses, effort="medium").stream(SYSTEM, MSGS, 500))
    assert items == ["Hel", "lo", StreamResult(30, 12, "end_turn", "gpt-6-luna")]
    call = responses.calls[0]
    assert call["model"] == "gpt-6-luna" and call["instructions"] == SYSTEM and call["max_output_tokens"] == 500
    assert call["input"] == MSGS and call["store"] is False and call["reasoning"] == {"effort": "medium"}


def test_no_effort_sends_no_reasoning():
    responses = FakeResponses(stream=FakeStream([ev("response.output_text.delta", "Hi"), end(response())]))
    list(provider(responses).stream(SYSTEM, MSGS, 100))
    assert "reasoning" not in responses.calls[0]


def test_cut_by_token_limit_is_a_result_not_an_error():
    final = response(status="incomplete", reason="max_output_tokens")
    responses = FakeResponses(stream=FakeStream([ev("response.output_text.delta", "Hel"), end(final)]))
    items = list(provider(responses).stream(SYSTEM, MSGS, 100))
    assert items[-1] == StreamResult(30, 12, "max_tokens", "gpt-6-luna")


@pytest.mark.parametrize("final", [response(refusal=True), response(status="incomplete", reason="content_filter")])
def test_refusal_raises_with_its_result(final):
    responses = FakeResponses(stream=FakeStream([ev("response.refusal.delta", "no"), end(final)]))
    with pytest.raises(ProviderRefusal) as exc:
        list(provider(responses).stream(SYSTEM, MSGS, 100))
    assert exc.value.result == StreamResult(30, 12, "refusal", "gpt-6-luna", "content_filter")


def test_failed_response_is_an_error_with_its_usage():
    responses = FakeResponses(stream=FakeStream([end(response(status="failed"))]))
    with pytest.raises(ProviderError) as exc:
        list(provider(responses).stream(SYSTEM, MSGS, 100))
    assert not isinstance(exc.value, (ProviderTimeout, ProviderRefusal))
    assert exc.value.result == StreamResult(30, 12, "failed", "gpt-6-luna")


def test_a_stream_without_a_terminal_event_is_an_error():
    responses = FakeResponses(stream=FakeStream([ev("response.output_text.delta", "Hel")]))
    with pytest.raises(ProviderError) as exc:
        list(provider(responses).stream(SYSTEM, MSGS, 100))
    assert exc.value.result is None and "terminal event" in str(exc.value)


def test_timeout_and_other_errors():
    with pytest.raises(ProviderTimeout):
        list(provider(FakeResponses(error=sdk_timeout())).stream(SYSTEM, MSGS, 100))
    with pytest.raises(ProviderError) as exc:
        list(provider(FakeResponses(error=RuntimeError("boom"))).stream(SYSTEM, MSGS, 100))
    assert not isinstance(exc.value, ProviderTimeout)


def test_complete_json_parses_and_asks_for_strict_schema():
    responses = FakeResponses(create=response(text='{"group": "ok"}'))
    p = provider(responses)
    data, result = p.complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
    assert data == {"group": "ok"} and result == StreamResult(30, 12, "end_turn", "gpt-6-luna")
    call = responses.calls[0]
    assert call["text"] == {"format": {"type": "json_schema", "name": "result", "schema": SCHEMA, "strict": True}}
    assert call["reasoning"] == {"effort": "low"} and call["store"] is False
    assert p.client.options == [{"timeout": 3.0, "max_retries": 0}]


def test_complete_json_failures():
    cut = FakeResponses(create=response(status="incomplete", reason="max_output_tokens", text='{"gr'))
    with pytest.raises(ProviderError) as exc:
        provider(cut).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
    assert exc.value.result is not None
    with pytest.raises(ProviderError):
        provider(FakeResponses(create=response(text="not json"))).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
    with pytest.raises(ProviderRefusal):
        provider(FakeResponses(create=response(refusal=True))).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
    with pytest.raises(ProviderTimeout):
        provider(FakeResponses(error=sdk_timeout())).complete_json(SYSTEM, MSGS[:1], SCHEMA, 64)
