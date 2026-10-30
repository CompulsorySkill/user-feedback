"""用户目录：只读列表。角色由 ADMIN_EMAILS 在登录时重算，此处不提供写操作。"""

from __future__ import annotations

from app.repositories.users import UserRepository
from app.schemas.common import Page
from app.schemas.user import AdminUserItem


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def list_page(
        self,
        *,
        limit: int,
        before_id: int | None = None,
        query: str | None = None,
        role: str | None = None,
    ) -> Page[AdminUserItem]:
        rows = await self.users.list_page(
            limit=limit + 1, before_id=before_id, query=query, role=role
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = str(rows[-1][0].id) if has_more and rows else None
        return Page(
            items=[
                AdminUserItem(
                    id=user.id,
                    email=user.email,
                    display_name=user.display_name,
                    role=user.role,
                    sso_provider=user.sso_provider,
                    post_count=post_count,
                    comment_count=comment_count,
                    created_at=user.created_at,
                )
                for user, post_count, comment_count in rows
            ],
            next_cursor=next_cursor,
        )
