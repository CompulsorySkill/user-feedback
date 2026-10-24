"""更新日志读路径响应模式。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import UTCModel


class ChangelogSummary(UTCModel):
    id: uuid.UUID
    title: str
    excerpt: str
    published_at: datetime | None
    created_at: datetime


class ChangelogDetail(ChangelogSummary):
    content: dict[str, Any]
