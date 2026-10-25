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


class ChangelogAttachmentInput(BaseModel):
    object_key: str = Field(min_length=1, max_length=255, pattern=r"^uploads/")
    filename: str = Field(min_length=1, max_length=255)


class ChangelogAttachment(BaseModel):
    id: int
    # 编辑需要 object_key；公开响应中不暴露，避免绕过下载接口直连存储。
    object_key: str | None = None
    filename: str
    content_type: str
    size: int
    download_url: str


class ChangelogDetail(ChangelogSummary):
    content: dict[str, Any]
    attachments: list[ChangelogAttachment] = Field(default_factory=list)


class ChangelogCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: dict[str, Any]
    attachments: list[ChangelogAttachmentInput] = Field(
        default_factory=list, max_length=10
    )

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
    attachments: list[ChangelogAttachmentInput] | None = Field(
        default=None, max_length=10
    )

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title
