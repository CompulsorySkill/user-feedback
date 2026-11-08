"""公告：仅管理员可写、草稿隐藏、全局唯一置顶、作者快照。"""

from __future__ import annotations

import time
from datetime import datetime

import jwt
import pytest
from httpx import AsyncClient

from app.api.deps import get_storage_backend
from app.core.config import settings
from app.main import app
from tests.conftest import FakeStorage, insert_upload

SSO_SECRET = "test-sso-secret-0123456789abcdef012345"
TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef012345"
ADMIN_EMAIL = "admin@example.com"


@pytest.fixture(autouse=True)
def sso_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "sso_secrets", [SSO_SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", TEST_SESSION_SECRET)
    monkeypatch.setattr(settings, "admin_emails", ADMIN_EMAIL)
    monkeypatch.setattr(settings, "sso_return_to_default", "/")


def sso_token(email: str, *, name: str | None = None) -> str:
    payload = {"email": email, "exp": int(time.time()) + 300}
    if name:
        payload["name"] = name
    return jwt.encode(payload, SSO_SECRET, algorithm="HS256")


async def login(client: AsyncClient, email: str, *, name: str | None = None) -> None:
    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token(email, name=name), "return_to": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 302


def doc(text: str = "公告正文") -> dict:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


async def test_announcement_writes_require_admin(client: AsyncClient) -> None:
    anonymous = await client.post(
        "/api/v1/announcements", json={"title": "匿名写", "content": doc()}
    )
    assert anonymous.status_code == 403
    assert anonymous.json()["code"] == "ADMIN_REQUIRED"

    await login(client, "alice@example.com")
    user_write = await client.post(
        "/api/v1/announcements", json={"title": "用户写", "content": doc()}
    )
    assert user_write.status_code == 403


async def test_announcement_lifecycle_and_pin(client: AsyncClient) -> None:
    await login(client, ADMIN_EMAIL, name="站点管理员")

    created = await client.post(
        "/api/v1/announcements", json={"title": "维护通知", "content": doc()}
    )
    assert created.status_code == 201
    entry = created.json()
    assert entry["is_published"] is False
    assert entry["is_pinned"] is False
    assert entry["author_name"] == "站点管理员"
    announcement_id = entry["id"]

    # 草稿不能置顶。
    pin_draft = await client.post(f"/api/v1/announcements/{announcement_id}/pin")
    assert pin_draft.status_code == 400
    assert pin_draft.json()["code"] == "ANNOUNCEMENT_NOT_PUBLISHED"

    published = await client.post(f"/api/v1/announcements/{announcement_id}/publish")
    assert published.status_code == 200
    assert published.json()["published_at"] is not None

    # 第二篇：置顶会顶掉第一篇。
    other = await client.post(
        "/api/v1/announcements", json={"title": "第二篇", "content": doc()}
    )
    other_id = other.json()["id"]
    await client.post(f"/api/v1/announcements/{other_id}/publish")

    first_pin = await client.post(f"/api/v1/announcements/{announcement_id}/pin")
    assert first_pin.json()["is_pinned"] is True
    second_pin = await client.post(f"/api/v1/announcements/{other_id}/pin")
    assert second_pin.json()["is_pinned"] is True

    listing = await client.get("/api/v1/announcements")
    items = listing.json()["items"]
    assert [item["id"] for item in items] == [other_id, announcement_id]
    assert items[0]["is_pinned"] is True
    assert items[1]["is_pinned"] is False

    unpin = await client.post(f"/api/v1/announcements/{other_id}/unpin")
    assert unpin.json()["is_pinned"] is False

    unpublish = await client.post(f"/api/v1/announcements/{announcement_id}/unpublish")
    assert unpublish.json()["is_published"] is False
    assert anonymous_list_titles(await client.get("/api/v1/announcements")) == [
        "第二篇"
    ]

    deleted = await client.delete(f"/api/v1/announcements/{announcement_id}")
    assert deleted.status_code == 204


def anonymous_list_titles(response) -> list[str]:
    return [item["title"] for item in response.json()["items"]]


async def test_announcement_drafts_hidden_from_public(
    client: AsyncClient, sqlite_conn
) -> None:
    await login(client, ADMIN_EMAIL)
    published = await client.post(
        "/api/v1/announcements", json={"title": "已发布", "content": doc()}
    )
    await client.post(f"/api/v1/announcements/{published.json()['id']}/publish")
    draft = await client.post(
        "/api/v1/announcements", json={"title": "草稿", "content": doc()}
    )

    admin_list = await client.get(
        "/api/v1/announcements", params={"include_drafts": "true"}
    )
    admin_titles = [item["title"] for item in admin_list.json()["items"]]
    assert sorted(admin_titles) == sorted(["草稿", "已发布"])
    assert (
        await client.get(f"/api/v1/announcements/{draft.json()['id']}")
    ).status_code == 200

    await client.post("/api/v1/auth/logout")
    public_list = await client.get("/api/v1/announcements")
    assert [item["title"] for item in public_list.json()["items"]] == ["已发布"]
    assert (
        await client.get(f"/api/v1/announcements/{draft.json()['id']}")
    ).status_code == 404


async def test_announcement_update_keeps_author(client: AsyncClient) -> None:
    await login(client, ADMIN_EMAIL, name="原作者")
    created = await client.post(
        "/api/v1/announcements", json={"title": "原标题", "content": doc()}
    )
    announcement_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/announcements/{announcement_id}", json={"title": "新标题"}
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "新标题"
    assert updated.json()["author_name"] == "原作者"


async def presign_attachment(
    client: AsyncClient,
    *,
    filename: str = "notice.zip",
    content_type: str = "application/zip",
) -> dict:
    response = await client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": filename,
            "content_type": content_type,
            "purpose": "announcement_attachment",
            "size": 2048,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_announcement_attachment_presign_requires_admin(
    client: AsyncClient,
) -> None:
    anonymous = await client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": "a.zip",
            "content_type": "application/zip",
            "purpose": "announcement_attachment",
            "size": 10,
        },
    )
    assert anonymous.status_code == 403
    assert anonymous.json()["code"] == "ADMIN_REQUIRED"

    await login(client, ADMIN_EMAIL)
    ticket = await presign_attachment(client)
    assert ticket["headers"]["Content-Type"] == "application/octet-stream"


