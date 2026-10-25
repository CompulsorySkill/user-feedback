"""更新日志附件：任意类型上传、归属校验、下载与草稿隔离。"""

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


def sso_token(email: str) -> str:
    return jwt.encode(
        {"email": email, "exp": int(time.time()) + 300},
        SSO_SECRET,
        algorithm="HS256",
    )


async def login(client: AsyncClient, email: str = ADMIN_EMAIL) -> None:
    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token(email), "return_to": "/"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


def changelog_doc(text: str = "发布说明") -> dict:
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


async def presign_attachment(
    client: AsyncClient,
    *,
    filename: str = "release.zip",
    content_type: str = "application/zip",
) -> dict:
    response = await client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": filename,
            "content_type": content_type,
            "purpose": "changelog_attachment",
            "size": 2048,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_attachment_presign_requires_admin(client: AsyncClient) -> None:
    anonymous = await client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": "a.zip",
            "content_type": "application/zip",
            "purpose": "changelog_attachment",
            "size": 10,
        },
    )
    assert anonymous.status_code == 403
    assert anonymous.json()["code"] == "ADMIN_REQUIRED"

    await login(client, "alice@example.com")
    user = await client.post(
        "/api/v1/uploads/presign",
        json={
            "filename": "a.zip",
            "content_type": "application/zip",
            "purpose": "changelog_attachment",
            "size": 10,
        },
    )
    assert user.status_code == 403
    assert user.json()["code"] == "ADMIN_REQUIRED"

    await login(client)
    ticket = await presign_attachment(client, filename="安装包.dmg")

    assert ticket["object_key"].startswith("uploads/")
    assert ticket["object_key"].endswith(".bin")
    # 浏览器 PUT 与对象元数据统一为 octet-stream，防止 HTML/SVG 被内联执行。
    assert ticket["headers"]["Content-Type"] == "application/octet-stream"


async def test_changelog_attachment_lifecycle(client: AsyncClient, sqlite_conn) -> None:
    await login(client)
    ticket = await presign_attachment(client, filename="release.zip")
    object_key = ticket["object_key"]

    created = await client.post(
        "/api/v1/changelogs",
        json={
            "title": "v1.0 发布说明",
            "content": changelog_doc(),
            "attachments": [
                {"object_key": object_key, "filename": "../../发布 说明.zip"}
            ],
        },
    )
    assert created.status_code == 201, created.text
    entry = created.json()
    assert len(entry["attachments"]) == 1
    attachment = entry["attachments"][0]
    assert attachment["filename"] == "发布 说明.zip"
    assert attachment["content_type"] == "application/zip"
    assert attachment["size"] == 2048
    assert attachment["object_key"] == object_key
    assert attachment["download_url"].endswith(f"/attachments/{attachment['id']}")

    # 草稿附件对匿名访客不可见，也不能下载。
    await client.post("/api/v1/auth/logout")
    assert (await client.get(f"/api/v1/changelogs/{entry['id']}")).status_code == 404
    assert (
        await client.get(
            f"/api/v1/changelogs/{entry['id']}/attachments/{attachment['id']}"
        )
    ).status_code == 404

    await login(client)
    published = await client.post(f"/api/v1/changelogs/{entry['id']}/publish")
    assert published.status_code == 200
    await client.post("/api/v1/auth/logout")

    public = await client.get(f"/api/v1/changelogs/{entry['id']}")
    assert public.status_code == 200
    public_attachment = public.json()["attachments"][0]
    assert public_attachment["filename"] == "发布 说明.zip"
    # 公开响应不暴露 object_key，只能走后端受控下载。
    assert public_attachment["object_key"] is None

    storage = FakeStorage()
    storage.objects[object_key] = b"release-binary"
    app.dependency_overrides[get_storage_backend] = lambda: storage

    download = await client.get(
        f"/api/v1/changelogs/{entry['id']}/attachments/{attachment['id']}"
    )
    assert download.status_code == 200
    assert download.content == b"release-binary"
    assert download.headers["content-type"] == "application/octet-stream"
    assert "attachment;" in download.headers["content-disposition"]
    assert "filename*=UTF-8''" in download.headers["content-disposition"]

    missing = await client.get(f"/api/v1/changelogs/{entry['id']}/attachments/99999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "ATTACHMENT_NOT_FOUND"


async def test_update_replaces_and_validates_attachments(
    client: AsyncClient, sqlite_conn
) -> None:
    await login(client)
    first = await presign_attachment(client, filename="first.zip")
    second = await presign_attachment(client, filename="second.zip")

    created = await client.post(
        "/api/v1/changelogs",
        json={
            "title": "附件编辑",
            "content": changelog_doc(),
            "attachments": [
                {"object_key": first["object_key"], "filename": "first.zip"}
            ],
        },
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]

    replaced = await client.patch(
        f"/api/v1/changelogs/{entry_id}",
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

    cleared = await client.patch(
        f"/api/v1/changelogs/{entry_id}", json={"attachments": []}
    )
    assert cleared.status_code == 200
    assert cleared.json()["attachments"] == []

    # 其他身份的 Upload 不能作为管理员附件引用。
    insert_upload(
        sqlite_conn,
        object_key="uploads/foreign.pdf",
        created_at=datetime(2026, 1, 1),
        identity="user:9999",
        purpose="changelog_attachment",
        content_type="application/pdf",
    )
    denied = await client.patch(
        f"/api/v1/changelogs/{entry_id}",
        json={
            "attachments": [
                {"object_key": "uploads/foreign.pdf", "filename": "foreign.pdf"}
            ]
        },
    )
    assert denied.status_code == 400
    assert denied.json()["code"] == "INVALID_ATTACHMENT"


async def test_attachment_limit_and_type(client: AsyncClient) -> None:
    await login(client)
    ticket = await presign_attachment(client)

    too_many = await client.post(
        "/api/v1/changelogs",
        json={
            "title": "附件过多",
            "content": changelog_doc(),
            "attachments": [
                {"object_key": ticket["object_key"], "filename": f"{i}.zip"}
                for i in range(11)
            ],
        },
    )
    assert too_many.status_code == 422

    invalid_key = await client.post(
        "/api/v1/changelogs",
        json={
            "title": "非法 key",
            "content": changelog_doc(),
            "attachments": [{"object_key": "https://evil.test/a", "filename": "a"}],
        },
    )
    assert invalid_key.status_code == 422
