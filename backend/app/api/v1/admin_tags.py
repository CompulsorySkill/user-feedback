"""管理员维护内置标签。"""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi import status as http_status

from app.api.deps import AdminUserDep, TagServiceDep
from app.schemas.tag import TagCreateRequest, TagSummary

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
    admin: AdminUserDep,
    service: TagServiceDep,
) -> TagSummary:
    return await service.create_builtin(payload, admin)


@router.delete(
    "/{tag_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除标签并解除帖子关联（管理员）",
)
async def delete_tag(
    tag_id: int,
    admin: AdminUserDep,
    service: TagServiceDep,
) -> Response:
    await service.delete(tag_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
