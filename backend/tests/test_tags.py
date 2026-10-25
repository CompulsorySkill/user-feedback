"""标签：发帖打标、作者/管理员维护、内置标签与站点名称。"""

from __future__ import annotations

import time
from datetime import datetime

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_post, sqlite_timestamp

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


async def login(client: AsyncClient, email: str) -> None:
    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token(email), "return_to": "/"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


def post_doc(text: str = "正文") -> dict:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


async def create_post(
    client: AsyncClient,
    *,
    slug: str = "product",
    title: str = "带标签的反馈",
    tags: list[str] | None = None,
) -> dict:
    payload = {"title": title, "content": post_doc()}
    if tags is not None:
        payload["tags"] = tags
    response = await client.post(f"/api/v1/boards/{slug}/posts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def insert_closed_post(conn) -> str:
    board_id = insert_board(conn)
    return insert_post(
        conn,
        board_id=board_id,
        title="已关闭反馈",
        created_at=datetime(2026, 2, 1, 12, 0, 0),
        status="closed",
    )


# --------------------------------------------------------------------------- #
# 帖子标签
# --------------------------------------------------------------------------- #


async def test_create_post_with_tags_and_read_back(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)

    created = await create_post(client, tags=[" Bug ", "UI", "bug", "#体验"])

    assert [tag["name"] for tag in created["tags"]] == ["Bug", "UI", "体验"]
    assert [tag["is_builtin"] for tag in created["tags"]] == [False, False, False]

    detail = await client.get(f"/api/v1/posts/{created['id']}")
    assert [tag["name"] for tag in detail.json()["tags"]] == ["Bug", "UI", "体验"]

    listed = await client.get("/api/v1/posts")
    assert [tag["name"] for tag in listed.json()["items"][0]["tags"]] == [
        "Bug",
        "UI",
        "体验",
    ]

    board_listed = await client.get("/api/v1/boards/product/posts")
    assert [tag["name"] for tag in board_listed.json()["items"][0]["tags"]] == [
        "Bug",
        "UI",
        "体验",
    ]


async def test_author_can_update_tags_and_reuse_existing(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    await login(client, "alice@example.com")

    first = await create_post(client, title="第一条", tags=["旧标签"])
    updated = await client.patch(
        f"/api/v1/posts/{first['id']}", json={"tags": ["Bug", "体验"]}
    )
    assert updated.status_code == 200
    assert [tag["name"] for tag in updated.json()["tags"]] == ["Bug", "体验"]

    second = await create_post(client, title="第二条", tags=["bug"])
    assert second["tags"][0]["id"] == updated.json()["tags"][0]["id"]


async def test_tags_are_removed_when_cleared(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn)
    await login(client, "alice@example.com")
    created = await create_post(client, tags=["临时"])

    cleared = await client.patch(f"/api/v1/posts/{created['id']}", json={"tags": []})

    assert cleared.status_code == 200
    assert cleared.json()["tags"] == []


async def test_admin_can_tag_closed_post(client: AsyncClient, sqlite_conn) -> None:
    post_id = insert_closed_post(sqlite_conn)
    await login(client, ADMIN_EMAIL)

    response = await client.patch(
        f"/api/v1/posts/{post_id}", json={"tags": ["历史", "归档"]}
    )

    assert response.status_code == 200
    assert [tag["name"] for tag in response.json()["tags"]] == ["历史", "归档"]


async def test_tag_limit_and_invalid_names(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn)

    too_many = await client.post(
        "/api/v1/boards/product/posts",
        json={
            "title": "标签过多",
            "content": post_doc(),
            "tags": ["a", "b", "c", "d", "e", "f"],
        },
    )
    assert too_many.status_code == 422

    blank = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "空标签", "content": post_doc(), "tags": ["  #  "]},
    )
    assert blank.status_code == 400
    assert blank.json()["code"] == "TAG_INVALID"

    too_long = await client.post(
        "/api/v1/boards/product/posts",
        json={"title": "超长标签", "content": post_doc(), "tags": ["x" * 25]},
    )
    assert too_long.status_code == 400
    assert too_long.json()["code"] == "TAG_INVALID"


async def test_post_lists_filter_by_tag(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn)
    await create_post(client, title="缺陷一", tags=["Bug"])
    await create_post(client, title="缺陷二", tags=["UI", "Bug"])
    await create_post(client, title="其他", tags=["Other"])

    all_posts = await client.get("/api/v1/posts", params={"tag": "bug"})
    assert all_posts.status_code == 200
    assert {item["title"] for item in all_posts.json()["items"]} == {"缺陷一", "缺陷二"}

    board_posts = await client.get(
        "/api/v1/boards/product/posts", params={"tag": "Bug"}
    )
    assert {item["title"] for item in board_posts.json()["items"]} == {
        "缺陷一",
        "缺陷二",
    }

    # 多个标签之间是 OR；大小写不敏感。
    any_tag = await client.get(
        "/api/v1/posts", params=[("tag", "bug"), ("tag", "other")]
    )
    assert {item["title"] for item in any_tag.json()["items"]} == {
        "缺陷一",
        "缺陷二",
        "其他",
    }

    missing = await client.get("/api/v1/posts", params={"tag": "不存在"})
    assert missing.json()["items"] == []

    too_many = await client.get(
        "/api/v1/posts",
        params=[("tag", f"t{index}") for index in range(6)],
    )
    assert too_many.status_code == 400
    assert too_many.json()["code"] == "TAG_LIMIT"


