"""The account (spec 2026-11-19 stage 4.3 §8): who is signed in, consent to reminder e-mails, the export of all
readings and deleting the account at once (no grace period). Signed in only (401 "sign_in"). The e-mail comes
from the token; the profile row is made on first use."""
import logging
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from app import account_repo, limits
from app.context import get_ctx
from app.reader import flow
from app.routes.common import respond, sign_in_required, viewer

log = logging.getLogger("arcana.account")

router = APIRouter(prefix="/api")


class AccountPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reminders_consent: bool


class AccountDelete(BaseModel):
    confirm: Literal["DELETE"]


def account_view(user, profile: dict) -> dict:
    return {"email": user.email, "created_at": profile["created_at"],
            "reminders_consent": profile["reminders_consent"], "consent_at": profile["consent_at"]}


@router.get("/account")
def get_account(request: Request, tz: str | None = None):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()
    now = ctx.clock()
    quota = who.quota
    day = limits.local_day(limits.resolve_tz(tz), now)
    with ctx.db.connect() as conn:
        profile = account_repo.ensure_profile(conn, who.user.id, now)
        used = limits.used(conn, quota.subject, day)
    return respond(200, {**account_view(who.user, profile), "limit": quota.limit, "used": used,
                         "remaining": max(quota.limit - used, 0), "day": day.isoformat()})


@router.patch("/account")
def update_account(body: AccountPatch, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()
    with ctx.db.connect() as conn:
        profile = account_repo.set_consent(conn, who.user.id, body.reminders_consent, ctx.clock())
    return respond(200, account_view(who.user, profile))


def export_reading(ctx, reading: dict, followups: list[dict]) -> dict:
    lang = reading["lang"]
    return {
        "id": str(reading["id"]), "created_at": reading["created_at"], "lang": lang, "kind": reading["kind"],
        "topic": reading["topic"], "situation": reading["situation"], "question": reading["question"],
        "cards": [{**c, "name": ctx.cards.name(c["card_id"], lang)} for c in reading["cards"]],
        "verdict": reading["verdict"], "answer_shown": reading["answer_shown"],
        "answer": flow.shown_sections(reading),
        "outcome": reading["outcome"], "outcome_at": reading["outcome_at"],
        "note": reading["note"], "note_updated_at": reading["note_updated_at"],
        "followups": [{"n": f["n"], "question": f["question"], "answer": flow.followup_text(f),
                       "created_at": f["created_at"]} for f in followups if flow.followup_text(f)],
    }


@router.get("/account/export")
def export_account(request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()
    now = ctx.clock()
    with ctx.db.connect() as conn:
        profile = account_repo.ensure_profile(conn, who.user.id, now)
        entries = account_repo.export_readings(conn, who.user.id)
        waitlist = account_repo.waitlist_entry(conn, who.user.id, who.user.email)
    payload = {"exported_at": now, "account": account_view(who.user, profile),
               "readings": [export_reading(ctx, reading, followups) for reading, followups in entries],
               "plus_waitlist": waitlist}
    response = respond(200, payload)
    response.headers["Content-Disposition"] = f'attachment; filename="arcana-diary-{now.date().isoformat()}.json"'
    return response


@router.delete("/account")
def delete_account(body: AccountDelete, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()
    with ctx.db.connect() as conn:
        counts = account_repo.delete_account(conn, who.user.id, who.user.email, ctx.clock())
    log.info("account deleted: %s", counts)  # counts only: no id, no e-mail
    if ctx.settings.supabase_url and counts.get("auth_users") != 1:  # Fable M2: never a silent half-deletion
        log.error("an account was deleted here, but its Supabase user was not deleted (auth.users: %s): find it in"
                  " Supabase → Authentication → Users by the time of this line", counts.get("auth_users"))
    return respond(200, {"deleted": True})
