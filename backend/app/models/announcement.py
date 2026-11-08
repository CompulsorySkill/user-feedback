"""公告：仅管理员可写；全局最多一篇置顶，作者按发布时快照记录。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, String, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Announcement(TimestampMixin, Base):
    __tablename__ = "announcements"
    __table_args__ = (
        Index("ix_announcements_published", "is_published", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    excerpt: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 公告作者是撰写 / 发布它的管理员；存快照，作者改名或账号删除后仍可展示。
    author_name: Mapped[str | None] = mapped_column(String(320), nullable=True)
