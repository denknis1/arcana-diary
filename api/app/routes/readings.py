"""Reading endpoints (§1.1, §1.2, §5.1, §8): create, restore, stream, retry. Follow-ups are in followups.py."""
import uuid
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app import limits, repo
from app.config import DAILY_LIMIT, GUEST_RETENTION_DAYS, IP_GUARD_LIMIT, RETRY_LIMIT
from app.context import get_ctx
from app.draw import draw_spread, new_seed
from app.reader import flow
from app.reader.compose import SITUATIONS
from app.routes.common import country_hint, is_owner, not_found, respond, stream_response
from app.safety.guard import NO_VERDICT_GROUPS, GuardUnavailable

router = APIRouter(prefix="/api")


class ReadingIn(BaseModel):
    lang: Literal["en", "es"]
    kind: Literal["one", "three", "yes_no", "card_page"]
    question: str | None = Field(default=None, max_length=500)
    topic: Literal["love", "work", "self", "decision", "general"] | None = None
    situation: str | None = Field(default=None, max_length=40)
    card_id: str | None = Field(default=None, max_length=80)
    tz: str | None = Field(default=None, max_length=64)
    turnstile_token: str | None = Field(default=None, max_length=4096)


def clean(text: str | None) -> str | None:
    if text is None:
        return None
    return text.strip() or None


def load_reading(ctx, reading_id) -> dict | None:
    with ctx.db.connect() as conn:
        return repo.get_reading(conn, reading_id, ctx.clock())


@router.post("/readings")
def create_reading(body: ReadingIn, request: Request):
    ctx = get_ctx(request)
    now = ctx.clock()
    guest_id, is_new = limits.guest_from_request(request)
    new_guest = guest_id if is_new else None
    card_ok = body.card_id is None or body.card_id in ctx.cards.deck
    if (body.kind == "card_page") != (body.card_id is not None) or not card_ok:
        return respond(422, {"reason": "invalid", "fields": ["card_id"]}, new_guest)
    if body.situation is not None and body.situation not in SITUATIONS:
        return respond(422, {"reason": "invalid", "fields": ["situation"]}, new_guest)
    day = limits.local_day(limits.resolve_tz(body.tz), now)
    ip_day = limits.utc_day(now)
    ip = limits.client_ip(request, ctx.settings.trust_cloudflare)
    ip_hash = ctx.salt.hash_ip(ip, now)
    hits = ctx.burst.hit(ip_hash, now)
    with ctx.db.connect() as conn:
        ip_used = limits.used(conn, limits.ip_subject(ip_hash), ip_day)
        checks = limits.used(conn, limits.guard_ip_subject(ip_hash), ip_day)
        guest_used = limits.used(conn, limits.guest_subject(guest_id), day)
    if limits.ip_blocked(ip_used):
        return respond(429, {"reason": "ip_limit", "remaining": 0}, new_guest)
    # В18: question checks count too, so crisis answers (no reading, no slot) also lead to Turnstile
    if limits.needs_turnstile(hits, max(ip_used, checks)) and not ctx.turnstile.verify(body.turnstile_token):
        return respond(403, {"reason": "turnstile", "sitekey": ctx.settings.turnstile_sitekey}, new_guest)
    if guest_used >= DAILY_LIMIT:
        return respond(429, {"reason": "limit", "remaining": 0}, new_guest)
    question = clean(body.question)
    reading_id = uuid.uuid4()
    guard = None
    if question:
        stop_phrase = bool(ctx.guard.filter.match(question))  # м12: a stop-phrase needs no model call, no slot
        allow_model = stop_phrase or not flow.guard_over_budget(ctx)  # ...and no budget query either
        if allow_model and not stop_phrase:
            # В18: IP_GUARD_LIMIT checks per address per UTC day, then only the stop-phrases answer
            with ctx.db.connect() as conn:
                allow_model = limits.take_slot(conn, limits.guard_ip_subject(ip_hash), ip_day,
                                               IP_GUARD_LIMIT) is not None
        try:
            guard = ctx.guard.classify(question, allow_model=allow_model)
        except GuardUnavailable:  # §9.2: never a reading without the question check
            return respond(503, {"reason": "unavailable"}, new_guest)
    if guard is not None:
        with ctx.db.connect() as conn:
            flow.record_guard(conn, ctx, guard, body.lang, ip_day, None if guard.group == "crisis" else reading_id)
    if guard is not None and guard.group == "crisis":
        payload = flow.crisis_answer(ctx, body.lang, country_hint(ctx, request), body.tz, guard.violence)
        return respond(200, {**payload, "remaining": DAILY_LIMIT - guest_used}, new_guest)
    group = guard.group if guard else "ok"
    seed = new_seed()
    cards = draw_spread(seed, body.kind, ctx.cards.order)
    with_verdict = body.kind == "yes_no" and group not in NO_VERDICT_GROUPS  # §8.1
    reading = {
        "id": reading_id, "guest_id": guest_id, "lang": body.lang, "kind": body.kind, "question": question,
        "topic": body.topic, "situation": body.situation, "source_card_id": body.card_id, "cards": cards,
        "seed": seed, "verdict": ctx.cards.verdict(cards) if with_verdict else None, "guard_group": group,
        "created_at": now, "expires_at": now + timedelta(days=GUEST_RETENTION_DAYS),
    }
    try:
        with ctx.db.connect() as conn:
            count = limits.take_reading_slots(conn, guest_id, day, ip_hash, ip_day)  # §8.11: atomic
            repo.insert_reading(conn, reading)
    except limits.LimitReached as exc:
        return respond(429, {"reason": exc.reason, "remaining": 0}, new_guest)
    view = flow.reading_view(ctx, reading, owner=True)
    return respond(201, {**view, "remaining": DAILY_LIMIT - count}, new_guest)


