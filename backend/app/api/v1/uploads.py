"""上传 presign。"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import APIRouter, Request, Response

from app.api.deps import IdentityDep, UploadServiceDep, resolve_write_identity
from app.core.config import settings
from app.schemas.upload import UploadPresignRequest, UploadPresignResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post(
    "/presign",
    response_model=UploadPresignResponse,
    summary="获取直传 RustFS 的 presigned PUT URL",
)
async def presign_upload(
    payload: UploadPresignRequest,
    request: Request,
    response: Response,
    identity: IdentityDep,
    service: UploadServiceDep,
) -> UploadPresignResponse:
    actor = resolve_write_identity(identity, request, response)
    # presign 的签名 Host 跟着实际访问入口走，http / https、裸 IP、自定义端口都成立。
    host = request.headers.get("host") or urlsplit(settings.public_origin).netloc
    return await service.presign(actor, payload, host=host)
