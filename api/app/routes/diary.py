"""The diary (spec 2026-11-19 stage 4.3 §6): the account's readings, "did it come true?", a private note, delete.

Stage 4.4b §5 (owner decision 9): the list shows only the FREE_DIARY_VISIBLE newest readings, in pages; the older
ones are not deleted — `hidden_count` says how many there are, and the export and the entry's own link still show
them. There is no Plus flag on an account yet, so the cap applies to everyone.

Signed in only (401 "sign_in"); a reading of someone else, a guest reading of this device and a missing one are
all 404 alike. The note is stored exactly as sent and returned only as JSON: the site shows it as text (escaped),
never as HTML. No model ever sees the note or the outcome (reader memory, §7, reads neither).
"""
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import account_repo
from app.config import FREE_DIARY_VISIBLE, NOTE_MAX_CHARS
from app.context import get_ctx
from app.reader import flow
from app.routes.common import not_found, respond, sign_in_required, viewer
from app.routes.readings import reject_nul

router = APIRouter(prefix="/api")


class DiaryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["yes", "partly", "no"] | None = None
    note: str | None = Field(default=None, max_length=NOTE_MAX_CHARS)

    _no_nul = field_validator("note", mode="after")(reject_nul)


def diary_item(ctx, row: dict) -> dict:
    """A crisis answer is listed without any text, as in GET /api/readings/{id}."""
    crisis = row["answer_shown"] == "crisis"
    sections = flow.shown_sections(row) or {}
    lang = row["lang"]
    return {
        "id": str(row["id"]), "created_at": row["created_at"], "lang": lang, "kind": row["kind"],
        "topic": None if crisis else row["topic"], "question": None if crisis else row["question"],
        "headline": None if row["answer_shown"] == "fallback" else sections.get("headline"),  # the fallback's notice is no headline
        "answer_shown": row["answer_shown"],
        "cards": [{**c, "name": ctx.cards.name(c["card_id"], lang)} for c in row["cards"]],
        "outcome": row["outcome"], "has_note": row["note"] is not None, "followups": row["followup_count"],
    }


@router.get("/diary")
def list_diary(request: Request, before: datetime | None = None, limit: int = Query(default=20, ge=1, le=50)):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()
    if before is not None and before.tzinfo is None:
        before = before.replace(tzinfo=timezone.utc)
    with ctx.db.connect() as conn:
        visible = account_repo.diary_page(conn, who.user.id, None, FREE_DIARY_VISIBLE)
        total = account_repo.diary_count(conn, who.user.id)
    rest = [row for row in visible if before is None or row["created_at"] < before]
    page = rest[:limit]
    return respond(200, {"items": [diary_item(ctx, row) for row in page],
                         "next_before": page[-1]["created_at"] if len(rest) > limit else None,
                         "hidden_count": max(total - len(visible), 0)})


@router.patch("/diary/{reading_id}")
def update_entry(reading_id: uuid.UUID, body: DiaryPatch, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()
    fields = body.model_dump(include=body.model_fields_set)
    if fields.get("note") is not None and not fields["note"].strip():
        fields["note"] = None  # an empty note is no note
    with ctx.db.connect() as conn:
        row = account_repo.update_diary_entry(conn, reading_id, who.user.id, fields, ctx.clock())
    if row is None:
        return not_found()
    return respond(200, {"id": str(reading_id), **row})


@router.delete("/diary/{reading_id}")
def delete_entry(reading_id: uuid.UUID, request: Request):
    ctx = get_ctx(request)
    who = viewer(ctx, request)
    if who.user is None:
        return sign_in_required()
    with ctx.db.connect() as conn:
        deleted = account_repo.delete_diary_entry(conn, reading_id, who.user.id)
    return Response(status_code=204) if deleted else not_found()
