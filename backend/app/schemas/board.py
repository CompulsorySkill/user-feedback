"""看板读路径响应模式与管理员写请求。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UTCModel

SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])$"


class BoardSummary(UTCModel):
    id: int
    slug: str
    name: str
    description: str | None
    is_public: bool
    allow_guest_posting: bool
    allow_guest_voting: bool
    allow_guest_commenting: bool
    post_count: int
    created_at: datetime


class BoardRef(BaseModel):
    id: int
    slug: str
    name: str


class BoardCreateRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    is_public: bool = True
    allow_guest_posting: bool = True
    allow_guest_voting: bool = True
    allow_guest_commenting: bool = True

    @field_validator("slug", mode="before")
    @classmethod
    def _normalize_slug(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("看板名称不能为空")
        return name

    @field_validator("description")
    @classmethod
    def _strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        description = value.strip()
        return description or None


class BoardUpdateRequest(BaseModel):
    slug: str | None = Field(
        default=None, min_length=2, max_length=64, pattern=SLUG_PATTERN
    )
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    is_public: bool | None = None
    allow_guest_posting: bool | None = None
    allow_guest_voting: bool | None = None
    allow_guest_commenting: bool | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def _normalize_slug(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name:
            raise ValueError("看板名称不能为空")
        return name

    @field_validator("description")
    @classmethod
    def _strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        description = value.strip()
        return description or None
