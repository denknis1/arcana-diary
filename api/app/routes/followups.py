"""Follow-ups (§2.3, §9.2, §9.4, §10): two free per reading; each next one uses a reading of the guest's
"3 per day" (the same counter as readings) and only with use_reading=true; the question goes through §3.

- Free follow-ups used, no use_reading: 402 {"reason": "confirm", "remaining": N} (the site warns "this will use
  1 reading"); no readings left: 402 {"reason": "plus", "remaining": 0}.
- Before the question check calls a model, every request takes an attempt of the reading (FOLLOWUP_ATTEMPTS) and of
  the address (IP_FOLLOWUP_LIMIT per UTC day): 429 "attempts" / "ip_limit"; exhausted attempts answer 429 before
  any 402 (nobody is asked to confirm a follow-up that cannot happen). Over the guard's budget a question that
  only the model can check is 503 and takes nothing (м1).
- A paid follow-up takes its reading in the transaction that inserts it, after the question check, so a crisis
  answer of the check takes none. A failed paid follow-up gives it back (reader/followups.py); the reader's
  [[crisis]] marker does not (§9.5).
"""
import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from app import limits, repo
from app.config import FOLLOWUP_ATTEMPTS
from app.context import get_ctx
from app.reader import flow
from app.reader.followups import stream_followup
from app.routes.common import country_hint, not_found, owns, respond, stream_response, viewer
from app.routes.readings import clean, reject_nul
from app.safety.guard import GuardUnavailable

router = APIRouter(prefix="/api")


class FollowupIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    tz: str | None = Field(default=None, max_length=64)
    use_reading: bool = False  # §10.1: the person confirmed that a follow-up after the free ones uses a reading

    _no_nul = field_validator("question", "tz", mode="after")(reject_nul)


@router.post("/readings/{reading_id}/followups")
def create_followup(reading_id: uuid.UUID, body: FollowupIn, request: Request):
    ctx = get_ctx(request)
    now = ctx.clock()
    who = viewer(ctx, request)
    with ctx.db.connect() as conn:
        reading = repo.get_reading(conn, reading_id, now)
        if reading:
            for paid_day in repo.delete_stale_followups(conn, reading_id, now - repo.STREAM_CLAIM_STALE):
                if paid_day is not None:  # cut by a crash: the reading goes back to the owner (stage 4.3 §5)
                    limits.give_back_slot(conn, limits.owner_quota(reading).subject, paid_day)
        previous = repo.list_followups(conn, reading_id) if reading else []
    if reading is None or not owns(who, reading):
        return not_found()
    if reading["answer"] is None:
        return respond(409, {"reason": "no_answer"})
    if reading["answer_shown"] in ("fallback", "crisis"):  # nothing to follow up on: retry first, or no reading
        return respond(409, {"reason": reading["answer_shown"]})
    if any(f["answer"] is None for f in previous):
        return respond(409, {"reason": "busy"})
    question = clean(body.question)
    if question is None:
        return respond(422, {"reason": "invalid", "fields": ["question"]})
    if reading["followup_attempts"] >= FOLLOWUP_ATTEMPTS:  # м13: never ask to confirm what cannot happen
        return respond(429, {"reason": "attempts"})
    paid_day = None
    if flow.followups_left(previous) == 0:  # §10.1: the free ones are used
        paid_day = limits.local_day(limits.resolve_tz(body.tz), now)
        with ctx.db.connect() as conn:
            left = limits.remaining(conn, limits.owner_quota(reading), paid_day)
        if left == 0:
            return respond(402, {"reason": "plus", "remaining": 0})
        if not body.use_reading:
            return respond(402, {"reason": "confirm", "remaining": left})
    allow_model = not flow.guard_over_budget(ctx)
    if not allow_model and not ctx.guard.answers_without_model(question):
        return respond(503, {"reason": "unavailable"})  # м1: nothing is taken for a question nobody checked
    day = limits.utc_day(now)
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    try:
        with ctx.db.connect() as conn:
            attempts = limits.take_followup_slots(conn, reading_id, ip_hash, day)
    except limits.LimitReached as exc:
        return respond(429, {"reason": exc.reason})
    try:
        guard = ctx.guard.classify(question, allow_model=allow_model)
    except GuardUnavailable:
        return respond(503, {"reason": "unavailable"})
    if guard.group == "crisis":
        with ctx.db.connect() as conn:
            flow.record_guard(conn, ctx, guard, reading["lang"], day, None)
        return respond(200, flow.crisis_answer(ctx, reading["lang"], country_hint(ctx, request), body.tz,
                                               guard.violence))
    followup = {"id": uuid.uuid4(), "reading_id": reading_id, "n": max((f["n"] for f in previous), default=0) + 1,
                "question": question, "guard_group": guard.group, "paid_day": paid_day, "created_at": now}
    with ctx.db.connect() as conn:
        flow.record_guard(conn, ctx, guard, reading["lang"], day, reading_id)
    try:
        with ctx.db.connect() as conn:
            inserted = repo.insert_followup(conn, followup)
            if inserted and paid_day is not None:  # atomic with the follow-up: never more than the owner's limit
                quota = limits.owner_quota(reading)  # stage 4.3 §5: the account if the reading has one, else the guest
                if limits.take_slot(conn, quota.subject, paid_day, quota.limit) is None:
                    raise limits.LimitReached("limit")
    except limits.LimitReached:  # a parallel reading or follow-up took the last one; the insert rolls back
        return respond(402, {"reason": "plus", "remaining": 0})
    if not inserted:
        return respond(409, {"reason": "busy"})
    return stream_response(stream_followup(ctx, reading, {**followup, "attempts": attempts}, previous, guard.group,
                                           country_hint(ctx, request), body.tz))
