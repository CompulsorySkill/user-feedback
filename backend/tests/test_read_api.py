"""P1 读路径 API 契约测试：看板、反馈、更新日志与 keyset 分页。"""

from __future__ import annotations

from datetime import datetime, timedelta

from httpx import AsyncClient

from tests.conftest import (
    insert_board,
    insert_changelog,
    insert_post,
    insert_user,
)

BASE = datetime(2026, 1, 1, 12, 0, 0)


# --------------------------------------------------------------------------- #
# 看板
# --------------------------------------------------------------------------- #


async def test_list_boards_only_public_with_counts(client: AsyncClient, sqlite_conn) -> None:
    product_id = insert_board(sqlite_conn, slug="product", name="功能建议")
    insert_board(sqlite_conn, slug="internal", name="内部看板", is_public=False)
    insert_post(sqlite_conn, board_id=product_id, title="a", created_at=BASE)
    insert_post(sqlite_conn, board_id=product_id, title="b", created_at=BASE)

    response = await client.get("/api/v1/boards")

    assert response.status_code == 200
    boards = response.json()
    assert [board["slug"] for board in boards] == ["product"]
    assert boards[0]["post_count"] == 2
    assert boards[0]["created_at"].endswith("+00:00")


async def test_board_detail_unknown_or_private_returns_404(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn, slug="internal", name="内部看板", is_public=False)

    private = await client.get("/api/v1/boards/internal")
    missing = await client.get("/api/v1/boards/nope")

    assert private.status_code == 404
    assert private.json()["code"] == "BOARD_NOT_FOUND"
    assert missing.status_code == 404


async def test_board_post_list_unknown_board_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/boards/nope/posts")

    assert response.status_code == 404
    assert response.json()["code"] == "BOARD_NOT_FOUND"


# --------------------------------------------------------------------------- #
# 反馈列表与分页
# --------------------------------------------------------------------------- #


async def test_posts_keyset_pagination_has_no_gaps_or_duplicates(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    for index in range(25):
        insert_post(
            sqlite_conn,
            board_id=board_id,
            title=f"post-{index:02d}",
            created_at=BASE - timedelta(minutes=index),
            excerpt=f"第 {index} 条",
            vote_count=index,
        )

    titles: list[str] = []
    pages = 0
    cursor: str | None = None
    while True:
        params = {"limit": 10}
        if cursor:
            params["cursor"] = cursor
        response = await client.get("/api/v1/boards/product/posts", params=params)
        assert response.status_code == 200
        body = response.json()
        titles.extend(item["title"] for item in body["items"])
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
        assert pages < 10, "分页未终止"

    assert pages == 3
    assert len(titles) == 25
    assert len(set(titles)) == 25
    assert titles == [f"post-{index:02d}" for index in range(25)]


async def test_posts_list_includes_author_and_anonymous(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    user_id = insert_user(sqlite_conn, email="lin@example.com", display_name="林小满")
    insert_post(
        sqlite_conn,
        board_id=board_id,
        title="登录用户",
        created_at=BASE,
        author_id=user_id,
    )
    insert_post(
        sqlite_conn,
        board_id=board_id,
        title="匿名用户",
        created_at=BASE - timedelta(minutes=1),
    )

    response = await client.get("/api/v1/boards/product/posts")
    items = response.json()["items"]

    assert items[0]["author_name"] == "林小满"
    assert items[1]["author_name"] is None


async def test_posts_list_rejects_invalid_cursor(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn)

    response = await client.get(
        "/api/v1/boards/product/posts", params={"cursor": "not-a-cursor!!"}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CURSOR"


# --------------------------------------------------------------------------- #
# 反馈详情
# --------------------------------------------------------------------------- #


async def test_post_detail_returns_rich_content(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    user_id = insert_user(sqlite_conn, email="lin@example.com", display_name="林小满")
    content = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "正文"}]},
            {"type": "video", "attrs": {"src": "uploads/demo.mp4", "poster": None}},
        ],
    }
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="带视频的反馈",
        created_at=BASE,
        content=content,
        author_id=user_id,
        vote_count=7,
        comment_count=2,
    )

    response = await client.get(f"/api/v1/posts/{post_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "带视频的反馈"
    assert body["board"] == {"id": board_id, "slug": "product", "name": "功能建议"}
    assert body["author_name"] == "林小满"
    assert body["content"] == content
    assert body["vote_count"] == 7
    assert body["comment_count"] == 2


async def test_post_detail_anonymous_has_no_author(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn, board_id=board_id, title="匿名", created_at=BASE
    )

    response = await client.get(f"/api/v1/posts/{post_id}")

    assert response.status_code == 200
    assert response.json()["author_name"] is None


async def test_post_detail_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/posts/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["code"] == "POST_NOT_FOUND"


async def test_post_in_private_board_returns_404(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn, slug="internal", name="内部", is_public=False)
    post_id = insert_post(
        sqlite_conn, board_id=board_id, title="机密", created_at=BASE
    )

    response = await client.get(f"/api/v1/posts/{post_id}")

    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# 更新日志
# --------------------------------------------------------------------------- #


async def test_changelog_list_hides_drafts(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_changelog(sqlite_conn, title="已发布", created_at=BASE)
    insert_changelog(
        sqlite_conn, title="草稿", created_at=BASE - timedelta(hours=1), published=False
    )

    response = await client.get("/api/v1/changelogs")
    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["已发布"]

    # P1 尚无鉴权，include_drafts 对匿名请求不生效。
    drafts = await client.get("/api/v1/changelogs", params={"include_drafts": "true"})
    assert [item["title"] for item in drafts.json()["items"]] == ["已发布"]


async def test_changelog_detail_draft_returns_404(
    client: AsyncClient, sqlite_conn
) -> None:
    entry_id = insert_changelog(
        sqlite_conn, title="草稿", created_at=BASE, published=False
    )

    response = await client.get(f"/api/v1/changelogs/{entry_id}")

    assert response.status_code == 404
    assert response.json()["code"] == "CHANGELOG_NOT_FOUND"


async def test_changelog_detail_returns_content(
    client: AsyncClient, sqlite_conn
) -> None:
    content = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "发布说明"}]}
        ],
    }
    entry_id = insert_changelog(
        sqlite_conn, title="v1.0", created_at=BASE, content=content
    )

    response = await client.get(f"/api/v1/changelogs/{entry_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == content
    assert body["published_at"].endswith("+00:00")


async def test_changelog_list_keyset_pagination(
    client: AsyncClient, sqlite_conn
) -> None:
    for index in range(3):
        insert_changelog(
            sqlite_conn,
            title=f"entry-{index}",
            created_at=BASE - timedelta(days=index),
            published=True,
        )

    first = await client.get("/api/v1/changelogs", params={"limit": 2})
    body = first.json()
    assert [item["title"] for item in body["items"]] == ["entry-0", "entry-1"]
    assert body["next_cursor"]

    second = await client.get(
        "/api/v1/changelogs",
        params={"limit": 2, "cursor": body["next_cursor"]},
    )
    assert [item["title"] for item in second.json()["items"]] == ["entry-2"]
    assert second.json()["next_cursor"] is None
