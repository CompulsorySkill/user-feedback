"""管理员审计日志查询。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUserDep, AuditServiceDep
from app.schemas.audit import AuditLogItem
from app.schemas.common import Page

router = APIRouter(prefix="/admin/audit-logs", tags=["admin"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
ActionQuery = Annotated[
    str | None, Query(max_length=64, description="按动作精确筛选，如 board.create")
]


@router.get("", response_model=Page[AuditLogItem], summary="审计日志（管理员）")
async def list_audit_logs(
    admin: AdminUserDep,
    service: AuditServiceDep,
    limit: LimitQuery = 50,
    before_id: int | None = None,
    action: ActionQuery = None,
) -> Page[AuditLogItem]:
    return await service.list_page(limit=limit, before_id=before_id, action=action)
