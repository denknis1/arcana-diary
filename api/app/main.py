"""Arcana Diary API: app assembly, routes, /health, background work (migrations, cleanup, card of the day)."""
import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders

from app.auth import AuthError, AuthUnavailable
from app.config import Settings, load_settings
from app.context import build_context
from app.db import DatabaseUnavailable
from app.housekeeping import run_background
from app.routes import account, auth_config, claim, daily, diary, events, followups, plus, readings
from app.routes import limits as limits_routes
from app.routes.common import check_token

# stage 4.3 §3: every /api/* route checks a Bearer token, when there is one, before anything else
API_AUTH = [Depends(check_token)]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("arcana")


class ApiHeaders:
    """Plain ASGI middleware (no buffering, safe for SSE): /api/* answers are never cached, never indexed and
    send no Referer onwards (§8.3)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                headers["Referrer-Policy"] = "no-referrer"
                headers["X-Robots-Tag"] = "noindex, nofollow"
            await send(message)

        await self.app(scope, receive, send_with_headers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = app.state.ctx
    task = asyncio.create_task(run_background(ctx)) if ctx.settings.database_url else None
    app.state.background_task = task
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def db_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
    log.error("database unavailable: %s", exc)
    return JSONResponse(status_code=503, content={"reason": "db"})


async def auth_failed(request: Request, exc: AuthError) -> JSONResponse:
    """Stage 4.3 §3: a bad or expired token is never a silent guest; the browser refreshes it and retries."""
    return JSONResponse(status_code=401, content={"reason": "auth"}, headers={"WWW-Authenticate": "Bearer"})


async def auth_unavailable(request: Request, exc: AuthUnavailable) -> JSONResponse:
    log.error("sign-in keys unavailable: %s", exc)
    return JSONResponse(status_code=503, content={"reason": "auth_unavailable"})


async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    """One shape for every 422: {"reason": ..., "fields": [...]} (the input itself is never echoed)."""
    fields = [".".join(str(part) for part in error["loc"][1:]) for error in exc.errors()]
    return JSONResponse(status_code=422, content={"reason": "invalid", "fields": fields})


def create_app(settings: Settings | None = None, *, reader=None, guard_provider=None, turnstile=None,
               clock=None, jwks=None) -> FastAPI:
    app = FastAPI(title="Arcana Diary API", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.ctx = build_context(settings or load_settings(), reader=reader, guard_provider=guard_provider,
                                  turnstile=turnstile, clock=clock, jwks=jwks)
    app.add_exception_handler(DatabaseUnavailable, db_unavailable)
    app.add_exception_handler(AuthError, auth_failed)
    app.add_exception_handler(AuthUnavailable, auth_unavailable)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_middleware(ApiHeaders)
    app.include_router(readings.router, dependencies=API_AUTH)
    app.include_router(followups.router, dependencies=API_AUTH)
    app.include_router(limits_routes.router, dependencies=API_AUTH)
    app.include_router(daily.router, dependencies=API_AUTH)
    app.include_router(claim.router, dependencies=API_AUTH)
    app.include_router(diary.router, dependencies=API_AUTH)
    app.include_router(account.router, dependencies=API_AUTH)
    app.include_router(plus.router, dependencies=API_AUTH)
    app.include_router(events.router, dependencies=API_AUTH)
    app.include_router(auth_config.router, dependencies=API_AUTH)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
