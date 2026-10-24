"""反馈帖数据访问（keyset 分页：最近 / 最热）。"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import Select, and_, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Cursor, TopCursor
from app.models import Board, Post, PostTag, Tag, User

PostSort = Literal["recent", "top"]

PostRow = tuple[Post, str, str, str | None]


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base(self) -> Select[tuple[Post, str, str, str | None]]:
        return (
            select(Post, Board.slug, Board.name, User.display_name)
            .join(Board, Board.id == Post.board_id)
            .outerjoin(User, User.id == Post.author_id)
            .where(Board.is_public.is_(True))
        )

    async def _list(
        self,
        *,
        board_id: int | None = None,
        board_slug: str | None = None,
        limit: int,
        sort: PostSort = "recent",
        status: str | None = None,
        query: str | None = None,
        tag_normalized: Sequence[str] | None = None,
        cursor: Cursor | None = None,
        top_cursor: TopCursor | None = None,
    ) -> list[PostRow]:
        stmt = self._base()
        if board_id is not None:
            stmt = stmt.where(Post.board_id == board_id)
        if board_slug is not None:
            stmt = stmt.where(Board.slug == board_slug)
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
        if tag_normalized:
            tagged_posts = (
                select(PostTag.post_id)
                .join(Tag, Tag.id == PostTag.tag_id)
                .where(Tag.normalized.in_(list(tag_normalized)))
            )
            stmt = stmt.where(Post.id.in_(tagged_posts))

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
        return [
            (post, slug, name, author_name)
            for post, slug, name, author_name in rows.all()
        ]

    async def list_by_board(
        self,
        board_id: int,
        *,
        limit: int,
        sort: PostSort = "recent",
        status: str | None = None,
        query: str | None = None,
        tag_normalized: Sequence[str] | None = None,
        cursor: Cursor | None = None,
        top_cursor: TopCursor | None = None,
    ) -> list[PostRow]:
        return await self._list(
            board_id=board_id,
            limit=limit,
            sort=sort,
            status=status,
            query=query,
            tag_normalized=tag_normalized,
            cursor=cursor,
            top_cursor=top_cursor,
        )

    async def list_all(
        self,
        *,
        limit: int,
        sort: PostSort = "recent",
        status: str | None = None,
        query: str | None = None,
        board_slug: str | None = None,
        tag_normalized: Sequence[str] | None = None,
        cursor: Cursor | None = None,
        top_cursor: TopCursor | None = None,
    ) -> list[PostRow]:
        """全部公开看板的反馈汇总；可按看板与标签筛选。"""
        return await self._list(
            board_slug=board_slug,
            limit=limit,
            sort=sort,
            status=status,
            query=query,
            tag_normalized=tag_normalized,
            cursor=cursor,
            top_cursor=top_cursor,
        )

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
