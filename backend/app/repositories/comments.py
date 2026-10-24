"""评论数据访问：按 post 扁平取出，Service 层组装树。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment, User


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_post(
        self, post_id: uuid.UUID
    ) -> list[tuple[Comment, str | None]]:
        stmt = (
            select(Comment, User.display_name)
            .outerjoin(User, User.id == Comment.author_id)
            .where(Comment.post_id == post_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
        )
        rows = await self.session.execute(stmt)
        return [(comment, name) for comment, name in rows.all()]

    async def get(self, comment_id: uuid.UUID) -> Comment | None:
        return await self.session.get(Comment, comment_id)

    def add(self, comment: Comment) -> None:
        self.session.add(comment)

    async def parent_chain_depth(self, comment: Comment) -> int:
        """返回评论深度（根评论为 1）。"""
        depth = 1
        current = comment
        seen: set[uuid.UUID] = set()
        while current.parent_id is not None and current.parent_id not in seen:
            seen.add(current.parent_id)
            parent = await self.get(current.parent_id)
            if parent is None:
                break
            depth += 1
            current = parent
        return depth
