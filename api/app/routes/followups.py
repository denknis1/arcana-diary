"""Follow-ups (§2.3, §9.2, §9.4, §10): two free per reading; each next one uses a reading of the owner's day
(the same counter as readings) and only with use_reading=true; the question goes through §3.

Order (stage 4.5 §3, owner decision 20.11.2026: help first, then the limits):
- the address: every request that may call the question check takes a slot of IP_FOLLOWUP_LIMIT per UTC day
  first (429 "ip_limit", except that a stop-phrase question still gets the crisis answer, no model called);
  over the guard's budget a question that only the model can check is 503 and takes nothing (м1);
- the question check: a crisis answer is 200 and takes no attempt and no reading;
- then 429 "attempts" (FOLLOWUP_ATTEMPTS per reading, never a confirm for what cannot happen), then 402: free
  follow-ups used and no use_reading — {"reason": "confirm", "remaining": N}; no readings left — {"reason":
  "plus", "remaining": 0};
- one transaction takes the attempt (its count is the follow-up's number n, never repeated) — which locks the
  reading — and reads the follow-ups again: one still being written, or the free ones used meanwhile by another
  tab while this question was checked, is 409 "busy"; then it inserts the follow-up and, for a paid one, takes its
  reading. The reader gets that fresh list. A failed paid follow-up gives it back (reader/followups.py); the
  reader's [[crisis]] marker does not (§9.5): the row stays as a tombstone ({"crisis": true}, not counted, no
  question) and the same request_id again replays the crisis answer with no model call; the hourly cleanup
  deletes tombstones after one day.
- request_id (stage 4.5 §5): the same number again in this reading gets that follow-up's stream — its saved
  answer, or "in_progress" while it is written — and takes nothing a second time; it is looked up in the list read
  first and again under the lock (a parallel twin). A tombstone is replayed the same way. `twin_or` turns a
  429 "attempts" / 402 "plus" that a parallel twin of the same request caused into the twin's stream.
"""
import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from app import limits, repo
from app.config import FOLLOWUP_ATTEMPTS, IP_FOLLOWUP_LIMIT
from app.context import get_ctx
from app.reader import flow
from app.reader.followups import replay_followup, stream_followup
from app.routes.common import country_hint, not_found, owns, respond, stream_response, viewer
from app.routes.readings import clean, reject_nul
from app.safety.guard import GuardUnavailable

router = APIRouter(prefix="/api")


class FollowupIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    tz: str | None = Field(default=None, max_length=64)
    use_reading: bool = False  # §10.1: the person confirmed that a follow-up after the free ones uses a reading
    request_id: uuid.UUID | None = None  # stage 4.5 §5: the site's number of this request; optional

    _no_nul = field_validator("question", "tz", mode="after")(reject_nul)


class Busy(Exception):
    """Another follow-up of the reading is still being written: the transaction rolls back (attempt included)."""


class Repeated(Exception):
    """A parallel request with the same request_id inserted its follow-up first: this one shows that one."""

    def __init__(self, followup: dict):
        super().__init__("repeated")
        self.followup = followup


