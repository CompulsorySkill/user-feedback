"""管理员邮箱 + 密码登录：开发与生产都可用，显示名可选。"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "s3cret-admin-pw"


@pytest.fixture
def admin_login_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_emails", ADMIN_EMAIL)
    monkeypatch.setattr(settings, "admin_password", ADMIN_PASSWORD)


async def admin_login(
    client: AsyncClient,
    *,
    email: str = ADMIN_EMAIL,
    password: str = ADMIN_PASSWORD,
    name: str | None = None,
) -> object:
    payload: dict[str, str] = {"email": email, "password": password}
    if name is not None:
        payload["name"] = name
    return await client.post("/api/v1/auth/admin-login", json=payload)


async def test_admin_login_in_development(client: AsyncClient, admin_login_env) -> None:
    caps = (await client.get("/api/v1/auth/capabilities")).json()
    assert caps["admin_login"] is True

    response = await admin_login(client, name="管理员")
    assert response.status_code == 200
    body = response.json()
    assert body["is_admin"] is True
    assert body["user"]["role"] == "admin"
    assert body["user"]["display_name"] == "管理员"

    me = (await client.get("/api/v1/auth/me")).json()
    assert me["user"]["email"] == ADMIN_EMAIL


async def test_admin_login_in_production(
    client: AsyncClient, admin_login_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "production")

    response = await admin_login(client)
    assert response.status_code == 200
    assert response.json()["is_admin"] is True


async def test_admin_login_display_name_is_optional(
    client: AsyncClient, admin_login_env
) -> None:
    response = await admin_login(client)
    assert response.status_code == 200
    assert response.json()["user"]["display_name"] is None


async def test_admin_login_rejects_wrong_password(
    client: AsyncClient, admin_login_env
) -> None:
    response = await admin_login(client, password="wrong")
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
    assert (await client.get("/api/v1/auth/me")).json()["authenticated"] is False


async def test_admin_login_rejects_non_admin_email(
    client: AsyncClient, admin_login_env
) -> None:
    response = await admin_login(client, email="user@example.com")
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_admin_login_disabled_without_config(client: AsyncClient) -> None:
    caps = (await client.get("/api/v1/auth/capabilities")).json()
    assert caps["admin_login"] is False

    response = await admin_login(client)
    assert response.status_code == 404
    assert (await client.get("/api/v1/auth/me")).json()["authenticated"] is False


async def test_admin_login_is_rate_limited(
    client: AsyncClient, admin_login_env
) -> None:
    for _ in range(10):
        assert (await admin_login(client, password="wrong")).status_code == 401

    blocked = await admin_login(client, password="wrong")
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "RATE_LIMITED"
