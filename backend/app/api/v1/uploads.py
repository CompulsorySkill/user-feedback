"""上传 presign。"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.api.deps import UploadServiceDep
from app.core.identity import ensure_anonymous_identity
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
    service: UploadServiceDep,
) -> UploadPresignResponse:
    identity = ensure_anonymous_identity(request, response)
    return await service.presign(identity, payload)
