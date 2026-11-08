"""公告业务规则：仅管理员可写，全局最多一篇置顶。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.pagination import decode_cursor, encode_cursor
from app.models import (
    Announcement as AnnouncementRow,
    AnnouncementAttachment as AnnouncementAttachmentRow,
    User,
)
from app.repositories.announcements import AnnouncementRepository
from app.repositories.uploads import UploadRepository
from app.schemas.announcement import (
    AnnouncementAttachment as AnnouncementAttachmentSchema,
    AnnouncementCreateRequest,
    AnnouncementDetail,
    AnnouncementSummary,
    AnnouncementUpdateRequest,
)
from app.schemas.attachment import AttachmentInput
from app.schemas.common import Page
from app.services.attachments import validate_attachments
from app.services.rich_text import collect_media_keys, validate_rich_text

ANNOUNCEMENT_MEDIA_PURPOSES: dict[str, tuple[str, ...]] = {
    "image": ("announcement_image",),
    "video": ("announcement_video",),
}


def _summary(entry: AnnouncementRow) -> AnnouncementSummary:
    return AnnouncementSummary(
        id=entry.id,
        title=entry.title,
        excerpt=entry.excerpt,
        is_published=entry.is_published,
        is_pinned=entry.is_pinned,
        published_at=entry.published_at,
        author_name=entry.author_name,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _author_name(actor: User) -> str:
    return actor.display_name or actor.email


class AnnouncementService:
    def __init__(
        self,
        session: AsyncSession,
        announcements: AnnouncementRepository,
        uploads: UploadRepository,
    ) -> None:
        self.session = session
        self.announcements = announcements
        self.uploads = uploads

    async def list_entries(
        self,
        *,
        limit: int,
        cursor_raw: str | None,
        include_drafts: bool = False,
        viewer_is_admin: bool = False,
    ) -> Page[AnnouncementSummary]:
        effective_include_drafts = include_drafts and viewer_is_admin
        cursor = decode_cursor(cursor_raw)

        # 置顶只出现在第一页，且不参与游标分页，避免翻页时重复。
        pinned = (
            await self.announcements.get_pinned(include_drafts=effective_include_drafts)
            if cursor is None
            else None
        )
        take = limit - 1 if pinned is not None and limit > 1 else limit
        entries = await self.announcements.list_entries(
            limit=take + 1,
            cursor=cursor,
            include_drafts=effective_include_drafts,
        )
        has_more = len(entries) > take
        entries = entries[:take]

        items = ([_summary(pinned)] if pinned is not None else []) + [
            _summary(entry) for entry in entries
        ]
        next_cursor = (
            encode_cursor(entries[-1].created_at, entries[-1].id)
            if has_more and entries
            else None
        )
        return Page(items=items, next_cursor=next_cursor)

    async def get(
        self, announcement_id: uuid.UUID, *, viewer_is_admin: bool = False
    ) -> AnnouncementDetail:
        entry = await self.announcements.get(
            announcement_id, include_drafts=viewer_is_admin
        )
        if entry is None:
            raise AppException(404, code="ANNOUNCEMENT_NOT_FOUND", detail="公告不存在")

        attachments = await self.announcements.list_attachments(entry.id)
        return AnnouncementDetail(
            **_summary(entry).model_dump(),
            content=entry.content,
            attachments=[
                AnnouncementAttachmentSchema(
                    id=attachment.id,
                    object_key=(attachment.object_key if viewer_is_admin else None),
                    filename=attachment.filename,
                    content_type=attachment.content_type,
                    size=attachment.size,
                    download_url=(
                        f"/api/v1/announcements/{entry.id}/attachments/{attachment.id}"
                    ),
                )
                for attachment in attachments
            ],
        )

    async def _validate(
        self, content: dict, actor: User, *, allowed_object_keys: set[str] | None = None
    ) -> str:
        return await validate_rich_text(
            content,
            identity_keys=[f"user:{actor.id}"],
            allowed_object_keys=allowed_object_keys,
            allowed_purposes=ANNOUNCEMENT_MEDIA_PURPOSES,
            uploads=self.uploads,
        )

    async def _validate_attachments(
        self, items: list[AttachmentInput], actor: User
    ) -> list[dict[str, str | int]]:
        return await validate_attachments(
            items,
            identity=f"user:{actor.id}",
            uploads=self.uploads,
            purpose="announcement_attachment",
        )

    @staticmethod
    def _attachment_rows(
        announcement_id: uuid.UUID, items: list[dict[str, str | int]]
    ) -> list[AnnouncementAttachmentRow]:
        return [
            AnnouncementAttachmentRow(
                announcement_id=announcement_id,
                object_key=str(item["object_key"]),
                filename=str(item["filename"]),
                content_type=str(item["content_type"]),
                size=int(item["size"]),
            )
            for item in items
        ]

    async def create(
        self, payload: AnnouncementCreateRequest, actor: User
    ) -> AnnouncementDetail:
        excerpt = await self._validate(payload.content, actor)
        attachments = await self._validate_attachments(payload.attachments, actor)
        entry = AnnouncementRow(
            title=payload.title,
            content=payload.content,
            excerpt=excerpt,
            is_published=False,
            is_pinned=False,
            published_at=None,
            author_name=_author_name(actor),
        )
        self.session.add(entry)
        await self.session.flush()
        if attachments:
            await self.announcements.replace_attachments(
                entry.id, self._attachment_rows(entry.id, attachments)
            )
        await self.session.commit()
        return await self.get(entry.id, viewer_is_admin=True)

    async def update(
        self,
        announcement_id: uuid.UUID,
        payload: AnnouncementUpdateRequest,
        actor: User,
    ) -> AnnouncementDetail:
        entry = await self.announcements.get(announcement_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="ANNOUNCEMENT_NOT_FOUND", detail="公告不存在")

        if payload.title is not None:
            entry.title = payload.title
        if payload.content is not None:
            previous_media = collect_media_keys(entry.content)
            entry.content = payload.content
            entry.excerpt = await self._validate(
                payload.content, actor, allowed_object_keys=previous_media
            )
        if payload.attachments is not None:
            attachments = await self._validate_attachments(payload.attachments, actor)
            await self.announcements.replace_attachments(
                announcement_id, self._attachment_rows(announcement_id, attachments)
            )
        await self.session.commit()
        return await self.get(announcement_id, viewer_is_admin=True)

    async def delete(self, announcement_id: uuid.UUID) -> None:
        entry = await self.announcements.get(announcement_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="ANNOUNCEMENT_NOT_FOUND", detail="公告不存在")
        await self.session.delete(entry)
        await self.session.commit()

    async def get_attachment(
        self,
        announcement_id: uuid.UUID,
        attachment_id: int,
        *,
        viewer_is_admin: bool = False,
    ) -> AnnouncementAttachmentRow:
        """校验公告可见性后返回附件；草稿附件仅管理员可下载。"""
        entry = await self.announcements.get(
            announcement_id, include_drafts=viewer_is_admin
        )
        if entry is None:
            raise AppException(404, code="ANNOUNCEMENT_NOT_FOUND", detail="公告不存在")
        attachment = await self.announcements.get_attachment(
            announcement_id, attachment_id
        )
        if attachment is None:
            raise AppException(404, code="ATTACHMENT_NOT_FOUND", detail="附件不存在")
        return attachment

    async def publish(self, announcement_id: uuid.UUID) -> AnnouncementDetail:
        entry = await self.announcements.get(announcement_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="ANNOUNCEMENT_NOT_FOUND", detail="公告不存在")
        entry.is_published = True
        entry.published_at = entry.published_at or datetime.now(timezone.utc)
        await self.session.commit()
        return await self.get(announcement_id, viewer_is_admin=True)

    async def unpublish(self, announcement_id: uuid.UUID) -> AnnouncementDetail:
        entry = await self.announcements.get(announcement_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="ANNOUNCEMENT_NOT_FOUND", detail="公告不存在")
        # 保留 published_at 供审计；撤回后也不应继续置顶。
        entry.is_published = False
        entry.is_pinned = False
        await self.session.commit()
        return await self.get(announcement_id, viewer_is_admin=True)

    async def set_pinned(
        self, announcement_id: uuid.UUID, *, pinned: bool
    ) -> AnnouncementDetail:
        entry = await self.announcements.get(announcement_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="ANNOUNCEMENT_NOT_FOUND", detail="公告不存在")
        if pinned and not entry.is_published:
            raise AppException(
                400, code="ANNOUNCEMENT_NOT_PUBLISHED", detail="只能置顶已发布的公告"
            )
        if pinned:
            await self.announcements.clear_pinned()
        entry.is_pinned = pinned
        await self.session.commit()
        return await self.get(announcement_id, viewer_is_admin=True)
