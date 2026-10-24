"""FastAPI 应用入口。"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.core.errors import AppException, register_exception_handlers
from app.core.logging import install_access_log_redaction
from app.core.rate_limit import cleanup_rate_limit_counters
from app.core.security import ACCESS_COOKIE, decode_session_token

install_access_log_redaction()


async def security_headers(request: Request, call_next):
    # access cookie 存在但失效时打标，前端据此 refresh 后重放请求。
    access_token = request.cookies.get(ACCESS_COOKIE)
    expired = False
    if access_token:
        try:
            decode_session_token(access_token, expected_type="access")
        except AppException:
            expired = True

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if expired:
        response.headers["X-Session-Expired"] = "1"
    return response


async def _rate_limit_cleanup_loop() -> None:
    """每小时清理过期窗口，防止计数表膨胀。"""
    while True:
        await asyncio.sleep(3600)
        async with SessionLocal() as session:
            await cleanup_rate_limit_counters(session)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    cleanup_task: asyncio.Task[None] | None = None
    if settings.rate_limit_enabled:
        cleanup_task = asyncio.create_task(_rate_limit_cleanup_loop())

    yield

    if cleanup_task is not None:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.public_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Session-Expired"],
    )
    app.middleware("http")(security_headers)

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
