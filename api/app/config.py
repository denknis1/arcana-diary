"""API settings from environment variables; limits; model prices for the LLM call log."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]

DEFAULT_MODEL = "claude-haiku-5-5"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
DAILY_LIMIT = 3
IP_HARD_LIMIT = 60
FOLLOWUP_LIMIT = 2         # free follow-ups per reading; each next one uses a reading of DAILY_LIMIT (§10.1)
FOLLOWUP_ATTEMPTS = 8      # §10.2: follow-up requests per reading, crisis answers, refusals and failures included
IP_FOLLOWUP_LIMIT = 40     # §9.2: follow-up requests per address per UTC day
IP_GUARD_LIMIT = 60        # §10.5 (В18): question checks by the model per address per UTC day on POST /api/readings
RETRY_LIMIT = 2
GUEST_RETENTION_DAYS = 7

# USD per 1M tokens: (input, output)
PRICES_PER_MTOK = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}


@dataclass(frozen=True)
class Settings:
    content_dir: Path
    banned_terms_path: Path
    migrations_dir: Path
    database_url: str
    reader_provider: str
    anthropic_api_key: str
    reader_model: str
    reader_effort: str
    guard_model: str
    judge_model: str
    turnstile_secret: str
    turnstile_sitekey: str
    trust_cloudflare: bool
    daily_budget_usd: float
    guard_budget_usd: float
    first_token_timeout_s: float
    guard_timeout_s: float
    cleanup_interval_s: float
    daily_job_interval_s: float
    run_migrations: bool


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def _true_or_false(name: str, value: str) -> bool:
    """Exactly "true" or "false", as Caddy reads the same variable (import cf-{$TRUST_CLOUDFLARE:false})."""
    if value not in ("true", "false"):
        raise ValueError(f"{name} must be exactly 'true' or 'false', got {value!r}")
    return value == "true"


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    provider = env.get("READER_PROVIDER") or "claude"
    if provider not in ("claude", "fake"):
        raise ValueError(f"READER_PROVIDER must be 'claude' or 'fake', got {provider!r}")
    effort = env.get("READER_EFFORT") or "medium"
    if effort not in EFFORTS:
        raise ValueError(f"READER_EFFORT must be one of {EFFORTS}, got {effort!r}")
    reader_model = env.get("READER_MODEL") or DEFAULT_MODEL
    guard_model = env.get("GUARD_MODEL") or DEFAULT_MODEL
    # И1: a model without a price row has cost_usd NULL, which the budgets count as 0 - both ceilings would be off
    for name, model in (("READER_MODEL", reader_model), ("GUARD_MODEL", guard_model)):
        if model not in PRICES_PER_MTOK:
            raise ValueError(f"{name}={model!r} has no price in PRICES_PER_MTOK (app/config.py): the money ceilings "
                             f"would not work. Add a price row for the model first.")
    return Settings(
        content_dir=Path(env.get("CONTENT_DIR") or REPO_ROOT / "content/cards"),
        banned_terms_path=Path(env.get("BANNED_TERMS_PATH") or REPO_ROOT / "tools/cards/banned_terms.json"),
        migrations_dir=Path(env.get("MIGRATIONS_DIR") or APP_DIR.parent / "migrations"),
        database_url=env.get("DATABASE_URL", ""),
        reader_provider=provider,
        anthropic_api_key=env.get("ANTHROPIC_API_KEY", ""),
        reader_model=reader_model,
        reader_effort=effort,
        guard_model=guard_model,
        judge_model=env.get("JUDGE_MODEL") or "claude-sonnet-5-5",
        turnstile_secret=env.get("TURNSTILE_SECRET", ""),
        turnstile_sitekey=env.get("TURNSTILE_SITEKEY", ""),
        trust_cloudflare=_true_or_false("TRUST_CLOUDFLARE", env.get("TRUST_CLOUDFLARE") or "false"),
        daily_budget_usd=float(env.get("DAILY_BUDGET_USD") or 5),
        guard_budget_usd=float(env.get("GUARD_BUDGET_USD") or 1),
        first_token_timeout_s=float(env.get("FIRST_TOKEN_TIMEOUT_S") or 15),
        guard_timeout_s=float(env.get("GUARD_TIMEOUT_S") or 5),
        cleanup_interval_s=float(env.get("CLEANUP_INTERVAL_S") or 86400),
        daily_job_interval_s=float(env.get("DAILY_JOB_INTERVAL_S") or 3600),
        run_migrations=_bool(env.get("RUN_MIGRATIONS") or "true"),
    )


def cost_usd(model: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
    price = PRICES_PER_MTOK.get(model)
    if price is None or tokens_in is None or tokens_out is None:
        return None
    return round((tokens_in * price[0] + tokens_out * price[1]) / 1_000_000, 6)
