"""投票业务规则：匿名唯一、计数同事务维护、关闭后拒绝。"""

from __future__ import annotations

import uuid

from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.identity import AnonymousIdentity
from app.core.rate_limit import enforce_rate_limit
from app.models import Board, Post
from app.repositories.posts import PostRepository
from app.repositories.votes import VoteRepository
from app.schemas.vote import VoteResponse


class VoteService:
    def __init__(
        self,
        session: AsyncSession,
        posts: PostRepository,
        votes: VoteRepository,
    ) -> None:
        self.session = session
        self.posts = posts
        self.votes = votes

    async def _target(self, post_id: uuid.UUID) -> tuple[Post, Board]:
        row = await self.posts.get_with_board(post_id)
        if row is None:
            raise AppException(404, code="POST_NOT_FOUND", detail="反馈不存在")
        post, board, _author = row
        if post.status == "closed":
            raise AppException(
                403, code="POST_CLOSED", detail="反馈已关闭，不能投票"
            )
        if not board.allow_guest_voting:
            raise AppException(
                403, code="GUEST_VOTING_DISABLED", detail="该看板仅允许登录用户投票"
            )
        return post, board

    async def _current_count(self, post_id: uuid.UUID) -> int:
        count = await self.session.scalar(
            select(Post.vote_count).where(Post.id == post_id)
        )
        return int(count or 0)

    async def add(
        self, post_id: uuid.UUID, identity: AnonymousIdentity
    ) -> VoteResponse:
        await self._target(post_id)
        await enforce_rate_limit(
            self.session, identity_key=identity.key, action="vote"
        )

        if await self.votes.exists(post_id, anonymous_token=identity.token):
            # 重复投票幂等返回，前端可安全重试。
            count = await self._current_count(post_id)
            await self.session.commit()
            return VoteResponse(voted=True, vote_count=count)

        self.votes.add(post_id, anonymous_token=identity.token)
        try:
            await self.session.flush()
        except IntegrityError:
            # 并发下唯一索引兜底。
            await self.session.rollback()
            return VoteResponse(
                voted=True, vote_count=await self._current_count(post_id)
            )

        await self.session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(vote_count=Post.vote_count + 1)
        )
        await self.session.commit()
        return VoteResponse(
            voted=True, vote_count=await self._current_count(post_id)
        )

    async def remove(
        self, post_id: uuid.UUID, identity: AnonymousIdentity
    ) -> VoteResponse:
        await self._target(post_id)
        await enforce_rate_limit(
            self.session, identity_key=identity.key, action="vote"
        )

        removed = await self.votes.remove(post_id, anonymous_token=identity.token)
        if removed:
            await self.session.execute(
                update(Post)
                .where(Post.id == post_id)
                .values(
                    vote_count=case(
                        (Post.vote_count > 0, Post.vote_count - 1), else_=0
                    )
                )
            )
        await self.session.commit()
        return VoteResponse(
            voted=False, vote_count=await self._current_count(post_id)
        )
