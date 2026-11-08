"""反馈时间线与任务接受 / 完成。"""

from __future__ import annotations

import time
from datetime import datetime

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import insert_board, insert_post, insert_user

BASE = datetime(2026, 5, 1, 12, 0, 0)
SSO_SECRET = "test-sso-secret-0123456789abcdef012345"
TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef012345"
ADMIN_EMAIL = "admin@example.com"


@pytest.fixture(autouse=True)
def sso_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sso_secrets", [SSO_SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", TEST_SESSION_SECRET)
    monkeypatch.setattr(
        settings,
        "admin_emails",
        "admin@example.com,worker@example.com,peer@example.com",
    )
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
    assert response.status_code == 302, response.text


def mention_doc(*user_ids: int) -> dict:
    nodes = []
    for user_id in user_ids:
        nodes.append(
            {"type": "mention", "attrs": {"id": str(user_id), "label": f"U{user_id}"}}
        )
        nodes.append({"type": "text", "text": " "})
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": nodes}],
    }


async def test_create_post_records_creation_event(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn, slug="general", name="General")
    await login(client, "worker@example.com", name="Worker")

    response = await client.post(
        "/api/v1/boards/general/posts",
        json={
            "title": "时间线起点",
            "content": {"type": "doc", "content": [{"type": "paragraph"}]},
            "tags": [],
        },
    )
    assert response.status_code == 201, response.text
    timeline = response.json()["timeline"]
    assert len(timeline) == 1
    assert timeline[0]["event_type"] == "created"
    assert timeline[0]["to_status"] == "open"
    assert timeline[0]["actor_name"] == "Worker"


async def test_status_change_records_actor(client: AsyncClient, sqlite_conn) -> None:
    admin_id = insert_user(sqlite_conn, email=ADMIN_EMAIL, display_name="Admin")
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="状态流转",
        created_at=BASE,
        author_id=admin_id,
    )

    await login(client, ADMIN_EMAIL, name="Admin")
    response = await client.patch(
        f"/api/v1/posts/{post_id}/status", json={"status": "planned"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "planned"
    event = body["timeline"][-1]
    assert event["event_type"] == "status_changed"
    assert event["from_status"] == "open"
    assert event["to_status"] == "planned"
    assert event["actor_name"] == "Admin"


async def test_mentioned_user_accepts_and_completes_task(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_user(sqlite_conn, email=ADMIN_EMAIL, display_name="Admin", role="admin")
    worker_id = insert_user(
        sqlite_conn, email="worker@example.com", display_name="Worker", role="admin"
    )
    peer_id = insert_user(
        sqlite_conn, email="peer@example.com", display_name="Peer", role="admin"
    )
    insert_user(sqlite_conn, email="outsider@example.com", display_name="Outsider")
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="可接受的任务",
        created_at=BASE,
        content=mention_doc(worker_id, peer_id),
        status="planned",
    )

    await login(client, "worker@example.com", name="Worker")
    detail = (await client.get(f"/api/v1/posts/{post_id}")).json()
    assert detail["can_accept_task"] is True
    assert detail["can_complete_task"] is False

    accepted = await client.post(f"/api/v1/posts/{post_id}/task/accept")
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["status"] == "in_progress"
    assert body["task"]["assignee_name"] == "Worker"
    assert body["can_accept_task"] is False
    assert body["can_complete_task"] is True
    assert body["timeline"][-1]["event_type"] == "task_accepted"
    assert body["timeline"][-1]["to_status"] == "in_progress"

    await login(client, "outsider@example.com", name="Outsider")
    detail = (await client.get(f"/api/v1/posts/{post_id}")).json()
    assert detail["can_accept_task"] is False
    rejected = await client.post(f"/api/v1/posts/{post_id}/task/accept")
    assert rejected.status_code == 403
    assert rejected.json()["code"] == "TASK_NOT_ASSIGNED"

    await login(client, "peer@example.com", name="Peer")
    taken = await client.post(f"/api/v1/posts/{post_id}/task/accept")
    assert taken.status_code == 409
    assert taken.json()["code"] == "TASK_ALREADY_ACCEPTED"
    not_assigned = await client.post(f"/api/v1/posts/{post_id}/task/complete")
    assert not_assigned.status_code == 403

    await login(client, "worker@example.com", name="Worker")
    completed = await client.post(f"/api/v1/posts/{post_id}/task/complete")
    assert completed.status_code == 200, completed.text
    body = completed.json()
    assert body["status"] == "completed"
    assert body["task"]["completed_at"] is not None
    assert body["can_complete_task"] is False
    assert body["timeline"][-1]["event_type"] == "task_completed"
    assert body["timeline"][-1]["actor_name"] == "Worker"


async def test_comment_mention_grants_task_permission(
    client: AsyncClient, sqlite_conn
) -> None:
    import json
    import uuid

    worker_id = insert_user(
        sqlite_conn, email="worker@example.com", display_name="Worker", role="admin"
    )
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="评论提及也能接任务",
        created_at=BASE,
    )
    sqlite_conn.execute(
        "INSERT INTO comments (id, post_id, content) VALUES (?, ?, ?)",
        (
            uuid.uuid4().hex,
            post_id,
            json.dumps(mention_doc(worker_id)),
        ),
    )
    sqlite_conn.commit()

    await login(client, "worker@example.com", name="Worker")
    detail = (await client.get(f"/api/v1/posts/{post_id}")).json()
    assert detail["can_accept_task"] is True

    accepted = await client.post(f"/api/v1/posts/{post_id}/task/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["task"]["assignee_name"] == "Worker"
