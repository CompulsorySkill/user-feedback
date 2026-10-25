"""未引用上传对象清理。

presign 会先写 ``uploads`` 记录，真正上传的 object key 只有在反馈 / 更新日志
富文本或 ``changelog_attachments`` 里出现才算被引用。这里清理超过保留期仍未被引用的记录与 RustFS 对象，
同时覆盖「presign 后从未上传」和「编辑内容后移除媒体」两种情况。

注意：只删除数据库中有 presign 记录的对象，不做 bucket 全量扫描，避免误删
运维手动放入 bucket 的文件。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import Text, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import StorageBackend
from app.models import ChangelogAttachment, ChangelogEntry, Post, Upload
from app.schemas.audit import UploadCleanupResult

MAX_BATCH = 200
MAX_SCAN = 5000
MAX_ERRORS = 20


class UploadCleanupService:
    def __init__(self, session: AsyncSession, storage: StorageBackend) -> None:
        self.session = session
        self.storage = storage

    async def _referenced_keys(self, keys: list[str]) -> set[str]:
        if not keys:
            return set()
        patterns = [f"%{key}%" for key in keys]
        referenced: set[str] = set()
        for model in (Post, ChangelogEntry):
            content = cast(model.content, Text)
            stmt = select(content).where(or_(*(content.like(p) for p in patterns)))
            rows = await self.session.execute(stmt)
            for (text,) in rows.all():
                if not text:
                    continue
                for key in keys:
                    if key in text:
                        referenced.add(key)

        # 更新日志附件不在 content JSON 中，必须单独计入引用。
        attachment_rows = await self.session.execute(
            select(ChangelogAttachment.object_key).where(
                ChangelogAttachment.object_key.in_(keys)
            )
        )
        referenced.update(attachment_rows.scalars().all())
        return referenced

    async def run(
        self,
        *,
        grace_hours: int | None = None,
        dry_run: bool = False,
        limit: int = MAX_BATCH,
    ) -> UploadCleanupResult:
        grace_hours = (
            settings.upload_cleanup_grace_hours if grace_hours is None else grace_hours
        )
        grace_hours = max(1, min(grace_hours, 24 * 30))
        limit = max(1, min(limit, 1000))
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            hours=grace_hours
        )

        scanned = 0
        referenced_count = 0
        deleted = 0
        failed = 0
        errors: list[str] = []
        last_key: str | None = None

        # 已引用的旧记录可能很多；按 object_key keyset 继续向后扫描，
        # 避免最早一批全部被引用时永远看不到后面的孤儿对象。
        while scanned < MAX_SCAN and deleted < limit:
            stmt = (
                select(Upload)
                .where(Upload.created_at < cutoff)
                .order_by(Upload.object_key.asc())
                .limit(MAX_BATCH)
            )
            if last_key is not None:
                stmt = stmt.where(Upload.object_key > last_key)
            uploads = list((await self.session.execute(stmt)).scalars().all())
            if not uploads:
                break
            last_key = uploads[-1].object_key
            keys = [upload.object_key for upload in uploads]
            referenced = await self._referenced_keys(keys)
            scanned += len(uploads)
            referenced_count += sum(1 for key in keys if key in referenced)

            for upload in uploads:
                if upload.object_key in referenced:
                    continue
                if deleted >= limit:
                    break
                if dry_run:
                    deleted += 1
                    continue
                try:
                    await asyncio.to_thread(
                        self.storage.delete_object, upload.object_key
                    )
                except Exception as exc:  # noqa: BLE001 - 单个对象失败不阻断批次
                    failed += 1
                    if len(errors) < MAX_ERRORS:
                        errors.append(f"{upload.object_key}: {exc}")
                    continue
                await self.session.delete(upload)
                deleted += 1

            if len(uploads) < MAX_BATCH:
                break

        if deleted and not dry_run:
            await self.session.commit()

        return UploadCleanupResult(
            dry_run=dry_run,
            grace_hours=grace_hours,
            scanned=scanned,
            referenced=referenced_count,
            deleted=deleted,
            failed=failed,
            errors=errors,
        )
