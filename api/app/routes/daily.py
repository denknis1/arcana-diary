"""GET /api/daily (§2.6, §8.8): a personal card per guest and local day, a text written ahead by the daily job.
Never waits for the model; not counted in the daily limit; rate-limited per address."""
from typing import Literal

from fastapi import APIRouter, Request

from app import limits, repo
from app.context import get_ctx
from app.daily import daily_text
from app.draw import daily_draw
from app.routes.common import respond

router = APIRouter(prefix="/api")


@router.get("/daily")
def daily(request: Request, lang: Literal["en", "es"], tz: str | None = None):
    ctx = get_ctx(request)
    now = ctx.clock()
    guest_id, is_new = limits.guest_from_request(request)
    new_guest = guest_id if is_new else None
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    if ctx.daily_burst.hit(ip_hash, now) > limits.DAILY_RATE_LIMIT:
        return respond(429, {"reason": "rate"}, new_guest)
    day = limits.local_day(limits.resolve_tz(tz), now)
    card_id, reversed_ = daily_draw(str(guest_id), day, ctx.cards.order)
    if not is_new:  # a request without the cookie is not a returning guest: nothing to remember
        with ctx.db.connect() as conn:
            repo.record_daily_draw(conn, guest_id, day, card_id, reversed_)
    payload = {"day": day.isoformat(),
               "card": {"card_id": card_id, "name": ctx.cards.name(card_id, lang), "reversed": reversed_},
               **daily_text(ctx, card_id, reversed_, lang, day)}
    return respond(200, payload, new_guest)
