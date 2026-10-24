"""API 路由汇总，统一挂到 ``/api`` 前缀。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import health, sso
from app.api.v1 import v1_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sso.router)
api_router.include_router(v1_router)

__all__ = ["api_router"]
