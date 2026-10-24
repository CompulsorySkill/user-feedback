"""更新日志：仅管理员可写；草稿 / 发布与 Post 状态独立。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, String, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ChangelogEntry(TimestampMixin, Base):
    __tablename__ = "changelog_entries"
    __table_args__ = (
        Index("ix_changelog_entries_published", "is_published", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    excerpt: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
