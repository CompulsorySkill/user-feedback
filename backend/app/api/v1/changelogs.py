"""更新日志：公开只读 + 管理员写。"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response
from fastapi import status as http_status

from app.api.deps import AdminUserDep, ChangelogServiceDep, IdentityDep
from app.core.identity import AuthenticatedUser
from app.schemas.changelog import (
    ChangelogCreateRequest,
    ChangelogDetail,
    ChangelogSummary,
    ChangelogUpdateRequest,
)
from app.schemas.common import Page

router = APIRouter(prefix="/changelogs", tags=["changelogs"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
CursorQuery = Annotated[str | None, Query(description="上一页返回的 next_cursor")]


def _is_admin(identity) -> bool:
    return isinstance(identity, AuthenticatedUser) and identity.is_admin


@router.get("", response_model=Page[ChangelogSummary], summary="更新日志列表")
async def list_changelogs(
    identity: IdentityDep,
    service: ChangelogServiceDep,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
    include_drafts: bool = False,
) -> Page[ChangelogSummary]:
    return await service.list_entries(
        limit=limit,
        cursor_raw=cursor,
        include_drafts=include_drafts,
        viewer_is_admin=_is_admin(identity),
    )


@router.post(
    "",
    response_model=ChangelogDetail,
    status_code=http_status.HTTP_201_CREATED,
    summary="创建更新日志草稿（管理员）",
)
async def create_changelog(
    payload: ChangelogCreateRequest,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
) -> ChangelogDetail:
    return await service.create(payload, admin)


@router.get("/{changelog_id}", response_model=ChangelogDetail, summary="更新日志详情")
async def get_changelog(
    changelog_id: uuid.UUID,
    identity: IdentityDep,
    service: ChangelogServiceDep,
) -> ChangelogDetail:
    return await service.get(changelog_id, viewer_is_admin=_is_admin(identity))


@router.patch(
    "/{changelog_id}",
    response_model=ChangelogDetail,
    summary="编辑更新日志（管理员）",
)
async def update_changelog(
    changelog_id: uuid.UUID,
    payload: ChangelogUpdateRequest,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
) -> ChangelogDetail:
    return await service.update(changelog_id, payload, admin)


@router.delete(
    "/{changelog_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除更新日志（管理员）",
)
async def delete_changelog(
    changelog_id: uuid.UUID,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
) -> Response:
    await service.delete(changelog_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post(
    "/{changelog_id}/publish",
    response_model=ChangelogDetail,
    summary="发布（管理员）",
)
async def publish_changelog(
    changelog_id: uuid.UUID,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
) -> ChangelogDetail:
    return await service.publish(changelog_id)


@router.post(
    "/{changelog_id}/unpublish",
    response_model=ChangelogDetail,
    summary="撤回发布（管理员）",
)
async def unpublish_changelog(
    changelog_id: uuid.UUID,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
) -> ChangelogDetail:
    return await service.unpublish(changelog_id)
