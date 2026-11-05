"""反馈列表筛选契约：多状态（OR）、作者筛选与作者候选。"""

from __future__ import annotations

from datetime import datetime, timedelta

from httpx import AsyncClient

from tests.conftest import insert_board, insert_post, insert_user

BASE = datetime(2026, 1, 1, 12, 0, 0)


def _seed(sqlite_conn) -> int:
    board_id = insert_board(sqlite_conn, slug="product", name="功能建议")
    alice = insert_user(sqlite_conn, email="alice@example.com", display_name="Alice")
    bob = insert_user(sqlite_conn, email="bob@example.com", display_name="Bob")
    insert_post(
        sqlite_conn, board_id=board_id, title="open-a", created_at=BASE, author_id=alice
    )
    insert_post(
        sqlite_conn,
        board_id=board_id,
        title="planned-a",
        created_at=BASE - timedelta(minutes=1),
        status="planned",
        author_id=alice,
    )
    insert_post(
        sqlite_conn,
        board_id=board_id,
        title="closed-b",
        created_at=BASE - timedelta(minutes=2),
        status="closed",
        author_id=bob,
    )
    insert_post(
        sqlite_conn,
        board_id=board_id,
        title="anon",
        created_at=BASE - timedelta(minutes=3),
        status="in_progress",
        anonymous_name="夜班运维",
    )
    return board_id


async def test_status_filter_accepts_multiple_values(
    client: AsyncClient, sqlite_conn
) -> None:
    _seed(sqlite_conn)

    response = await client.get(
        "/api/v1/posts", params=[("status", "open"), ("status", "planned")]
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == [
        "open-a",
        "planned-a",
    ]


async def test_status_filter_rejects_unknown_value(
    client: AsyncClient, sqlite_conn
) -> None:
    _seed(sqlite_conn)

    response = await client.get("/api/v1/posts?status=done")

    assert response.status_code == 422


async def test_author_filter_matches_display_name_and_nickname(
    client: AsyncClient, sqlite_conn
) -> None:
    _seed(sqlite_conn)

    by_name = await client.get("/api/v1/posts?author=Alice")
    anon = await client.get("/api/v1/posts?author=夜班运维")
    missing = await client.get("/api/v1/posts?author=无人")

    assert [item["title"] for item in by_name.json()["items"]] == [
        "open-a",
        "planned-a",
    ]
    assert [item["title"] for item in anon.json()["items"]] == ["anon"]
    assert missing.json()["items"] == []


async def test_author_facets_merge_names_and_nicknames(
    client: AsyncClient, sqlite_conn
) -> None:
    _seed(sqlite_conn)

    response = await client.get("/api/v1/posts/authors")

    assert response.status_code == 200
    assert response.json() == [
        {"name": "Alice", "post_count": 2},
        {"name": "Bob", "post_count": 1},
        {"name": "夜班运维", "post_count": 1},
    ]


async def test_author_facets_scoped_to_board(client: AsyncClient, sqlite_conn) -> None:
    _seed(sqlite_conn)
    other = insert_board(sqlite_conn, slug="bugs", name="问题反馈")
    insert_post(sqlite_conn, board_id=other, title="x", created_at=BASE)

    response = await client.get("/api/v1/posts/authors?board=product")

    assert [row["name"] for row in response.json()] == ["Alice", "Bob", "夜班运维"]


async def test_board_posts_support_status_and_author(
    client: AsyncClient, sqlite_conn
) -> None:
    _seed(sqlite_conn)

    response = await client.get(
        "/api/v1/boards/product/posts",
        params=[("status", "planned"), ("status", "closed"), ("author", "Bob")],
    )

    assert [item["title"] for item in response.json()["items"]] == ["closed-b"]
