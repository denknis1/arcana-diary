"""Builds model providers (spec 2026-11-19 §4): the class follows the model-name prefix, the key comes from
settings. The live reader follows READER_PROVIDER; the question check stays on Claude (context.py).
max_retries=None keeps each SDK's own default (Claude and OpenAI: 1 retry; google-genai does not retry); the
comparison passes 0 so every billed attempt is a metered call. The OpenAI and Gemini classes are imported only
when such a model is built, so the live process with READER_PROVIDER=claude never loads their SDKs."""
from app.config import REWRITE_TIMEOUT_S, Settings, provider_for_model
from app.reader.claude import ClaudeProvider
from app.reader.provider import FakeProvider


def make_provider(model: str, settings: Settings, *, effort: str | None = None, json_timeout_s: float = 3.0,
                  json_effort: str | None = "low", max_retries: int | None = None):
    family = provider_for_model(model)
    common = {"effort": effort, "json_timeout_s": json_timeout_s, "json_effort": json_effort}
    retries = {} if max_retries is None else {"max_retries": max_retries}
    if family == "claude":
        return ClaudeProvider(settings.anthropic_api_key, model, **common, **retries)
    if family == "openai":
        from app.reader.openai_provider import OpenAIProvider
        return OpenAIProvider(settings.openai_api_key, model, **common, **retries)
    from app.reader.gemini_provider import GeminiProvider
    return GeminiProvider(settings.google_ai_api_key, model, **common)


def make_reader(settings: Settings):
    if settings.reader_provider == "fake":
        return FakeProvider(model=f"fake-{settings.reader_model}")
    # stage 4.7: the reader's only JSON call is the gender rewrite (rewrite.py), a short one
    return make_provider(settings.reader_model, settings, effort=settings.reader_effort,
                         json_timeout_s=REWRITE_TIMEOUT_S)
