"""反馈帖读路径响应模式与创建请求。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.board import BoardRef
from app.schemas.common import UTCModel

PostStatus = Literal["open", "planned", "in_progress", "completed", "closed"]


class PostSummary(UTCModel):
    id: uuid.UUID
    board_slug: str
    title: str
    excerpt: str
    status: PostStatus
    vote_count: int
    comment_count: int
    author_name: str | None
    created_at: datetime
    updated_at: datetime


class PostDetail(PostSummary):
    board: BoardRef
    content: dict[str, Any]


class PostCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: dict[str, Any]

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title
