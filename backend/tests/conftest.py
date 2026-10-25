"""测试夹具：每个用例一份独立 SQLite 库，schema 由 Alembic 迁移构建。"""

from __future__ import annotations

import sqlite3
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_storage_backend
from app.core.config import settings
from app.core.db import get_session
from app.core.storage import PresignedUpload, StorageObject
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]

# CI 中没有 deploy/.env；测试必须自带可用的密钥与默认值，
# 不能依赖开发机的本地配置。
TEST_SSO_SECRET = "test-sso-secret-0123456789abcdef012345"
TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef012345"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "app_name", "FeedLog")
    monkeypatch.setattr(settings, "sso_secrets", [TEST_SSO_SECRET])
    monkeypatch.setattr(settings, "session_jwt_secret", TEST_SESSION_SECRET)
    monkeypatch.setattr(settings, "admin_emails", "")
    monkeypatch.setattr(settings, "sso_return_to_default", "/")
    monkeypatch.setattr(settings, "rate_limit_enabled", True)


def alembic_config(db_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def sqlite_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def sqlite_timestamp(value: datetime) -> str:
    """与 SQLite DATETIME 存储格式一致（naive UTC）。"""
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """迁移到 head 的空库（同步执行，便于同步夹具复用）。"""
    path = tmp_path / "test.db"
    command.upgrade(alembic_config(sqlite_url(path)), "head")
    return path


@pytest.fixture
def sqlite_conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
async def client(db_path: Path) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(sqlite_url(db_path))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_storage_backend] = lambda: FakeStorage()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


class FakeStorage:
    """测试用存储：不访问 RustFS，只返回可断言的假 URL。"""

    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.objects: dict[str, bytes] = {}

    def presign_put(self, *, object_key: str, content_type: str) -> PresignedUpload:
        return PresignedUpload(
            object_key=object_key,
            upload_url=f"http://storage.test/{object_key}?signature=fake",
            expires_in=600,
            headers={"Content-Type": content_type},
        )

    def delete_object(self, object_key: str) -> None:
        self.deleted.append(object_key)

    def open_object(self, object_key: str) -> StorageObject:
        from io import BytesIO

        if object_key not in self.objects:
            raise FileNotFoundError(object_key)
        data = self.objects[object_key]
        return StorageObject(
            body=BytesIO(data),
            content_type="application/octet-stream",
            content_length=len(data),
        )


# --------------------------------------------------------------------------- #
# 数据构造
# --------------------------------------------------------------------------- #


def insert_board(
    conn: sqlite3.Connection,
    *,
    slug: str = "product",
    name: str = "功能建议",
    is_public: bool = True,
    allow_guest_posting: bool = True,
    allow_guest_voting: bool = True,
) -> int:
    cursor = conn.execute(
        "INSERT INTO boards (slug, name, description, is_public,"
        " allow_guest_posting, allow_guest_voting)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            slug,
            name,
            None,
            1 if is_public else 0,
            1 if allow_guest_posting else 0,
            1 if allow_guest_voting else 0,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def insert_user(
    conn: sqlite3.Connection,
    *,
    email: str,
    display_name: str | None = None,
    role: str = "user",
) -> int:
    cursor = conn.execute(
        "INSERT INTO users (email, display_name, role) VALUES (?, ?, ?)",
        (email, display_name, role),
    )
    conn.commit()
    return int(cursor.lastrowid)


def insert_post(
    conn: sqlite3.Connection,
    *,
    board_id: int,
    title: str,
    created_at: datetime,
    content: dict | None = None,
    excerpt: str = "",
    status: str = "open",
    author_id: int | None = None,
    vote_count: int = 0,
    comment_count: int = 0,
) -> str:
    import json
    import uuid

    post_id = uuid.uuid4()
    stamp = sqlite_timestamp(created_at)
    conn.execute(
        "INSERT INTO posts (id, board_id, title, content, excerpt, status,"
        " author_id, vote_count, comment_count, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            post_id.hex,
            board_id,
            title,
            json.dumps(content or {"type": "doc", "content": []}),
            excerpt,
            status,
            author_id,
            vote_count,
            comment_count,
            stamp,
            stamp,
        ),
    )
    conn.commit()
    return post_id.hex


def insert_upload(
    conn: sqlite3.Connection,
    *,
    object_key: str,
    created_at: datetime,
    identity: str = "anon:test",
    purpose: str = "post_image",
    content_type: str = "image/png",
    size: int = 1024,
) -> None:
    conn.execute(
        "INSERT INTO uploads (object_key, identity, purpose, content_type, size,"
        " created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            object_key,
            identity,
            purpose,
            content_type,
            size,
            sqlite_timestamp(created_at),
        ),
    )
    conn.commit()


def insert_changelog(
    conn: sqlite3.Connection,
    *,
    title: str,
    created_at: datetime,
    published: bool = True,
    content: dict | None = None,
) -> str:
    import json
    import uuid

    entry_id = uuid.uuid4()
    stamp = sqlite_timestamp(created_at)
    conn.execute(
        "INSERT INTO changelog_entries (id, title, content, excerpt, is_published,"
        " published_at, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            entry_id.hex,
            title,
            json.dumps(content or {"type": "doc", "content": []}),
            "",
            1 if published else 0,
            stamp if published else None,
            stamp,
            stamp,
        ),
    )
    conn.commit()
    return entry_id.hex