def twin_or(ctx, request: Request, reading: dict, body: FollowupIn, status: int, refusal: dict):
    """Stage 4.5 review M2: a refusal that a parallel twin of this request caused (it took the last attempt or
    reading) shows the twin's follow-up instead, found in a new connection; otherwise the refusal."""
    if body.request_id is not None:
        with ctx.db.connect() as conn:
            same = next((f for f in repo.list_followups(conn, reading["id"]) if f["request_id"] == body.request_id),
                        None)
        if same is not None:
            return stream_response(replay_followup(ctx, reading, same, country_hint(ctx, request), body.tz))
    return respond(status, refusal)


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
    question = clean(body.question)
    if question is None:
        return respond(422, {"reason": "invalid", "fields": ["question"]})
    if body.request_id is not None:
        same = next((f for f in previous if f["request_id"] == body.request_id), None)
        if same is not None:  # stage 4.5 §5: the same request again
            return stream_response(replay_followup(ctx, reading, same, country_hint(ctx, request), body.tz))
    if any(f["answer"] is None for f in previous):
        return respond(409, {"reason": "busy"})
    allow_model = not flow.guard_over_budget(ctx)
    if not allow_model and not ctx.guard.answers_without_model(question):
        return respond(503, {"reason": "unavailable"})  # м1: nothing is taken for a question nobody checked
    day = limits.utc_day(now)
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    with ctx.db.connect() as conn:  # §9.2: the address first — it bounds the question checks
        address_ok = limits.take_slot(conn, limits.followup_ip_subject(ip_hash), day, IP_FOLLOWUP_LIMIT) is not None
    if not address_ok:
        # final review (Task 3): a stop-phrase needs no model, so help still comes when the address's slots are
        # used (mobile carriers share addresses); any other question is 429
        try:
            guard = ctx.guard.classify(question, allow_model=False)
        except GuardUnavailable:
            return respond(429, {"reason": "ip_limit"})
        if guard.group != "crisis":
            return respond(429, {"reason": "ip_limit"})
        with ctx.db.connect() as conn:
            flow.record_guard(conn, ctx, guard, reading["lang"], day, None)
        return respond(200, flow.crisis_answer(ctx, reading["lang"], country_hint(ctx, request), body.tz,
                                               guard.violence))
    try:
        guard = ctx.guard.classify(question, allow_model=allow_model)
    except GuardUnavailable:
        return respond(503, {"reason": "unavailable"})
    with ctx.db.connect() as conn:  # every check is counted, and a model call logged for the guard budget
        flow.record_guard(conn, ctx, guard, reading["lang"], day, None if guard.group == "crisis" else reading_id)
    if guard.group == "crisis":
        return respond(200, flow.crisis_answer(ctx, reading["lang"], country_hint(ctx, request), body.tz,
                                               guard.violence))
    if reading["followup_attempts"] >= FOLLOWUP_ATTEMPTS:  # м13: never ask to confirm what cannot happen
        return twin_or(ctx, request, reading, body, 429, {"reason": "attempts"})
    paid_day = None
    if flow.followups_left(previous) == 0:  # §10.1: the free ones are used
        paid_day = limits.local_day(limits.resolve_tz(body.tz), now)
        with ctx.db.connect() as conn:
            left = limits.remaining(conn, limits.owner_quota(reading), paid_day)
        if left == 0:
            return twin_or(ctx, request, reading, body, 402, {"reason": "plus", "remaining": 0})
        if not body.use_reading:
            return respond(402, {"reason": "confirm", "remaining": left})
    followup = {"id": uuid.uuid4(), "reading_id": reading_id, "question": question, "guard_group": guard.group,
                "paid_day": paid_day, "request_id": body.request_id, "created_at": now}
    try:
        with ctx.db.connect() as conn:
            attempts = limits.take_followup_attempt(conn, reading_id)  # locks the reading until the commit
            # read again under the lock: another tab (or a twin of this request) may have asked meanwhile
            current = repo.list_followups(conn, reading_id)
            twin = next((f for f in current if body.request_id and f["request_id"] == body.request_id), None)
            if twin is not None:
                raise Repeated(twin)
            if any(f["answer"] is None for f in current):
                raise Busy()
            if paid_day is None and flow.followups_left(current) == 0:  # the free ones went meanwhile
                raise Busy()  # the next press gets 402 confirm
            followup["n"] = attempts
            if not repo.insert_followup(conn, followup):
                raise Busy()
            if paid_day is not None:  # atomic with the follow-up: never more than the owner's limit
                quota = limits.owner_quota(reading)  # stage 4.3 §5: the account if the reading has one, else the guest
                if limits.take_slot(conn, quota.subject, paid_day, quota.limit) is None:
                    raise limits.LimitReached("limit")
    except limits.LimitReached as exc:  # the last attempt or reading went to a parallel request; all rolls back
        if exc.reason == "attempts":
            return twin_or(ctx, request, reading, body, 429, {"reason": "attempts"})
        return twin_or(ctx, request, reading, body, 402, {"reason": "plus", "remaining": 0})
    except Busy:
        return respond(409, {"reason": "busy"})
    except Repeated as exc:
        return stream_response(replay_followup(ctx, reading, exc.followup, country_hint(ctx, request), body.tz))
    return stream_response(stream_followup(ctx, reading, {**followup, "attempts": attempts}, current, guard.group,
                                           country_hint(ctx, request), body.tz))
