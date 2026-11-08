"""公告：公开只读 + 管理员写；全局最多一篇置顶。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi import status as http_status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    AdminUserDep,
    AnnouncementServiceDep,
    AuditServiceDep,
    IdentityDep,
    StorageDep,
)
from app.api.v1.download import content_disposition, stream_object
from app.core.errors import AppException
from app.core.identity import AuthenticatedUser
from app.schemas.announcement import (
    AnnouncementCreateRequest,
    AnnouncementDetail,
    AnnouncementSummary,
    AnnouncementUpdateRequest,
)
from app.schemas.common import Page
from app.services.audit import request_ip

router = APIRouter(prefix="/announcements", tags=["announcements"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
CursorQuery = Annotated[str | None, Query(description="上一页返回的 next_cursor")]


def _is_admin(identity) -> bool:
    return isinstance(identity, AuthenticatedUser) and identity.is_admin


@router.get("", response_model=Page[AnnouncementSummary], summary="公告列表")
async def list_announcements(
    identity: IdentityDep,
    service: AnnouncementServiceDep,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
    include_drafts: bool = False,
) -> Page[AnnouncementSummary]:
    return await service.list_entries(
        limit=limit,
        cursor_raw=cursor,
        include_drafts=include_drafts,
        viewer_is_admin=_is_admin(identity),
    )


@router.post(
    "",
    response_model=AnnouncementDetail,
    status_code=http_status.HTTP_201_CREATED,
    summary="创建公告草稿（管理员）",
)
async def create_announcement(
    payload: AnnouncementCreateRequest,
    request: Request,
    admin: AdminUserDep,
    service: AnnouncementServiceDep,
    audit: AuditServiceDep,
) -> AnnouncementDetail:
    entry = await service.create(payload, admin)
    await audit.record(
        action="announcement.create",
        actor=admin,
        target_type="announcement",
        target_id=entry.id,
        detail={"title": entry.title, "is_published": entry.is_published},
        ip=request_ip(request),
    )
    return entry


@router.get("/{announcement_id}", response_model=AnnouncementDetail, summary="公告详情")
async def get_announcement(
    announcement_id: uuid.UUID,
    identity: IdentityDep,
    service: AnnouncementServiceDep,
) -> AnnouncementDetail:
    return await service.get(announcement_id, viewer_is_admin=_is_admin(identity))


@router.get(
    "/{announcement_id}/attachments/{attachment_id}",
    summary="下载公告附件",
)
async def download_attachment(
    announcement_id: uuid.UUID,
    attachment_id: int,
    identity: IdentityDep,
    service: AnnouncementServiceDep,
    storage: StorageDep,
) -> StreamingResponse:
    attachment = await service.get_attachment(
        announcement_id,
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
        stream_object(stored.body),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": content_disposition(attachment.filename),
            "Content-Length": str(stored.content_length or attachment.size),
            "Cache-Control": "private, max-age=0, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/{announcement_id}",
    response_model=AnnouncementDetail,
    summary="编辑公告（管理员）",
)
async def update_announcement(
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdateRequest,
    request: Request,
    admin: AdminUserDep,
    service: AnnouncementServiceDep,
    audit: AuditServiceDep,
) -> AnnouncementDetail:
    entry = await service.update(announcement_id, payload, admin)
    await audit.record(
        action="announcement.update",
        actor=admin,
        target_type="announcement",
        target_id=announcement_id,
        detail={
            "title": entry.title,
            "title_changed": payload.title is not None,
            "content_changed": payload.content is not None,
        },
        ip=request_ip(request),
    )
    return entry


@router.delete(
    "/{announcement_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除公告（管理员）",
)
async def delete_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: AnnouncementServiceDep,
    audit: AuditServiceDep,
) -> Response:
    await service.delete(announcement_id)
    await audit.record(
        action="announcement.delete",
        actor=admin,
        target_type="announcement",
        target_id=announcement_id,
        ip=request_ip(request),
    )
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post(
    "/{announcement_id}/publish",
    response_model=AnnouncementDetail,
    summary="发布（管理员）",
)
async def publish_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: AnnouncementServiceDep,
    audit: AuditServiceDep,
) -> AnnouncementDetail:
    entry = await service.publish(announcement_id)
    await audit.record(
        action="announcement.publish",
        actor=admin,
        target_type="announcement",
        target_id=announcement_id,
        detail={"title": entry.title},
        ip=request_ip(request),
    )
    return entry


@router.post(
    "/{announcement_id}/unpublish",
    response_model=AnnouncementDetail,
    summary="撤回发布（管理员）",
)
async def unpublish_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: AnnouncementServiceDep,
    audit: AuditServiceDep,
) -> AnnouncementDetail:
    entry = await service.unpublish(announcement_id)
    await audit.record(
        action="announcement.unpublish",
        actor=admin,
        target_type="announcement",
        target_id=announcement_id,
        detail={"title": entry.title},
        ip=request_ip(request),
    )
    return entry


@router.post(
    "/{announcement_id}/pin",
    response_model=AnnouncementDetail,
    summary="置顶（管理员，仅一篇）",
)
async def pin_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: AnnouncementServiceDep,
    audit: AuditServiceDep,
) -> AnnouncementDetail:
    entry = await service.set_pinned(announcement_id, pinned=True)
    await audit.record(
        action="announcement.pin",
        actor=admin,
        target_type="announcement",
        target_id=announcement_id,
        detail={"title": entry.title},
        ip=request_ip(request),
    )
    return entry


@router.post(
    "/{announcement_id}/unpin",
    response_model=AnnouncementDetail,
    summary="取消置顶（管理员）",
)
async def unpin_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: AnnouncementServiceDep,
    audit: AuditServiceDep,
) -> AnnouncementDetail:
    entry = await service.set_pinned(announcement_id, pinned=False)
    await audit.record(
        action="announcement.unpin",
        actor=admin,
        target_type="announcement",
        target_id=announcement_id,
        detail={"title": entry.title},
        ip=request_ip(request),
    )
    return entry
