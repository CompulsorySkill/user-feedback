"""反馈提及投影：正文与评论里被 @ 的用户，(post, user) 唯一。

读路径（管理员任务页、任务权限）只查这张表，不再每次解析富文本 JSON。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PostMention(Base):
    __tablename__ = "post_mentions"
    __table_args__ = (Index("ix_post_mentions_user_post", "user_id", "post_id"),)

    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
