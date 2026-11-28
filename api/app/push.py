"""The morning reminder (stage 8.1 §2.5, §3): every PUSH_JOB_INTERVAL_S the job looks for subscriptions whose local
hour has come and sends one Web Push message — at most one a day per browser, none on a day the owner's card is
already open (the day is marked anyway). The message names no card: it carries only the language, and the service
worker shows "Your card for today is waiting" (the lock screen). No model is called.

Delivery: 2xx — the failure count goes back to 0; 404 / 410 — the browser dropped the subscription, the row goes at
once; 401 / 403 — the push service refused our VAPID key (a server problem, not the browser's): logged, not counted,
so a key mistake never wipes everyone's subscriptions; anything else (5xx, 429, a network error) — one more failure
in a row, and MAX_FAILS in a row delete the row. Nothing about the person or the endpoint is logged.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

import httpx

from app import repo, webpush
from app.limits import resolve_tz

log = logging.getLogger("arcana.push")

SEND_WINDOW_H = 2      # from the chosen hour up to 2 hours later; a day missed by then is skipped, not sent late
MAX_FAILS = 3          # spec §3: three failed deliveries in a row delete the subscription
GONE = frozenset({404, 410})
REFUSED_KEY = frozenset({401, 403})
POST_TIMEOUT_S = 10.0


def due_day(sub: dict, now: datetime) -> date | None:
    """The subscriber's local day when its hour has come and that day has had no reminder yet; else None."""
    local = now.astimezone(resolve_tz(sub["tz"]))
    if sub["last_sent_day"] == local.date():
        return None
    start = local.replace(hour=sub["hour"], minute=0, second=0, microsecond=0)
    return local.date() if start <= local < start + timedelta(hours=SEND_WINDOW_H) else None


def http_post(url: str, headers: dict, body: bytes) -> int:
    return httpx.post(url, headers=headers, content=body, timeout=POST_TIMEOUT_S, follow_redirects=False).status_code


def send_due(ctx, now: datetime, post=http_post) -> dict[str, int]:
    counts = {"sent": 0, "skipped": 0, "failed": 0, "deleted": 0}
    if ctx.vapid is None:
        return counts
    with ctx.db.connect() as conn:
        subs = repo.push_subscriptions(conn)
    for sub in subs:
        day = due_day(sub, now)
        if day is None:
            continue
        with ctx.db.connect() as conn:
            if not repo.claim_push_day(conn, sub["id"], day):
                continue
            opened = repo.opened_daily(conn, sub["user_id"], sub["guest_id"], day)
        if opened:
            counts["skipped"] += 1
            continue
        headers, body = webpush.push_request(sub["endpoint"], sub["p256dh"], sub["auth"], {"lang": sub["lang"]},
                                             ctx.vapid, ctx.settings.vapid_subject, now.timestamp())
        try:
            status = post(sub["endpoint"], headers, body)
        except httpx.HTTPError:
            status = 0
        with ctx.db.connect() as conn:
            if 200 <= status < 300:
                repo.push_delivered(conn, sub["id"])
                counts["sent"] += 1
            elif status in GONE:
                repo.delete_push_by_id(conn, sub["id"])
                counts["deleted"] += 1
            elif status in REFUSED_KEY:
                log.error("a push service refused our VAPID key (HTTP %s): check VAPID_* in deploy/.env", status)
                counts["failed"] += 1
            elif (repo.push_failed(conn, sub["id"]) or 0) >= MAX_FAILS:
                repo.delete_push_by_id(conn, sub["id"])
                counts["deleted"] += 1
            else:
                counts["failed"] += 1
    return counts


async def push_loop(ctx, interval_s: float) -> None:
    while True:
        try:
            counts = await asyncio.to_thread(send_due, ctx, ctx.clock())
            if any(counts.values()):
                log.info("morning reminders: %s", counts)
        except Exception:  # a failed run must not stop the loop or the API
            log.exception("morning reminder run failed")
        await asyncio.sleep(interval_s)
