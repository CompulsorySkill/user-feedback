"""A2–A4：会话过期标记、POST SSO 登录与合并失败降级。"""

from __future__ import annotations

import time

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.errors import AppException
from tests.conftest import insert_board

SECRET = "session-hardening-secret-0123456789abcdef"
SESSION_SECRET = "session-hardening-session-0123456789abcdef"


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "sso_secrets", [SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", SESSION_SECRET)
    monkeypatch.setattr(settings, "admin_emails", "admin@example.com")
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "sso_return_to_default", "/")


def sso_token(email: str = "admin@example.com", secret: str = SECRET) -> str:
    return jwt.encode(
        {"email": email, "name": "测试", "exp": int(time.time()) + 300},
        secret,
        algorithm="HS256",
    )


def doc() -> dict:
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "正文"}]}
        ],
    }


async def test_post_sso_login_sets_session(client: AsyncClient, auth_env) -> None:
    response = await client.post(
        "/api/sso/jwt",
        json={"token": sso_token(), "return_to": "/b/product"},
    )

    assert response.status_code == 200
    assert response.json() == {"redirect_to": "/b/product"}
    assert "feedback_access" in client.cookies
    assert "feedback_refresh" in client.cookies
    assert (await client.get("/api/v1/auth/me")).json()["is_admin"] is True


async def test_post_sso_login_rejects_invalid_token(
    client: AsyncClient, auth_env
) -> None:
    response = await client.post(
        "/api/sso/jwt",
        json={"token": sso_token(secret="wrong-secret-0123456789abcdef")},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_SSO_TOKEN"
    assert "feedback_access" not in client.cookies


async def test_post_sso_login_validates_return_to(
    client: AsyncClient, auth_env
) -> None:
    response = await client.post(
        "/api/sso/jwt",
        json={"token": sso_token(), "return_to": "//evil.example.com"},
    )

    assert response.status_code == 200
    assert response.json()["redirect_to"] == "/"


async def test_merge_failure_does_not_block_get_login(
    client: AsyncClient, sqlite_conn, auth_env, monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    insert_board(sqlite_conn)
    created = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "匿名帖", "content": doc()},
    )
    assert created.status_code == 201

    async def boom(*_args, **_kwargs):
        raise RuntimeError("merge failed")

    monkeypatch.setattr("app.services.sso.merge_anonymous_identity", boom)

    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token(), "return_to": "/"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "feedback_access" in client.cookies
    # 合并失败保留匿名 cookie，账号仍是登录态
    assert "feedback_anonymous" in client.cookies
    assert (await client.get("/api/v1/auth/me")).json()["authenticated"] is True
    assert sqlite_conn.execute(
        "SELECT author_id FROM posts WHERE title='匿名帖'"
    ).fetchone() == (None,)
    assert any("匿名数据合并失败" in record.message for record in caplog.records)


async def test_merge_failure_does_not_block_dev_login(
    client: AsyncClient, sqlite_conn, auth_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    insert_board(sqlite_conn)
    await client.post(
        "/api/v1/boards/product/posts", json={"title": "匿名帖", "content": doc()}
    )

    async def boom(*_args, **_kwargs):
        raise RuntimeError("merge failed")

    monkeypatch.setattr("app.services.sso.merge_anonymous_identity", boom)

    response = await client.post(
        "/api/v1/auth/dev-login", json={"email": "admin@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert "feedback_anonymous" in client.cookies


async def test_session_expired_header(client: AsyncClient, auth_env) -> None:
    client.cookies.set("feedback_access", "not-a-valid-jwt")
    expired = await client.get("/api/v1/auth/me")

    assert expired.headers.get("x-session-expired") == "1"

    client.cookies.delete("feedback_access")
    await client.get(
        "/api/sso/jwt", params={"token": sso_token(), "return_to": "/"}, follow_redirects=False
    )
    valid = await client.get("/api/v1/auth/me")
    assert valid.headers.get("x-session-expired") is None


async def test_verify_sso_rotation_accepts_old_and_new_secret(
    monkeypatch: pytest.MonkeyPatch, auth_env
) -> None:
    from app.core.security import verify_sso_token

    old = "old-secret-0123456789abcdef012345"
    new = "new-secret-0123456789abcdef012345"
    monkeypatch.setattr(settings, "sso_secrets", [new, old])

    assert verify_sso_token(sso_token(secret=old)).email == "admin@example.com"
    assert verify_sso_token(sso_token(secret=new)).email == "admin@example.com"

    monkeypatch.setattr(settings, "sso_secrets", [new])
    with pytest.raises(AppException):
        verify_sso_token(sso_token(secret=old))
