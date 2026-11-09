"""编辑反馈时可迁移所属看板（仅限公开看板）。"""

from __future__ import annotations

import time
from datetime import datetime

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board

SSO_SECRET = "test-sso-secret-0123456789abcdef012345"
TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef012345"
ADMIN_EMAIL = "admin@example.com"
BASE = datetime(2026, 5, 1, 12, 0, 0)


@pytest.fixture(autouse=True)
def sso_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "sso_secrets", [SSO_SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", TEST_SESSION_SECRET)
    monkeypatch.setattr(settings, "admin_emails", ADMIN_EMAIL)
    monkeypatch.setattr(settings, "sso_return_to_default", "/")


async def login(client: AsyncClient, email: str) -> None:
    payload = {"email": email, "exp": int(time.time()) + 300}
    token = jwt.encode(payload, SSO_SECRET, algorithm="HS256")
    response = await client.get(
        "/api/sso/jwt",
        params={"token": token, "return_to": "/"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


def doc(text: str = "正文") -> dict:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


async def test_author_can_move_post_to_another_board(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn, slug="product", name="功能建议")
    insert_board(sqlite_conn, slug="bugs", name="问题反馈")
    await login(client, "alice@example.com")

    created = await client.post(
        "/api/v1/boards/product/posts", json={"title": "跑错板块", "content": doc()}
    )
    assert created.status_code == 201, created.text

    moved = await client.patch(
        f"/api/v1/posts/{created.json()['id']}", json={"board_slug": "bugs"}
    )

    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["board_slug"] == "bugs"
    assert body["board"]["slug"] == "bugs"
    # 详情与看板列表都要按新看板读回，不能只在响应体里改字段。
    assert (await client.get(f"/api/v1/boards/bugs/posts")).json()["items"][0][
        "board_slug"
    ] == "bugs"
    assert (await client.get("/api/v1/boards/product/posts")).json()["items"] == []


async def test_move_rejects_unknown_or_private_board(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn, slug="product")
    insert_board(sqlite_conn, slug="secret", is_public=False)
    await login(client, "alice@example.com")
    created = await client.post(
        "/api/v1/boards/product/posts", json={"title": "标题", "content": doc()}
    )
    post_id = created.json()["id"]

    hidden = await client.patch(
        f"/api/v1/posts/{post_id}", json={"board_slug": "secret"}
    )
    assert hidden.status_code == 404
    assert hidden.json()["code"] == "BOARD_NOT_FOUND"

    missing = await client.patch(
        f"/api/v1/posts/{post_id}", json={"board_slug": "nope"}
    )
    assert missing.status_code == 404
    assert (await client.get(f"/api/v1/posts/{post_id}")).json()[
        "board_slug"
    ] == "product"


async def test_omitting_board_slug_keeps_current_board(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn, slug="product")
    await login(client, "alice@example.com")
    created = await client.post(
        "/api/v1/boards/product/posts", json={"title": "旧标题", "content": doc()}
    )

    updated = await client.patch(
        f"/api/v1/posts/{created.json()['id']}", json={"title": "新标题"}
    )

    assert updated.status_code == 200
    assert updated.json()["title"] == "新标题"
    assert updated.json()["board_slug"] == "product"
