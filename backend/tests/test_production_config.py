"""A5：生产配置校验、Secure cookie 与 ADMIN_EMAILS 升降级。"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import Response
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.security import set_session_cookies
from httpx import AsyncClient

SECRET = "production-rehearsal-secret-0123456789abcdef"
SESSION_SECRET = "production-rehearsal-session-0123456789abcdef"


@pytest.fixture
def prod_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "sso_secrets", [SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", SESSION_SECRET)
    monkeypatch.setattr(settings, "admin_emails", "admin@example.com")
    monkeypatch.setattr(settings, "sso_return_to_default", "/")


def make_settings(**overrides) -> Settings:
    base = {
        "environment": "production",
        "database_url": "postgresql+asyncpg://feedback:pw@postgres:5432/feedback",
        "sso_secrets": ["a" * 64],
        "session_jwt_secret": SESSION_SECRET,
        "rustfs_endpoint_internal": "http://rustfs:9000",
        "rustfs_endpoint_public": "https://feedback.example.com",
        "rustfs_access_key": "access",
        "rustfs_secret_key": "secret",
        "public_origin": "https://feedback.example.com",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_production_config_accepts_complete_settings() -> None:
    config = make_settings()

    assert config.is_production is True
    assert config.database_url.startswith("postgresql")


@pytest.mark.parametrize(
    "overrides",
    [
        {"database_url": "sqlite+aiosqlite:///./feedback.db"},
        {"sso_secrets": []},
        {"session_jwt_secret": ""},
        {"rustfs_endpoint_public": ""},
        {"rustfs_access_key": ""},
    ],
)
def test_production_config_rejects_incomplete_settings(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        make_settings(**overrides)


def test_secure_cookies_in_production(monkeypatch: pytest.MonkeyPatch, prod_env) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    response = Response()
    set_session_cookies(response, access_token="access", refresh_token="refresh")

    headers = response.headers.getlist("set-cookie")
    assert len(headers) == 2
    for header in headers:
        lowered = header.lower()
        assert "httponly" in lowered
        assert "secure" in lowered
        assert "samesite=lax" in lowered

    monkeypatch.setattr(settings, "environment", "development")
    dev_response = Response()
    set_session_cookies(dev_response, access_token="access", refresh_token="refresh")
    assert all(
        "secure" not in header.lower()
        for header in dev_response.headers.getlist("set-cookie")
    )


def token_for(email: str) -> str:
    return jwt.encode(
        {"email": email, "exp": int(time.time()) + 300},
        SECRET,
        algorithm="HS256",
    )


async def test_admin_emails_promotes_and_demotes_on_login(
    client: AsyncClient, prod_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def login() -> dict:
        await client.get(
            "/api/sso/jwt",
            params={"token": token_for("bob@example.com"), "return_to": "/"},
            follow_redirects=False,
        )
        return (await client.get("/api/v1/auth/me")).json()

    monkeypatch.setattr(settings, "admin_emails", "")
    assert (await login())["user"]["role"] == "user"

    monkeypatch.setattr(settings, "admin_emails", "bob@example.com,alice@example.com")
    promoted = await login()
    assert promoted["user"]["role"] == "admin"
    assert promoted["is_admin"] is True

    monkeypatch.setattr(settings, "admin_emails", "")
    demoted = await login()
    assert demoted["user"]["role"] == "user"
    assert demoted["is_admin"] is False
