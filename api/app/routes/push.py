"""Browser reminders (stage 8.1 §2.5, §3): "Remind me each morning" under the Card of the Day.

- GET /api/push/key → {"enabled", "public_key"}: the VAPID public key the browser subscribes with; "enabled" false
  (and no key) while VAPID_* is not set in deploy/.env — the site then offers nothing.
- POST /api/push/subscription {"endpoint", "keys": {"p256dh", "auth"}, "hour", "tz", "lang"} → 201 {"hour", "tz"}:
  stores the browser's subscription for the account when signed in, otherwise for this guest cookie. Only an https
  address of a known push service is taken (422 "endpoint"), only real keys (422 "keys"); reminders off → 503
  "push_off"; more than PUSH_PER_MINUTE a minute from one address → 429 "rate"; more than
  PUSH_SUBSCRIPTIONS_PER_OWNER browsers of one owner → 429 "subscriptions". Asking again replaces the row.
- DELETE /api/push/subscription {"endpoint"} → 204: whoever knows the endpoint is that browser; always 204, so the
  answer tells nothing about other people's rows.
"""
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app import account_repo, limits, repo, webpush
from app.config import PUSH_PER_MINUTE, PUSH_SUBSCRIPTIONS_PER_OWNER
from app.context import get_ctx
from app.routes.common import respond, viewer

router = APIRouter(prefix="/api")


class PushKeys(BaseModel):
    model_config = ConfigDict(extra="forbid")
    p256dh: str = Field(max_length=200)
    auth: str = Field(max_length=50)


class PushIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str = Field(max_length=webpush.ENDPOINT_MAX)
    keys: PushKeys
    hour: int = Field(ge=0, le=23)
    tz: str | None = Field(default=None, max_length=64)
    lang: Literal["en", "es"]


class PushOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str = Field(max_length=webpush.ENDPOINT_MAX)


@router.get("/push/key")
def push_key(request: Request):
    vapid = get_ctx(request).vapid
    return respond(200, {"enabled": vapid is not None, "public_key": vapid.public_key if vapid else ""})


@router.post("/push/subscription")
def subscribe(body: PushIn, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    now = ctx.clock()
    if ctx.vapid is None:
        return respond(503, {"reason": "push_off"}, who.new_guest)
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    if ctx.push_burst.hit(ip_hash, now) > PUSH_PER_MINUTE:
        return respond(429, {"reason": "rate"}, who.new_guest)
    if not webpush.valid_endpoint(body.endpoint):
        return respond(422, {"reason": "invalid", "fields": ["endpoint"]}, who.new_guest)
    if not webpush.valid_keys(body.keys.p256dh, body.keys.auth):
        return respond(422, {"reason": "invalid", "fields": ["keys"]}, who.new_guest)
    user_id = who.user.id if who.user else None
    guest_id = None if who.user else who.guest_id
    tz = limits.resolve_tz(body.tz).key
    with ctx.db.connect() as conn:
        if who.user:
            account_repo.lock_account(conn, who.user.id)  # takes turns with delete_account
            account_repo.refuse_deleted(conn, who.user.id)
        if repo.count_push(conn, user_id, guest_id, body.endpoint) >= PUSH_SUBSCRIPTIONS_PER_OWNER:
            return respond(429, {"reason": "subscriptions"}, who.new_guest)
        repo.upsert_push(conn, {"user_id": user_id, "guest_id": guest_id, "endpoint": body.endpoint,
                                "p256dh": body.keys.p256dh, "auth": body.keys.auth, "lang": body.lang, "tz": tz,
                                "hour": body.hour, "now": now})
    return respond(201, {"hour": body.hour, "tz": tz}, who.new_guest)


@router.delete("/push/subscription")
def unsubscribe(body: PushOut, request: Request):
    ctx = get_ctx(request)
    with ctx.db.connect() as conn:
        repo.delete_push(conn, body.endpoint)
    return Response(status_code=204)
