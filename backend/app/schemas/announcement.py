"""公告请求 / 响应模式。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.attachment import AttachmentInput
from app.schemas.common import UTCModel


class AnnouncementSummary(UTCModel):
    id: uuid.UUID
    title: str
    excerpt: str
    is_published: bool
    is_pinned: bool
    published_at: datetime | None
    author_name: str | None
    created_at: datetime
    updated_at: datetime


class AnnouncementAttachment(BaseModel):
    id: int
    # 编辑需要 object_key；公开响应中不暴露，避免绕过下载接口直连存储。
    object_key: str | None = None
    filename: str
    content_type: str
    size: int
    download_url: str


class AnnouncementDetail(AnnouncementSummary):
    content: dict[str, Any]
    attachments: list[AnnouncementAttachment] = Field(default_factory=list)


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: dict[str, Any]
    attachments: list[AttachmentInput] = Field(default_factory=list, max_length=10)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: dict[str, Any] | None = None
    attachments: list[AttachmentInput] | None = Field(default=None, max_length=10)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title
