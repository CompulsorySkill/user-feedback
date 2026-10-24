"""反馈帖：富文本 JSON 为真相源，vote/comment 计数同事务维护。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

POST_STATUSES = ("open", "planned", "in_progress", "completed", "closed")


class Post(TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'planned', 'in_progress', 'completed', 'closed')",
            name="status",
        ),
        # keyset 分页 (board_id, created_at DESC, id DESC)：升序索引可反向扫描。
        Index("ix_posts_board_keyset", "board_id", "created_at", "id"),
        Index("ix_posts_status", "status"),
        Index("ix_posts_author_id", "author_id"),
        Index("ix_posts_anonymous_token", "anonymous_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    board_id: Mapped[int] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    excerpt: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open"
    )

    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    anonymous_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 匿名发布时允许自填昵称；展示侧必须同时标注「匿名」。
    anonymous_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 用户主动勾选时保存的浏览器 / 操作系统环境信息。
    client_env: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    vote_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    comment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
