"""更新日志数据访问：非管理员强制只看已发布。"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Cursor
from app.models import ChangelogAttachment, ChangelogEntry


class ChangelogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_entries(
        self,
        *,
        limit: int,
        cursor: Cursor | None = None,
        include_drafts: bool = False,
    ) -> list[ChangelogEntry]:
        stmt = select(ChangelogEntry)
        if not include_drafts:
            stmt = stmt.where(ChangelogEntry.is_published.is_(True))
        if cursor is not None:
            stmt = stmt.where(
                tuple_(ChangelogEntry.created_at, ChangelogEntry.id)
                < tuple_(cursor.created_at, cursor.id)
            )
        stmt = stmt.order_by(
            ChangelogEntry.created_at.desc(), ChangelogEntry.id.desc()
        ).limit(limit)
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all())

    async def get(
        self, changelog_id: uuid.UUID, *, include_drafts: bool = False
    ) -> ChangelogEntry | None:
        stmt = select(ChangelogEntry).where(ChangelogEntry.id == changelog_id)
        if not include_drafts:
            stmt = stmt.where(ChangelogEntry.is_published.is_(True))
        return await self.session.scalar(stmt)

    async def list_attachments(
        self, changelog_id: uuid.UUID
    ) -> list[ChangelogAttachment]:
        rows = await self.session.execute(
            select(ChangelogAttachment)
            .where(ChangelogAttachment.changelog_id == changelog_id)
            .order_by(ChangelogAttachment.id.asc())
        )
        return list(rows.scalars().all())

    async def get_attachment(
        self, changelog_id: uuid.UUID, attachment_id: int
    ) -> ChangelogAttachment | None:
        return await self.session.scalar(
            select(ChangelogAttachment).where(
                ChangelogAttachment.id == attachment_id,
                ChangelogAttachment.changelog_id == changelog_id,
            )
        )

    async def replace_attachments(
        self, changelog_id: uuid.UUID, attachments: list[ChangelogAttachment]
    ) -> None:
        await self.session.execute(
            delete(ChangelogAttachment).where(
                ChangelogAttachment.changelog_id == changelog_id
            )
        )
        if attachments:
            self.session.add_all(attachments)
