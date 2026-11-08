"""公告附件：与更新日志附件相同，任意类型文件仅管理员可上传，下载强制 attachment。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnnouncementAttachment(Base):
    __tablename__ = "announcement_attachments"
    __table_args__ = (
        Index("ix_announcement_attachments_announcement_id", "announcement_id"),
        UniqueConstraint(
            "announcement_id",
            "object_key",
            name="uq_announcement_attachments_announcement_object",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    announcement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(
        ForeignKey("uploads.object_key", ondelete="RESTRICT"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
