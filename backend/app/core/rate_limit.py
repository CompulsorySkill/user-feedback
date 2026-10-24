"""限流：数据库计数表 + 固定窗口 UPSERT（无 Redis）。

窗口按 Unix 时间戳取整，SQLite 与 Postgres 共用同一套 SQL；
多 worker 下依赖主键冲突保证计数正确。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppException
from app.models import RateLimitCounter

# action -> (窗口秒数, 上限)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "vote": (60, 20),
    "post": (600, 5),
    "comment": (60, 10),
}


def _window_start(window_seconds: int) -> datetime:
    now = datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(
        epoch - epoch % window_seconds, tz=timezone.utc
    ).replace(tzinfo=None)


async def enforce_rate_limit(
    session: AsyncSession, *, identity_key: str, action: str
) -> None:
    if not settings.rate_limit_enabled:
        return

    window_seconds, limit = RATE_LIMITS[action]
    window_start = _window_start(window_seconds)

    insert = (
        postgresql_insert
        if session.bind is not None and session.bind.dialect.name == "postgresql"
        else sqlite_insert
    )
    stmt = (
        insert(RateLimitCounter)
        .values(
            identity_key=identity_key,
            action=action,
            window_start=window_start,
            count=1,
        )
        .on_conflict_do_update(
            index_elements=[
                RateLimitCounter.identity_key,
                RateLimitCounter.action,
                RateLimitCounter.window_start,
            ],
            # 显式限定目标表，避免 Postgres 把 count 解析到 excluded 上而报 ambiguous。
            set_={"count": RateLimitCounter.__table__.c.count + 1},
        )
        .returning(RateLimitCounter.count)
    )

    count = await session.scalar(stmt)
    if count is not None and count > limit:
        raise AppException(
            429,
            code="RATE_LIMITED",
            detail=f"操作过于频繁，请 {window_seconds // 60 or 1} 分钟后再试",
        )


async def cleanup_rate_limit_counters(session: AsyncSession) -> int:
    """清理 1 小时前的窗口，防止计数表膨胀。"""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    result = await session.execute(
        delete(RateLimitCounter).where(RateLimitCounter.window_start < cutoff)
    )
    await session.commit()
    return int(result.rowcount or 0)
