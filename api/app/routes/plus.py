""""Tell me when Plus opens" (spec 2026-11-19 stage 4.3 §8). An e-mail and a language; signed in, the e-mail comes
from the token. A repeat of the same e-mail is no error and answers the same as a new one; at most
WAITLIST_IP_LIMIT requests per address per UTC day."""
import re
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from app import account_repo, limits
from app.config import WAITLIST_IP_LIMIT
from app.context import get_ctx
from app.routes.common import respond, viewer
from app.routes.readings import reject_nul

router = APIRouter(prefix="/api")

EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class WaitlistIn(BaseModel):
    email: str | None = Field(default=None, max_length=254)
    lang: Literal["en", "es"]

    _no_nul = field_validator("email", mode="after")(reject_nul)


@router.post("/plus/waitlist")
def join_waitlist(body: WaitlistIn, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    now = ctx.clock()
    email = (who.user.email if who.user and who.user.email else body.email or "").strip().lower()
    if len(email) > 254 or not EMAIL.fullmatch(email):
        return respond(422, {"reason": "invalid", "fields": ["email"]})
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    with ctx.db.connect() as conn:
        if who.user:
            account_repo.refuse_deleted(conn, who.user.id)
        if limits.take_slot(conn, limits.waitlist_ip_subject(ip_hash), limits.utc_day(now), WAITLIST_IP_LIMIT) is None:
            return respond(429, {"reason": "ip_limit"})
        account_repo.join_waitlist(conn, email, body.lang, who.user.id if who.user else None, now)
    return respond(200, {"ok": True})
