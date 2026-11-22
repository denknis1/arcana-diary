"""GET /api/auth-config (spec 2026-11-22 stage 4.4b §3): what the browser needs to sign in with Supabase — the
project's public address and public key (neither is a secret) and whether "Continue with Google" is on. Without the
address or the key sign-in is off: the site hides "Save to diary" and the diary says that sign-in opens soon."""
from fastapi import APIRouter, Request

from app.context import get_ctx
from app.routes.common import respond

router = APIRouter(prefix="/api")


@router.get("/auth-config")
def auth_config(request: Request):
    settings = get_ctx(request).settings
    enabled = bool(settings.supabase_url and settings.supabase_anon_key)
    return respond(200, {"enabled": enabled, "supabase_url": settings.supabase_url if enabled else "",
                         "anon_key": settings.supabase_anon_key if enabled else "",
                         "google": enabled and settings.google_signin})
