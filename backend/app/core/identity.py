"""身份：匿名签名 cookie + 登录用户会话。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

from fastapi import Request, Response

from app.core.config import settings
from app.models import User


def _sign(token: str) -> str:
    digest = hmac.new(
        settings.session_jwt_secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _encode(token: str) -> str:
    return f"{token}.{_sign(token)}"


def _decode(value: str | None) -> str | None:
    if not value:
        return None
    token, separator, signature = value.partition(".")
    if not separator or not token:
        return None
    if not hmac.compare_digest(signature, _sign(token)):
        return None
    return token


@dataclass(frozen=True)
class AnonymousIdentity:
    token: str

    @property
    def key(self) -> str:
        """写入 Upload / RateLimitCounter / Vote 的身份键。"""
        return f"anon:{self.token}"


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User

    @property
    def key(self) -> str:
        return f"user:{self.user.id}"

    @property
    def is_admin(self) -> bool:
        return self.user.role == "admin"


Identity = AuthenticatedUser | AnonymousIdentity | None


def get_anonymous_identity(request: Request) -> AnonymousIdentity | None:
    token = _decode(request.cookies.get(settings.anonymous_cookie_name))
    return AnonymousIdentity(token) if token else None


def set_anonymous_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.anonymous_cookie_name,
        value=_encode(token),
        max_age=settings.anonymous_cookie_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


def ensure_anonymous_identity(
    request: Request, response: Response
) -> AnonymousIdentity:
    """首次写操作签发匿名 cookie；已有合法 cookie 则复用。"""
    existing = get_anonymous_identity(request)
    if existing is not None:
        return existing

    identity = AnonymousIdentity(secrets.token_urlsafe(32))
    set_anonymous_cookie(response, identity.token)
    return identity
