"""反馈时间线与任务数据访问。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PostTask, PostTimelineEvent


class PostTimelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_events(self, post_id: uuid.UUID) -> list[PostTimelineEvent]:
        rows = await self.session.execute(
            select(PostTimelineEvent)
            .where(PostTimelineEvent.post_id == post_id)
            .order_by(PostTimelineEvent.created_at.asc(), PostTimelineEvent.id.asc())
        )
        return list(rows.scalars().all())

    async def get_task(self, post_id: uuid.UUID) -> PostTask | None:
        return await self.session.scalar(
            select(PostTask).where(PostTask.post_id == post_id)
        )

    def add_event(
        self,
        *,
        post_id: uuid.UUID,
        event_type: str,
        actor_name: str | None,
        actor_id: int | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        created_at: datetime | None = None,
    ) -> PostTimelineEvent:
        event = PostTimelineEvent(
            post_id=post_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_name=actor_name,
            from_status=from_status,
            to_status=to_status,
            **({"created_at": created_at} if created_at is not None else {}),
        )
        self.session.add(event)
        return event

    def add_task(
        self,
        *,
        post_id: uuid.UUID,
        assignee_id: int | None,
        assignee_name: str,
        accepted_at: datetime,
    ) -> PostTask:
        task = PostTask(
            post_id=post_id,
            assignee_id=assignee_id,
            assignee_name=assignee_name,
            accepted_at=accepted_at,
        )
        self.session.add(task)
        return task
