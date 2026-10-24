"""更新日志数据访问：非管理员强制只看已发布。"""

from __future__ import annotations

import uuid

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Cursor
from app.models import ChangelogEntry


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
