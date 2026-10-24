"""更新日志业务规则：仅管理员可写，草稿仅管理员可见。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.pagination import decode_cursor, encode_cursor
from app.models import ChangelogEntry, User
from app.repositories.changelogs import ChangelogRepository
from app.repositories.uploads import UploadRepository
from app.schemas.changelog import (
    ChangelogCreateRequest,
    ChangelogDetail,
    ChangelogSummary,
    ChangelogUpdateRequest,
)
from app.schemas.common import Page
from app.services.rich_text import validate_rich_text

CHANGELOG_MEDIA_PURPOSES: dict[str, tuple[str, ...]] = {
    "image": ("changelog_image",),
    "video": ("changelog_video",),
}


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
        entry = await self.changelogs.get(
            changelog_id, include_drafts=viewer_is_admin
        )
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")

        return ChangelogDetail(**_summary(entry).model_dump(), content=entry.content)

    async def _validate(self, content: dict, actor: User) -> str:
        return await validate_rich_text(
            content,
            identity_key=f"user:{actor.id}",
            allowed_purposes=CHANGELOG_MEDIA_PURPOSES,
            uploads=self.uploads,
        )

    async def create(
        self, payload: ChangelogCreateRequest, actor: User
    ) -> ChangelogDetail:
        excerpt = await self._validate(payload.content, actor)
        entry = ChangelogEntry(
            title=payload.title,
            content=payload.content,
            excerpt=excerpt,
            is_published=False,
            published_at=None,
        )
        self.session.add(entry)
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
            entry.content = payload.content
            entry.excerpt = await self._validate(payload.content, actor)
        await self.session.commit()
        return await self.get(changelog_id, viewer_is_admin=True)

    async def delete(self, changelog_id: uuid.UUID) -> None:
        entry = await self.changelogs.get(changelog_id, include_drafts=True)
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")
        await self.session.delete(entry)
        await self.session.commit()

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
