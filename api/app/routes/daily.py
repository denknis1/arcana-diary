"""GET /api/daily (§2.6, §8.8; stage 8.1 §3): the card of the day and its text written ahead by the daily job. Signed
in, the card is the account's (one per local day on every device); otherwise this guest cookie's, as before. The
answer carries the streak and, for an account, today's evening mark. Never waits for the model; not counted in the
daily limit; rate-limited per address."""
from typing import Literal

from fastapi import APIRouter, Request

from app import account_repo, journal, limits, repo
from app.context import get_ctx
from app.daily import daily_text
from app.draw import daily_draw
from app.routes.common import respond, viewer

router = APIRouter(prefix="/api")


@router.get("/daily")
def daily(request: Request, lang: Literal["en", "es"], tz: str | None = None):
    ctx = get_ctx(request)
    now = ctx.clock()
    who = viewer(ctx, request)
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    if ctx.daily_burst.hit(ip_hash, now) > limits.DAILY_RATE_LIMIT:
        return respond(429, {"reason": "rate"}, who.new_guest)
    day = limits.local_day(limits.resolve_tz(tz), now)
    mark = None
    if who.user is not None:
        card_id, reversed_ = daily_draw(str(who.user.id), day, ctx.cards.order)
        with ctx.db.connect() as conn:
            account_repo.lock_account(conn, who.user.id)  # takes turns with delete_account
            account_repo.refuse_deleted(conn, who.user.id)
            row = repo.account_daily_draw(conn, who.user.id, day, card_id, reversed_)
            days = repo.draw_days(conn, who.user.id, None)
        card_id, reversed_ = row["card_id"], row["reversed"]
        mark = {"felt": row["felt"], "note": row["note"]}
    else:
        card_id, reversed_ = daily_draw(str(who.guest_id), day, ctx.cards.order)
        days = [day]
        if who.new_guest is None:  # a request without the cookie is not a returning guest: nothing to remember
            with ctx.db.connect() as conn:
                repo.record_daily_draw(conn, who.guest_id, day, card_id, reversed_)
                repo.touch_guest_push(conn, who.guest_id, now)
                days = repo.draw_days(conn, None, who.guest_id)
    streak, best = journal.streaks(days, day)
    payload = {"day": day.isoformat(),
               "card": {"card_id": card_id, "name": ctx.cards.name(card_id, lang), "reversed": reversed_},
               **daily_text(ctx, card_id, reversed_, lang, day),
               "streak": streak, "best_streak": best, "mark": mark}
    return respond(200, payload, who.new_guest)
