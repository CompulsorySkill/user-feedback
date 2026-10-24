"""反馈帖数据访问（keyset 分页：最近 / 最热）。"""

from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import Select, and_, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Cursor, TopCursor
from app.models import Board, Post, User

PostSort = Literal["recent", "top"]


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base(self) -> Select[tuple[Post, User.display_name]]:
        return select(Post, User.display_name).outerjoin(
            User, User.id == Post.author_id
        )

    async def list_by_board(
        self,
        board_id: int,
        *,
        limit: int,
        sort: PostSort = "recent",
        status: str | None = None,
        query: str | None = None,
        cursor: Cursor | None = None,
        top_cursor: TopCursor | None = None,
    ) -> list[tuple[Post, str | None]]:
        stmt = self._base().where(Post.board_id == board_id)
        if status is not None:
            stmt = stmt.where(Post.status == status)
        if query:
            escaped = (
                query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            stmt = stmt.where(
                or_(
                    Post.title.ilike(pattern, escape="\\"),
                    Post.excerpt.ilike(pattern, escape="\\"),
                )
            )

        if sort == "top":
            if top_cursor is not None:
                stmt = stmt.where(
                    or_(
                        Post.vote_count < top_cursor.vote_count,
                        and_(
                            Post.vote_count == top_cursor.vote_count,
                            Post.id < top_cursor.id,
                        ),
                    )
                )
            stmt = stmt.order_by(Post.vote_count.desc(), Post.id.desc())
        else:
            if cursor is not None:
                stmt = stmt.where(
                    tuple_(Post.created_at, Post.id)
                    < tuple_(cursor.created_at, cursor.id)
                )
            stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc())

        stmt = stmt.limit(limit)
        rows = await self.session.execute(stmt)
        return [(post, author_name) for post, author_name in rows.all()]

    async def get_with_board(
        self, post_id: uuid.UUID
    ) -> tuple[Post, Board, str | None] | None:
        stmt = (
            select(Post, Board, User.display_name)
            .join(Board, Board.id == Post.board_id)
            .outerjoin(User, User.id == Post.author_id)
            .where(Post.id == post_id, Board.is_public.is_(True))
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        post, board, author_name = row
        return post, board, author_name
