import pytest

from app.config import load_settings
from app.reader.claude import ClaudeProvider
from app.reader.gemini_provider import GeminiProvider
from app.reader.openai_provider import OpenAIProvider
from app.reader.provider import FakeProvider
from app.reader.providers import make_provider, make_reader

KEYS = {"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "o", "GOOGLE_AI_API_KEY": "g"}


def settings(**env):
    return load_settings({**KEYS, **env})


def test_make_provider_picks_the_class_by_model_name():
    s = settings()
    claude = make_provider("claude-haiku-5-5", s, json_timeout_s=5.0)
    assert isinstance(claude, ClaudeProvider) and claude._json_timeout_s == 5.0
    gpt = make_provider("gpt-6-luna", s, effort="medium")
    assert isinstance(gpt, OpenAIProvider) and (gpt.model, gpt._api_key, gpt._effort) == ("gpt-6-luna", "o", "medium")
    gemini = make_provider("gemini-4-argon", s, json_timeout_s=120.0, json_effort=None)
    assert isinstance(gemini, GeminiProvider) and gemini._api_key == "g"
    assert (gemini._json_timeout_s, gemini._json_effort) == (120.0, None)


def test_make_provider_passes_max_retries_to_claude_and_openai():
    s = settings()
    assert make_provider("claude-haiku-5-5", s)._max_retries == 1      # the providers' own default
    assert make_provider("claude-haiku-5-5", s, max_retries=0)._max_retries == 0
    assert make_provider("gpt-6-luna", s, max_retries=0)._max_retries == 0
    assert isinstance(make_provider("gemini-3.8-flash", s, max_retries=0), GeminiProvider)  # no retries by default


def test_make_provider_rejects_unknown_families():
    with pytest.raises(ValueError):
        make_provider("llama-4", settings())


def test_make_reader_follows_the_settings():
    fake = make_reader(settings(READER_PROVIDER="fake"))
    assert isinstance(fake, FakeProvider) and fake.model == "fake-claude-haiku-5-5"
    gpt = make_reader(settings(READER_PROVIDER="openai", READER_MODEL="gpt-6-luna", READER_EFFORT="high"))
    assert isinstance(gpt, OpenAIProvider) and gpt._effort == "high"
    gemini = make_reader(settings(READER_PROVIDER="gemini", READER_MODEL="gemini-3.8-flash"))
    assert isinstance(gemini, GeminiProvider) and gemini._effort == "medium"
    assert isinstance(make_reader(settings()), ClaudeProvider)
