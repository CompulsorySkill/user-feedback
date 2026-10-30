"""用户目录：管理员只读列表、搜索、角色筛选与 keyset 分页。"""

from __future__ import annotations

import time
import uuid
from datetime import datetime

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_post, insert_user, sqlite_timestamp

SSO_SECRET = "test-sso-secret-0123456789abcdef012345"
TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef012345"
ADMIN_EMAIL = "admin@example.com"
BASE = datetime(2026, 4, 1, 12, 0, 0)


@pytest.fixture(autouse=True)
def sso_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "sso_secrets", [SSO_SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", TEST_SESSION_SECRET)
    monkeypatch.setattr(settings, "admin_emails", ADMIN_EMAIL)
    monkeypatch.setattr(settings, "sso_return_to_default", "/")


def sso_token(email: str) -> str:
    payload = {"email": email, "exp": int(time.time()) + 300}
    return jwt.encode(payload, SSO_SECRET, algorithm="HS256")


async def login(client: AsyncClient, email: str = ADMIN_EMAIL) -> None:
    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token(email), "return_to": "/"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


def insert_comment(conn, *, post_id: str, author_id: int) -> None:
    comment_id = uuid.uuid4()
    stamp = sqlite_timestamp(BASE)
    conn.execute(
        "INSERT INTO comments (id, post_id, content, author_id, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (comment_id.hex, post_id, "评论", author_id, stamp, stamp),
    )
    conn.commit()


async def test_requires_admin(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 403
    assert response.json()["code"] == "ADMIN_REQUIRED"

    await login(client, "someone@example.com")
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 403
    assert response.json()["code"] == "ADMIN_REQUIRED"


async def test_lists_users_with_counts(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    author_id = insert_user(
        sqlite_conn, email="writer@example.com", display_name="作者"
    )
    post_id = insert_post(
        sqlite_conn, board_id=board_id, title="一", created_at=BASE, author_id=author_id
    )
    insert_post(
        sqlite_conn, board_id=board_id, title="二", created_at=BASE, author_id=author_id
    )
    insert_comment(sqlite_conn, post_id=post_id, author_id=author_id)
    # 匿名反馈没有 author_id，不计入任何人的统计。
    insert_post(sqlite_conn, board_id=board_id, title="匿名", created_at=BASE)

    await login(client)
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert response.json()["next_cursor"] is None
    by_email = {item["email"]: item for item in items}

    assert by_email["admin@example.com"]["role"] == "admin"
    assert by_email["admin@example.com"]["post_count"] == 0
    writer = by_email["writer@example.com"]
    assert writer["display_name"] == "作者"
    assert writer["post_count"] == 2
    assert writer["comment_count"] == 1
    assert writer["created_at"].endswith("+00:00")


async def test_search_and_role_filter(client: AsyncClient, sqlite_conn) -> None:
    insert_user(sqlite_conn, email="alice@example.com", display_name="100% 完成")
    insert_user(sqlite_conn, email="bob@example.com", display_name="Alice 的同事")
    await login(client)

    response = await client.get("/api/v1/admin/users", params={"q": "alice"})
    assert response.status_code == 200
    assert {item["email"] for item in response.json()["items"]} == {
        "alice@example.com",
        "bob@example.com",
    }

    # % 必须按字面匹配，不能被当成通配符。
    response = await client.get("/api/v1/admin/users", params={"q": "%"})
    assert [item["email"] for item in response.json()["items"]] == ["alice@example.com"]

    response = await client.get("/api/v1/admin/users", params={"role": "admin"})
    roles = {item["role"] for item in response.json()["items"]}
    assert roles == {"admin"}


async def test_keyset_pagination(client: AsyncClient, sqlite_conn) -> None:
    for index in range(3):
        insert_user(sqlite_conn, email=f"u{index}@example.com")
    await login(client)

    first = await client.get("/api/v1/admin/users", params={"limit": 2})
    assert first.status_code == 200
    body = first.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None

    second = await client.get(
        "/api/v1/admin/users",
        params={"limit": 2, "before_id": body["next_cursor"]},
    )
    assert second.status_code == 200
    assert second.json()["next_cursor"] is None
    ids = [item["id"] for item in body["items"] + second.json()["items"]]
    assert ids == sorted(ids, reverse=True)
    assert len(set(ids)) == len(ids)
