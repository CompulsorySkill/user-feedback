"""管理员任务面板：只列出「@ 了我」的反馈，并带任务进度。"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_comment, insert_post, insert_user

SSO_SECRET = "test-sso-secret-0123456789abcdef012345"
TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef012345"
BASE = datetime(2026, 5, 1, 12, 0, 0)


@pytest.fixture(autouse=True)
def sso_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sso_secrets", [SSO_SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", TEST_SESSION_SECRET)
    monkeypatch.setattr(settings, "admin_emails", "a@example.com,b@example.com")
    monkeypatch.setattr(settings, "sso_return_to_default", "/")


def sso_token(email: str) -> str:
    payload = {"email": email, "exp": int(time.time()) + 300}
    return jwt.encode(payload, SSO_SECRET, algorithm="HS256")


async def login(client: AsyncClient, email: str) -> None:
    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token(email), "return_to": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 302, response.text


def mention_doc(*user_ids: int) -> dict:
    nodes = []
    for user_id in user_ids:
        nodes.append(
            {"type": "mention", "attrs": {"id": str(user_id), "label": f"U{user_id}"}}
        )
    return {"type": "doc", "content": [{"type": "paragraph", "content": nodes}]}


async def test_lists_only_own_mentions(client: AsyncClient, sqlite_conn) -> None:
    admin_a = insert_user(
        sqlite_conn, email="a@example.com", display_name="A", role="admin"
    )
    admin_b = insert_user(
        sqlite_conn, email="b@example.com", display_name="B", role="admin"
    )
    board_id = insert_board(sqlite_conn, slug="product", name="功能建议")
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="请 A 看看",
        created_at=BASE,
        content=mention_doc(admin_a),
    )
    insert_post(
        sqlite_conn,
        board_id=board_id,
        title="只提了 B",
        created_at=BASE + timedelta(hours=1),
        content=mention_doc(admin_b),
    )

    await login(client, "a@example.com")
    response = await client.get("/api/v1/admin/tasks")
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["title"] for item in body["items"]] == ["请 A 看看"]
    item = body["items"][0]
    assert item["post_id"] == str(uuid.UUID(post_id))
    assert item["board_slug"] == "product"
    assert item["status"] == "open"
    assert item["mentioned_at"].endswith("Z") or "+00:00" in item["mentioned_at"]
    assert item["task_state"] == "pending"
    assert item["assignee_name"] is None


async def test_comment_mention_shows_up(client: AsyncClient, sqlite_conn) -> None:
    admin_a = insert_user(
        sqlite_conn, email="a@example.com", display_name="A", role="admin"
    )
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn, board_id=board_id, title="评论里 @ 你", created_at=BASE
    )
    insert_comment(sqlite_conn, post_id=post_id, content=mention_doc(admin_a))

    await login(client, "a@example.com")
    body = (await client.get("/api/v1/admin/tasks")).json()
    assert [item["title"] for item in body["items"]] == ["评论里 @ 你"]


async def test_task_state_follows_accept_and_complete(
    client: AsyncClient, sqlite_conn
) -> None:
    admin_a = insert_user(
        sqlite_conn, email="a@example.com", display_name="A", role="admin"
    )
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="接一下",
        created_at=BASE,
        content=mention_doc(admin_a),
    )

    await login(client, "a@example.com")
    task = (await client.get("/api/v1/admin/tasks")).json()["items"][0]
    assert task["task_state"] == "pending"

    accepted = await client.post(f"/api/v1/posts/{post_id}/task/accept")
    assert accepted.status_code == 200, accepted.text
    task = (await client.get("/api/v1/admin/tasks")).json()["items"][0]
    assert task["task_state"] == "active"
    assert task["assignee_name"] == "A"
    assert task["accepted_at"] is not None
    assert task["completed_at"] is None

    completed = await client.post(f"/api/v1/posts/{post_id}/task/complete")
    assert completed.status_code == 200, completed.text
    task = (await client.get("/api/v1/admin/tasks")).json()["items"][0]
    assert task["task_state"] == "done"
    assert task["completed_at"] is not None

    done = await client.get("/api/v1/admin/tasks", params={"task_state": "done"})
    assert [item["title"] for item in done.json()["items"]] == ["接一下"]
    pending = await client.get("/api/v1/admin/tasks", params={"task_state": "pending"})
    assert pending.json()["items"] == []


async def test_board_filter_and_ordering(client: AsyncClient, sqlite_conn) -> None:
    admin_a = insert_user(
        sqlite_conn, email="a@example.com", display_name="A", role="admin"
    )
    product = insert_board(sqlite_conn, slug="product", name="功能建议")
    design = insert_board(sqlite_conn, slug="design", name="设计")
    insert_post(
        sqlite_conn,
        board_id=product,
        title="旧",
        created_at=BASE,
        content=mention_doc(admin_a),
    )
    insert_post(
        sqlite_conn,
        board_id=design,
        title="新",
        created_at=BASE + timedelta(hours=2),
        content=mention_doc(admin_a),
    )

    await login(client, "a@example.com")
    titles = [
        i["title"] for i in (await client.get("/api/v1/admin/tasks")).json()["items"]
    ]
    assert titles == ["新", "旧"]

    only_product = await client.get("/api/v1/admin/tasks", params={"board": "product"})
    assert [i["title"] for i in only_product.json()["items"]] == ["旧"]


async def test_editing_content_drops_mention(client: AsyncClient, sqlite_conn) -> None:
    admin_a = insert_user(
        sqlite_conn, email="a@example.com", display_name="A", role="admin"
    )
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="先 @ 后删",
        created_at=BASE,
        content=mention_doc(admin_a),
    )

    await login(client, "a@example.com")
    assert len((await client.get("/api/v1/admin/tasks")).json()["items"]) == 1

    response = await client.patch(
        f"/api/v1/posts/{post_id}",
        json={"content": {"type": "doc", "content": [{"type": "paragraph"}]}},
    )
    assert response.status_code == 200, response.text
    assert (await client.get("/api/v1/admin/tasks")).json()["items"] == []


async def test_requires_admin(client: AsyncClient, sqlite_conn) -> None:
    insert_user(sqlite_conn, email="plain@example.com", display_name="Plain")
    await login(client, "plain@example.com")
    response = await client.get("/api/v1/admin/tasks")
    assert response.status_code == 403
    assert response.json()["code"] == "ADMIN_REQUIRED"
