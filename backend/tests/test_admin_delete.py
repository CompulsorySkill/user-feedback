"""管理员删除反馈 / 评论：权限、级联清理与计数维护。"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_post, sqlite_timestamp

BASE = datetime(2026, 3, 1, 12, 0, 0)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "s3cret-admin-pw"


@pytest.fixture(autouse=True)
def admin_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_emails", ADMIN_EMAIL)
    monkeypatch.setattr(settings, "admin_password", ADMIN_PASSWORD)


async def login_admin(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/admin-login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text


def insert_comment(
    conn, *, post_id: str, content: str, parent_id: str | None = None
) -> str:
    comment_id = uuid.uuid4()
    stamp = sqlite_timestamp(BASE)
    conn.execute(
        "INSERT INTO comments (id, post_id, parent_id, content, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            comment_id.hex,
            post_id,
            uuid.UUID(parent_id).hex if parent_id else None,
            content,
            stamp,
            stamp,
        ),
    )
    conn.commit()
    return comment_id.hex


def count(conn, sql: str, *params) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


async def test_admin_delete_post_cascades(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn, board_id=board_id, title="待删除", created_at=BASE
    )
    raw_post_id = uuid.UUID(post_id).hex
    insert_comment(sqlite_conn, post_id=post_id, content="评论")
    sqlite_conn.execute(
        "INSERT INTO votes (post_id, anonymous_token) VALUES (?, ?)",
        (raw_post_id, "anon-1"),
    )
    sqlite_conn.execute("INSERT INTO tags (name, normalized) VALUES ('Bug', 'bug')")
    sqlite_conn.execute(
        "INSERT INTO post_tags (post_id, tag_id) SELECT ?, id FROM tags", (raw_post_id,)
    )
    sqlite_conn.commit()

    await login_admin(client)
    response = await client.delete(f"/api/v1/posts/{post_id}")
    assert response.status_code == 204, response.text

    assert (await client.get(f"/api/v1/posts/{post_id}")).status_code == 404
    for table in ("posts", "comments", "votes", "post_tags"):
        column = "id" if table == "posts" else "post_id"
        assert (
            count(
                sqlite_conn,
                f"SELECT count(*) FROM {table} WHERE {column} = ?",
                raw_post_id,
            )
            == 0
        )

    audit = sqlite_conn.execute(
        "SELECT action, target_id FROM audit_logs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit == ("post.delete", str(uuid.UUID(post_id)))


async def test_delete_post_requires_admin(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(sqlite_conn, board_id=board_id, title="保留", created_at=BASE)

    response = await client.delete(f"/api/v1/posts/{post_id}")
    assert response.status_code == 403
    assert response.json()["code"] == "ADMIN_REQUIRED"
    assert count(sqlite_conn, "SELECT count(*) FROM posts") == 1


async def test_admin_delete_comment_removes_replies(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn, board_id=board_id, title="有评论", created_at=BASE, comment_count=4
    )
    raw_post_id = uuid.UUID(post_id).hex
    root = insert_comment(sqlite_conn, post_id=post_id, content="根")
    child = insert_comment(sqlite_conn, post_id=post_id, content="子", parent_id=root)
    insert_comment(sqlite_conn, post_id=post_id, content="孙", parent_id=child)
    sibling = insert_comment(sqlite_conn, post_id=post_id, content="另一条根")

    await login_admin(client)
    response = await client.delete(f"/api/v1/posts/{post_id}/comments/{root}")
    assert response.status_code == 204, response.text

    remaining = [
        row[0]
        for row in sqlite_conn.execute(
            "SELECT id FROM comments WHERE post_id = ?", (raw_post_id,)
        ).fetchall()
    ]
    assert remaining == [uuid.UUID(sibling).hex]
    assert (
        count(sqlite_conn, "SELECT comment_count FROM posts WHERE id = ?", raw_post_id)
        == 1
    )
    listed = (await client.get(f"/api/v1/posts/{post_id}/comments")).json()
    assert listed["total"] == 1


async def test_delete_comment_rejects_foreign_comment(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    post_a = insert_post(sqlite_conn, board_id=board_id, title="A", created_at=BASE)
    post_b = insert_post(sqlite_conn, board_id=board_id, title="B", created_at=BASE)
    comment = insert_comment(sqlite_conn, post_id=post_b, content="属于 B")

    await login_admin(client)
    response = await client.delete(f"/api/v1/posts/{post_a}/comments/{comment}")
    assert response.status_code == 404
    assert response.json()["code"] == "COMMENT_NOT_FOUND"


async def test_delete_comment_requires_admin(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(sqlite_conn, board_id=board_id, title="保留", created_at=BASE)
    comment = insert_comment(sqlite_conn, post_id=post_id, content="保留评论")

    response = await client.delete(f"/api/v1/posts/{post_id}/comments/{comment}")
    assert response.status_code == 403
    assert count(sqlite_conn, "SELECT count(*) FROM comments") == 1
