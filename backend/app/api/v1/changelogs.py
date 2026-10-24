"""更新日志列表与详情（只读，非管理员仅见已发布）。"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ChangelogServiceDep
from app.schemas.changelog import ChangelogDetail, ChangelogSummary
from app.schemas.common import Page

router = APIRouter(prefix="/changelogs", tags=["changelogs"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
CursorQuery = Annotated[str | None, Query(description="上一页返回的 next_cursor")]


@router.get("", response_model=Page[ChangelogSummary], summary="更新日志列表")
async def list_changelogs(
    service: ChangelogServiceDep,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
    include_drafts: bool = False,
) -> Page[ChangelogSummary]:
    # 鉴权在 P3 接入；当前 viewer_is_admin 恒为 False，草稿不可见。
    return await service.list_entries(
        limit=limit,
        cursor_raw=cursor,
        include_drafts=include_drafts,
        viewer_is_admin=False,
    )


@router.get("/{changelog_id}", response_model=ChangelogDetail, summary="更新日志详情")
async def get_changelog(
    changelog_id: uuid.UUID, service: ChangelogServiceDep
) -> ChangelogDetail:
    return await service.get(changelog_id)
