"""标签数据访问。"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Board, Post, PostTag, Tag


class TagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_counts(
        self,
        *,
        board_slug: str | None = None,
        public_only: bool = True,
        builtin_only: bool = False,
    ):
        """返回标签及其帖子数；计数可按看板限定，并默认只统计公开看板。"""
        counts = (
            select(PostTag.tag_id, func.count(PostTag.post_id).label("count"))
            .join(Post, Post.id == PostTag.post_id)
            .join(Board, Board.id == Post.board_id)
            .group_by(PostTag.tag_id)
        )
        if board_slug is not None:
            counts = counts.where(Board.slug == board_slug)
        if public_only:
            counts = counts.where(Board.is_public.is_(True))
        counted = counts.subquery()

        stmt = (
            select(Tag, func.coalesce(counted.c.count, 0))
            .outerjoin(counted, counted.c.tag_id == Tag.id)
            .order_by(Tag.name.asc(), Tag.id.asc())
        )
        if builtin_only:
            stmt = stmt.where(Tag.is_builtin.is_(True))
        return stmt

    async def list_builtin(
        self, *, board_slug: str | None = None
    ) -> list[tuple[Tag, int]]:
        rows = await self.session.execute(
            self._with_counts(board_slug=board_slug, builtin_only=True)
        )
        return [(tag, count) for tag, count in rows.all()]

    async def list_all(
        self,
        *,
        board_slug: str | None = None,
        public_only: bool = True,
    ) -> list[tuple[Tag, int]]:
        rows = await self.session.execute(
            self._with_counts(board_slug=board_slug, public_only=public_only)
        )
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
