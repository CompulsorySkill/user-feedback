"""更新日志请求 / 响应模式。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UTCModel


class ChangelogSummary(UTCModel):
    id: uuid.UUID
    title: str
    excerpt: str
    is_published: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChangelogDetail(ChangelogSummary):
    content: dict[str, Any]


class ChangelogCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: dict[str, Any]

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title


class ChangelogUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: dict[str, Any] | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title
