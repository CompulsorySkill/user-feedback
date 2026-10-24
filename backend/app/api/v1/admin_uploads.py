"""管理员手动触发未引用上传对象清理。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.api.deps import AdminUserDep, AuditServiceDep, UploadCleanupServiceDep
from app.schemas.audit import UploadCleanupResult
from app.services.audit import request_ip

router = APIRouter(prefix="/admin/uploads", tags=["admin"])


@router.post(
    "/cleanup",
    response_model=UploadCleanupResult,
    summary="清理未引用上传对象（管理员）",
)
async def cleanup_uploads(
    request: Request,
    admin: AdminUserDep,
    service: UploadCleanupServiceDep,
    audit: AuditServiceDep,
    dry_run: bool = False,
    grace_hours: Annotated[int | None, Query(ge=1, le=720)] = None,
) -> UploadCleanupResult:
    result = await service.run(grace_hours=grace_hours, dry_run=dry_run)
    await audit.record(
        action="upload.cleanup",
        actor=admin,
        target_type="upload",
        detail=result.model_dump(),
        ip=request_ip(request),
    )
    return result
