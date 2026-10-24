"""上传 presign 业务规则。"""

from __future__ import annotations

from app.core.config import settings
from app.core.errors import AppException
from app.core.identity import Identity
from app.core.storage import StorageBackend, build_object_key
from app.models import Upload
from app.schemas.upload import (
    PURPOSE_CONTENT_TYPES,
    UploadPresignRequest,
    UploadPresignResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession


class UploadService:
    def __init__(self, session: AsyncSession, storage: StorageBackend) -> None:
        self.session = session
        self.storage = storage

    async def presign(
        self, identity: Identity, payload: UploadPresignRequest
    ) -> UploadPresignResponse:
        if identity is None:
            raise AppException(403, code="IDENTITY_REQUIRED", detail="缺少身份")
        content_type = payload.content_type.strip().lower()
        allowed_types = PURPOSE_CONTENT_TYPES[payload.purpose]
        if content_type not in allowed_types:
            raise AppException(
                415,
                code="UNSUPPORTED_MEDIA_TYPE",
                detail=f"{payload.purpose} 只允许 {', '.join(allowed_types)}",
            )
        if payload.size > settings.upload_max_bytes:
            raise AppException(
                413,
                code="UPLOAD_TOO_LARGE",
                detail=f"单文件不能超过 {settings.upload_max_bytes // (1024 * 1024)}MB",
            )

        object_key = build_object_key(content_type)
        presigned = self.storage.presign_put(
            object_key=object_key, content_type=content_type
        )

        self.session.add(
            Upload(
                object_key=object_key,
                identity=identity.key,
                purpose=payload.purpose,
                content_type=content_type,
                size=payload.size,
            )
        )
        await self.session.commit()

        return UploadPresignResponse(
            object_key=presigned.object_key,
            upload_url=presigned.upload_url,
            expires_in=presigned.expires_in,
            headers=presigned.headers,
        )
