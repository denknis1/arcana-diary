"""Shared bits for routes: JSON answers that may set the guest cookie, SSE responses, who is asking."""
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse

from app import limits
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


def is_owner(request, reading: dict) -> bool:
    guest_id, _ = limits.guest_from_request(request)
    return reading["guest_id"] == guest_id


def country_hint(ctx, request) -> str | None:
    """CF-IPCountry only behind Cloudflare (TRUST_CLOUDFLARE, §8.2); for the crisis answer only."""
    return limits.client_country(request, ctx.settings.trust_cloudflare)
