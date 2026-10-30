"""用户目录数据访问：id 倒序 keyset 分页，附带反馈 / 评论计数。"""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment, Post, User

UserRow = tuple[User, int, int]


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base(self) -> Select[tuple[User, int, int]]:
        post_counts = (
            select(Post.author_id, func.count(Post.id).label("count"))
            .where(Post.author_id.is_not(None))
            .group_by(Post.author_id)
            .subquery()
        )
        comment_counts = (
            select(Comment.author_id, func.count(Comment.id).label("count"))
            .where(Comment.author_id.is_not(None))
            .group_by(Comment.author_id)
            .subquery()
        )
        return (
            select(
                User,
                func.coalesce(post_counts.c.count, 0),
                func.coalesce(comment_counts.c.count, 0),
            )
            .outerjoin(post_counts, post_counts.c.author_id == User.id)
            .outerjoin(comment_counts, comment_counts.c.author_id == User.id)
        )

    async def list_page(
        self,
        *,
        limit: int,
        before_id: int | None = None,
        query: str | None = None,
        role: str | None = None,
    ) -> list[UserRow]:
        stmt = self._base().order_by(User.id.desc())
        if before_id is not None:
            stmt = stmt.where(User.id < before_id)
        if role is not None:
            stmt = stmt.where(User.role == role)
        if query:
            escaped = (
                query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            stmt = stmt.where(
                or_(
                    User.email.ilike(pattern, escape="\\"),
                    User.display_name.ilike(pattern, escape="\\"),
                )
            )
        rows = await self.session.execute(stmt.limit(limit))
        return [
            (user, int(posts), int(comments)) for user, posts, comments in rows.all()
        ]
