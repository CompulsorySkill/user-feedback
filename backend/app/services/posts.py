"""反馈帖业务规则：读路径 + 匿名创建。"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.identity import AnonymousIdentity
from app.core.pagination import decode_cursor, encode_cursor
from app.core.rate_limit import enforce_rate_limit
from app.models import Post
from app.repositories.boards import BoardRepository
from app.repositories.posts import PostRepository
from app.repositories.uploads import UploadRepository
from app.schemas.board import BoardRef
from app.schemas.common import Page
from app.schemas.post import PostCreateRequest, PostDetail, PostSummary
from app.services.rich_text import validate_rich_text

# 反馈中允许的媒体节点 -> Upload purpose
POST_MEDIA_PURPOSES: dict[str, tuple[str, ...]] = {
    "image": ("post_image",),
    "video": ("post_video",),
}


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
    def __init__(
        self,
        session: AsyncSession,
        posts: PostRepository,
        boards: BoardRepository,
        uploads: UploadRepository,
    ) -> None:
        self.session = session
        self.posts = posts
        self.boards = boards
        self.uploads = uploads

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

    async def create(
        self,
        slug: str,
        payload: PostCreateRequest,
        identity: AnonymousIdentity,
    ) -> PostDetail:
        board = await self.boards.get_public_by_slug(slug)
        if board is None:
            raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")
        if not board.allow_guest_posting:
            raise AppException(
                403,
                code="GUEST_POSTING_DISABLED",
                detail="该看板仅允许登录用户发布",
            )

        await enforce_rate_limit(
            self.session, identity_key=identity.key, action="post"
        )
        excerpt = await validate_rich_text(
            payload.content,
            identity_key=identity.key,
            allowed_purposes=POST_MEDIA_PURPOSES,
            uploads=self.uploads,
        )

        post = Post(
            board_id=board.id,
            title=payload.title,
            content=payload.content,
            excerpt=excerpt,
            status="open",
            author_id=None,
            anonymous_token=identity.token,
        )
        self.session.add(post)
        await self.session.commit()

        return await self.get(post.id)
