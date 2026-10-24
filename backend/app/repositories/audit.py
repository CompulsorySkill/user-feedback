"""审计日志数据访问：按 id 倒序 keyset 分页。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, entry: AuditLog) -> None:
        self.session.add(entry)

    async def list_page(
        self,
        *,
        limit: int,
        before_id: int | None = None,
        action: str | None = None,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.id.desc())
        if before_id is not None:
            stmt = stmt.where(AuditLog.id < before_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.limit(limit)
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all())
