"""看板读路径响应模式。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import UTCModel


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
