"""管理员任务面板：列出被 @ 的反馈与其任务进度（只读）。"""

from __future__ import annotations

from app.core.pagination import decode_cursor, encode_cursor
from app.repositories.post_mentions import PostMentionRepository
from app.schemas.admin_task import AdminTaskItem, TaskState
from app.schemas.common import Page


class AdminTaskService:
    def __init__(self, mentions: PostMentionRepository) -> None:
        self.mentions = mentions

    async def list_page(
        self,
        *,
        user_id: int,
        limit: int,
        cursor_raw: str | None = None,
        task_state: TaskState | None = None,
        board_slug: str | None = None,
    ) -> Page[AdminTaskItem]:
        cursor = decode_cursor(cursor_raw)
        rows = await self.mentions.list_for_user(
            user_id,
            limit=limit + 1,
            task_state=task_state,
            board_slug=board_slug,
            cursor=cursor,
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            encode_cursor(rows[-1][0].created_at, rows[-1][0].id)
            if has_more and rows
            else None
        )
        return Page(
            items=[
                AdminTaskItem(
                    post_id=post.id,
                    title=post.title,
                    board_slug=slug,
                    board_name=name,
                    status=post.status,
                    mentioned_at=mentioned_at,
                    task_state=(
                        "pending"
                        if task is None
                        else ("active" if task.completed_at is None else "done")
                    ),
                    assignee_name=task.assignee_name if task is not None else None,
                    accepted_at=task.accepted_at if task is not None else None,
                    completed_at=task.completed_at if task is not None else None,
                )
                for post, slug, name, task, mentioned_at in rows
            ],
            next_cursor=next_cursor,
        )
