"""上传记录数据访问。"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Upload


class UploadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, upload: Upload) -> None:
        self.session.add(upload)

    async def list_for_identity(
        self, identity_key: str, object_keys: Sequence[str]
    ) -> list[Upload]:
        return await self.list_for_identities([identity_key], object_keys)

    async def list_for_identities(
        self, identity_keys: Sequence[str], object_keys: Sequence[str]
    ) -> list[Upload]:
        if not object_keys or not identity_keys:
            return []
        stmt = select(Upload).where(
            Upload.identity.in_(list(identity_keys)),
            Upload.object_key.in_(list(object_keys)),
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars().all())
