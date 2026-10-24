"""审计日志：写入管理操作，并提供管理员查询。"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User
from app.repositories.audit import AuditRepository
from app.schemas.audit import AuditLogItem
from app.schemas.common import Page

logger = logging.getLogger(__name__)

MAX_ACTION_LENGTH = 64


def request_ip(request: Any | None) -> str | None:
    """取反向代理后的客户端地址；Caddy/Uvicorn 已处理 X-Forwarded-For。"""
    if request is None:
        return None
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return str(host)[:64] if host else None


class AuditService:
    def __init__(self, session: AsyncSession, audit: AuditRepository) -> None:
        self.session = session
        self.audit = audit

    async def record(
        self,
        *,
        action: str,
        actor: User | None = None,
        target_type: str | None = None,
        target_id: str | int | None = None,
        detail: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> None:
        """追加一条审计记录。

        业务操作已经提交；审计失败只记日志，不回滚、不影响主流程。
        """
        entry = AuditLog(
            actor_id=actor.id if actor is not None else None,
            actor_email=actor.email if actor is not None else None,
            action=action[:MAX_ACTION_LENGTH],
            target_type=target_type,
            target_id=str(target_id)[:64] if target_id is not None else None,
            detail=detail,
            ip=ip,
        )
        try:
            self.audit.add(entry)
            await self.session.commit()
        except Exception:  # noqa: BLE001 - 审计不可拖垮主流程
            await self.session.rollback()
            logger.exception("写入审计日志失败: action=%s", action)

    async def record_system(
        self, *, action: str, detail: dict[str, Any] | None = None
    ) -> None:
        await self.record(action=action, detail=detail)

    async def list_page(
        self,
        *,
        limit: int,
        before_id: int | None = None,
        action: str | None = None,
    ) -> Page[AuditLogItem]:
        rows = await self.audit.list_page(
            limit=limit + 1, before_id=before_id, action=action
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = str(rows[-1].id) if has_more and rows else None
        return Page(
            items=[
                AuditLogItem(
                    id=row.id,
                    actor_email=row.actor_email,
                    action=row.action,
                    target_type=row.target_type,
                    target_id=row.target_id,
                    detail=row.detail,
                    ip=row.ip,
                    created_at=row.created_at,
                )
                for row in rows
            ],
            next_cursor=next_cursor,
        )
