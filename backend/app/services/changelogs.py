"""更新日志业务规则：仅管理员可写，草稿仅管理员可见。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.pagination import decode_cursor, encode_cursor
from app.models import (
    ChangelogAttachment as ChangelogAttachmentRow,
    ChangelogEntry,
    User,
)
from app.repositories.changelogs import ChangelogRepository
from app.repositories.uploads import UploadRepository
from app.schemas.changelog import (
    ChangelogAttachment as ChangelogAttachmentSchema,
    ChangelogAttachmentInput,
    ChangelogCreateRequest,
    ChangelogDetail,
    ChangelogSummary,
    ChangelogUpdateRequest,
)
from app.schemas.common import Page
from app.services.rich_text import collect_media_keys, validate_rich_text

CHANGELOG_MEDIA_PURPOSES: dict[str, tuple[str, ...]] = {
    "image": ("changelog_image",),
    "video": ("changelog_video",),
}
MAX_ATTACHMENTS = 10


def sanitize_filename(value: str) -> str:
    """去掉路径与控制字符，仅保留用于展示 / 下载的文件名。"""
    name = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    name = "".join(char for char in name if ord(char) >= 32 and char not in '\r\n"')
    name = name[:200].strip()
    return name or "attachment"


def _summary(entry: ChangelogEntry) -> ChangelogSummary:
    return ChangelogSummary(
        id=entry.id,
        title=entry.title,
        excerpt=entry.excerpt,
        is_published=entry.is_published,
        published_at=entry.published_at,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


class ChangelogService:
    def __init__(
        self,
        session: AsyncSession,
        changelogs: ChangelogRepository,
        uploads: UploadRepository,
    ) -> None:
        self.session = session
        self.changelogs = changelogs
        self.uploads = uploads

    async def list_entries(
        self,
        *,
        limit: int,
        cursor_raw: str | None,
        include_drafts: bool = False,
        viewer_is_admin: bool = False,
    ) -> Page[ChangelogSummary]:
        effective_include_drafts = include_drafts and viewer_is_admin
        cursor = decode_cursor(cursor_raw)
        entries = await self.changelogs.list_entries(
            limit=limit + 1, cursor=cursor, include_drafts=effective_include_drafts
        )
        has_more = len(entries) > limit
        entries = entries[:limit]

        next_cursor = (
            encode_cursor(entries[-1].created_at, entries[-1].id)
            if has_more and entries
            else None
        )
        return Page(
            items=[_summary(entry) for entry in entries], next_cursor=next_cursor
        )

    async def get(
        self, changelog_id: uuid.UUID, *, viewer_is_admin: bool = False
    ) -> ChangelogDetail:
        entry = await self.changelogs.get(changelog_id, include_drafts=viewer_is_admin)
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")

        attachments = await self.changelogs.list_attachments(entry.id)
        return ChangelogDetail(
            **_summary(entry).model_dump(),
            content=entry.content,
            attachments=[
                ChangelogAttachmentSchema(
                    id=attachment.id,
                    object_key=(attachment.object_key if viewer_is_admin else None),
                    filename=attachment.filename,
                    content_type=attachment.content_type,
                    size=attachment.size,
                    download_url=(
                        f"/api/v1/changelogs/{entry.id}/attachments/{attachment.id}"
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
            allowed_purposes=CHANGELOG_MEDIA_PURPOSES,
            uploads=self.uploads,
        )

    async def _validate_attachments(
        self, items: list[ChangelogAttachmentInput], actor: User
    ) -> list[dict[str, str | int]]:
        if len(items) > MAX_ATTACHMENTS:
            raise AppException(
                400,
                code="ATTACHMENT_LIMIT",
                detail=f"每条更新日志最多 {MAX_ATTACHMENTS} 个附件",
            )
        if not items:
            return []

        keys: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item.object_key in seen:
                continue
            seen.add(item.object_key)
            keys.append(item.object_key)

        uploads = await self.uploads.list_for_identity(f"user:{actor.id}", keys)
        uploads_by_key = {upload.object_key: upload for upload in uploads}
        result: list[dict[str, str | int]] = []
        for item in items:
            upload = uploads_by_key.get(item.object_key)
            if upload is None or upload.purpose != "changelog_attachment":
                raise AppException(
                    400,
                    code="INVALID_ATTACHMENT",
                    detail="附件不存在、已失效或不属于当前管理员",
                )
            if any(row["object_key"] == item.object_key for row in result):
                continue
            result.append(
                {
                    "object_key": item.object_key,
                    "filename": sanitize_filename(item.filename),
                    "content_type": upload.content_type,
                    "size": upload.size,
                }
            )
        return result

    @staticmethod
    def _attachment_rows(
        changelog_id: uuid.UUID, items: list[dict[str, str | int]]
    ) -> list[ChangelogAttachmentRow]:
        return [
            ChangelogAttachmentRow(
                changelog_id=changelog_id,
                object_key=str(item["object_key"]),
                filename=str(item["filename"]),
                content_type=str(item["content_type"]),
                size=int(item["size"]),
            )
            for item in items
        ]

    async def create(
        self, payload: ChangelogCreateRequest, actor: User
    ) -> ChangelogDetail:
        excerpt = await self._validate(payload.content, actor)
        attachments = await self._validate_attachments(payload.attachments, actor)
        entry = ChangelogEntry(
            title=payload.title,
            content=payload.content,
            excerpt=excerpt,
            is_published=False,
            published_at=None,
        )
        self.session.add(entry)
        await self.session.flush()
        if attachments:
            await self.changelogs.replace_attachments(
                entry.id, self._attachment_rows(entry.id, attachments)
            )
        await self.session.commit()
        return await self.get(entry.id, viewer_is_admin=True)

    async def update(
        self,
        changelog_id: uuid.UUID,
        payload: ChangelogUpdateRequest,
        actor: User,
    ) -> ChangelogDetail:
        entry = await self.changelogs.get(changelog_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")

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
            await self.changelogs.replace_attachments(
                changelog_id, self._attachment_rows(changelog_id, attachments)
            )
        await self.session.commit()
        return await self.get(changelog_id, viewer_is_admin=True)

    async def delete(self, changelog_id: uuid.UUID) -> None:
        entry = await self.changelogs.get(changelog_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")
        await self.session.delete(entry)
        await self.session.commit()

    async def get_attachment(
        self,
        changelog_id: uuid.UUID,
        attachment_id: int,
        *,
        viewer_is_admin: bool = False,
    ) -> ChangelogAttachmentRow:
        """校验更新日志可见性后返回附件；草稿附件仅管理员可下载。"""
        entry = await self.changelogs.get(changelog_id, include_drafts=viewer_is_admin)
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")
        attachment = await self.changelogs.get_attachment(changelog_id, attachment_id)
        if attachment is None:
            raise AppException(404, code="ATTACHMENT_NOT_FOUND", detail="附件不存在")
        return attachment

    async def publish(self, changelog_id: uuid.UUID) -> ChangelogDetail:
        entry = await self.changelogs.get(changelog_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")
        entry.is_published = True
        entry.published_at = datetime.now(timezone.utc)
        await self.session.commit()
        return await self.get(changelog_id, viewer_is_admin=True)

    async def unpublish(self, changelog_id: uuid.UUID) -> ChangelogDetail:
        entry = await self.changelogs.get(changelog_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")
        # 保留 published_at 供审计，用 is_published 控制可见性。
        entry.is_published = False
        await self.session.commit()
        return await self.get(changelog_id, viewer_is_admin=True)
