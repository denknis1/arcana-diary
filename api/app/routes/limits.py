"""How many readings are left today for this guest (§1.1, §4.1)."""
from fastapi import APIRouter, Request

from app import limits
from app.config import DAILY_LIMIT
from app.context import get_ctx
from app.routes.common import respond

router = APIRouter(prefix="/api")


@router.get("/limits")
def get_limits(request: Request, tz: str | None = None):
    ctx = get_ctx(request)
    guest_id, is_new = limits.guest_from_request(request)
    day = limits.local_day(limits.resolve_tz(tz), ctx.clock())
    with ctx.db.connect() as conn:
        used = limits.used(conn, limits.guest_subject(guest_id), day)
    return respond(200, {"limit": DAILY_LIMIT, "used": used, "remaining": max(DAILY_LIMIT - used, 0),
                         "day": day.isoformat()}, guest_id if is_new else None)