async def test_announcement_attachment_lifecycle(client: AsyncClient) -> None:
    await login(client, ADMIN_EMAIL)
    ticket = await presign_attachment(client)
    object_key = ticket["object_key"]

    created = await client.post(
        "/api/v1/announcements",
        json={
            "title": "带附件的公告",
            "content": doc(),
            "attachments": [
                {"object_key": object_key, "filename": "../../通知 附件.zip"}
            ],
        },
    )
    assert created.status_code == 201, created.text
    entry = created.json()
    attachment = entry["attachments"][0]
    assert attachment["filename"] == "通知 附件.zip"
    assert attachment["content_type"] == "application/zip"
    assert attachment["size"] == 2048
    assert attachment["object_key"] == object_key
    assert attachment["download_url"].endswith(f"/attachments/{attachment['id']}")

    # 草稿附件对匿名访客不可见。
    await client.post("/api/v1/auth/logout")
    assert (
        await client.get(
            f"/api/v1/announcements/{entry['id']}/attachments/{attachment['id']}"
        )
    ).status_code == 404

    await login(client, ADMIN_EMAIL)
    await client.post(f"/api/v1/announcements/{entry['id']}/publish")
    await client.post("/api/v1/auth/logout")

    public = await client.get(f"/api/v1/announcements/{entry['id']}")
    assert public.status_code == 200
    # 公开响应不暴露 object_key。
    assert public.json()["attachments"][0]["object_key"] is None

    storage = FakeStorage()
    storage.objects[object_key] = b"notice-binary"
    app.dependency_overrides[get_storage_backend] = lambda: storage

    download = await client.get(
        f"/api/v1/announcements/{entry['id']}/attachments/{attachment['id']}"
    )
    assert download.status_code == 200
    assert download.content == b"notice-binary"
    assert download.headers["content-type"] == "application/octet-stream"
    assert "attachment;" in download.headers["content-disposition"]
    assert "filename*=UTF-8''" in download.headers["content-disposition"]

    missing = await client.get(f"/api/v1/announcements/{entry['id']}/attachments/99999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "ATTACHMENT_NOT_FOUND"


async def test_announcement_attachment_update_and_purpose(
    client: AsyncClient, sqlite_conn
) -> None:
    await login(client, ADMIN_EMAIL)
    first = await presign_attachment(client, filename="first.zip")
    second = await presign_attachment(client, filename="second.zip")

    created = await client.post(
        "/api/v1/announcements",
        json={
            "title": "附件编辑",
            "content": doc(),
            "attachments": [
                {"object_key": first["object_key"], "filename": "first.zip"}
            ],
        },
    )
    entry_id = created.json()["id"]

    replaced = await client.patch(
        f"/api/v1/announcements/{entry_id}",
        json={
            "attachments": [
                {"object_key": second["object_key"], "filename": "second.zip"}
            ]
        },
    )
    assert replaced.status_code == 200
    assert [item["filename"] for item in replaced.json()["attachments"]] == [
        "second.zip"
    ]

    # 更新日志附件不能混用为公告附件。
    admin_id = sqlite_conn.execute(
        "SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)
    ).fetchone()[0]
    insert_upload(
        sqlite_conn,
        object_key="uploads/changelog-only.zip",
        created_at=datetime(2026, 1, 1),
        identity=f"user:{admin_id}",
        purpose="changelog_attachment",
        content_type="application/zip",
    )
    denied = await client.patch(
        f"/api/v1/announcements/{entry_id}",
        json={
            "attachments": [
                {"object_key": "uploads/changelog-only.zip", "filename": "x.zip"}
            ]
        },
    )
    assert denied.status_code == 400
    assert denied.json()["code"] == "INVALID_ATTACHMENT"
