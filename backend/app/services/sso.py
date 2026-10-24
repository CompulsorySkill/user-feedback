"""SSO JIT 用户与匿名数据合并。"""

from __future__ import annotations

import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import SSOClaims
from app.models import Post, User, Vote

logger = logging.getLogger(__name__)


def role_for(email: str) -> str:
    return "admin" if email in settings.admin_email_set else "user"


async def login_or_create_user(session: AsyncSession, claims: SSOClaims) -> User:
    user = await session.scalar(select(User).where(User.email == claims.email))
    role = role_for(claims.email)

    if user is None:
        user = User(
            email=claims.email,
            display_name=claims.name,
            role=role,
            sso_provider="sso",
        )
        session.add(user)
        await session.flush()
        return user

    user.role = role
    if claims.name:
        user.display_name = claims.name
    user.sso_provider = "sso"
    return user


async def merge_anonymous_identity(
    session: AsyncSession, anonymous_token: str, user_id: int
) -> None:
    """登录时把匿名反馈与匿名票归到账号下（同一事务内）。"""
    await session.execute(
        update(Post)
        .where(Post.anonymous_token == anonymous_token)
        .values(author_id=user_id, anonymous_token=None)
    )

    votes = (
        await session.execute(
            select(Vote).where(Vote.anonymous_token == anonymous_token)
        )
    ).scalars().all()

    for vote in votes:
        existing = await session.scalar(
            select(Vote.id).where(
                Vote.post_id == vote.post_id, Vote.user_id == user_id
            )
        )
        if existing is not None:
            await session.delete(vote)
        else:
            vote.user_id = user_id
            vote.anonymous_token = None


async def merge_anonymous_identity_safely(
    session: AsyncSession, anonymous_token: str, user_id: int
) -> bool:
    """合并匿名数据；失败不阻断登录，回滚并记录日志。

    返回 True 表示合并成功（调用方可以清除匿名 cookie）。
    """
    try:
        await merge_anonymous_identity(session, anonymous_token, user_id)
        await session.commit()
        return True
    except Exception:  # noqa: BLE001 - 合并是尽力而为，不能影响登录
        await session.rollback()
        logger.exception("匿名数据合并失败，已跳过（user_id=%s）", user_id)
        return False
