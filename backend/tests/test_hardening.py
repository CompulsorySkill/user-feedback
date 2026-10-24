"""P4 加固：安全头、日志脱敏、限流清理、富文本白名单与跨身份媒体。"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import RedactSsoTokenFilter, redact_sso_token
from app.core.rate_limit import cleanup_rate_limit_counters
from app.models import RateLimitCounter
from app.services.rich_text import MAX_PAYLOAD_BYTES
from tests.conftest import insert_board, insert_post, sqlite_url

SECRET = "hardening-sso-secret-0123456789abcdef"
BASE = datetime(2026, 3, 1, 12, 0, 0)


@pytest.fixture
def sso_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "sso_secrets", [SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", "hardening-session-0123456789abcdef")
    monkeypatch.setattr(settings, "admin_emails", "admin@example.com")
    monkeypatch.setattr(settings, "sso_return_to_default", "/")


def _token(email: str) -> str:
    return jwt.encode(
        {"email": email, "name": "Admin", "exp": int(time.time()) + 300},
        SECRET,
        algorithm="HS256",
    )


async def _login_admin(client: AsyncClient) -> None:
    await client.get(
        "/api/sso/jwt",
        params={"token": _token("admin@example.com"), "return_to": "/"},
        follow_redirects=False,
    )


def doc(text: str = "正文") -> dict:
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]}
        ],
    }


# --------------------------------------------------------------------------- #
# 安全头 / 日志
# --------------------------------------------------------------------------- #


async def test_security_headers_present(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_sso_token_redacted_from_access_log() -> None:
    assert (
        redact_sso_token("/api/sso/jwt?token=abc.def.ghi&return_to=/x")
        == "/api/sso/jwt?token=***&return_to=/x"
    )

    import logging

    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1", "GET", "/api/sso/jwt?token=secret-token", "1.1", 302),
        None,
    )
    assert RedactSsoTokenFilter().filter(record) is True
    assert "secret-token" not in str(record.args)
    assert "token=***" in str(record.args)


# --------------------------------------------------------------------------- #
# 限流清理
# --------------------------------------------------------------------------- #


async def test_cleanup_removes_only_expired_windows(db_path) -> None:
    engine = create_async_engine(sqlite_url(db_path))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        async with sessionmaker() as session:
            session.add(
                RateLimitCounter(
                    identity_key="anon:old",
                    action="post",
                    window_start=now - timedelta(hours=2),
                    count=3,
                )
            )
            session.add(
                RateLimitCounter(
                    identity_key="anon:new",
                    action="post",
                    window_start=now,
                    count=1,
                )
            )
            await session.commit()

            removed = await cleanup_rate_limit_counters(session)

        assert removed == 1
        async with sessionmaker() as session:
            keys = [
                row.identity_key
                for row in (
                    await session.execute(select(RateLimitCounter))
                ).scalars()
            ]
        assert keys == ["anon:new"]
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------- #
# 富文本白名单与跨身份媒体
# --------------------------------------------------------------------------- #


async def test_rich_text_rejects_unknown_node(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    content = {
        "type": "doc",
        "content": [
            {"type": "script", "content": [{"type": "text", "text": "alert(1)"}]}
        ],
    }

    response = await client.post(
        "/api/v1/boards/product/posts", json={"title": "未知节点", "content": content}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CONTENT"


async def test_rich_text_rejects_unknown_mark(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "x",
                        "marks": [{"type": "onclick", "attrs": {"href": "x"}}],
                    }
                ],
            }
        ],
    }

    response = await client.post(
        "/api/v1/boards/product/posts", json={"title": "未知标记", "content": content}
    )

    assert response.status_code == 400


async def test_rich_text_rejects_unsafe_link(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "x",
                        "marks": [
                            {"type": "link", "attrs": {"href": "javascript:alert(1)"}}
                        ],
                    }
                ],
            }
        ],
    }

    response = await client.post(
        "/api/v1/boards/product/posts", json={"title": "危险链接", "content": content}
    )

    assert response.status_code == 400


async def test_rich_text_rejects_oversized_payload(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    content = doc("x" * (MAX_PAYLOAD_BYTES + 1024))

    response = await client.post(
        "/api/v1/boards/product/posts", json={"title": "超大内容", "content": content}
    )

    assert response.status_code == 400
    assert "体积超限" in response.json()["detail"]


async def test_media_from_other_identity_rejected(
    client: AsyncClient, sqlite_conn
) -> None:
    insert_board(sqlite_conn)
    sqlite_conn.execute(
        "INSERT INTO uploads (object_key, identity, purpose, content_type, size)"
        " VALUES ('uploads/other.png', 'anon:someone-else', 'post_image', 'image/png', 10)"
    )
    sqlite_conn.commit()

    content = {
        "type": "doc",
        "content": [
            {
                "type": "image",
                "attrs": {"src": "uploads/other.png"},
            }
        ],
    }
    response = await client.post(
        "/api/v1/boards/product/posts", json={"title": "盗用媒体", "content": content}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CONTENT"


# --------------------------------------------------------------------------- #
# 8.2 必测补充：管理员重开
# --------------------------------------------------------------------------- #


async def test_admin_can_reopen_closed_post(
    client: AsyncClient, sqlite_conn, sso_env
) -> None:
    board_id = insert_board(sqlite_conn)
    post_id = insert_post(
        sqlite_conn,
        board_id=board_id,
        title="已关闭待重开",
        created_at=BASE,
        status="closed",
    )
    await _login_admin(client)

    response = await client.patch(
        f"/api/v1/posts/{post_id}/status", json={"status": "open"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "open"
