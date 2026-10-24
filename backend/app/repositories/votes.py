"""投票数据访问：登录票与匿名票各走一条唯一索引。"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Vote


class VoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(
        self,
        post_id: uuid.UUID,
        *,
        user_id: int | None = None,
        anonymous_token: str | None = None,
    ) -> bool:
        stmt = select(Vote.id).where(Vote.post_id == post_id)
        if user_id is not None:
            stmt = stmt.where(Vote.user_id == user_id)
        else:
            stmt = stmt.where(Vote.anonymous_token == anonymous_token)
        return await self.session.scalar(stmt) is not None

    def add(
        self,
        post_id: uuid.UUID,
        *,
        user_id: int | None = None,
        anonymous_token: str | None = None,
    ) -> None:
        self.session.add(
            Vote(
                post_id=post_id,
                user_id=user_id,
                anonymous_token=anonymous_token,
            )
        )

    async def remove(
        self,
        post_id: uuid.UUID,
        *,
        user_id: int | None = None,
        anonymous_token: str | None = None,
    ) -> int:
        stmt = delete(Vote).where(Vote.post_id == post_id)
        if user_id is not None:
            stmt = stmt.where(Vote.user_id == user_id)
        else:
            stmt = stmt.where(Vote.anonymous_token == anonymous_token)
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def count_voters(self, post_id: uuid.UUID) -> int:
        stmt = select(func.count(Vote.id)).where(Vote.post_id == post_id)
        return int(await self.session.scalar(stmt) or 0)
