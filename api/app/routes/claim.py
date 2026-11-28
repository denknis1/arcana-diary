"""Moving guest readings into an account (spec 2026-11-19 stage 4.3 §4).

- POST /api/readings/{id}/claim-token: only the device that made the reading (its guest cookie) gets a one-time
  token for it — random, only its sha256 is stored, valid CLAIM_TOKEN_DAYS, at most CLAIM_TOKENS_PER_READING live
  at once. The site puts it into the sign-in link (/diary?claim=<token>), so the reading can be saved from whatever
  device the person signs in on. A shared link to the reading is not enough to take it.
- POST /api/account/claim {"tokens": [...], "device": true | false} (signed in): moves every unexpired guest reading
  of this device and the readings of the tokens into the account. A reading that already belongs to an account never
  moves; an unknown, used or expired token is skipped. A moved reading loses its expiry; the day slots the guest used
  stay with the guest. Stage 4.4b §4 (owner decision 12): "device": false moves only the readings of the tokens — the
  site sends it when the e-mail link is opened on a device where the sign-in was not started (someone else's guest
  readings stay there); left out, it is true, as in 4.3.
- Stage 8.1 §3: with "device" true the same call also moves this cookie's cards of the day (a day the account
  already has keeps the account's card) and its browser reminders. The answer stays {"claimed": [...]}.
"""
import secrets
import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, StrictBool

from app import account_repo, repo
from app.config import CLAIM_TOKEN_DAYS, CLAIM_TOKENS_PER_READING
from app.context import get_ctx
from app.routes.common import not_found, respond, sign_in_required, viewer

router = APIRouter(prefix="/api")

ClaimToken = Annotated[str, Field(min_length=1, max_length=100)]


class ClaimIn(BaseModel):
    tokens: list[ClaimToken] = Field(default_factory=list, max_length=20)
    device: StrictBool = True  # stage 4.4b §4: false — this device's guest readings stay where they are


@router.post("/readings/{reading_id}/claim-token")
def create_claim_token(reading_id: uuid.UUID, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    now = ctx.clock()
    with ctx.db.connect() as conn:
        reading = repo.get_reading(conn, reading_id, now)
        if reading is None or who.new_guest is not None or reading["guest_id"] != who.guest_id:
            return not_found()  # only the device that made it; nobody else learns that the reading exists
        if reading["user_id"] is not None:
            return respond(409, {"reason": "in_diary"})
        if account_repo.live_claim_tokens(conn, reading_id, now) >= CLAIM_TOKENS_PER_READING:
            return respond(429, {"reason": "tokens"})
        token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(days=CLAIM_TOKEN_DAYS)
        account_repo.insert_claim_token(conn, account_repo.token_hash(token), reading_id, now, expires_at)
    return respond(201, {"token": token, "expires_at": expires_at})


@router.post("/account/claim")
def claim(request: Request, body: ClaimIn | None = None):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()
    now = ctx.clock()
    hashes = [account_repo.token_hash(token) for token in (body.tokens if body else [])]
    device = body.device if body else True
    with ctx.db.connect() as conn:
        account_repo.ensure_profile(conn, who.user.id, now)
        this_device = device and who.new_guest is None
        moved = account_repo.claim_device(conn, who.user.id, who.guest_id, now) if this_device else []
        moved += [i for i in account_repo.claim_by_tokens(conn, who.user.id, hashes, now) if i not in moved]
        if this_device:
            account_repo.claim_daily(conn, who.user.id, who.guest_id)
            account_repo.claim_push(conn, who.user.id, who.guest_id)
    return respond(200, {"claimed": [str(i) for i in moved]})
