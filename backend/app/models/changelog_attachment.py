"""更新日志附件：管理员可上传任意类型文件，下载时强制 attachment。

附件引用 ``uploads.object_key``，文件本身仍由 RustFS 保存；清理任务必须把
附件表也算作引用，否则会误删仍被更新日志使用的文件。
"""

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


class ChangelogAttachment(Base):
    __tablename__ = "changelog_attachments"
    __table_args__ = (
        Index("ix_changelog_attachments_changelog_id", "changelog_id"),
        UniqueConstraint(
            "changelog_id",
            "object_key",
            name="uq_changelog_attachments_changelog_object",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    changelog_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("changelog_entries.id", ondelete="CASCADE"), nullable=False
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
