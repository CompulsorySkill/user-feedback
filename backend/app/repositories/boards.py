"""看板数据访问。"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Board, Comment, Post, PostTag, Vote


class BoardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_counts(self):
        return (
            select(Board, func.count(Post.id))
            .outerjoin(Post, Post.board_id == Board.id)
            .group_by(Board.id)
            .order_by(Board.created_at.asc(), Board.id.asc())
        )

    async def list_public(self) -> list[tuple[Board, int]]:
        """公开看板 + 已发布内容量（P1 读路径按公开性过滤）。"""
        stmt = self._with_counts().where(Board.is_public.is_(True))
        rows = await self.session.execute(stmt)
        return [(board, count) for board, count in rows.all()]

    async def list_all(self) -> list[tuple[Board, int]]:
        """管理员视图：包含未公开看板。"""
        rows = await self.session.execute(self._with_counts())
        return [(board, count) for board, count in rows.all()]

    async def get_public_by_slug(self, slug: str) -> Board | None:
        stmt = select(Board).where(Board.slug == slug, Board.is_public.is_(True))
        return await self.session.scalar(stmt)

    async def get_by_slug(self, slug: str) -> Board | None:
        return await self.session.scalar(select(Board).where(Board.slug == slug))

    async def get_by_id(self, board_id: int) -> Board | None:
        return await self.session.get(Board, board_id)

    async def count_posts(self, board_id: int) -> int:
        stmt = select(func.count(Post.id)).where(Post.board_id == board_id)
        return int(await self.session.scalar(stmt) or 0)

    def add(self, board: Board) -> None:
        self.session.add(board)

    async def delete_with_content(self, board: Board) -> None:
        """显式级联删除，不依赖数据库 FK 开关（测试与服务端连接行为一致）。"""
        post_ids = select(Post.id).where(Post.board_id == board.id)
        await self.session.execute(delete(Vote).where(Vote.post_id.in_(post_ids)))
        await self.session.execute(delete(Comment).where(Comment.post_id.in_(post_ids)))
        await self.session.execute(delete(PostTag).where(PostTag.post_id.in_(post_ids)))
        await self.session.execute(delete(Post).where(Post.board_id == board.id))
        await self.session.delete(board)
