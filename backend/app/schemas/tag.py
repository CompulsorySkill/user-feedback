"""标签读写模式。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TagRef(BaseModel):
    id: int
    name: str
    is_builtin: bool


class TagSummary(TagRef):
    post_count: int


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=24)

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        name = " ".join(value.strip().lstrip("#").split())
        return name

    @field_validator("name")
    @classmethod
    def _reject_control_chars(cls, value: str) -> str:
        if not value:
            raise ValueError("标签不能为空")
        if any(ord(char) < 32 for char in value):
            raise ValueError("标签不能包含控制字符")
        return value
