"""反馈提及投影表 post_mentions

- (post_id, user_id) 复合主键：同一篇反馈对同一个人只留一条，重复 @ 不叠加
- 回填历史数据：扫描 posts.content 与 comments.content 里的 mention 节点
- 之后由 MentionService 在发帖 / 编辑 / 评论 / 删评论时同步

Revision ID: 0011_post_mentions
Revises: 0010_post_timeline_tasks
Create Date: 2026-11-02 10:00:00.000000
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0011_post_mentions"
down_revision: str | None = "0010_post_timeline_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BACKFILL_CHUNK = 500


def _mentioned_ids(content: Any) -> set[int]:
    """迁移内自带解析：不依赖未来可能变动的业务代码。"""
    ids: set[int] = set()
    stack = [content]
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        if node.get("type") == "mention":
            attrs = node.get("attrs")
            raw = attrs.get("id") if isinstance(attrs, dict) else None
            try:
                ids.add(int(raw))
            except (TypeError, ValueError):
                pass
        children = node.get("content")
        if isinstance(children, list):
            stack.extend(children)
    return ids


def _load(raw: Any) -> Any:
    if isinstance(raw, (str, bytes)):
        try:
            return json.loads(raw)
        except ValueError:
            return None
    return raw


def _insert(bind: sa.Connection, table: sa.TableClause, pairs: Iterable) -> None:
    chunk: list[dict] = []
    for post_id, user_id in pairs:
        chunk.append({"post_id": post_id, "user_id": user_id})
        if len(chunk) >= BACKFILL_CHUNK:
            bind.execute(sa.insert(table), chunk)
            chunk = []
    if chunk:
        bind.execute(sa.insert(table), chunk)


def upgrade() -> None:
    op.create_table(
        "post_mentions",
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            name=op.f("fk_post_mentions_post_id_posts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_post_mentions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("post_id", "user_id", name=op.f("pk_post_mentions")),
    )
    op.create_index(
        "ix_post_mentions_user_post", "post_mentions", ["user_id", "post_id"]
    )

    bind = op.get_bind()
    table = sa.table(
        "post_mentions",
        sa.column("post_id", sa.Uuid()),
        sa.column("user_id", sa.Integer()),
    )
    users = {row[0] for row in bind.execute(sa.text("SELECT id FROM users"))}

    pairs: dict[tuple[uuid.UUID, int], None] = {}
    for post_id, content in bind.execute(sa.text("SELECT id, content FROM posts")):
        for user_id in _mentioned_ids(_load(content)):
            if user_id in users:
                pairs[(uuid.UUID(str(post_id)), user_id)] = None
    for post_id, content in bind.execute(
        sa.text("SELECT post_id, content FROM comments")
    ):
        for user_id in _mentioned_ids(_load(content)):
            if user_id in users:
                pairs[(uuid.UUID(str(post_id)), user_id)] = None
    _insert(bind, table, pairs)


def downgrade() -> None:
    op.drop_index("ix_post_mentions_user_post", table_name="post_mentions")
    op.drop_table("post_mentions")
