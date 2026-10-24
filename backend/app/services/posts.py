"""反馈帖读路径业务规则。"""

from __future__ import annotations

import uuid

from app.core.errors import AppException
from app.core.pagination import decode_cursor, encode_cursor
from app.repositories.boards import BoardRepository
from app.repositories.posts import PostRepository
from app.schemas.board import BoardRef
from app.schemas.common import Page
from app.schemas.post import PostDetail, PostSummary


def _summary(post, board_slug: str, author_name: str | None) -> PostSummary:
    return PostSummary(
        id=post.id,
        board_slug=board_slug,
        title=post.title,
        excerpt=post.excerpt,
        status=post.status,
        vote_count=post.vote_count,
        comment_count=post.comment_count,
        author_name=author_name,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


class PostService:
    def __init__(self, posts: PostRepository, boards: BoardRepository) -> None:
        self.posts = posts
        self.boards = boards

    async def list_for_board(
        self,
        slug: str,
        *,
        limit: int,
        cursor_raw: str | None,
    ) -> Page[PostSummary]:
        board = await self.boards.get_public_by_slug(slug)
        if board is None:
            raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")

        cursor = decode_cursor(cursor_raw)
        rows = await self.posts.list_by_board(
            board.id, limit=limit + 1, cursor=cursor
        )
        has_more = len(rows) > limit
        rows = rows[:limit]

        items = [_summary(post, board.slug, name) for post, name in rows]
        next_cursor = (
            encode_cursor(rows[-1][0].created_at, rows[-1][0].id)
            if has_more and rows
            else None
        )
        return Page(items=items, next_cursor=next_cursor)

    async def get(self, post_id: uuid.UUID) -> PostDetail:
        row = await self.posts.get_with_board(post_id)
        if row is None:
            raise AppException(404, code="POST_NOT_FOUND", detail="反馈不存在")

        post, board, author_name = row
        return PostDetail(
            **_summary(post, board.slug, author_name).model_dump(),
            board=BoardRef(id=board.id, slug=board.slug, name=board.name),
            content=post.content,
        )
