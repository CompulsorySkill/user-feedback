"""管理员任务面板：被 @ 的反馈与任务进度。"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import AdminTaskServiceDep, AdminUserDep
from app.schemas.admin_task import AdminTaskItem
from app.schemas.common import Page

router = APIRouter(prefix="/admin/tasks", tags=["admin"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
TaskStateQuery = Annotated[
    Literal["pending", "active", "done"] | None,
    Query(description="任务状态：未接受 / 进行中 / 已完成"),
]
BoardQuery = Annotated[str | None, Query(max_length=64, description="按看板 slug 筛选")]


@router.get("", response_model=Page[AdminTaskItem], summary="任务面板（管理员）")
async def list_tasks(
    admin: AdminUserDep,
    service: AdminTaskServiceDep,
    limit: LimitQuery = 30,
    before: str | None = None,
    task_state: TaskStateQuery = None,
    board: BoardQuery = None,
) -> Page[AdminTaskItem]:
    """只返回「@ 了当前管理员」的反馈；别人的提及不可见。"""
    return await service.list_page(
        user_id=admin.id,
        limit=limit,
        cursor_raw=before,
        task_state=task_state,
        board_slug=board,
    )
