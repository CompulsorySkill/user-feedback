"""评论请求 / 响应模式。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UTCModel


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("评论不能为空")
        return content


class CommentItem(UTCModel):
    id: uuid.UUID
    post_id: uuid.UUID
    parent_id: uuid.UUID | None
    content: str
    author_name: str | None
    is_anonymous: bool
    created_at: datetime


class CommentList(BaseModel):
    items: list[CommentItem]
    total: int
