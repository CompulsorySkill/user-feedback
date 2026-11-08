"""评论请求 / 响应模式。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import UTCModel


class CommentCreateRequest(BaseModel):
    content: dict[str, Any] = Field(description="Tiptap JSON 富文本")
    parent_id: uuid.UUID | None = None


class CommentItem(UTCModel):
    id: uuid.UUID
    post_id: uuid.UUID
    parent_id: uuid.UUID | None
    content: dict[str, Any]
    author_name: str | None
    is_anonymous: bool
    created_at: datetime


class CommentList(BaseModel):
    items: list[CommentItem]
    total: int
