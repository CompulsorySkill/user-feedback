"""登录会话相关请求 / 响应模式。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("邮箱格式不正确")
    return email


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


class DevLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str | None = Field(default=None, max_length=128)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return normalize_email(value)


class AdminLoginRequest(DevLoginRequest):
    """管理员邮箱 + 密码登录；显示名仍可选。"""

    password: str = Field(min_length=1, max_length=128)


class AuthCapabilities(BaseModel):
    sso: bool = True
    dev_login: bool
    admin_login: bool = False


class SSOLoginRequest(BaseModel):
    token: str = Field(min_length=1, max_length=4096)
    return_to: str | None = None


class SSOLoginResponse(BaseModel):
    redirect_to: str
