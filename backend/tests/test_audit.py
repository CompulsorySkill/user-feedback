"""审计日志：管理操作留痕、查询权限与清理触发。"""

from __future__ import annotations

import time
import uuid
from datetime import datetime

import jwt
import pytest
from httpx import AsyncClient

from app.api.deps import get_storage_backend
from app.core.config import settings
from app.main import app
from tests.conftest import FakeStorage, insert_board, insert_post

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


async def login(client: AsyncClient, email: str = ADMIN_EMAIL) -> None:
    response = await client.get(
        "/api/sso/jwt",
        params={"token": sso_token(email), "return_to": "/"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


async def test_audit_log_records_admin_actions(client: AsyncClient) -> None:
    await login(client)

    created = await client.post(
        "/api/v1/admin/boards", json={"slug": "audit-board", "name": "审计看板"}
    )
    assert created.status_code == 201
    board_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/admin/boards/{board_id}", json={"name": "审计看板改名"}
    )
    assert updated.status_code == 200

    tag = await client.post("/api/v1/admin/tags", json={"name": "审计标签"})
    assert tag.status_code == 201

    logs = await client.get("/api/v1/admin/audit-logs")
    assert logs.status_code == 200
    items = logs.json()["items"]
    actions = [item["action"] for item in items]
    assert actions[:3] == ["tag.create", "board.update", "board.create"]
    assert all(item["actor_email"] == ADMIN_EMAIL for item in items)
    assert all(item["ip"] for item in items)

    update = next(item for item in items if item["action"] == "board.update")
    assert update["target_type"] == "board"
    assert update["target_id"] == str(board_id)
    assert update["detail"] == {"name": "审计看板改名"}

    filtered = await client.get(
        "/api/v1/admin/audit-logs", params={"action": "board.create"}
    )
    assert [item["action"] for item in filtered.json()["items"]] == ["board.create"]


async def test_audit_log_pagination_and_permissions(
    client: AsyncClient, sqlite_conn
) -> None:
    assert (await client.get("/api/v1/admin/audit-logs")).status_code == 403

    await login(client, "alice@example.com")
    assert (await client.get("/api/v1/admin/audit-logs")).status_code == 403

    await login(client)
    for index in range(3):
        response = await client.post(
            "/api/v1/admin/boards",
            json={"slug": f"audit-{index}", "name": f"审计 {index}"},
        )
        assert response.status_code == 201

    first = await client.get("/api/v1/admin/audit-logs", params={"limit": 2})
    body = first.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"]

    second = await client.get(
        "/api/v1/admin/audit-logs",
        params={"limit": 2, "before_id": body["next_cursor"]},
    )
    assert [item["action"] for item in second.json()["items"]] == ["board.create"]
    assert second.json()["next_cursor"] is None


async def test_audit_log_records_status_change(
    client: AsyncClient, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="待审计反馈",
        created_at=datetime(2026, 3, 1, 12, 0, 0),
    )
    await login(client)

    response = await client.patch(
        f"/api/v1/posts/{post_id}/status", json={"status": "planned"}
    )
    assert response.status_code == 200

    logs = await client.get(
        "/api/v1/admin/audit-logs", params={"action": "post.status"}
    )
    item = logs.json()["items"][0]
    assert item["target_id"] == str(uuid.UUID(post_id))
    assert item["detail"]["status"] == "planned"
    assert item["detail"]["by_admin"] is True


async def test_admin_upload_cleanup_endpoint(client: AsyncClient, sqlite_conn) -> None:
    from datetime import datetime, timedelta, timezone

    from tests.conftest import insert_upload

    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=48)
    insert_upload(sqlite_conn, object_key="uploads/orphan.png", created_at=old)
    storage = FakeStorage()
    app.dependency_overrides[get_storage_backend] = lambda: storage
    await login(client)

    dry = await client.post("/api/v1/admin/uploads/cleanup", params={"dry_run": "true"})
    assert dry.status_code == 200
    assert dry.json()["deleted"] == 1
    assert storage.deleted == []

    result = await client.post("/api/v1/admin/uploads/cleanup")
    assert result.status_code == 200
    assert result.json()["deleted"] == 1
    assert storage.deleted == ["uploads/orphan.png"]

    logs = await client.get(
        "/api/v1/admin/audit-logs", params={"action": "upload.cleanup"}
    )
    assert len(logs.json()["items"]) == 2
