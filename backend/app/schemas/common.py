"""通用响应模式：UTC 时间序列化与分页包装。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, field_serializer

T = TypeVar("T")


def to_utc(value: datetime | None) -> datetime | None:
    """SQLite 存 naive UTC，出参统一补上 UTC 时区，避免前端按本地时间解析。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UTCModel(BaseModel):
    @field_serializer("created_at", "updated_at", "published_at", check_fields=False)
    def _serialize_datetimes(self, value: datetime | None) -> str | None:
        utc_value = to_utc(value)
        return utc_value.isoformat() if utc_value is not None else None


class Page(BaseModel, Generic[T]):
    """keyset 分页响应：``next_cursor`` 为 null 表示没有更多。"""

    items: list[T]
    next_cursor: str | None = None
