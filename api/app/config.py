"""API settings from environment variables; limits; model prices for the LLM call log."""
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Mapping

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]

DEFAULT_MODEL = "claude-haiku-5-5"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
DAILY_LIMIT = 3
USER_DAILY_LIMIT = 5       # signed in: per account, on every device (spec 2026-11-19 stage 4.3 §5)
IP_HARD_LIMIT = 60
FOLLOWUP_LIMIT = 2         # free follow-ups per reading; each next one uses a reading of DAILY_LIMIT (§10.1)
FOLLOWUP_ATTEMPTS = 8      # §10.2: follow-up requests per reading, crisis answers, refusals and failures included
IP_FOLLOWUP_LIMIT = 40     # §9.2: follow-up requests per address per UTC day
IP_GUARD_LIMIT = 60        # §10.5 (В18): question checks by the model per address per UTC day on POST /api/readings
RETRY_LIMIT = 2
GUEST_RETENTION_DAYS = 7
CLAIM_TOKEN_DAYS = 7           # stage 4.3 §4.2: a one-time token to save a guest reading from another device
CLAIM_TOKENS_PER_READING = 5   # live tokens per reading at once ("Save to diary" may be pressed again, not forever)
NOTE_MAX_CHARS = 1000          # stage 4.3 §6: the private note of a diary entry (never sent to a model)

PROVIDERS = ("claude", "openai", "gemini", "fake")
KEY_NAMES = {"claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GOOGLE_AI_API_KEY"}

# USD per 1M tokens: (input, output). Official pages on 19.11.2026: developers.openai.com/api/docs/pricing,
# aistudio.google.com/docs/pricing (spec 2026-11-19 §3).
PRICES_PER_MTOK = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6.2-sol": (2.00, 10.00),
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-4-argon": (2.00, 10.00),
}
# Announced price rises: model -> (first UTC day, (input, output)). cost_usd applies the new price from that day on,
# so the comparison meter and the live budgets never undercount; reports also show it as a second column.
PRICE_CHANGES = {
    "gemini-4-argon": ("2026-12-01", (4.00, 20.00)),
    "gemini-3.8-flash": ("2027-01-01", (1.50, 7.50)),
}


def provider_for_model(model: str) -> str:
    """claude-... -> claude, gpt-... -> openai, gemini-... -> gemini; any other name raises ValueError."""
    for prefix, provider in (("claude-", "claude"), ("gpt-", "openai"), ("gemini-", "gemini")):
        if model.startswith(prefix):
            return provider
    raise ValueError(f"no provider for model {model!r}: expected a claude-, gpt- or gemini- model")


@dataclass(frozen=True)
class Settings:
    content_dir: Path
    banned_terms_path: Path
    migrations_dir: Path
    database_url: str
    reader_provider: str
    anthropic_api_key: str
    openai_api_key: str
    google_ai_api_key: str
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
    supabase_url: str  # stage 4.3 §3: the project's public address; "" — sign-in is off


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def _true_or_false(name: str, value: str) -> bool:
    """Exactly "true" or "false", as Caddy reads the same variable (import cf-{$TRUST_CLOUDFLARE:false})."""
    if value not in ("true", "false"):
        raise ValueError(f"{name} must be exactly 'true' or 'false', got {value!r}")
    return value == "true"


def _supabase_url(value: str) -> str:
    """Tokens must name <SUPABASE_URL>/auth/v1 as their issuer; the keys come from the same address."""
    url = value.strip().rstrip("/")
    if url and not url.startswith("https://"):
        raise ValueError(f"SUPABASE_URL must start with https://, got {url!r}")
    return url


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    provider = env.get("READER_PROVIDER") or "claude"
    if provider not in PROVIDERS:
        raise ValueError(f"READER_PROVIDER must be one of {PROVIDERS}, got {provider!r}")
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
    if provider != "fake":
        family = provider_for_model(reader_model)
        if family != provider:
            raise ValueError(f"READER_MODEL={reader_model!r} is a {family} model, but READER_PROVIDER={provider}")
        if provider in ("openai", "gemini"):
            for key in (KEY_NAMES[provider], "ANTHROPIC_API_KEY"):  # the question check stays on Claude
                if not env.get(key):
                    raise ValueError(f"READER_PROVIDER={provider} needs {key} (deploy/.env)")
    if provider_for_model(guard_model) != "claude":
        raise ValueError(f"GUARD_MODEL={guard_model!r}: the question check stays on Claude (spec 2026-11-19 §2.4)")
    return Settings(
        content_dir=Path(env.get("CONTENT_DIR") or REPO_ROOT / "content/cards"),
        banned_terms_path=Path(env.get("BANNED_TERMS_PATH") or REPO_ROOT / "tools/cards/banned_terms.json"),
        migrations_dir=Path(env.get("MIGRATIONS_DIR") or APP_DIR.parent / "migrations"),
        database_url=env.get("DATABASE_URL", ""),
        reader_provider=provider,
        anthropic_api_key=env.get("ANTHROPIC_API_KEY", ""),
        openai_api_key=env.get("OPENAI_API_KEY", ""),
        google_ai_api_key=env.get("GOOGLE_AI_API_KEY", ""),
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
        supabase_url=_supabase_url(env.get("SUPABASE_URL") or ""),
    )


def cost_usd(model: str, tokens_in: int | None, tokens_out: int | None, day: date | None = None) -> float | None:
    """The price of a call on `day` (default: today, UTC): from the day of an announced rise (PRICE_CHANGES) the
    new price applies. None for a model without a price row or a call without usage."""
    price = PRICES_PER_MTOK.get(model)
    if price is None or tokens_in is None or tokens_out is None:
        return None
    change = PRICE_CHANGES.get(model)
    if change is not None and (day or datetime.now(timezone.utc).date()) >= date.fromisoformat(change[0]):
        price = change[1]
    return round((tokens_in * price[0] + tokens_out * price[1]) / 1_000_000, 6)
