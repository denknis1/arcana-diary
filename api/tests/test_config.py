from datetime import date

import pytest

from app.config import DEFAULT_MODEL, PRICE_CHANGES, PRICES_PER_MTOK, cost_usd, load_settings, provider_for_model


def test_defaults():
    s = load_settings({})
    assert s.reader_model == "claude-haiku-5-5"
    assert s.guard_model == "claude-haiku-5-5"
    assert s.judge_model == "claude-sonnet-5-5"
    assert s.reader_provider == "claude"
    assert s.first_token_timeout_s == 15.0
    assert s.guard_timeout_s == 5.0
    assert s.reader_effort == "medium"
    assert s.trust_cloudflare is False
    assert s.daily_budget_usd == 5.0
    assert s.guard_budget_usd == 1.0
    assert s.daily_job_interval_s == 3600.0
    assert s.cleanup_interval_s == 3600.0  # stage 4.3 §10: hourly, not daily
    assert s.run_migrations is True
    assert s.database_url == ""
    assert (s.content_dir / "deck.json").is_file()
    assert s.banned_terms_path.is_file()
    assert s.migrations_dir.name == "migrations"


def test_env_overrides(tmp_path):
    s = load_settings({"CONTENT_DIR": str(tmp_path), "READER_MODEL": "claude-sonnet-5-5", "GUARD_MODEL": "",
                       "READER_PROVIDER": "fake", "RUN_MIGRATIONS": "false", "DATABASE_URL": "postgresql://x",
                       "TRUST_CLOUDFLARE": "true", "DAILY_BUDGET_USD": "0.5", "READER_EFFORT": "high",
                       "GUARD_BUDGET_USD": "0.25"})
    assert s.content_dir == tmp_path
    assert s.reader_model == "claude-sonnet-5-5"
    assert s.guard_model == DEFAULT_MODEL
    assert s.reader_provider == "fake"
    assert s.run_migrations is False
    assert s.database_url == "postgresql://x"
    assert (s.trust_cloudflare, s.daily_budget_usd, s.reader_effort) == (True, 0.5, "high")
    assert s.guard_budget_usd == 0.25


@pytest.mark.parametrize("env", [{"READER_PROVIDER": "mistral"}, {"READER_EFFORT": "extreme"},
                                 {"TRUST_CLOUDFLARE": "True"}, {"TRUST_CLOUDFLARE": "1"}])
def test_unknown_provider_effort_or_cloudflare_flag_rejected(env):
    with pytest.raises(ValueError):
        load_settings(env)


def test_price_table():
    assert PRICES_PER_MTOK["claude-haiku-5-5"] == (0.10, 0.50)
    assert PRICES_PER_MTOK["claude-sonnet-5-5"] == (2.00, 10.00)


@pytest.mark.parametrize("model, tokens_in, tokens_out, expected", [
    ("claude-haiku-5-5", 1_000_000, 1_000_000, 0.60),
    ("claude-haiku-5-5", 120, 80, 0.000052),
    ("claude-sonnet-5-5", 1000, 500, 0.007),
])
def test_cost_usd(model, tokens_in, tokens_out, expected):
    assert cost_usd(model, tokens_in, tokens_out) == pytest.approx(expected)


def test_cost_unknown_model_or_tokens():
    assert cost_usd("fake-reader", 10, 10) is None
    assert cost_usd("claude-haiku-5-5", None, 10) is None


def test_unpriced_reader_model_refuses_to_start():
    with pytest.raises(ValueError, match=r"READER_MODEL.*claude-opus-5-5.*PRICES_PER_MTOK"):
        load_settings({"READER_MODEL": "claude-opus-5-5"})


def test_unpriced_guard_model_refuses_to_start():
    with pytest.raises(ValueError, match=r"GUARD_MODEL.*claude-haiku-5-5-20261001.*PRICES_PER_MTOK"):
        load_settings({"GUARD_MODEL": "claude-haiku-5-5-20261001"})


def test_priced_models_load_and_cost_is_known():
    s = load_settings({"READER_MODEL": "claude-sonnet-5-5", "GUARD_MODEL": "claude-haiku-5-5"})
    assert cost_usd(s.reader_model, 1000, 1000) is not None and cost_usd(s.guard_model, 1000, 1000) is not None
    assert cost_usd("claude-opus-5-5", 1000, 1000) is None  # cost_usd itself is unchanged


