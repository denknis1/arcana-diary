"""Reading endpoints (§1.1, §1.2, §5.1, §8): create, restore, stream, retry. Follow-ups are in followups.py."""
import uuid
from datetime import timedelta
from typing import Literal

import psycopg
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from app import account_repo, limits, repo
from app.config import GUEST_RETENTION_DAYS, IP_GUARD_LIMIT, RETRY_LIMIT
from app.context import get_ctx
from app.db import DatabaseUnavailable
from app.draw import draw_spread, new_seed
from app.reader import flow
from app.reader.compose import SITUATIONS
from app.routes.common import country_hint, not_found, owns, respond, stream_response, viewer
from app.safety.guard import NO_VERDICT_GROUPS, GuardUnavailable

router = APIRouter(prefix="/api")


def reject_nul(value: str | None) -> str | None:
    """PostgreSQL text cannot hold NUL: reject it with the standard 422 before any model call or slot."""
    if value is not None and "\x00" in value:
        raise ValueError("NUL character")
    return value


class ReadingIn(BaseModel):
    lang: Literal["en", "es"]
    kind: Literal["one", "three", "yes_no", "card_page"]
    question: str | None = Field(default=None, max_length=500)
    topic: Literal["love", "work", "self", "decision", "general"] | None = None
    situation: str | None = Field(default=None, max_length=40)
    card_id: str | None = Field(default=None, max_length=80)
    tz: str | None = Field(default=None, max_length=64)
    turnstile_token: str | None = Field(default=None, max_length=4096)
    count: Literal[1, 3] | None = None  # stage 4.5 §4: yes_no only — one card (default) or three
    request_id: uuid.UUID | None = None  # stage 4.5 §5: the site's number of this draw; optional

    _no_nul = field_validator("question", "situation", "card_id", "tz", mode="after")(reject_nul)

    @field_validator("count", mode="before")
    @classmethod
    def count_is_an_integer(cls, value):
        if isinstance(value, (bool, float)):  # true and 1.0 must not pass as 1
            raise ValueError("count must be 1 or 3")
        return value


def clean(text: str | None) -> str | None:
    if text is None:
        return None
    return text.strip() or None


class Repeated(Exception):
    """A parallel request with the same request_id inserted its reading first: this transaction (and its slots)
    rolls back and the request answers with that reading."""


def load_reading(ctx, reading_id) -> dict | None:
    with ctx.db.connect() as conn:
        return repo.get_reading(conn, reading_id, ctx.clock())


def repeat_answer(ctx, reading: dict, quota, quota_used: int, new_guest):
    """Stage 4.5 §5: the reading this owner already made with the request's number, as its first answer was."""
    return respond(201, {**flow.reading_view(ctx, reading, owner=True), "remaining": max(quota.limit - quota_used, 0)},
                   new_guest)


