"""更新日志：公开只读 + 管理员写。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Query, Request, Response
from fastapi import status as http_status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    AdminUserDep,
    AuditServiceDep,
    ChangelogServiceDep,
    IdentityDep,
    StorageDep,
)
from app.core.errors import AppException
from app.core.identity import AuthenticatedUser
from app.schemas.changelog import (
    ChangelogCreateRequest,
    ChangelogDetail,
    ChangelogSummary,
    ChangelogUpdateRequest,
)
from app.schemas.common import Page
from app.services.audit import request_ip

router = APIRouter(prefix="/changelogs", tags=["changelogs"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
CursorQuery = Annotated[str | None, Query(description="上一页返回的 next_cursor")]


def _is_admin(identity) -> bool:
    return isinstance(identity, AuthenticatedUser) and identity.is_admin


def _content_disposition(filename: str) -> str:
    fallback = (
        "".join(
            char if 32 <= ord(char) < 127 and char not in '"\\' else "_"
            for char in filename
        )
        or "attachment"
    )
    return (
        f'attachment; filename="{fallback}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


async def _stream_object(body: Any):
    try:
        while True:
            chunk = await asyncio.to_thread(body.read, 64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        await asyncio.to_thread(body.close)


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
    request: Request,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
    audit: AuditServiceDep,
) -> ChangelogDetail:
    entry = await service.create(payload, admin)
    await audit.record(
        action="changelog.create",
        actor=admin,
        target_type="changelog",
        target_id=entry.id,
        detail={
            "title": entry.title,
            "is_published": entry.is_published,
            "attachment_count": len(entry.attachments),
        },
        ip=request_ip(request),
    )
    return entry


@router.get("/{changelog_id}", response_model=ChangelogDetail, summary="更新日志详情")
async def get_changelog(
    changelog_id: uuid.UUID,
    identity: IdentityDep,
    service: ChangelogServiceDep,
) -> ChangelogDetail:
    return await service.get(changelog_id, viewer_is_admin=_is_admin(identity))


@router.get(
    "/{changelog_id}/attachments/{attachment_id}",
    summary="下载更新日志附件",
)
async def download_attachment(
    changelog_id: uuid.UUID,
    attachment_id: int,
    identity: IdentityDep,
    service: ChangelogServiceDep,
    storage: StorageDep,
) -> StreamingResponse:
    attachment = await service.get_attachment(
        changelog_id,
        attachment_id,
        viewer_is_admin=_is_admin(identity),
    )
    try:
        stored = await asyncio.to_thread(storage.open_object, attachment.object_key)
    except FileNotFoundError:
        raise AppException(
            404, code="ATTACHMENT_NOT_FOUND", detail="附件文件不存在"
        ) from None

    return StreamingResponse(
        _stream_object(stored.body),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition(attachment.filename),
            "Content-Length": str(stored.content_length or attachment.size),
            "Cache-Control": "private, max-age=0, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/{changelog_id}",
    response_model=ChangelogDetail,
    summary="编辑更新日志（管理员）",
)
async def update_changelog(
    changelog_id: uuid.UUID,
    payload: ChangelogUpdateRequest,
    request: Request,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
    audit: AuditServiceDep,
) -> ChangelogDetail:
    entry = await service.update(changelog_id, payload, admin)
    await audit.record(
        action="changelog.update",
        actor=admin,
        target_type="changelog",
        target_id=changelog_id,
        detail={
            "title": entry.title,
            "title_changed": payload.title is not None,
            "content_changed": payload.content is not None,
            "attachments_changed": payload.attachments is not None,
            "attachment_count": len(entry.attachments),
        },
        ip=request_ip(request),
    )
    return entry


@router.delete(
    "/{changelog_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除更新日志（管理员）",
)
async def delete_changelog(
    changelog_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
    audit: AuditServiceDep,
) -> Response:
    await service.delete(changelog_id)
    await audit.record(
        action="changelog.delete",
        actor=admin,
        target_type="changelog",
        target_id=changelog_id,
        ip=request_ip(request),
    )
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post(
    "/{changelog_id}/publish",
    response_model=ChangelogDetail,
    summary="发布（管理员）",
)
async def publish_changelog(
    changelog_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
    audit: AuditServiceDep,
) -> ChangelogDetail:
    entry = await service.publish(changelog_id)
    await audit.record(
        action="changelog.publish",
        actor=admin,
        target_type="changelog",
        target_id=changelog_id,
        detail={"title": entry.title},
        ip=request_ip(request),
    )
    return entry


@router.post(
    "/{changelog_id}/unpublish",
    response_model=ChangelogDetail,
    summary="撤回发布（管理员）",
)
async def unpublish_changelog(
    changelog_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: ChangelogServiceDep,
    audit: AuditServiceDep,
) -> ChangelogDetail:
    entry = await service.unpublish(changelog_id)
    await audit.record(
        action="changelog.unpublish",
        actor=admin,
        target_type="changelog",
        target_id=changelog_id,
        detail={"title": entry.title},
        ip=request_ip(request),
    )
    return entry
