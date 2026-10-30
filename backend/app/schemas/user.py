"""用户目录只读模式（角色由 ADMIN_EMAILS 在登录时决定，界面不提供写操作）。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.schemas.common import UTCModel


class AdminUserItem(UTCModel):
    id: int
    email: str
    display_name: str | None
    role: Literal["user", "admin"]
    sso_provider: str | None
    post_count: int
    comment_count: int
    created_at: datetime
