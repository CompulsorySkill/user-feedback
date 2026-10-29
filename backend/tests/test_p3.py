"""P3：SSO 会话、角色、状态机、更新日志管理写与评论。"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_changelog, insert_post

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


def sso_token(
    email: str, *, name: str | None = None, secret: str = SSO_SECRET, ttl: int = 300
) -> str:
    payload = {"email": email, "exp": int(time.time()) + ttl}
    if name:
        payload["name"] = name
    return jwt.encode(payload, secret, algorithm="HS256")


async def login(
    client: AsyncClient, email: str, *, name: str | None = None, target: str = "/"
):
    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token(email, name=name), "return_to": target},
        follow_redirects=False,
    )
    return response


# --------------------------------------------------------------------------- #
# SSO / 会话
# --------------------------------------------------------------------------- #


async def test_sso_login_creates_user_and_session(
    client: AsyncClient, sqlite_conn
) -> None:
    response = await login(client, "alice@example.com", name="Alice", target="/b/product")

    assert response.status_code == 302
    assert response.headers["location"] == "/b/product"
    assert "feedback_access" in client.cookies
    assert "feedback_refresh" in client.cookies

    me = await client.get("/api/v1/auth/me")
    body = me.json()
    assert body["authenticated"] is True
    assert body["is_admin"] is False
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["display_name"] == "Alice"
    assert body["user"]["role"] == "user"

    row = sqlite_conn.execute(
        "SELECT email, display_name, role, sso_provider FROM users WHERE email=?",
        ("alice@example.com",),
    ).fetchone()
    assert row == ("alice@example.com", "Alice", "user", "sso")


async def test_admin_emails_grants_admin_role(client: AsyncClient, sqlite_conn) -> None:
    await login(client, ADMIN_EMAIL, name="Admin")

    me = (await client.get("/api/v1/auth/me")).json()
    assert me["is_admin"] is True
    assert me["user"]["role"] == "admin"

    row = sqlite_conn.execute(
        "SELECT role FROM users WHERE email=?", (ADMIN_EMAIL,)
    ).fetchone()
    assert row == ("admin",)


async def test_invalid_sso_token_degrades_to_anonymous(client: AsyncClient) -> None:
    bad = sso_token("alice@example.com", secret="wrong-secret")

    response = await client.get(
        "/api/sso/jwt",
        params={"token": bad, "return_to": "/b/product"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/b/product"
    assert "feedback_access" not in client.cookies
    assert (await client.get("/api/v1/auth/me")).json()["authenticated"] is False


async def test_expired_sso_token_degrades_to_anonymous(client: AsyncClient) -> None:
    token = jwt.encode(
        {"email": "alice@example.com", "exp": int(time.time()) - 10},
        SSO_SECRET,
        algorithm="HS256",
    )

    response = await client.get(
        "/api/sso/jwt", params={"token": token}, follow_redirects=False
    )

    assert response.status_code == 302
    assert "feedback_access" not in client.cookies


async def test_sso_redirect_respects_base_path(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "base_path", "feedback")

    response = await login(client, "alice@example.com", target="/b/product")
    assert response.headers["location"] == "/feedback/b/product"

    posted = await client.post(
        "/api/sso/jwt",
        json={"token": sso_token("bob@example.com"), "return_to": "/post/1"},
    )
    assert posted.status_code == 200
    assert posted.json()["redirect_to"] == "/feedback/post/1"


@pytest.mark.parametrize(
    "return_to",
    ["//evil.com", "https://evil.com", "/\\evil.com", "javascript:alert(1)"],
)
async def test_malicious_return_to_falls_back_to_root(
    client: AsyncClient, return_to: str
) -> None:
    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token("alice@example.com"), "return_to": return_to},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/"


async def test_refresh_rotates_access_token(client: AsyncClient) -> None:
    await login(client, "alice@example.com")
    old_access = client.cookies.get("feedback_access")

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert client.cookies.get("feedback_access") != old_access
    assert (await client.get("/api/v1/auth/me")).json()["authenticated"] is True


async def test_logout_clears_session(client: AsyncClient) -> None:
    await login(client, "alice@example.com")

    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert (await client.get("/api/v1/auth/me")).json()["authenticated"] is False


async def test_login_merges_anonymous_posts_and_votes(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn, board_id=board_id, title="匿名反馈", created_at=BASE
    )

    # 匿名写：先建投票与另一条反馈，随后登录合并。
    await client.post(f"/api/v1/posts/{post_id}/vote")
    created = await client.post(
        "/api/v1/boards/product/posts",
        json={
            "title": "登录前的匿名反馈",
            "content": {
                "type": "doc",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "正文"}]}],
            },
        },
    )
    assert created.status_code == 201

    await login(client, "alice@example.com")

    user_id = sqlite_conn.execute(
        "SELECT id FROM users WHERE email='alice@example.com'"
    ).fetchone()[0]
    merged_post = sqlite_conn.execute(
        "SELECT author_id, anonymous_token FROM posts WHERE title='登录前的匿名反馈'"
    ).fetchone()
    assert merged_post == (user_id, None)
    vote_row = sqlite_conn.execute(
        "SELECT user_id, anonymous_token FROM votes WHERE post_id=?",
        (uuid.UUID(post_id).hex,),
    ).fetchone()
    assert vote_row == (user_id, None)
    assert "feedback_anonymous" not in client.cookies


# --------------------------------------------------------------------------- #
# 状态机与编辑
# --------------------------------------------------------------------------- #


async def _create_post_for(
    client: AsyncClient, sqlite_conn, *, author_id: int | None, status: str = "open"
) -> str:
    board_id = insert_board(sqlite_conn)
    return insert_post(
        sqlite_conn,
        board_id=board_id,
        title="状态机目标",
        created_at=BASE,
        author_id=author_id,
        status=status,
    )


async def test_admin_can_change_any_status(client: AsyncClient, sqlite_conn) -> None:
    await login(client, ADMIN_EMAIL)
    post_id = await _create_post_for(client, sqlite_conn, author_id=None)

    response = await client.patch(
        f"/api/v1/posts/{post_id}/status", json={"status": "planned"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "planned"


async def test_author_can_only_close_once(
    client: AsyncClient, sqlite_conn
) -> None:
    await login(client, "alice@example.com")
    me = (await client.get("/api/v1/auth/me")).json()
    post_id = await _create_post_for(
        client, sqlite_conn, author_id=me["user"]["id"]
    )

    closed = await client.patch(
        f"/api/v1/posts/{post_id}/status", json={"status": "closed"}
    )
    reopened = await client.patch(
        f"/api/v1/posts/{post_id}/status", json={"status": "open"}
    )
    planned = await client.patch(
        f"/api/v1/posts/{post_id}/status", json={"status": "planned"}
    )

    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert reopened.status_code == 403
    assert reopened.json()["code"] == "STATUS_FORBIDDEN"
    assert planned.status_code == 403


async def test_anonymous_post_cannot_change_status(
    client: AsyncClient, sqlite_conn
) -> None:
    post_id = await _create_post_for(client, sqlite_conn, author_id=None)

    response = await client.patch(
        f"/api/v1/posts/{post_id}/status", json={"status": "closed"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "STATUS_FORBIDDEN"


async def test_closed_post_rejects_author_edit_but_allows_admin(
    client: AsyncClient, sqlite_conn
) -> None:
    await login(client, "alice@example.com")
    me = (await client.get("/api/v1/auth/me")).json()
    post_id = await _create_post_for(
        client, sqlite_conn, author_id=me["user"]["id"], status="closed"
    )

    denied = await client.patch(
        f"/api/v1/posts/{post_id}", json={"title": "作者修改已关闭帖"}
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "POST_CLOSED"

    await client.post("/api/v1/auth/logout")
    await login(client, ADMIN_EMAIL)
    allowed = await client.patch(
        f"/api/v1/posts/{post_id}", json={"title": "管理员修改已关闭帖"}
    )
    assert allowed.status_code == 200
    assert allowed.json()["title"] == "管理员修改已关闭帖"


async def test_anonymous_cannot_edit_post(client: AsyncClient, sqlite_conn) -> None:
    post_id = await _create_post_for(client, sqlite_conn, author_id=None)

    response = await client.patch(
        f"/api/v1/posts/{post_id}", json={"title": "匿名改标题"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "POST_EDIT_FORBIDDEN"


# --------------------------------------------------------------------------- #
# 更新日志管理写
# --------------------------------------------------------------------------- #


def changelog_doc() -> dict:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "发布说明"}]}],
    }


async def test_changelog_writes_require_admin(client: AsyncClient) -> None:
    anonymous = await client.post(
        "/api/v1/changelogs", json={"title": "匿名写", "content": changelog_doc()}
    )
    assert anonymous.status_code == 403
    assert anonymous.json()["code"] == "ADMIN_REQUIRED"

    await login(client, "alice@example.com")
    user_write = await client.post(
        "/api/v1/changelogs", json={"title": "用户写", "content": changelog_doc()}
    )
    assert user_write.status_code == 403
    assert user_write.json()["code"] == "ADMIN_REQUIRED"


async def test_admin_changelog_lifecycle(client: AsyncClient) -> None:
    await login(client, ADMIN_EMAIL)

    created = await client.post(
        "/api/v1/changelogs",
        json={"title": "v1.0 发布说明", "content": changelog_doc()},
    )
    assert created.status_code == 201
    entry = created.json()
    assert entry["is_published"] is False
    assert entry["published_at"] is None
    changelog_id = entry["id"]

    published = await client.post(f"/api/v1/changelogs/{changelog_id}/publish")
    assert published.status_code == 200
    assert published.json()["is_published"] is True
    assert published.json()["published_at"] is not None

    unpublish = await client.post(f"/api/v1/changelogs/{changelog_id}/unpublish")
    assert unpublish.json()["is_published"] is False
    # 保留发布时间供审计
    assert unpublish.json()["published_at"] is not None

    updated = await client.patch(
        f"/api/v1/changelogs/{changelog_id}", json={"title": "v1.0 修订"}
    )
    assert updated.json()["title"] == "v1.0 修订"

    deleted = await client.delete(f"/api/v1/changelogs/{changelog_id}")
    assert deleted.status_code == 204


async def test_admin_sees_drafts_in_list_and_detail(
    client: AsyncClient, sqlite_conn
) -> None:
    draft_id = insert_changelog(
        sqlite_conn, title="草稿", created_at=BASE, published=False
    )
    published_id = insert_changelog(
        sqlite_conn,
        title="已发布",
        created_at=BASE - timedelta(hours=1),
        published=True,
    )

    await login(client, ADMIN_EMAIL)
    listing = await client.get(
        "/api/v1/changelogs", params={"include_drafts": "true"}
    )
    titles = [item["title"] for item in listing.json()["items"]]
    assert titles == ["草稿", "已发布"]
    assert (await client.get(f"/api/v1/changelogs/{draft_id}")).status_code == 200
    assert (await client.get(f"/api/v1/changelogs/{published_id}")).status_code == 200


# --------------------------------------------------------------------------- #
# 评论
# --------------------------------------------------------------------------- #


async def _comment(
    client: AsyncClient, post_id: str, content: str, parent_id: str | None = None
):
    payload: dict = {"content": content}
    if parent_id:
        payload["parent_id"] = parent_id
    return await client.post(f"/api/v1/posts/{post_id}/comments", json=payload)


async def test_comment_create_and_list(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(sqlite_conn, board_id=board_id, title="评论目标", created_at=BASE)

    created = await _comment(client, post_id, "第一条评论")
    assert created.status_code == 201
    body = created.json()
    assert body["content"] == "第一条评论"
    assert body["is_anonymous"] is True
    assert body["parent_id"] is None

    listing = await client.get(f"/api/v1/posts/{post_id}/comments")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["content"] == "第一条评论"

    detail = await client.get(f"/api/v1/posts/{post_id}")
    assert detail.json()["comment_count"] == 1


async def test_comment_depth_caps_at_three(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(sqlite_conn, board_id=board_id, title="深评", created_at=BASE)

    root = (await _comment(client, post_id, "根评论")).json()
    level2 = (
        await _comment(client, post_id, "二层", parent_id=root["id"])
    ).json()
    level3 = (
        await _comment(client, post_id, "三层", parent_id=level2["id"])
    ).json()
    level4 = (
        await _comment(client, post_id, "四层", parent_id=level3["id"])
    ).json()

    assert level3["parent_id"] == level2["id"]
    # 超出 3 层：挂到根评论并前缀「回复 @xxx」
    assert level4["parent_id"] == root["id"]
    assert level4["content"].startswith("回复 @匿名用户：")


async def test_comment_rejected_when_post_closed_or_guest_disabled(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    closed_post = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="已关闭",
        created_at=BASE,
        status="closed",
    )
    assert (await _comment(client, closed_post, "关门了")).status_code == 403

    disabled_board = insert_board(
        sqlite_conn, slug="login-only", name="仅登录", allow_guest_posting=False
    )
    # 该看板 allow_guest_commenting 仍为默认 True，先单独改为 False
    sqlite_conn.execute(
        "UPDATE boards SET allow_guest_commenting=0 WHERE id=?", (disabled_board,)
    )
    sqlite_conn.commit()
    post_id = insert_post(
        sqlite_conn, board_id=disabled_board, title="仅登录评论", created_at=BASE
    )
    response = await _comment(client, post_id, "匿名评论")
    assert response.status_code == 403
    assert response.json()["code"] == "GUEST_COMMENTING_DISABLED"


async def test_comment_rate_limit(client: AsyncClient, sqlite_conn) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(sqlite_conn, board_id=board_id, title="限流评论", created_at=BASE)

    statuses = []
    for index in range(11):
        response = await _comment(client, post_id, f"评论 {index}")
        statuses.append(response.status_code)

    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429
