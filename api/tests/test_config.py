import pytest

from app.config import DEFAULT_MODEL, PRICES_PER_MTOK, cost_usd, load_settings


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


@pytest.mark.parametrize("env", [{"READER_PROVIDER": "gemini"}, {"READER_EFFORT": "extreme"},
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
