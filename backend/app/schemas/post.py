"""反馈帖读路径响应模式与创建请求。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.board import BoardRef
from app.schemas.common import UTCModel

PostStatus = Literal["open", "planned", "in_progress", "completed", "closed"]


class ClientEnvironment(BaseModel):
    """前端采集的浏览器 / 操作系统环境，字段与长度均受约束。"""

    user_agent: str | None = Field(default=None, max_length=512)
    platform: str | None = Field(default=None, max_length=128)
    language: str | None = Field(default=None, max_length=64)
    viewport: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)

    model_config = {"extra": "ignore"}


class PostSummary(UTCModel):
    id: uuid.UUID
    board_slug: str
    board_name: str
    title: str
    excerpt: str
    status: PostStatus
    vote_count: int
    comment_count: int
    author_name: str | None
    anonymous_name: str | None
    is_anonymous: bool
    created_at: datetime
    updated_at: datetime


class PostDetail(PostSummary):
    board: BoardRef
    content: dict[str, Any]
    environment: ClientEnvironment | None = None
    is_author: bool = False


class PostCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: dict[str, Any]
    anonymous_name: str | None = Field(default=None, max_length=50)
    environment: ClientEnvironment | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title

    @field_validator("anonymous_name")
    @classmethod
    def _normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        return name or None


class PostStatusUpdate(BaseModel):
    status: PostStatus


class PostUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: dict[str, Any] | None = None

    @field_validator("title")
    @classmethod
    def _strip_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title
