"""Shared bits for routes: JSON answers that may set the guest cookie, SSE responses, who is asking."""
import uuid
from dataclasses import dataclass

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse

from app import auth, limits
from app.auth import User
from app.context import get_ctx
from app.limits import set_guest_cookie

SSE_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}


def respond(status: int, payload: dict, new_guest=None) -> JSONResponse:
    response = JSONResponse(status_code=status, content=jsonable_encoder(payload))
    if new_guest is not None:
        set_guest_cookie(response, new_guest)
    return response


def not_found() -> JSONResponse:
    return respond(404, {"reason": "not_found"})


def stream_response(events, new_guest=None) -> StreamingResponse:
    response = StreamingResponse(events, media_type="text/event-stream", headers=SSE_HEADERS)
    if new_guest is not None:
        set_guest_cookie(response, new_guest)
    return response


def sign_in_required() -> JSONResponse:
    """An account-only address asked without a token (a bad token is 401 "auth" instead)."""
    return respond(401, {"reason": "sign_in"})


@dataclass(frozen=True)
class Viewer:
    """Who is asking: the device (guest cookie; a new id when it is missing) and, when signed in, the account."""
    guest_id: uuid.UUID
    new_guest: uuid.UUID | None  # set when the request had no cookie: the answer may set it
    user: User | None

    @property
    def quota(self) -> limits.Quota:
        """Stage 4.3 §5, 4.4b §2: signed in — the account's 3 a day on every device; otherwise this device's 2."""
        return limits.user_quota(self.user.id) if self.user else limits.guest_quota(self.guest_id)


_UNCHECKED = object()


def check_token(request: Request) -> None:
    """A dependency of every /api/* router (app/main.py): a Bearer token, when present, is checked before anything
    else — before the body or the query is validated — so a bad token is 401 on every route, the card of the day
    included, and never a silent guest. Raises auth.AuthError / auth.AuthUnavailable (401 / 503)."""
    request.state.user = auth.current_user(get_ctx(request).auth, request)


def viewer(ctx, request) -> Viewer:
    """The account comes from check_token (checked once per request); the device from the guest cookie."""
    user = getattr(request.state, "user", _UNCHECKED)
    if user is _UNCHECKED:  # a route outside the /api routers
        user = auth.current_user(ctx.auth, request)
    guest_id, is_new = limits.guest_from_request(request)
    return Viewer(guest_id, guest_id if is_new else None, user)


def owns(who: Viewer, reading: dict) -> bool:
    """Stage 4.3 §6 (owner decision 19.11.2026): a reading in an account belongs to that account only — a device
    cookie alone sees it as a shared link; a guest reading belongs to the device that made it (guest cookie)."""
    if reading.get("user_id") is not None:
        return who.user is not None and reading["user_id"] == who.user.id
    return who.new_guest is None and reading["guest_id"] == who.guest_id


def country_hint(ctx, request) -> str | None:
    """CF-IPCountry only behind Cloudflare (TRUST_CLOUDFLARE, §8.2); for the crisis answer only."""
    return limits.client_country(request, ctx.settings.trust_cloudflare)
