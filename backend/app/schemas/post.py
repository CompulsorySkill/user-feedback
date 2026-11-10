"""反馈帖读路径响应模式与创建请求。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.board import BoardRef
from app.schemas.common import UTCModel
from app.schemas.tag import TagRef

PostStatus = Literal["open", "planned", "in_progress", "completed", "closed"]
PostTimelineEventType = Literal[
    "created", "status_changed", "task_accepted", "task_completed"
]


class ClientEnvironment(BaseModel):
    """前端采集的浏览器 / 操作系统环境，字段与长度均受约束。"""

    user_agent: str | None = Field(default=None, max_length=512)
    platform: str | None = Field(default=None, max_length=128)
    language: str | None = Field(default=None, max_length=64)
    viewport: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)

    model_config = {"extra": "ignore"}


class PostSummary(UTCModel):
    id: uuid.UUID
    board_slug: str
    board_name: str
    title: str
    excerpt: str
    status: PostStatus
    vote_count: int
    comment_count: int
    author_name: str | None
    anonymous_name: str | None
    is_anonymous: bool
    created_at: datetime
    updated_at: datetime
    tags: list[TagRef] = Field(default_factory=list)


class PostTimelineEvent(UTCModel):
    id: int
    event_type: PostTimelineEventType
    from_status: PostStatus | None
    to_status: PostStatus | None
    actor_name: str | None
    created_at: datetime


class PostTaskInfo(UTCModel):
    assignee_id: int | None
    assignee_name: str
    accepted_at: datetime
    completed_at: datetime | None


class PostNeighbor(UTCModel):
    """同看板的前 / 后一条反馈；详情页侧栏用。"""

    id: uuid.UUID
    title: str
    created_at: datetime


class PostReference(BaseModel):
    """正文中引用（postRef 节点）的其他反馈，渲染在正文末尾。"""

    id: uuid.UUID
    title: str


class PostDetail(PostSummary):
    board: BoardRef
    content: dict[str, Any]
    environment: ClientEnvironment | None = None
    is_author: bool = False
    timeline: list[PostTimelineEvent] = Field(default_factory=list)
    task: PostTaskInfo | None = None
    can_accept_task: bool = False
    can_complete_task: bool = False
    previous: list[PostNeighbor] = Field(default_factory=list)
    next: list[PostNeighbor] = Field(default_factory=list)
    references: list[PostReference] = Field(default_factory=list)


class AuthorFacet(BaseModel):
    """筛选器用的作者候选：登录作者显示名或匿名昵称。"""

    name: str
    post_count: int


class PostCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: dict[str, Any]
    anonymous_name: str | None = Field(default=None, max_length=50)
    environment: ClientEnvironment | None = None
    tags: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title

    @field_validator("anonymous_name")
    @classmethod
    def _normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        return name or None


class PostStatusUpdate(BaseModel):
    status: PostStatus


class PostUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: dict[str, Any] | None = None
    tags: list[str] | None = Field(default=None, max_length=5)
    # 迁移所属看板；只能移到公开看板，None 表示不改。
    board_slug: str | None = Field(default=None, max_length=64)

    @field_validator("title")
    @classmethod
    def _strip_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title
