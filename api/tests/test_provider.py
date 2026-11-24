import time

import pytest

from app.reader.check import VERDICT_PATTERNS, load_reader_terms
from app.reader.engine import Chunk, Failed, Finished, run_stream
from app.reader.errors import ProviderTimeout
from app.reader.provider import FakeProvider, FakeReply, ProviderRefusal, StreamResult, canned_answer, canned_text
from app.reader.sections import SectionParser, required_sections
from app.terms import find_banned

MSG3 = [{"role": "user", "content": '<reading kind="three" lang="en" guard_group="ok">\n<cards count="3">'}]
MSG_YN = [{"role": "user", "content": '<reading kind="yes_no" lang="en" guard_group="ok">\n<cards count="1">\n'
                                      '</cards>\n<verdict value="yes">Yes</verdict>'}]
MSG_YN_NO_VERDICT = [{"role": "user", "content": '<reading kind="yes_no" lang="en" guard_group="redirect_topic">\n'
                                                 '<cards count="1">'}]


def collect(provider, messages):
    return list(provider.stream("system", messages, 100))


def parse(items):
    parser = SectionParser()
    for item in items:
        if isinstance(item, str):
            parser.feed(item)
    parser.finish()
    return parser.sections()


def test_canned_three_has_required_sections():
    items = collect(FakeProvider(), MSG3)
    assert isinstance(items[-1], StreamResult) and items[-1].stop_reason == "end_turn"
    assert set(parse(items)) == set(required_sections("three", False))


def test_canned_yes_no_has_why_only_with_a_verdict():
    assert set(parse(collect(FakeProvider(), MSG_YN))) == set(required_sections("yes_no", True))
    assert set(parse(collect(FakeProvider(), MSG_YN_NO_VERDICT))) == set(required_sections("yes_no", False))


def test_replies_are_used_in_order_and_calls_recorded():
    fake = FakeProvider(replies=[FakeReply(chunks=["one"]), FakeReply(chunks=["two"])])
    assert collect(fake, MSG3)[0] == "one"
    assert collect(fake, MSG3)[0] == "two"
    assert len(fake.stream_calls()) == 2 and fake.stream_calls()[0]["system"] == "system"


def test_refusal_raises_after_text():
    fake = FakeProvider(replies=[FakeReply(chunks=["a", "b"], refuse=True)])
    gen = fake.stream("s", MSG3, 10)
    assert [next(gen), next(gen)] == ["a", "b"]
    with pytest.raises(ProviderRefusal) as info:
        next(gen)
    assert info.value.result.stop_reason == "refusal"
    assert info.value.result.refusal_category == "general_harms"


def test_chunk_delay_and_stop_reason():
    fake = FakeProvider(replies=[FakeReply(chunks=["a", "b", "c"], chunk_delay=0.05, stop_reason="max_tokens")])
    started = time.monotonic()
    items = collect(fake, MSG3)
    assert items[:3] == ["a", "b", "c"] and items[-1].stop_reason == "max_tokens"
    assert time.monotonic() - started >= 0.1


def test_complete_json_default_queue_and_error():
    fake = FakeProvider(json_replies=[{"group": "crisis"}, RuntimeError("down")])
    assert fake.complete_json("s", [], {}, 10)[0] == {"group": "crisis"}
    with pytest.raises(RuntimeError):
        fake.complete_json("s", [], {}, 10)
    data, usage = fake.complete_json("s", [], {}, 10)
    assert data == {"group": "ok", "violence": False} and usage.model == "fake-reader"
    assert len(fake.json_calls()) == 3


def test_canned_texts_are_clean():
    banned = load_reader_terms()["en"]
    for text in (canned_answer(3, True), canned_text()):
        assert find_banned(text, banned) == []
    why = canned_answer(1, True).split("[[why]]\n")[1]
    assert find_banned(why, VERDICT_PATTERNS["en"]) == []


def test_run_stream_normal():
    items = list(run_stream(FakeProvider(), "s", MSG3, 100, first_token_timeout=1.0))
    assert all(isinstance(i, Chunk) for i in items[:-1])
    assert isinstance(items[-1], Finished) and items[-1].ms_first_token is not None
    assert items[-1].result.tokens_in == 120


def test_run_stream_first_token_timeout():
    started = time.monotonic()
    items = list(run_stream(FakeProvider(replies=[FakeReply(first_delay=1.0)]), "s", MSG3, 100,
                            first_token_timeout=0.1))
    assert len(items) == 1 and isinstance(items[0], Failed)
    assert (items[0].reason, items[0].after_text) == ("timeout", False)
    assert time.monotonic() - started < 0.5


def test_run_stream_error_before_text():
    [item] = list(run_stream(FakeProvider(replies=[FakeReply(fail_after=0)]), "s", MSG3, 100, 1.0))
    assert isinstance(item, Failed) and (item.reason, item.after_text) == ("error", False)


def test_run_stream_cut_after_text():
    items = list(run_stream(FakeProvider(replies=[FakeReply(fail_after=3)]), "s", MSG3, 100, 1.0))
    assert [type(i) for i in items] == [Chunk, Chunk, Chunk, Failed]
    assert (items[-1].reason, items[-1].after_text) == ("error", True)


def test_run_stream_refusal():
    items = list(run_stream(FakeProvider(replies=[FakeReply(chunks=["a"], refuse=True)]), "s", MSG3, 100, 1.0))
    assert isinstance(items[-1], Failed) and items[-1].reason == "refusal" and items[-1].after_text
    assert items[-1].result.stop_reason == "refusal"


class _TimeoutProvider:
    model = "t"

    def __init__(self, chunks):
        self.chunks = chunks

    def stream(self, system, messages, max_tokens):
        yield from self.chunks
        raise ProviderTimeout("sdk gave up")


@pytest.mark.parametrize("chunks, after_text", [([], False), (["a"], True)])
def test_run_stream_provider_timeout_is_reported_as_timeout(chunks, after_text):
    items = list(run_stream(_TimeoutProvider(chunks), "s", MSG3, 100, 1.0))
    assert isinstance(items[-1], Failed) and items[-1].reason == "timeout" and items[-1].after_text is after_text
