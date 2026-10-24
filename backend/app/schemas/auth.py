"""登录会话相关响应模式。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class UserInfo(BaseModel):
    id: int
    email: str
    display_name: str | None
    role: Literal["user", "admin"]


class MeResponse(BaseModel):
    authenticated: bool
    is_admin: bool
    is_anonymous: bool
    user: UserInfo | None = None
