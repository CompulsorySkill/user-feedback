"""标签数据访问。"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PostTag, Tag


class TagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_counts(self):
        return (
            select(Tag, func.count(PostTag.post_id))
            .outerjoin(PostTag, PostTag.tag_id == Tag.id)
            .group_by(Tag.id)
            .order_by(Tag.name.asc(), Tag.id.asc())
        )

    async def list_builtin(self) -> list[tuple[Tag, int]]:
        rows = await self.session.execute(
            self._with_counts().where(Tag.is_builtin.is_(True))
        )
        return [(tag, count) for tag, count in rows.all()]

    async def list_all(self) -> list[tuple[Tag, int]]:
        rows = await self.session.execute(self._with_counts())
        return [(tag, count) for tag, count in rows.all()]

    async def get_by_normalized(self, normalized: str) -> Tag | None:
        return await self.session.scalar(
            select(Tag).where(Tag.normalized == normalized)
        )

    async def get_by_id(self, tag_id: int) -> Tag | None:
        return await self.session.get(Tag, tag_id)

    async def for_posts(self, post_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Tag]]:
        if not post_ids:
            return {}
        stmt = (
            select(PostTag.post_id, Tag)
            .join(Tag, Tag.id == PostTag.tag_id)
            .where(PostTag.post_id.in_(post_ids))
            .order_by(Tag.name.asc(), Tag.id.asc())
        )
        rows = await self.session.execute(stmt)
        result: dict[uuid.UUID, list[Tag]] = {}
        for post_id, tag in rows.all():
            result.setdefault(post_id, []).append(tag)
        return result

    async def replace_for_post(self, post_id: uuid.UUID, tag_ids: list[int]) -> None:
        await self.session.execute(delete(PostTag).where(PostTag.post_id == post_id))
        if tag_ids:
            await self.session.execute(
                insert(PostTag),
                [{"post_id": post_id, "tag_id": tag_id} for tag_id in tag_ids],
            )

    async def count_usage(self, tag_id: int) -> int:
        stmt = select(func.count(PostTag.post_id)).where(PostTag.tag_id == tag_id)
        return int(await self.session.scalar(stmt) or 0)

    async def delete_cascade(self, tag: Tag) -> None:
        await self.session.execute(delete(PostTag).where(PostTag.tag_id == tag.id))
        await self.session.delete(tag)
