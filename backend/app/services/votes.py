"""投票业务规则：登录 / 匿名双路径、关闭冻结、计数同事务。"""

from __future__ import annotations

import uuid

from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.core.identity import AnonymousIdentity, AuthenticatedUser, Identity
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

    async def _target(
        self, post_id: uuid.UUID, identity: Identity
    ) -> tuple[Post, Board, int | None, str | None]:
        if identity is None:
            raise AppException(403, code="IDENTITY_REQUIRED", detail="缺少身份")

        row = await self.posts.get_with_board(post_id)
        if row is None:
            raise AppException(404, code="POST_NOT_FOUND", detail="反馈不存在")
        post, board, _author = row

        if post.status == "closed":
            raise AppException(
                403, code="POST_CLOSED", detail="反馈已关闭，不能投票"
            )

        user_id: int | None = None
        anonymous_token: str | None = None
        if isinstance(identity, AuthenticatedUser):
            user_id = identity.user.id
        else:
            if not board.allow_guest_voting:
                raise AppException(
                    403,
                    code="GUEST_VOTING_DISABLED",
                    detail="该看板仅允许登录用户投票",
                )
            assert isinstance(identity, AnonymousIdentity)
            anonymous_token = identity.token

        return post, board, user_id, anonymous_token

    async def _current_count(self, post_id: uuid.UUID) -> int:
        count = await self.session.scalar(
            select(Post.vote_count).where(Post.id == post_id)
        )
        return int(count or 0)

    async def add(self, post_id: uuid.UUID, identity: Identity) -> VoteResponse:
        _post, _board, user_id, anonymous_token = await self._target(
            post_id, identity
        )
        assert identity is not None
        await enforce_rate_limit(
            self.session, identity_key=identity.key, action="vote"
        )

        if await self.votes.exists(
            post_id, user_id=user_id, anonymous_token=anonymous_token
        ):
            count = await self._current_count(post_id)
            await self.session.commit()
            return VoteResponse(voted=True, vote_count=count)

        self.votes.add(
            post_id, user_id=user_id, anonymous_token=anonymous_token
        )
        try:
            await self.session.flush()
        except IntegrityError:
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

    async def remove(self, post_id: uuid.UUID, identity: Identity) -> VoteResponse:
        _post, _board, user_id, anonymous_token = await self._target(
            post_id, identity
        )
        assert identity is not None
        await enforce_rate_limit(
            self.session, identity_key=identity.key, action="vote"
        )

        removed = await self.votes.remove(
            post_id, user_id=user_id, anonymous_token=anonymous_token
        )
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
