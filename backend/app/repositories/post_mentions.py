"""提及投影数据访问：(post, user) 去重，按反馈创建时间 keyset 分页。"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import Select, delete, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Cursor
from app.models import Board, Post, PostMention, PostTask

TaskState = str

# (反馈, 看板 slug, 看板名, 任务或 None, 首次被提及时间)
AdminTaskRow = tuple[Post, str, str, PostTask | None, datetime]


class PostMentionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_user_ids(self, post_id: uuid.UUID) -> set[int]:
        rows = await self.session.execute(
            select(PostMention.user_id).where(PostMention.post_id == post_id)
        )
        return set(rows.scalars().all())

    async def replace(self, post_id: uuid.UUID, user_ids: Iterable[int]) -> None:
        """按当前正文 + 评论重算：不再被提及的删掉，新出现的补上。"""
        wanted = set(user_ids)
        current = await self.list_user_ids(post_id)
        if stale := current - wanted:
            await self.session.execute(
                delete(PostMention).where(
                    PostMention.post_id == post_id,
                    PostMention.user_id.in_(stale),
                )
            )
        self.session.add_all(
            PostMention(post_id=post_id, user_id=user_id)
            for user_id in sorted(wanted - current)
        )

    async def add(self, post_id: uuid.UUID, user_ids: Iterable[int]) -> None:
        """新增提及（评论），已有记录保留原始提及时间。"""
        current = await self.list_user_ids(post_id)
        self.session.add_all(
            PostMention(post_id=post_id, user_id=user_id)
            for user_id in sorted(set(user_ids) - current)
        )

    def _for_user(self, user_id: int, board_slug: str | None) -> Select:
        stmt = (
            select(Post, Board.slug, Board.name, PostTask, PostMention.created_at)
            .join(PostMention, PostMention.post_id == Post.id)
            .join(Board, Board.id == Post.board_id)
            .outerjoin(PostTask, PostTask.post_id == Post.id)
            .where(PostMention.user_id == user_id)
        )
        if board_slug is not None:
            stmt = stmt.where(Board.slug == board_slug)
        return stmt

    async def list_for_user(
        self,
        user_id: int,
        *,
        limit: int,
        task_state: TaskState | None = None,
        board_slug: str | None = None,
        cursor: Cursor | None = None,
    ) -> list[AdminTaskRow]:
        stmt = self._for_user(user_id, board_slug)
        if task_state == "pending":
            stmt = stmt.where(PostTask.post_id.is_(None))
        elif task_state == "active":
            stmt = stmt.where(
                PostTask.post_id.is_not(None), PostTask.completed_at.is_(None)
            )
        elif task_state == "done":
            stmt = stmt.where(PostTask.completed_at.is_not(None))
        if cursor is not None:
            stmt = stmt.where(
                tuple_(Post.created_at, Post.id) < tuple_(cursor.created_at, cursor.id)
            )
        stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit)
        rows = await self.session.execute(stmt)
        return [
            (post, slug, name, task, mentioned_at)
            for post, slug, name, task, mentioned_at in rows.all()
        ]
