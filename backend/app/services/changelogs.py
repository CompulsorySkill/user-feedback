"""更新日志读路径业务规则：非管理员仅见已发布。"""

from __future__ import annotations

import uuid

from app.core.errors import AppException
from app.core.pagination import decode_cursor, encode_cursor
from app.repositories.changelogs import ChangelogRepository
from app.schemas.changelog import ChangelogDetail, ChangelogSummary
from app.schemas.common import Page


def _summary(entry) -> ChangelogSummary:
    return ChangelogSummary(
        id=entry.id,
        title=entry.title,
        excerpt=entry.excerpt,
        published_at=entry.published_at,
        created_at=entry.created_at,
    )


class ChangelogService:
    def __init__(self, changelogs: ChangelogRepository) -> None:
        self.changelogs = changelogs

    async def list_entries(
        self,
        *,
        limit: int,
        cursor_raw: str | None,
        include_drafts: bool = False,
        viewer_is_admin: bool = False,
    ) -> Page[ChangelogSummary]:
        # P1 尚无鉴权：viewer_is_admin 恒为 False，草稿对任何请求都不可见。
        effective_include_drafts = include_drafts and viewer_is_admin
        cursor = decode_cursor(cursor_raw)
        entries = await self.changelogs.list_entries(
            limit=limit + 1, cursor=cursor, include_drafts=effective_include_drafts
        )
        has_more = len(entries) > limit
        entries = entries[:limit]

        next_cursor = (
            encode_cursor(entries[-1].created_at, entries[-1].id)
            if has_more and entries
            else None
        )
        return Page(
            items=[_summary(entry) for entry in entries], next_cursor=next_cursor
        )

    async def get(
        self, changelog_id: uuid.UUID, *, viewer_is_admin: bool = False
    ) -> ChangelogDetail:
        entry = await self.changelogs.get(
            changelog_id, include_drafts=viewer_is_admin
        )
        if entry is None:
            raise AppException(404, code="CHANGELOG_NOT_FOUND", detail="更新日志不存在")

        return ChangelogDetail(
            **_summary(entry).model_dump(), content=entry.content
        )