@router.get("/readings/{reading_id}")
def get_reading(reading_id: uuid.UUID, request: Request, tz: str | None = None):
    ctx = get_ctx(request)
    with ctx.db.connect() as conn:
        reading = repo.get_reading(conn, reading_id, ctx.clock())
        followups = repo.list_followups(conn, reading_id) if reading else []
    if reading is None:
        return not_found()
    owner = is_owner(request, reading)
    if reading["answer_shown"] == "crisis":
        if not owner:
            return not_found()
        crisis = flow.crisis_answer(ctx, reading["lang"], country_hint(ctx, request), tz, False)
        return respond(200, {**flow.full_view(ctx, reading, followups, owner, ctx.clock()), **crisis})
    return respond(200, flow.full_view(ctx, reading, followups, owner, ctx.clock()))


@router.get("/readings/{reading_id}/stream")
def stream_reading(reading_id: uuid.UUID, request: Request, tz: str | None = None):
    """The first stream only for the owner (§8.3); afterwards the saved answer replays for anyone with the link."""
    ctx = get_ctx(request)
    reading = load_reading(ctx, reading_id)
    if reading is None:
        return not_found()
    if not is_owner(request, reading):
        if reading["answer_shown"] == "crisis":
            return not_found()
        if reading["answer"] is None:
            return respond(403, {"reason": "owner_only"})
    return stream_response(flow.stream_reading(ctx, reading, country_hint(ctx, request), tz))


@router.post("/readings/{reading_id}/retry")
def retry_reading(reading_id: uuid.UUID, request: Request, tz: str | None = None):
    """After a fallback: a new attempt that does not use the daily limit, at most RETRY_LIMIT times (§5.1)."""
    ctx = get_ctx(request)
    reading = load_reading(ctx, reading_id)
    if reading is None or not is_owner(request, reading):
        return not_found()
    if reading["answer_shown"] != "fallback":
        return respond(409, {"reason": "not_fallback"})
    if reading["retries"] >= RETRY_LIMIT:
        return respond(409, {"reason": "retries"})
    with ctx.db.connect() as conn:
        retries = repo.reset_for_retry(conn, reading_id, RETRY_LIMIT)
    if retries is None:  # a parallel retry got there first
        return respond(409, {"reason": "busy"})
    fresh = {**reading, "answer": None, "answer_shown": None, "retries": retries}
    return stream_response(flow.stream_reading(ctx, fresh, country_hint(ctx, request), tz))
