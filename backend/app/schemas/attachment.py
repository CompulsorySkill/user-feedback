"""共享附件输入模式：更新日志与公告附件字段一致。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AttachmentInput(BaseModel):
    object_key: str = Field(min_length=1, max_length=255, pattern=r"^uploads/")
    filename: str = Field(min_length=1, max_length=255)
