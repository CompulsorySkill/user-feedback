"""管理员查看用户目录（只读）。"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import AdminUserDep, UserServiceDep
from app.schemas.common import Page
from app.schemas.user import AdminUserItem

router = APIRouter(prefix="/admin/users", tags=["admin"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
SearchQuery = Annotated[
    str | None,
    Query(min_length=1, max_length=100, description="按邮箱与显示名模糊搜索"),
]
RoleQuery = Annotated[
    Literal["user", "admin"] | None,
    Query(description="按角色筛选"),
]


@router.get("", response_model=Page[AdminUserItem], summary="用户目录（管理员）")
async def list_users(
    admin: AdminUserDep,
    service: UserServiceDep,
    limit: LimitQuery = 30,
    before_id: int | None = None,
    q: SearchQuery = None,
    role: RoleQuery = None,
) -> Page[AdminUserItem]:
    return await service.list_page(limit=limit, before_id=before_id, query=q, role=role)
