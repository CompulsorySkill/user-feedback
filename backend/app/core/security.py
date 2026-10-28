"""JWT：SSO 校验、本系统会话签发、return_to 白名单。"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import jwt
from fastapi import Response

from app.core.config import settings
from app.core.errors import AppException

ACCESS_COOKIE = "feedlog_access"
REFRESH_COOKIE = "feedlog_refresh"
ANONYMOUS_COOKIE = settings.anonymous_cookie_name


@dataclass(frozen=True)
class SSOClaims:
    email: str
    name: str | None


def validate_return_to(raw: str | None) -> str:
    """仅允许站内相对路径；非法值静默回退默认路径。"""
    if not raw:
        return settings.sso_return_to_default
    if not raw.startswith("/") or raw.startswith("//") or "\\" in raw:
        return settings.sso_return_to_default

    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        return settings.sso_return_to_default
    return raw


def verify_sso_token(token: str) -> SSOClaims:
    """按 SSO_SECRETS 顺序尝试校验；仅 HS256，密钥按 UTF-8 直接使用。"""
    for secret in settings.sso_secrets:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"require": ["exp", "email"]},
            )
        except jwt.PyJWTError:
            continue

        email = str(payload.get("email", "")).strip().lower()
        if "@" not in email:
            continue
        name = payload.get("name")
        return SSOClaims(email=email, name=str(name)[:128] if name else None)

    raise AppException(401, code="INVALID_SSO_TOKEN", detail="SSO token 无效或已过期")


def _encode(user_id: int, email: str, role: str, *, token_type: str, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": token_type,
        "jti": secrets.token_urlsafe(8),
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.session_jwt_secret, algorithm="HS256")


def create_access_token(*, user_id: int, email: str, role: str) -> str:
    return _encode(
        user_id,
        email,
        role,
        token_type="access",
        lifetime=timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(*, user_id: int, email: str, role: str) -> str:
    return _encode(
        user_id,
        email,
        role,
        token_type="refresh",
        lifetime=timedelta(days=settings.refresh_token_days),
    )


def decode_session_token(token: str, *, expected_type: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.session_jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError:
        raise AppException(401, code="UNAUTHENTICATED", detail="会话已过期") from None

    if payload.get("type") != expected_type:
        raise AppException(401, code="UNAUTHENTICATED", detail="会话类型错误")
    return payload


def set_session_cookies(
    response: Response, *, access_token: str, refresh_token: str
) -> None:
    secure = settings.secure_cookies
    max_age_access = settings.access_token_minutes * 60
    max_age_refresh = settings.refresh_token_days * 24 * 3600

    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=max_age_access,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=max_age_refresh,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
