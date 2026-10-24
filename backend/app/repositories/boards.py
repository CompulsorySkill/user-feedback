"""看板数据访问。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Board, Post


class BoardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_public(self) -> list[tuple[Board, int]]:
        """公开看板 + 已发布内容量（P1 读路径按公开性过滤）。"""
        stmt = (
            select(Board, func.count(Post.id))
            .outerjoin(Post, Post.board_id == Board.id)
            .where(Board.is_public.is_(True))
            .group_by(Board.id)
            .order_by(Board.created_at.asc(), Board.id.asc())
        )
        rows = await self.session.execute(stmt)
        return [(board, count) for board, count in rows.all()]

    async def get_public_by_slug(self, slug: str) -> Board | None:
        stmt = select(Board).where(
            Board.slug == slug, Board.is_public.is_(True)
        )
        return await self.session.scalar(stmt)

    async def count_posts(self, board_id: int) -> int:
        stmt = select(func.count(Post.id)).where(Post.board_id == board_id)
        return int(await self.session.scalar(stmt) or 0)
