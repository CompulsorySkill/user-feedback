"""公告数据访问：置顶单独取，分页列表永远排除置顶。"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Cursor
from app.models import Announcement, AnnouncementAttachment


class AnnouncementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_entries(
        self,
        *,
        limit: int,
        cursor: Cursor | None = None,
        include_drafts: bool = False,
    ) -> list[Announcement]:
        stmt = select(Announcement).where(Announcement.is_pinned.is_(False))
        if not include_drafts:
            stmt = stmt.where(Announcement.is_published.is_(True))
        if cursor is not None:
            stmt = stmt.where(
                tuple_(Announcement.created_at, Announcement.id)
                < tuple_(cursor.created_at, cursor.id)
            )
        stmt = stmt.order_by(
            Announcement.created_at.desc(), Announcement.id.desc()
        ).limit(limit)
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all())

    async def get_pinned(self, *, include_drafts: bool = False) -> Announcement | None:
        stmt = select(Announcement).where(Announcement.is_pinned.is_(True))
        if not include_drafts:
            stmt = stmt.where(Announcement.is_published.is_(True))
        return await self.session.scalar(stmt.limit(1))

    async def get(
        self, announcement_id: uuid.UUID, *, include_drafts: bool = False
    ) -> Announcement | None:
        stmt = select(Announcement).where(Announcement.id == announcement_id)
        if not include_drafts:
            stmt = stmt.where(Announcement.is_published.is_(True))
        return await self.session.scalar(stmt)

    async def clear_pinned(self) -> None:
        await self.session.execute(
            update(Announcement)
            .where(Announcement.is_pinned.is_(True))
            .values(is_pinned=False)
        )

    async def list_attachments(
        self, announcement_id: uuid.UUID
    ) -> list[AnnouncementAttachment]:
        rows = await self.session.execute(
            select(AnnouncementAttachment)
            .where(AnnouncementAttachment.announcement_id == announcement_id)
            .order_by(AnnouncementAttachment.id.asc())
        )
        return list(rows.scalars().all())

    async def get_attachment(
        self, announcement_id: uuid.UUID, attachment_id: int
    ) -> AnnouncementAttachment | None:
        return await self.session.scalar(
            select(AnnouncementAttachment).where(
                AnnouncementAttachment.id == attachment_id,
                AnnouncementAttachment.announcement_id == announcement_id,
            )
        )

    async def replace_attachments(
        self, announcement_id: uuid.UUID, attachments: list[AnnouncementAttachment]
    ) -> None:
        await self.session.execute(
            delete(AnnouncementAttachment).where(
                AnnouncementAttachment.announcement_id == announcement_id
            )
        )
        if attachments:
            self.session.add_all(attachments)
