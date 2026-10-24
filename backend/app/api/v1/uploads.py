"""上传 presign。"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.api.deps import IdentityDep, UploadServiceDep, resolve_write_identity
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
    return await service.presign(actor, payload)
