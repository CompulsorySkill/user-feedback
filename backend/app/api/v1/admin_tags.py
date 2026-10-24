"""管理员维护内置标签。"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi import status as http_status

from app.api.deps import AdminUserDep, AuditServiceDep, TagServiceDep
from app.schemas.tag import TagCreateRequest, TagSummary
from app.services.audit import request_ip

router = APIRouter(prefix="/admin/tags", tags=["admin"])


@router.get("", response_model=list[TagSummary], summary="全部标签（管理员）")
async def list_tags(admin: AdminUserDep, service: TagServiceDep) -> list[TagSummary]:
    return await service.list_admin()


@router.post(
    "",
    response_model=TagSummary,
    status_code=http_status.HTTP_201_CREATED,
    summary="新增内置标签（管理员）",
)
async def create_tag(
    payload: TagCreateRequest,
    request: Request,
    admin: AdminUserDep,
    service: TagServiceDep,
    audit: AuditServiceDep,
) -> TagSummary:
    tag = await service.create_builtin(payload, admin)
    await audit.record(
        action="tag.create",
        actor=admin,
        target_type="tag",
        target_id=tag.id,
        detail={"name": tag.name},
        ip=request_ip(request),
    )
    return tag


@router.delete(
    "/{tag_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除标签并解除帖子关联（管理员）",
)
async def delete_tag(
    tag_id: int,
    request: Request,
    admin: AdminUserDep,
    service: TagServiceDep,
    audit: AuditServiceDep,
) -> Response:
    await service.delete(tag_id)
    await audit.record(
        action="tag.delete",
        actor=admin,
        target_type="tag",
        target_id=tag_id,
        ip=request_ip(request),
    )
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
