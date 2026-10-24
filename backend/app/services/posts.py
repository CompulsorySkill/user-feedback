"""反馈帖业务规则：读路径、创建、状态机与编辑权限。"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.identity import (
    AnonymousIdentity,
    AuthenticatedUser,
    Identity,
)
from app.core.pagination import (
    decode_cursor,
    decode_top_cursor,
    encode_cursor,
    encode_top_cursor,
)
from app.core.rate_limit import enforce_rate_limit
from app.models import Post, Tag
from app.repositories.boards import BoardRepository
from app.repositories.posts import PostRepository
from app.repositories.tags import TagRepository
from app.repositories.uploads import UploadRepository
from app.schemas.board import BoardRef
from app.schemas.common import Page
from app.schemas.post import (
    ClientEnvironment,
    PostCreateRequest,
    PostDetail,
    PostSummary,
    PostUpdateRequest,
)
from app.services.rich_text import collect_media_keys, validate_rich_text
from app.services.tags import TagService, to_ref

# 反馈中允许的媒体节点 -> Upload purpose
POST_MEDIA_PURPOSES: dict[str, tuple[str, ...]] = {
    "image": ("post_image",),
    "video": ("post_video",),
}


def _summary(
    post,
    board_slug: str,
    board_name: str,
    author_name: str | None,
    tags: list[Tag] | None = None,
) -> PostSummary:
    return PostSummary(
        id=post.id,
        board_slug=board_slug,
        board_name=board_name,
        title=post.title,
        excerpt=post.excerpt,
        status=post.status,
        vote_count=post.vote_count,
        comment_count=post.comment_count,
        author_name=author_name,
        anonymous_name=post.anonymous_name,
        is_anonymous=post.author_id is None,
        created_at=post.created_at,
        updated_at=post.updated_at,
        tags=[to_ref(tag) for tag in tags or []],
    )


class PostService:
    def __init__(
        self,
        session: AsyncSession,
        posts: PostRepository,
        boards: BoardRepository,
        uploads: UploadRepository,
        tags: TagRepository,
    ) -> None:
        self.session = session
        self.posts = posts
        self.boards = boards
        self.uploads = uploads
        self.tags = tags
        self.tag_service = TagService(session, tags)

    async def _paginate(
        self,
        fetch,
        *,
        limit: int,
        cursor_raw: str | None,
        sort: str,
    ) -> Page[PostSummary]:
        if sort == "top":
            top_cursor = decode_top_cursor(cursor_raw)
            rows = await fetch(limit + 1, "top", top_cursor=top_cursor)
            has_more = len(rows) > limit
            rows = rows[:limit]
            next_cursor = (
                encode_top_cursor(rows[-1][0].vote_count, rows[-1][0].id)
                if has_more and rows
                else None
            )
        else:
            cursor = decode_cursor(cursor_raw)
            rows = await fetch(limit + 1, "recent", cursor=cursor)
            has_more = len(rows) > limit
            rows = rows[:limit]
            next_cursor = (
                encode_cursor(rows[-1][0].created_at, rows[-1][0].id)
                if has_more and rows
                else None
            )

        tag_map = await self.tags.for_posts([row[0].id for row in rows])
        items = [
            _summary(
                post,
                board_slug,
                board_name,
                name,
                tag_map.get(post.id, []),
            )
            for post, board_slug, board_name, name in rows
        ]
        return Page(items=items, next_cursor=next_cursor)

    async def list_for_board(
        self,
        slug: str,
        *,
        limit: int,
        cursor_raw: str | None,
        status: str | None = None,
        sort: str = "recent",
        query: str | None = None,
    ) -> Page[PostSummary]:
        board = await self.boards.get_public_by_slug(slug)
        if board is None:
            raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")

        async def fetch(size: int, order: str, **kwargs):
            return await self.posts.list_by_board(
                board.id,
                limit=size,
                sort=order,
                status=status,
                query=query,
                **kwargs,
            )

        return await self._paginate(
            fetch, limit=limit, cursor_raw=cursor_raw, sort=sort
        )

    async def list_all(
        self,
        *,
        limit: int,
        cursor_raw: str | None,
        status: str | None = None,
        sort: str = "recent",
        query: str | None = None,
        board_slug: str | None = None,
    ) -> Page[PostSummary]:
        """全部公开看板的反馈汇总，供根页面使用。"""
        if board_slug:
            board = await self.boards.get_public_by_slug(board_slug)
            if board is None:
                raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")

        async def fetch(size: int, order: str, **kwargs):
            return await self.posts.list_all(
                limit=size,
                sort=order,
                status=status,
                query=query,
                board_slug=board_slug,
                **kwargs,
            )

        return await self._paginate(
            fetch, limit=limit, cursor_raw=cursor_raw, sort=sort
        )

    async def get(self, post_id: uuid.UUID, viewer: Identity = None) -> PostDetail:
        row = await self.posts.get_with_board(post_id)
        if row is None:
            raise AppException(404, code="POST_NOT_FOUND", detail="反馈不存在")

        post, board, author_name = row
        is_author = (
            isinstance(viewer, AuthenticatedUser) and post.author_id == viewer.user.id
        )
        tag_map = await self.tags.for_posts([post.id])
        return PostDetail(
            **_summary(
                post,
                board.slug,
                board.name,
                author_name,
                tag_map.get(post.id, []),
            ).model_dump(),
            board=BoardRef(id=board.id, slug=board.slug, name=board.name),
            content=post.content,
            environment=(
                ClientEnvironment(**post.client_env) if post.client_env else None
            ),
            is_author=is_author,
        )

    async def create(
        self,
        slug: str,
        payload: PostCreateRequest,
        identity: Identity,
    ) -> PostDetail:
        if identity is None:
            raise AppException(403, code="IDENTITY_REQUIRED", detail="缺少身份")
        board = await self.boards.get_public_by_slug(slug)
        if board is None:
            raise AppException(404, code="BOARD_NOT_FOUND", detail="看板不存在")

        authenticated = isinstance(identity, AuthenticatedUser)
        if not authenticated and not board.allow_guest_posting:
            raise AppException(
                403,
                code="GUEST_POSTING_DISABLED",
                detail="该看板仅允许登录用户发布",
            )

        await enforce_rate_limit(self.session, identity_key=identity.key, action="post")
        excerpt = await validate_rich_text(
            payload.content,
            identity_keys=[identity.key],
            allowed_purposes=POST_MEDIA_PURPOSES,
            uploads=self.uploads,
        )
        tag_ids = await self.tag_service.resolve_tag_ids(payload.tags, identity)

        post = Post(
            board_id=board.id,
            title=payload.title,
            content=payload.content,
            excerpt=excerpt,
            status="open",
            author_id=identity.user.id if authenticated else None,
            anonymous_token=(
                identity.token if isinstance(identity, AnonymousIdentity) else None
            ),
            anonymous_name=None if authenticated else payload.anonymous_name,
            client_env=(
                payload.environment.model_dump(exclude_none=True)
                if payload.environment is not None
                else None
            ),
        )
        self.session.add(post)
        await self.session.flush()
        if tag_ids:
            await self.tags.replace_for_post(post.id, tag_ids)
        await self.session.commit()

        return await self.get(post.id, identity)

    async def change_status(
        self, post_id: uuid.UUID, target: str, identity: Identity
    ) -> PostDetail:
        row = await self.posts.get_with_board(post_id)
        if row is None:
            raise AppException(404, code="POST_NOT_FOUND", detail="反馈不存在")
        post, _board, _author = row

        if isinstance(identity, AuthenticatedUser):
            if identity.is_admin:
                post.status = target
            elif post.author_id == identity.user.id:
                # 作者仅可单向关闭，关闭后不能自行重开。
                if target != "closed" or post.status == "closed":
                    raise AppException(
                        403, code="STATUS_FORBIDDEN", detail="无权变更该状态"
                    )
                post.status = "closed"
            else:
                raise AppException(
                    403, code="STATUS_FORBIDDEN", detail="无权变更该状态"
                )
        else:
            # 匿名 Post 无作者身份，匿名 cookie 不作为授权依据。
            raise AppException(403, code="STATUS_FORBIDDEN", detail="无权变更该状态")

        await self.session.commit()
        return await self.get(post_id, identity)

    async def update(
        self,
        post_id: uuid.UUID,
        payload: PostUpdateRequest,
        identity: Identity,
    ) -> PostDetail:
        row = await self.posts.get_with_board(post_id)
        if row is None:
            raise AppException(404, code="POST_NOT_FOUND", detail="反馈不存在")
        post, _board, _author = row

        is_admin = isinstance(identity, AuthenticatedUser) and identity.is_admin
        is_author = (
            isinstance(identity, AuthenticatedUser)
            and post.author_id == identity.user.id
        )
        if not (is_admin or is_author):
            raise AppException(403, code="POST_EDIT_FORBIDDEN", detail="无权编辑该反馈")
        if post.status == "closed" and not is_admin:
            raise AppException(403, code="POST_CLOSED", detail="已关闭的反馈不能编辑")

        if payload.title is not None:
            post.title = payload.title
        if payload.content is not None:
            previous_media = collect_media_keys(post.content)
            post.content = payload.content
            post.excerpt = await validate_rich_text(
                payload.content,
                identity_keys=[identity.key],
                allowed_object_keys=previous_media,
                allowed_purposes=POST_MEDIA_PURPOSES,
                uploads=self.uploads,
            )
        if payload.tags is not None:
            tag_ids = await self.tag_service.resolve_tag_ids(payload.tags, identity)
            await self.tags.replace_for_post(post.id, tag_ids)
        await self.session.commit()
        return await self.get(post_id, identity)
