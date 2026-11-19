"""Everything a request needs, built once per app: settings, DB, card base, providers, prompts, texts, counters."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.auth import TokenVerifier
from app.cards import CardBase, load_cards
from app.config import Settings
from app.db import Database
from app.limits import BurstCounter, DailySalt
from app.reader.check import load_reader_terms
from app.reader.claude import ClaudeProvider
from app.reader.compose import load_prompts
from app.reader.provider import FakeProvider
from app.reader.providers import make_reader
from app.safety.content import load_all_texts, load_helplines
from app.safety.guard import Guard
from app.turnstile import TurnstileVerifier


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AppContext:
    settings: Settings
    db: Database
    cards: CardBase
    reader: object
    guard: Guard
    turnstile: object
    auth: TokenVerifier | None  # None: SUPABASE_URL is empty, sign-in is off (stage 4.3 §3)
    prompts: dict
    texts: dict
    helplines: dict
    terms: dict          # the live-answer dictionary (reader_banned_terms.json), language → patterns
    salt: DailySalt
    burst: BurstCounter        # POST /api/readings per address
    daily_burst: BurstCounter  # GET /api/daily per address
    clock: Callable[[], datetime]


def _reader(settings: Settings):
    return make_reader(settings)


def _guard_provider(settings: Settings):
    if settings.reader_provider == "fake":
        return FakeProvider(model=f"fake-{settings.guard_model}")
    return ClaudeProvider(settings.anthropic_api_key, settings.guard_model, json_timeout_s=settings.guard_timeout_s)


def build_context(settings: Settings, *, reader=None, guard_provider=None, turnstile=None,
                  clock=None, jwks=None) -> AppContext:
    """jwks: tests pass a fake JWKS source; by default the keys come from SUPABASE_URL."""
    prompts = load_prompts()
    guard_prompt = prompts[("guard", None)]
    guard = Guard(guard_provider or _guard_provider(settings), guard_prompt.text, guard_prompt.version)
    return AppContext(
        settings=settings, db=Database(settings.database_url), cards=load_cards(settings.content_dir),
        reader=reader or _reader(settings), guard=guard,
        turnstile=turnstile or TurnstileVerifier(settings.turnstile_secret),
        auth=TokenVerifier(settings.supabase_url, jwks) if settings.supabase_url else None, prompts=prompts,
        texts=load_all_texts(), helplines=load_helplines(), terms=load_reader_terms(),
        salt=DailySalt(), burst=BurstCounter(), daily_burst=BurstCounter(), clock=clock or utc_now,
    )


def get_ctx(request) -> AppContext:
    return request.app.state.ctx