def test_price_table_has_the_compared_models():
    assert PRICES_PER_MTOK["gpt-6-luna"] == (0.10, 0.50)
    assert PRICES_PER_MTOK["gpt-6.2-sol"] == (2.00, 10.00)
    assert PRICES_PER_MTOK["gemini-3.8-flash"] == (0.75, 3.75)
    assert PRICES_PER_MTOK["gemini-4-argon"] == (2.00, 10.00)


def test_price_changes_are_announced_rises_of_priced_models():
    assert PRICE_CHANGES == {"gemini-4-argon": ("2026-12-01", (4.00, 20.00)),
                             "gemini-3.8-flash": ("2027-01-01", (1.50, 7.50))}
    for model, (_, (price_in, price_out)) in PRICE_CHANGES.items():
        assert price_in >= PRICES_PER_MTOK[model][0] and price_out >= PRICES_PER_MTOK[model][1]


@pytest.mark.parametrize("model, day, expected", [
    ("gemini-4-argon", date(2026, 11, 30), 0.012),
    ("gemini-4-argon", date(2026, 12, 1), 0.024),
    ("gemini-3.8-flash", date(2026, 12, 31), 0.0045),
    ("gemini-3.8-flash", date(2027, 1, 1), 0.009),
    ("claude-haiku-5-5", date(2030, 1, 1), 0.0006),
])
def test_cost_usd_applies_an_announced_rise_from_its_day(model, day, expected):
    assert cost_usd(model, 1000, 1000, day) == pytest.approx(expected)


@pytest.mark.parametrize("model, provider", [("claude-haiku-5-5", "claude"), ("gpt-6-luna", "openai"),
                                             ("gpt-6.2-sol", "openai"), ("gemini-4-argon", "gemini")])
def test_provider_for_model(model, provider):
    assert provider_for_model(model) == provider


def test_unknown_model_family():
    with pytest.raises(ValueError):
        provider_for_model("llama-4")


def test_openai_and_gemini_readers_need_their_keys():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        load_settings({"READER_PROVIDER": "openai", "READER_MODEL": "gpt-6-luna", "ANTHROPIC_API_KEY": "a"})
    s = load_settings({"READER_PROVIDER": "openai", "READER_MODEL": "gpt-6-luna", "OPENAI_API_KEY": "k",
                       "ANTHROPIC_API_KEY": "a"})
    assert (s.reader_provider, s.reader_model, s.openai_api_key) == ("openai", "gpt-6-luna", "k")
    with pytest.raises(ValueError, match="GOOGLE_AI_API_KEY"):
        load_settings({"READER_PROVIDER": "gemini", "READER_MODEL": "gemini-3.8-flash", "ANTHROPIC_API_KEY": "a"})
    s = load_settings({"READER_PROVIDER": "gemini", "READER_MODEL": "gemini-3.8-flash", "GOOGLE_AI_API_KEY": "g",
                       "ANTHROPIC_API_KEY": "a"})
    assert (s.reader_provider, s.google_ai_api_key) == ("gemini", "g")


def test_openai_and_gemini_readers_need_the_claude_key_for_the_question_check():
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        load_settings({"READER_PROVIDER": "openai", "READER_MODEL": "gpt-6-luna", "OPENAI_API_KEY": "k"})
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        load_settings({"READER_PROVIDER": "gemini", "READER_MODEL": "gemini-3.8-flash", "GOOGLE_AI_API_KEY": "g"})
    # claude and fake still start without any key (local runs and the tests use load_settings({}))
    assert load_settings({}).anthropic_api_key == ""
    assert load_settings({"READER_PROVIDER": "fake"}).reader_provider == "fake"


def test_reader_model_must_belong_to_the_provider():
    with pytest.raises(ValueError, match="is a claude model, but READER_PROVIDER=openai"):
        load_settings({"READER_PROVIDER": "openai", "READER_MODEL": "claude-haiku-5-5", "OPENAI_API_KEY": "k"})


def test_guard_stays_on_claude():
    with pytest.raises(ValueError, match="GUARD_MODEL"):
        load_settings({"GUARD_MODEL": "gpt-6-luna"})


def test_keys_default_to_empty():
    s = load_settings({})
    assert (s.openai_api_key, s.google_ai_api_key) == ("", "")


def test_supabase_url():
    assert load_settings({}).supabase_url == ""  # sign-in off
    assert load_settings({"SUPABASE_URL": " https://abc.supabase.co/ "}).supabase_url == "https://abc.supabase.co"
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        load_settings({"SUPABASE_URL": "http://abc.supabase.co"})
