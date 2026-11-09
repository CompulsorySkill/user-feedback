"""管理员任务面板：只看「@ 了我」的反馈及其任务状态。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import field_serializer

from app.schemas.common import UTCModel, to_utc
from app.schemas.post import PostStatus

TaskState = Literal["pending", "active", "done"]


class AdminTaskItem(UTCModel):
    post_id: uuid.UUID
    title: str
    board_slug: str
    board_name: str
    status: PostStatus
    mentioned_at: datetime
    task_state: TaskState
    assignee_name: str | None = None
    accepted_at: datetime | None = None
    completed_at: datetime | None = None

    # UTCModel 只覆盖 created_at/updated_at/published_at，这几个单独补时区。
    @field_serializer("mentioned_at", "accepted_at", "completed_at")
    def _serialize_utc(self, value: datetime | None) -> str | None:
        utc_value = to_utc(value)
        return utc_value.isoformat() if utc_value is not None else None
