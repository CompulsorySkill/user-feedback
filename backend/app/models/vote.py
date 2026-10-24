"""投票：登录与匿名双路径，各用一条部分唯一索引去重。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        # 部分唯一索引：SQLite 与 Postgres 语义一致，由 Alembic 显式渲染。
        Index(
            "uq_votes_post_user",
            "post_id",
            "user_id",
            unique=True,
            sqlite_where=text("user_id IS NOT NULL"),
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uq_votes_post_anonymous",
            "post_id",
            "anonymous_token",
            unique=True,
            sqlite_where=text("anonymous_token IS NOT NULL"),
            postgresql_where=text("anonymous_token IS NOT NULL"),
        ),
        Index("ix_votes_post_id", "post_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    anonymous_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
