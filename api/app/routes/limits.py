"""How many readings are left today: for the account when signed in (5), else for this guest (3) (§1.1, §4.1,
stage 4.3 §5)."""
from fastapi import APIRouter, Request

from app import limits
from app.context import get_ctx
from app.routes.common import respond, viewer

router = APIRouter(prefix="/api")


@router.get("/limits")
def get_limits(request: Request, tz: str | None = None):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    quota = who.quota
    day = limits.local_day(limits.resolve_tz(tz), ctx.clock())
    with ctx.db.connect() as conn:
        used = limits.used(conn, quota.subject, day)
    return respond(200, {"limit": quota.limit, "used": used, "remaining": max(quota.limit - used, 0),
                         "day": day.isoformat()}, who.new_guest)
