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

from app.core.db import get_session
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]


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
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# --------------------------------------------------------------------------- #
# 数据构造
# --------------------------------------------------------------------------- #


def insert_board(
    conn: sqlite3.Connection,
    *,
    slug: str = "product",
    name: str = "功能建议",
    is_public: bool = True,
) -> int:
    cursor = conn.execute(
        "INSERT INTO boards (slug, name, description, is_public) VALUES (?, ?, ?, ?)",
        (slug, name, None, 1 if is_public else 0),
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
