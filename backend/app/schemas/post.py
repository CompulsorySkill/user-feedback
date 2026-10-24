"""反馈帖读路径响应模式。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

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
