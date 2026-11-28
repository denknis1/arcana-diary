"""The Card of the Day (§2.6, §8.8; stage 8.1 §2-§4).

- GET /api/daily: the card and its text written ahead by the daily job. Signed in, the card is the account's (one
  per local day on every device); otherwise this guest cookie's, as before. The answer carries the streak and, for
  an account, today's evening mark. Never waits for the model; not counted in the daily limit; rate-limited per
  address.
- GET /api/daily/calendar and PUT /api/daily/{day} count against the same per-address limit as GET /api/daily.
- GET /api/daily/calendar?month=YYYY-MM: the account's cards of a month with their texts, marks and notes, the
  streaks and the month's most frequent card; the free calendar opens the current and the previous month, older
  months answer "locked" (kept, for Plus). A guest gets this device's last CALENDAR_GUEST_DAYS days, without marks
  or notes, whatever the month.
- PUT /api/daily/{day} {"felt", "note"} (signed in): the evening mark and the one-line note of a day that has a
  card; a day without one is 404 (a card is never drawn after the fact).

The note and the mark are stored exactly as sent, returned only as JSON and shown as text; no model and no event
ever gets them.
"""
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import account_repo, journal, limits, repo
from app.config import CALENDAR_GUEST_DAYS, DAILY_NOTE_MAX_CHARS
from app.context import get_ctx
from app.daily import daily_text, past_text
from app.draw import daily_draw
from app.routes.common import not_found, respond, sign_in_required, viewer
from app.routes.readings import reject_nul

router = APIRouter(prefix="/api")


def too_fast(ctx, request: Request, now) -> bool:
    """One count per address for the three Card of the Day routes (the same limit as GET /api/daily)."""
    ip_hash = ctx.salt.hash_ip(limits.client_ip(request, ctx.settings.trust_cloudflare), now)
    return ctx.daily_burst.hit(ip_hash, now) > limits.DAILY_RATE_LIMIT


@router.get("/daily")
def daily(request: Request, lang: Literal["en", "es"], tz: str | None = None):
    ctx = get_ctx(request)
    now = ctx.clock()
    who = viewer(ctx, request)
    if too_fast(ctx, request, now):
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


class DailyMark(BaseModel):
    model_config = ConfigDict(extra="forbid")
    felt: Literal["yes", "partly", "no"] | None = None
    note: str | None = Field(default=None, max_length=DAILY_NOTE_MAX_CHARS)

    _no_nul = field_validator("note", mode="after")(reject_nul)


def calendar_day(ctx, row: dict, lang: str, with_mark: bool) -> dict:
    item = {"day": row["day"].isoformat(),
            "card": {"card_id": row["card_id"], "name": ctx.cards.name(row["card_id"], lang),
                     "reversed": row["reversed"]},
            **past_text(ctx, row["card_id"], row["reversed"], lang, row["cached_text"])}
    if with_mark:
        item.update(felt=row["felt"], note=row["note"])
    return item


@router.get("/daily/calendar")
def calendar(request: Request, lang: Literal["en", "es"], month: str | None = Query(default=None, max_length=7),
             tz: str | None = None):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if too_fast(ctx, request, ctx.clock()):
        return respond(429, {"reason": "rate"}, who.new_guest)
    today = limits.local_day(limits.resolve_tz(tz), ctx.clock())
    if who.user is None:
        rows, days = [], []
        if who.new_guest is None:
            with ctx.db.connect() as conn:
                rows = repo.calendar_rows(conn, None, who.guest_id, today - timedelta(days=CALENDAR_GUEST_DAYS - 1),
                                          today + timedelta(days=1), lang)
                days = repo.draw_days(conn, None, who.guest_id)
        streak, best = journal.streaks(days, today)
        return respond(200, {"guest": True, "today": today.isoformat(), "month": None, "months": [], "locked": False,
                             "streak": streak, "best_streak": best, "top_card": None,
                             "days": [calendar_day(ctx, r, lang, with_mark=False) for r in rows]}, who.new_guest)
    first = journal.parse_month(month) if month else today.replace(day=1)
    if first is None:
        return respond(422, {"reason": "invalid", "fields": ["month"]})
    oldest, current = journal.free_months(today)
    locked = first < oldest
    with ctx.db.connect() as conn:
        days = repo.draw_days(conn, who.user.id, None)
        rows = [] if locked else repo.calendar_rows(conn, who.user.id, None, first, journal.next_month(first), lang)
    streak, best = journal.streaks(days, today)
    top = journal.top_card(rows)
    return respond(200, {
        "guest": False, "today": today.isoformat(), "month": journal.month_key(first),
        "months": [journal.month_key(oldest), journal.month_key(current)], "locked": locked,
        "streak": streak, "best_streak": best,
        "top_card": {"card_id": top[0], "name": ctx.cards.name(top[0], lang), "count": top[1]} if top else None,
        "days": [calendar_day(ctx, r, lang, with_mark=True) for r in rows]}, who.new_guest)


@router.put("/daily/{day}")
def mark_day(day: date, body: DailyMark, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if too_fast(ctx, request, ctx.clock()):
        return respond(429, {"reason": "rate"}, who.new_guest)
    if who.user is None:
        return sign_in_required()  # spec §2.4: marks and notes only after sign-in
    fields = body.model_dump(include=body.model_fields_set)
    if fields.get("note") is not None and not fields["note"].strip():
        fields["note"] = None  # an empty note is no note
    with ctx.db.connect() as conn:
        row = repo.set_daily_mark(conn, who.user.id, day, fields, ctx.clock())
    if row is None:
        return not_found()
    return respond(200, {"day": row["day"].isoformat(), "felt": row["felt"], "note": row["note"],
                         "noted_at": row["noted_at"]})
