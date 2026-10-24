"""根页面聚合列表与管理员看板增删改。"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_post

BASE = datetime(2026, 2, 1, 12, 0, 0)
SSO_SECRET = "test-sso-secret-0123456789abcdef012345"
TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef012345"
ADMIN_EMAIL = "admin@example.com"


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


# --------------------------------------------------------------------------- #
# 全部看板聚合列表
# --------------------------------------------------------------------------- #


def seed_two_boards(conn) -> tuple[int, int]:
    product = insert_board(conn, slug="product", name="功能建议")
    internal = insert_board(conn, slug="internal", name="内部", is_public=False)
    insert_post(
        conn,
        board_id=product,
        title="公开反馈",
        created_at=BASE,
        status="open",
        vote_count=2,
    )
    insert_post(
        conn,
        board_id=product,
        title="已计划反馈",
        created_at=BASE + timedelta(minutes=1),
        status="planned",
        vote_count=9,
    )
    insert_post(
        conn,
        board_id=internal,
        title="内部反馈",
        created_at=BASE + timedelta(minutes=2),
    )
    return product, internal


async def test_all_posts_aggregates_public_boards(
    client: AsyncClient, sqlite_conn
) -> None:
    seed_two_boards(sqlite_conn)

    response = await client.get("/api/v1/posts")

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["items"]] == ["已计划反馈", "公开反馈"]
    assert {item["board_name"] for item in body["items"]} == {"功能建议"}
    assert all(item["board_slug"] == "product" for item in body["items"])


async def test_all_posts_filters_and_sort(client: AsyncClient, sqlite_conn) -> None:
    seed_two_boards(sqlite_conn)

    by_status = await client.get("/api/v1/posts", params={"status": "planned"})
    assert [item["title"] for item in by_status.json()["items"]] == ["已计划反馈"]

    by_query = await client.get("/api/v1/posts", params={"q": "公开"})
    assert [item["title"] for item in by_query.json()["items"]] == ["公开反馈"]

    by_board = await client.get("/api/v1/posts", params={"board": "product"})
    assert len(by_board.json()["items"]) == 2

    missing_board = await client.get("/api/v1/posts", params={"board": "nope"})
    assert missing_board.status_code == 404
    assert missing_board.json()["code"] == "BOARD_NOT_FOUND"

    top = await client.get("/api/v1/posts", params={"sort": "top"})
    assert [item["title"] for item in top.json()["items"]] == ["已计划反馈", "公开反馈"]


async def test_all_posts_pagination(client: AsyncClient, sqlite_conn) -> None:
    seed_two_boards(sqlite_conn)

    first = await client.get("/api/v1/posts", params={"limit": 1})
    body = first.json()
    assert len(body["items"]) == 1
    assert body["next_cursor"]

    second = await client.get(
        "/api/v1/posts", params={"limit": 1, "cursor": body["next_cursor"]}
    )
    assert [item["title"] for item in second.json()["items"]] == ["公开反馈"]
    assert second.json()["next_cursor"] is None


# --------------------------------------------------------------------------- #
# 管理员看板维护
# --------------------------------------------------------------------------- #


async def test_board_admin_requires_admin(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)

    assert (await client.get("/api/v1/admin/boards")).status_code == 403
    created = await client.post(
        "/api/v1/admin/boards", json={"slug": "new-board", "name": "新看板"}
    )
    assert created.status_code == 403
    updated = await client.patch(
        f"/api/v1/admin/boards/{board_id}", json={"name": "改名"}
    )
    assert updated.status_code == 403
    deleted = await client.delete(f"/api/v1/admin/boards/{board_id}")
    assert deleted.status_code == 403

    await login(client, "alice@example.com")
    assert (await client.get("/api/v1/admin/boards")).status_code == 403


async def test_admin_board_lifecycle(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn, slug="existing", name="已有看板")
    await login(client, ADMIN_EMAIL)

    created = await client.post(
        "/api/v1/admin/boards",
        json={
            "slug": "New-Board",
            "name": "  新看板  ",
            "description": "  说明  ",
            "is_public": False,
            "allow_guest_posting": False,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["slug"] == "new-board"
    assert body["name"] == "新看板"
    assert body["description"] == "说明"
    assert body["is_public"] is False
    assert body["allow_guest_posting"] is False
    assert body["allow_guest_voting"] is True
    assert body["post_count"] == 0

    listed = await client.get("/api/v1/admin/boards")
    assert [item["slug"] for item in listed.json()] == ["existing", "new-board"]

    updated = await client.patch(
        f"/api/v1/admin/boards/{body['id']}",
        json={
            "slug": "renamed",
            "name": "改名后",
            "description": None,
            "is_public": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["slug"] == "renamed"
    assert updated.json()["name"] == "改名后"
    assert updated.json()["description"] is None
    assert updated.json()["is_public"] is True

    public = await client.get("/api/v1/boards/renamed")
    assert public.status_code == 200
    assert public.json()["name"] == "改名后"

    deleted = await client.delete(f"/api/v1/admin/boards/{body['id']}")
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/boards/renamed")).status_code == 404


async def test_admin_board_slug_conflict(client: AsyncClient, sqlite_conn) -> None:
    insert_board(sqlite_conn, slug="taken", name="占用")
    await login(client, ADMIN_EMAIL)

    conflict = await client.post(
        "/api/v1/admin/boards", json={"slug": "taken", "name": "重复"}
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "BOARD_SLUG_TAKEN"

    board = await client.post(
        "/api/v1/admin/boards", json={"slug": "another", "name": "另一个"}
    )
    rename = await client.patch(
        f"/api/v1/admin/boards/{board.json()['id']}", json={"slug": "taken"}
    )
    assert rename.status_code == 409
    assert rename.json()["code"] == "BOARD_SLUG_TAKEN"


async def test_admin_board_slug_validation(client: AsyncClient) -> None:
    await login(client, ADMIN_EMAIL)

    for slug in ["A", "has space", "-leading", "trailing-", "中文"]:
        response = await client.post(
            "/api/v1/admin/boards", json={"slug": slug, "name": "非法"}
        )
        assert response.status_code == 422, slug


async def test_admin_board_delete_requires_force_when_not_empty(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    insert_post(sqlite_conn, board_id=board_id, title="占用反馈", created_at=BASE)
    await login(client, ADMIN_EMAIL)

    refused = await client.delete(f"/api/v1/admin/boards/{board_id}")
    assert refused.status_code == 409
    assert refused.json()["code"] == "BOARD_NOT_EMPTY"
    assert (await client.get("/api/v1/boards/product")).status_code == 200

    forced = await client.delete(
        f"/api/v1/admin/boards/{board_id}", params={"force": "true"}
    )
    assert forced.status_code == 204
    assert (await client.get("/api/v1/boards/product")).status_code == 404
    assert (await client.get("/api/v1/posts")).json()["items"] == []
    assert sqlite_conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0


async def test_admin_board_update_missing(client: AsyncClient) -> None:
    await login(client, ADMIN_EMAIL)

    assert (
        await client.patch("/api/v1/admin/boards/999", json={"name": "x"})
    ).status_code == 404
    assert (await client.delete("/api/v1/admin/boards/999")).status_code == 404