async def test_public_tag_list_can_include_custom(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    await create_post(client, title="带自定义标签", tags=["性能"])

    builtin_only = await client.get("/api/v1/tags")
    assert builtin_only.json() == []

    all_tags = await client.get("/api/v1/tags", params={"include_custom": "true"})
    assert [(tag["name"], tag["post_count"]) for tag in all_tags.json()] == [
        ("性能", 1)
    ]


async def test_public_tag_counts_are_scoped_by_board(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    insert_board(sqlite_conn, slug="mobile", name="移动端")
    await create_post(client, slug="product", title="产品 Bug", tags=["Bug", "UI"])
    await create_post(client, slug="mobile", title="移动端 Bug", tags=["Bug"])

    async def counts(**params: str) -> dict[str, int]:
        response = await client.get(
            "/api/v1/tags", params={"include_custom": "true", **params}
        )
        assert response.status_code == 200
        return {tag["name"]: tag["post_count"] for tag in response.json()}

    assert await counts() == {"Bug": 2, "UI": 1}
    assert await counts(board="product") == {"Bug": 1, "UI": 1}
    assert await counts(board="mobile") == {"Bug": 1, "UI": 0}

    # 未公开看板的使用不计入公开计数（也不应泄露其帖子量）。
    private_board = insert_board(
        sqlite_conn, slug="internal", name="内部", is_public=False
    )
    private_post = insert_post(
        sqlite_conn, board_id=private_board, title="内部帖", created_at=BASE
    )
    sqlite_conn.execute(
        "INSERT INTO tags (name, normalized, is_builtin) VALUES ('内部', '内部', 0)"
    )
    tag_id = sqlite_conn.execute(
        "SELECT id FROM tags WHERE normalized='内部'"
    ).fetchone()[0]
    sqlite_conn.execute(
        "INSERT INTO post_tags (post_id, tag_id, created_at) VALUES (?, ?, ?)",
        (private_post, tag_id, sqlite_timestamp(BASE)),
    )
    sqlite_conn.commit()

    assert (await counts())["内部"] == 0
    assert (await counts(board="product"))["内部"] == 0


# --------------------------------------------------------------------------- #
# 内置标签管理
# --------------------------------------------------------------------------- #


async def test_builtin_tag_lifecycle(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn)

    anonymous_list = await client.get("/api/v1/tags")
    assert anonymous_list.json() == []

    assert (
        await client.post("/api/v1/admin/tags", json={"name": "功能请求"})
    ).status_code == 403
    assert (await client.get("/api/v1/admin/tags")).status_code == 403
    assert (await client.delete("/api/v1/admin/tags/1")).status_code == 403

    await login(client, ADMIN_EMAIL)
    created = await client.post("/api/v1/admin/tags", json={"name": "  功能请求  "})
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "功能请求"
    assert body["is_builtin"] is True
    assert body["post_count"] == 0

    public = await client.get("/api/v1/tags")
    assert [tag["name"] for tag in public.json()] == ["功能请求"]

    duplicate = await client.post("/api/v1/admin/tags", json={"name": "功能请求"})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "TAG_EXISTS"

    post = await create_post(client, tags=["功能请求", "自定义"])
    tags = {tag["name"]: tag for tag in post["tags"]}
    assert tags["功能请求"]["is_builtin"] is True
    assert tags["自定义"]["is_builtin"] is False

    public_after = await client.get("/api/v1/tags")
    assert [tag["name"] for tag in public_after.json()] == ["功能请求"]

    admin_list = await client.get("/api/v1/admin/tags")
    counts = {tag["name"]: tag["post_count"] for tag in admin_list.json()}
    assert counts == {"功能请求": 1, "自定义": 1}

    deleted = await client.delete(f"/api/v1/admin/tags/{tags['功能请求']['id']}")
    assert deleted.status_code == 204
    after = await client.get(f"/api/v1/posts/{post['id']}")
    assert [tag["name"] for tag in after.json()["tags"]] == ["自定义"]

    assert (await client.delete("/api/v1/admin/tags/9999")).status_code == 404


async def test_admin_can_promote_custom_tag(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn)
    await login(client, "alice@example.com")
    created = await create_post(client, tags=["性能"])
    assert created["tags"][0]["is_builtin"] is False

    await login(client, ADMIN_EMAIL)
    promoted = await client.post("/api/v1/admin/tags", json={"name": "性能"})

    assert promoted.status_code == 201
    assert promoted.json()["is_builtin"] is True
    assert promoted.json()["post_count"] == 1
    detail = await client.get(f"/api/v1/posts/{created['id']}")
    assert detail.json()["tags"][0]["is_builtin"] is True


# --------------------------------------------------------------------------- #
# 站点名称
# --------------------------------------------------------------------------- #


async def test_site_name_from_settings(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "app_name", "反馈中心")

    response = await client.get("/api/v1/site")

    assert response.status_code == 200
    assert response.json() == {"name": "反馈中心"}
