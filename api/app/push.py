"""The morning reminder (stage 8.1 §2.5, §3): every PUSH_JOB_INTERVAL_S the job looks for subscriptions whose local
hour has come and sends one Web Push message — at most one a day per browser, none on a day the owner's card is
already open (the day is marked anyway). The message names no card: it carries only the language, and the service
worker shows "Your card for today is waiting" (the lock screen). No model is called.

Delivery: 2xx — the failure count goes back to 0; 404 / 410 — the browser dropped the subscription, the row goes at
once; 401 / 403 — the push service refused our VAPID key (a server problem, not the browser's): logged, not counted,
so a key mistake never wipes everyone's subscriptions; any other HTTP answer (5xx, 429...) — one more failure
in a row, and MAX_FAILS in a row delete the row; our own network errors (no answer) are not counted, so an outage
never wipes subscriptions. Nothing about the person is logged, the endpoint only as a short hash.
"""
import asyncio
import logging
from datetime import date, datetime, time, timedelta

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
    """The local day whose reminder window [hour, hour+2h) holds now and that has had no reminder yet; else None.
    The window may end on the next local day (hour 23), so yesterday's window is looked at too."""
    zone = resolve_tz(sub["tz"])
    local = now.astimezone(zone)
    for day in (local.date(), local.date() - timedelta(days=1)):
        start = datetime.combine(day, time(sub["hour"]), tzinfo=zone)
        if start <= local < start + timedelta(hours=SEND_WINDOW_H):
            return None if sub["last_sent_day"] == day else day
    return None


def http_post(url: str, headers: dict, body: bytes) -> int:
    return httpx.post(url, headers=headers, content=body, timeout=POST_TIMEOUT_S, follow_redirects=False).status_code


def send_due(ctx, now: datetime, post=http_post) -> dict[str, int]:
    counts = {"sent": 0, "skipped": 0, "failed": 0, "deleted": 0}
    if ctx.vapid is None:
        return counts
    with ctx.db.connect() as conn:
        subs = repo.push_subscriptions(conn)
    for sub in subs:
        try:
            _send_one(ctx, sub, now, post, counts)
        except Exception as exc:  # one bad row never stops the run; the type only, the endpoint is a secret
            counts["failed"] += 1
            log.error("a reminder failed (%s) for subscription %s", type(exc).__name__,
                      webpush.endpoint_tag(sub.get("endpoint")))
    return counts


def _send_one(ctx, sub: dict, now: datetime, post, counts: dict) -> None:
    day = due_day(sub, now)
    if day is None:
        return
    if not webpush.valid_endpoint(sub["endpoint"]):  # a row that got in before the check was strict
        with ctx.db.connect() as conn:
            repo.delete_push_by_id(conn, sub["id"])
        counts["deleted"] += 1
        log.warning("deleted a subscription with an invalid endpoint (%s)", webpush.endpoint_tag(sub["endpoint"]))
        return
    with ctx.db.connect() as conn:
        if not repo.claim_push_day(conn, sub["id"], day):
            return
        opened = repo.opened_daily(conn, sub["user_id"], sub["guest_id"], day)
    if opened:
        counts["skipped"] += 1
        return
    counted = True
    try:
        headers, body = webpush.push_request(sub["endpoint"], sub["p256dh"], sub["auth"], {"lang": sub["lang"]},
                                             ctx.vapid, ctx.settings.vapid_subject, now.timestamp())
        status = post(sub["endpoint"], headers, body)
    except httpx.RequestError:  # our own network (connect, timeout, DNS): no answer, so the browser is not at fault
        status, counted = 0, False
    except Exception as exc:  # the row cannot be sent at all (bad keys, bad address): counts like a refusal
        status = 0
        log.error("a reminder could not be sent (%s) to subscription %s", type(exc).__name__,
                  webpush.endpoint_tag(sub["endpoint"]))
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
        elif counted and (repo.push_failed(conn, sub["id"]) or 0) >= MAX_FAILS:
            repo.delete_push_by_id(conn, sub["id"])
            counts["deleted"] += 1
        else:
            counts["failed"] += 1


async def push_loop(ctx, interval_s: float) -> None:
    while True:
        try:
            counts = await asyncio.to_thread(send_due, ctx, ctx.clock())
            if any(counts.values()):
                log.info("morning reminders: %s", counts)
        except Exception:  # a failed run must not stop the loop or the API
            log.exception("morning reminder run failed")
        await asyncio.sleep(interval_s)