@router.post("/readings")
def create_reading(body: ReadingIn, request: Request):
    ctx = get_ctx(request)
    now = ctx.clock()
    who = viewer(ctx, request)
    guest_id, new_guest = who.guest_id, who.new_guest
    card_ok = body.card_id is None or body.card_id in ctx.cards.deck
    if (body.kind == "card_page") != (body.card_id is not None) or not card_ok:
        return respond(422, {"reason": "invalid", "fields": ["card_id"]}, new_guest)
    if body.situation is not None and body.situation not in SITUATIONS:
        return respond(422, {"reason": "invalid", "fields": ["situation"]}, new_guest)
    if body.count is not None and body.kind != "yes_no":
        return respond(422, {"reason": "invalid", "fields": ["count"]}, new_guest)
    day = limits.local_day(limits.resolve_tz(body.tz), now)
    ip_day = limits.utc_day(now)
    ip = limits.client_ip(request, ctx.settings.trust_cloudflare)
    ip_hash = ctx.salt.hash_ip(ip, now)
    hits = ctx.burst.hit(ip_hash, now)
    quota = who.quota  # stage 4.3 §5, 4.4b §2: the account's 3 when signed in, else this device's 2
    owner_id = who.user.id if who.user else None
    with ctx.db.connect() as conn:
        if who.user:  # stage 4.3 §8: a token that outlived its account — before any model call
            account_repo.refuse_deleted(conn, who.user.id)
        # stage 4.5 §5: the same request again (no answer reached the site) gets the reading it already made —
        # before every check and limit, since it takes nothing: no slot, no question check
        earlier = (repo.find_reading_by_request(conn, body.request_id, owner_id, guest_id, now)
                   if body.request_id is not None else None)
        ip_used = limits.used(conn, limits.ip_subject(ip_hash), ip_day)
        checks = limits.used(conn, limits.guard_ip_subject(ip_hash), ip_day)
        quota_used = limits.used(conn, quota.subject, day)
    if earlier is not None:
        return repeat_answer(ctx, earlier, quota, quota_used, new_guest)
    if limits.ip_blocked(ip_used):
        return respond(429, {"reason": "ip_limit", "remaining": 0}, new_guest)
    # В18: question checks count too, so crisis answers (no reading, no slot) also lead to Turnstile
    if limits.needs_turnstile(hits, max(ip_used, checks)) and not ctx.turnstile.verify(body.turnstile_token):
        return respond(403, {"reason": "turnstile", "sitekey": ctx.settings.turnstile_sitekey}, new_guest)
    # stage 4.5 §3: the question check comes before the daily limit, so a crisis question gets help even when
    # today's readings are used; its result is kept for the reading (guard_group, guard_source), never re-checked
    at_limit = quota_used >= quota.limit
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
            if at_limit:  # no reading can come of it anyway: the limit (its screen links to help), not "unavailable"
                return respond(429, {"reason": "limit", "remaining": 0}, new_guest)
            return respond(503, {"reason": "unavailable"}, new_guest)
    if guard is not None:  # the call is logged with the reading it is for — none at the limit or on a crisis
        with ctx.db.connect() as conn:
            flow.record_guard(conn, ctx, guard, body.lang, ip_day,
                              None if guard.group == "crisis" or at_limit else reading_id)
    if guard is not None and guard.group == "crisis":
        payload = flow.crisis_answer(ctx, body.lang, country_hint(ctx, request), body.tz, guard.violence)
        return respond(200, {**payload, "remaining": max(quota.limit - quota_used, 0)}, new_guest)
    if at_limit:
        return respond(429, {"reason": "limit", "remaining": 0}, new_guest)
    group = guard.group if guard else "ok"
    seed = new_seed()
    cards = draw_spread(seed, body.kind, ctx.cards.order, body.count)
    # §8.1, decisions 48–49: no verdict (and no votes) on health, pregnancy, death, courts or safety, also with three
    # cards; a question about another person gets one (redirect_person is not in NO_VERDICT_GROUPS);
    # three cards: the yes and no cards decide, "unclear" ones abstain, a tie or none is "unclear" (spread_verdict)
    with_verdict = body.kind == "yes_no" and group not in NO_VERDICT_GROUPS
    reading = {
        "id": reading_id, "guest_id": guest_id, "user_id": who.user.id if who.user else None,
        "lang": body.lang, "kind": body.kind, "question": question,
        "topic": body.topic, "situation": body.situation, "source_card_id": body.card_id, "cards": cards,
        "seed": seed, "verdict": ctx.cards.verdict(cards) if with_verdict else None, "guard_group": group,
        "guard_source": guard.source if guard else None,  # final review I2: only 'terms'/'model' feed the memory
        "request_id": body.request_id,
        # an account's readings stay until it deletes them; a guest's live GUEST_RETENTION_DAYS (stage 4.3 §4)
        "created_at": now, "expires_at": None if who.user else now + timedelta(days=GUEST_RETENTION_DAYS),
    }
    try:
        with ctx.db.connect() as conn:
            if who.user:  # and again in the insert transaction: the account may have gone meanwhile
                account_repo.lock_account(conn, who.user.id)  # R4: takes turns with delete_account
                account_repo.refuse_deleted(conn, who.user.id)
            # the insert first: a parallel request with the same request_id waits here and then finds this one
            if not repo.insert_reading(conn, reading):
                raise Repeated()
            count = limits.take_reading_slots(conn, quota, day, ip_hash, ip_day)  # §8.11: atomic
    except limits.LimitReached as exc:
        return respond(429, {"reason": exc.reason, "remaining": 0}, new_guest)
    except psycopg.errors.CheckViolation as exc:  # 008 not applied yet: the same answer as an unmigrated database
        raise DatabaseUnavailable("readings_verdict_allowed: migration 008 has not run yet") from exc
    except Repeated:
        with ctx.db.connect() as conn:
            earlier = repo.find_reading_by_request(conn, body.request_id, owner_id, guest_id, now)
            quota_used = limits.used(conn, quota.subject, day)
        if earlier is None:  # the number belongs to an expired reading not purged yet (a hand-made request)
            return respond(409, {"reason": "request_id"}, new_guest)
        return repeat_answer(ctx, earlier, quota, quota_used, new_guest)
    view = flow.reading_view(ctx, reading, owner=True)
    return respond(201, {**view, "remaining": quota.limit - count}, new_guest)


@router.get("/readings/{reading_id}")
def get_reading(reading_id: uuid.UUID, request: Request, tz: str | None = None):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    with ctx.db.connect() as conn:
        reading = repo.get_reading(conn, reading_id, ctx.clock())
        followups = repo.list_followups(conn, reading_id) if reading else []
    if reading is None:
        return not_found()
    owner = owns(who, reading)
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
    who = viewer(ctx, request)
    reading = load_reading(ctx, reading_id)
    if reading is None:
        return not_found()
    if not owns(who, reading):
        if reading["answer_shown"] == "crisis":
            return not_found()
        if reading["answer"] is None:
            return respond(403, {"reason": "owner_only"})
    return stream_response(flow.stream_reading(ctx, reading, country_hint(ctx, request), tz))


@router.post("/readings/{reading_id}/retry")
def retry_reading(reading_id: uuid.UUID, request: Request, tz: str | None = None):
    """After a fallback: a new attempt that does not use the daily limit, at most RETRY_LIMIT times (§5.1)."""
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    reading = load_reading(ctx, reading_id)
    if reading is None or not owns(who, reading):
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
