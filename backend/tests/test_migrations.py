"""Alembic 初始迁移的 schema 契约测试。"""

from __future__ import annotations

import sqlite3
import uuid

import pytest
from alembic import command

from tests.conftest import alembic_config, sqlite_url

EXPECTED_TABLES = {
    "boards",
    "changelog_entries",
    "comments",
    "posts",
    "post_tags",
    "rate_limit_counters",
    "tags",
    "uploads",
    "users",
    "votes",
}


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in rows} - {"alembic_version", "sqlite_sequence"}


def _index_sql(conn: sqlite3.Connection, name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone()
    assert row is not None, f"index {name} missing"
    return row[0]


def _insert_board(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO boards (slug, name) VALUES ('general', 'General')")


def _insert_post(conn: sqlite3.Connection) -> str:
    post_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO posts (id, board_id, title, content) VALUES (?, 1, 'hello', '{}')",
        (post_id,),
    )
    return post_id


def test_upgrade_creates_all_tables(sqlite_conn: sqlite3.Connection) -> None:
    assert _tables(sqlite_conn) == EXPECTED_TABLES

    version = sqlite_conn.execute("SELECT version_num FROM alembic_version").fetchone()
    assert version == ("0003_tags",)


def test_vote_partial_unique_indexes(sqlite_conn: sqlite3.Connection) -> None:
    user_index = _index_sql(sqlite_conn, "uq_votes_post_user")
    anonymous_index = _index_sql(sqlite_conn, "uq_votes_post_anonymous")

    assert "UNIQUE" in user_index.upper()
    assert "WHERE user_id IS NOT NULL" in user_index
    assert "WHERE anonymous_token IS NOT NULL" in anonymous_index


def test_vote_duplicate_login_rejected(sqlite_conn: sqlite3.Connection) -> None:
    _insert_board(sqlite_conn)
    post_id = _insert_post(sqlite_conn)
    sqlite_conn.execute("INSERT INTO users (email) VALUES ('alice@example.com')")
    sqlite_conn.execute(
        "INSERT INTO votes (post_id, user_id) VALUES (?, 1)", (post_id,)
    )

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_conn.execute(
            "INSERT INTO votes (post_id, user_id) VALUES (?, 1)", (post_id,)
        )

    # 同一用户不同 Post 可以投票。
    second_post = _insert_post(sqlite_conn)
    sqlite_conn.execute(
        "INSERT INTO votes (post_id, user_id) VALUES (?, 1)", (second_post,)
    )


def test_vote_duplicate_anonymous_rejected(sqlite_conn: sqlite3.Connection) -> None:
    _insert_board(sqlite_conn)
    post_id = _insert_post(sqlite_conn)
    sqlite_conn.execute(
        "INSERT INTO votes (post_id, anonymous_token) VALUES (?, 'anon-1')", (post_id,)
    )

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_conn.execute(
            "INSERT INTO votes (post_id, anonymous_token) VALUES (?, 'anon-1')",
            (post_id,),
        )


def test_vote_allows_multiple_null_rows(sqlite_conn: sqlite3.Connection) -> None:
    """NULL 不参与部分唯一索引，避免匿名票互相覆盖。"""
    _insert_board(sqlite_conn)
    post_id = _insert_post(sqlite_conn)
    for token in ("anon-1", "anon-2", "anon-3"):
        sqlite_conn.execute(
            "INSERT INTO votes (post_id, anonymous_token) VALUES (?, ?)",
            (post_id, token),
        )


def test_post_status_check_constraint(sqlite_conn: sqlite3.Connection) -> None:
    _insert_board(sqlite_conn)
    post_id = _insert_post(sqlite_conn)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_conn.execute("UPDATE posts SET status='done' WHERE id=?", (post_id,))


def test_downgrade_removes_schema(tmp_path) -> None:
    db_path = tmp_path / "downgrade.db"
    config = alembic_config(f"sqlite+aiosqlite:///{db_path.as_posix()}")

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    conn = sqlite3.connect(db_path)
    try:
        assert _tables(conn) == set()
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        assert version is None
    finally:
        conn.close()


def test_created_at_server_default_present(sqlite_conn: sqlite3.Connection) -> None:
    _insert_board(sqlite_conn)
    created_at = sqlite_conn.execute("SELECT created_at FROM boards").fetchone()[0]
    assert created_at is not None
