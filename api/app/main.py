"""Arcana Diary API: app assembly, routes, /health."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders

from app.config import Settings, load_settings
from app.context import build_context
from app.db import DatabaseUnavailable, migrate
from app.routes import followups, readings
from app.routes import limits as limits_routes

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
    if ctx.settings.run_migrations and ctx.settings.database_url:
        try:
            await asyncio.to_thread(migrate, ctx.db, ctx.settings.migrations_dir)
        except DatabaseUnavailable as exc:
            log.error("migrations skipped, database unavailable: %s", exc)
    yield


async def db_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
    log.error("database unavailable: %s", exc)
    return JSONResponse(status_code=503, content={"reason": "db"})


async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    """One shape for every 422: {"reason": ..., "fields": [...]} (the input itself is never echoed)."""
    fields = [".".join(str(part) for part in error["loc"][1:]) for error in exc.errors()]
    return JSONResponse(status_code=422, content={"reason": "invalid", "fields": fields})


def create_app(settings: Settings | None = None, *, reader=None, guard_provider=None, turnstile=None,
               clock=None) -> FastAPI:
    app = FastAPI(title="Arcana Diary API", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.ctx = build_context(settings or load_settings(), reader=reader, guard_provider=guard_provider,
                                  turnstile=turnstile, clock=clock)
    app.add_exception_handler(DatabaseUnavailable, db_unavailable)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_middleware(ApiHeaders)
    app.include_router(readings.router)
    app.include_router(followups.router)
    app.include_router(limits_routes.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
