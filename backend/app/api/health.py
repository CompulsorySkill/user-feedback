"""健康检查：同时探测数据库连通性。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.errors import AppException
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="服务健康检查")
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:  # noqa: BLE001 - 对外只暴露稳定业务码
        raise AppException(503, code="DATABASE_UNAVAILABLE") from exc

    return HealthResponse(
        status="ok",
        database="ok",
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
