"""POST /api/events (spec 2026-11-19 stage 4.4a §6): {"name", "tool", "lang", "params"} → 204. The site sends it
with navigator.sendBeacon; nothing here reads or sets a cookie, and the answer carries no body. More than
EVENTS_PER_MINUTE requests a minute from one address, or more than EVENTS_GLOBAL_PER_MINUTE from all addresses together
(a flood from many addresses) → 429 {"reason": "rate"}, nothing stored."""
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app import events, limits
from app.config import EVENTS_GLOBAL_PER_MINUTE, EVENTS_PER_MINUTE
from app.context import get_ctx
from app.routes.common import respond

router = APIRouter(prefix="/api")
ALL_ADDRESSES = "all"  # the key of the global counter; address keys are sha256 hex, so they never collide


class EventIn(BaseModel):
    name: str = Field(max_length=40)
    tool: str | None = Field(default=None, max_length=40)
    lang: Literal["en", "es"]
    params: dict[str, Any] = Field(default_factory=dict, max_length=8)


@router.post("/events")
def post_event(body: EventIn, request: Request):
    ctx = get_ctx(request)
    now = ctx.clock()
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    if ctx.events_burst.hit(ip_hash, now) > EVENTS_PER_MINUTE:
        return respond(429, {"reason": "rate"})
    if ctx.events_burst.hit(ALL_ADDRESSES, now) > EVENTS_GLOBAL_PER_MINUTE:
        return respond(429, {"reason": "rate"})
    try:
        events.check_event(body.name, body.tool, body.params)
    except events.InvalidEvent as exc:
        return respond(422, {"reason": "invalid", "fields": [exc.field]})
    with ctx.db.connect() as conn:
        events.record_event(conn, body.name, body.tool, body.lang, body.params, now)
    return Response(status_code=204)
