"""上传记录：presign 时落库，供保存富文本时校验归属。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Upload(Base):
    __tablename__ = "uploads"
    __table_args__ = (Index("ix_uploads_identity", "identity"),)

    object_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    identity: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
