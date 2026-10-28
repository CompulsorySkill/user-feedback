"""评论业务规则：3 层上限、关闭冻结、匿名身份。"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.identity import (
    AnonymousIdentity,
    AuthenticatedUser,
    Identity,
)
from app.core.rate_limit import enforce_rate_limit
from app.models import Board, Comment, Post, User
from app.repositories.comments import CommentRepository
from app.repositories.posts import PostRepository
from app.schemas.comment import CommentCreateRequest, CommentItem, CommentList

MAX_DEPTH = 3


class CommentService:
    def __init__(
        self,
        session: AsyncSession,
        posts: PostRepository,
        comments: CommentRepository,
    ) -> None:
        self.session = session
        self.posts = posts
        self.comments = comments

    async def _post(self, post_id: uuid.UUID) -> tuple[Post, Board]:
        row = await self.posts.get_with_board(post_id)
        if row is None:
            raise AppException(404, code="POST_NOT_FOUND", detail="反馈不存在")
        post, board, _author = row
        return post, board

    @staticmethod
    def _item(
        comment: Comment, author_name: str | None
    ) -> CommentItem:
        return CommentItem(
            id=comment.id,
            post_id=comment.post_id,
            parent_id=comment.parent_id,
            content=comment.content,
            author_name=author_name,
            is_anonymous=comment.author_id is None,
            created_at=comment.created_at,
        )

    async def list(self, post_id: uuid.UUID) -> CommentList:
        await self._post(post_id)
        rows = await self.comments.list_for_post(post_id)
        return CommentList(
            items=[self._item(comment, name) for comment, name in rows],
            total=len(rows),
        )

    async def create(
        self,
        post_id: uuid.UUID,
        payload: CommentCreateRequest,
        identity: Identity,
    ) -> CommentItem:
        post, board = await self._post(post_id)
        if post.status == "closed":
            raise AppException(
                403, code="POST_CLOSED", detail="反馈已关闭，不能评论"
            )
        if isinstance(identity, AnonymousIdentity) and not board.allow_guest_commenting:
            raise AppException(
                403,
                code="GUEST_COMMENTING_DISABLED",
                detail="该看板仅允许登录用户评论",
            )
        if identity is None:
            raise AppException(403, code="IDENTITY_REQUIRED", detail="缺少身份")

        await enforce_rate_limit(
            self.session, identity_key=identity.key, action="comment"
        )

        content = payload.content
        parent_id = payload.parent_id

        if parent_id is not None:
            parent = await self.comments.get(parent_id)
            if parent is None or parent.post_id != post_id:
                raise AppException(404, code="PARENT_NOT_FOUND", detail="父评论不存在")

            depth = await self.comments.parent_chain_depth(parent)
            if depth + 1 > MAX_DEPTH:
                # 超过 3 层：挂到根评论，用「回复 @xxx」平铺呈现。
                root = parent
                while root.parent_id is not None:
                    ancestor = await self.comments.get(root.parent_id)
                    if ancestor is None:
                        break
                    root = ancestor
                label = await self._author_label(parent)
                content = f"回复 @{label}：{content}"
                parent_id = root.id

        author_id = (
            identity.user.id if isinstance(identity, AuthenticatedUser) else None
        )
        anonymous_token = (
            identity.token if isinstance(identity, AnonymousIdentity) else None
        )

        comment = Comment(
            post_id=post_id,
            parent_id=parent_id,
            content=content,
            author_id=author_id,
            anonymous_token=anonymous_token,
        )
        self.comments.add(comment)
        await self.session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(comment_count=Post.comment_count + 1)
        )
        await self.session.commit()

        author_name = None
        if author_id is not None:
            user = await self.session.get(User, author_id)
            author_name = user.display_name if user else None

        return self._item(comment, author_name)

    async def delete(self, post_id: uuid.UUID, comment_id: uuid.UUID) -> str:
        """管理员删除评论及其全部回复，返回被删评论内容供审计。"""
        post, _board = await self._post(post_id)
        comment = await self.comments.get(comment_id)
        if comment is None or comment.post_id != post_id:
            raise AppException(404, code="COMMENT_NOT_FOUND", detail="评论不存在")

        content = comment.content
        levels = await self.comments.subtree(comment_id)
        for level in levels:
            await self.session.execute(delete(Comment).where(Comment.id.in_(level)))
        post.comment_count = max(0, post.comment_count - sum(len(x) for x in levels))
        await self.session.commit()
        return content

    async def _author_label(self, comment: Comment) -> str:
        if comment.author_id is None:
            return "匿名用户"
        user = await self.session.get(User, comment.author_id)
        return user.display_name if user and user.display_name else "用户"
