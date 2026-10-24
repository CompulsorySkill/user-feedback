"""列表筛选/排序、开发快速登录与作者编辑入口。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_post

BASE = datetime(2026, 4, 1, 12, 0, 0)


def doc(text: str = "正文") -> dict:
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]}
        ],
    }


@pytest.fixture
def dev_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "admin_emails", "admin@example.com")
    monkeypatch.setattr(settings, "sso_return_to_default", "/")


async def dev_login(client: AsyncClient, email: str):
    return await client.post(
        "/api/v1/auth/dev-login", json={"email": email, "name": email.split("@")[0]}
    )


# --------------------------------------------------------------------------- #
# 开发快速登录
# --------------------------------------------------------------------------- #


async def test_capabilities_and_dev_login(client: AsyncClient, dev_env) -> None:
    caps = await client.get("/api/v1/auth/capabilities")
    assert caps.json() == {"sso": True, "dev_login": True}

    response = await dev_login(client, "admin@example.com")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["is_admin"] is True
    assert body["user"]["role"] == "admin"

    me = await client.get("/api/v1/auth/me")
    assert me.json()["user"]["email"] == "admin@example.com"


async def test_dev_login_disabled_in_production(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "production")

    caps = await client.get("/api/v1/auth/capabilities")
    assert caps.json()["dev_login"] is False

    response = await client.post(
        "/api/v1/auth/dev-login", json={"email": "admin@example.com"}
    )
    assert response.status_code == 404
    assert (await client.get("/api/v1/auth/me")).json()["authenticated"] is False


async def test_dev_login_merges_anonymous_post(
    client: AsyncClient, sqlite_conn, dev_env
) -> None:
    insert_board(sqlite_conn)
    created = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "登录前的匿名帖", "content": doc()},
    )
    assert created.status_code == 201

    await dev_login(client, "alice@example.com")

    user_id = sqlite_conn.execute(
        "SELECT id FROM users WHERE email='alice@example.com'"
    ).fetchone()[0]
    row = sqlite_conn.execute(
        "SELECT author_id, anonymous_token FROM posts WHERE title='登录前的匿名帖'"
    ).fetchone()
    assert row == (user_id, None)
    assert "feedlog_anonymous" not in client.cookies


# --------------------------------------------------------------------------- #
# 状态筛选
# --------------------------------------------------------------------------- #


async def test_status_filter(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    for index, status in enumerate(["open", "planned", "open", "closed"]):
        insert_post(
            sqlite_conn,
            board_id=board_id,
            title=f"{status}-{index}",
            created_at=BASE - timedelta(minutes=index),
            status=status,
        )

    response = await client.get(
        "/api/v1/boards/product/posts", params={"status": "planned"}
    )
    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["planned-1"]

    closed = await client.get(
        "/api/v1/boards/product/posts", params={"status": "closed"}
    )
    assert [item["title"] for item in closed.json()["items"]] == ["closed-3"]


async def test_invalid_status_and_sort_rejected(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn)

    bad_status = await client.get(
        "/api/v1/boards/product/posts", params={"status": "done"}
    )
    bad_sort = await client.get(
        "/api/v1/boards/product/posts", params={"sort": "popular"}
    )

    assert bad_status.status_code == 422
    assert bad_sort.status_code == 422


# --------------------------------------------------------------------------- #
# 最热排序与 keyset 分页
# --------------------------------------------------------------------------- #


async def _seed_votes(conn, board_id: int) -> None:
    for index, votes in enumerate([5, 4, 4, 3, 1]):
        insert_post(
            conn,
            board_id=board_id,
            title=f"vote-{votes}-{index}",
            created_at=BASE - timedelta(minutes=index),
            vote_count=votes,
        )


async def test_sort_top_by_votes(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    await _seed_votes(sqlite_conn, board_id)

    response = await client.get(
        "/api/v1/boards/product/posts", params={"sort": "top", "limit": 10}
    )

    votes = [item["vote_count"] for item in response.json()["items"]]
    assert votes == [5, 4, 4, 3, 1]


async def test_top_sort_keyset_pagination(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    await _seed_votes(sqlite_conn, board_id)

    first = await client.get(
        "/api/v1/boards/product/posts", params={"sort": "top", "limit": 2}
    )
    body = first.json()
    assert [item["vote_count"] for item in body["items"]] == [5, 4]
    assert body["next_cursor"]

    second = await client.get(
        "/api/v1/boards/product/posts",
        params={"sort": "top", "limit": 2, "cursor": body["next_cursor"]},
    )
    assert [item["vote_count"] for item in second.json()["items"]] == [4, 3]

    third = await client.get(
        "/api/v1/boards/product/posts",
        params={
            "sort": "top",
            "limit": 2,
            "cursor": second.json()["next_cursor"],
        },
    )
    assert [item["vote_count"] for item in third.json()["items"]] == [1]
    assert third.json()["next_cursor"] is None


# --------------------------------------------------------------------------- #
# 作者编辑
# --------------------------------------------------------------------------- #


async def test_author_can_edit_own_post(
    client: AsyncClient, sqlite_conn, dev_env
) -> None:
    insert_board(sqlite_conn)
    await dev_login(client, "alice@example.com")
    created = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "原标题", "content": doc("原正文")},
    )
    post_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/posts/{post_id}",
        json={"title": "新标题", "content": doc("修改后的正文")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "新标题"
    assert body["excerpt"] == "修改后的正文"
    assert body["is_author"] is True


async def test_author_cannot_edit_others_post(
    client: AsyncClient, sqlite_conn, dev_env
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn, board_id=board_id, title="别人的帖子", created_at=BASE
    )
    await dev_login(client, "alice@example.com")

    response = await client.patch(
        f"/api/v1/posts/{post_id}", json={"title": "越权修改"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "POST_EDIT_FORBIDDEN"


async def test_admin_edit_keeps_legacy_media_without_upload_row(
    client: AsyncClient, sqlite_conn, dev_env
) -> None:
    """历史/种子内容里的媒体没有 Upload 记录，编辑时应允许保留原 key。"""
    board_id = insert_board(sqlite_conn)
    legacy_content = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "旧内容"}]},
            {"type": "image", "attrs": {"src": "uploads/legacy.png"}},
        ],
    }
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="历史媒体",
        created_at=BASE,
        content=legacy_content,
    )
    await dev_login(client, "admin@example.com")  # ADMIN_EMAILS 命中

    response = await client.patch(
        f"/api/v1/posts/{post_id}",
        json={
            "title": "历史媒体（已编辑）",
            "content": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "更新后的说明"}],
                    },
                    {"type": "image", "attrs": {"src": "uploads/legacy.png"}},
                ],
            },
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "历史媒体（已编辑）"
