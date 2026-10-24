"""清理未引用的上传对象。

用法（backend/ 下）::

    uv run python -m scripts.cleanup_uploads --dry-run
    uv run python -m scripts.cleanup_uploads
    uv run python -m scripts.cleanup_uploads --grace-hours 72 --limit 500

建议由 cron / 定时任务每日执行一次；生产环境可用::

    docker compose exec -T backend python -m scripts.cleanup_uploads

只处理 ``uploads`` 表中超过保留期且未被反馈 / 更新日志引用的记录与对象。
"""

from __future__ import annotations

import argparse
import asyncio
import json

from app.core.db import SessionLocal, engine
from app.core.storage import get_storage
from app.repositories.audit import AuditRepository
from app.services.audit import AuditService
from app.services.upload_cleanup import UploadCleanupService


async def run(*, grace_hours: int | None, dry_run: bool, limit: int) -> None:
    storage = get_storage()
    async with SessionLocal() as session:
        service = UploadCleanupService(session, storage)
        result = await service.run(
            grace_hours=grace_hours, dry_run=dry_run, limit=limit
        )
        if not dry_run:
            audit = AuditService(session, AuditRepository(session))
            await audit.record_system(
                action="upload.cleanup",
                detail={**result.model_dump(), "source": "cli"},
            )
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="清理未引用的上传对象")
    parser.add_argument(
        "--grace-hours",
        type=int,
        default=None,
        help="只清理创建超过该小时数且未被引用的对象（1–720，默认读 UPLOAD_CLEANUP_GRACE_HOURS）",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="只统计，不删除 RustFS 对象与数据库记录"
    )
    parser.add_argument(
        "--limit", type=int, default=200, help="单次最多删除的记录数（默认 200）"
    )
    args = parser.parse_args()

    async def _main() -> None:
        try:
            await run(
                grace_hours=args.grace_hours,
                dry_run=args.dry_run,
                limit=args.limit,
            )
        finally:
            await engine.dispose()

    asyncio.run(_main())


if __name__ == "__main__":
    main()
