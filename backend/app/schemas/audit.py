"""审计日志读写模式。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import UTCModel


class AuditLogItem(UTCModel):
    id: int
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: dict[str, Any] | None
    ip: str | None
    created_at: datetime


class UploadCleanupResult(BaseModel):
    dry_run: bool
    grace_hours: int
    scanned: int
    referenced: int
    deleted: int
    failed: int
    errors: list[str] = Field(default_factory=list)
