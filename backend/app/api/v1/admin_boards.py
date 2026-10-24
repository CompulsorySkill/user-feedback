"""管理员看板维护。"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi import status as http_status

from app.api.deps import AdminUserDep, AuditServiceDep, BoardServiceDep
from app.schemas.board import (
    BoardCreateRequest,
    BoardSummary,
    BoardUpdateRequest,
)
from app.services.audit import request_ip

router = APIRouter(prefix="/admin/boards", tags=["admin"])


@router.get("", response_model=list[BoardSummary], summary="看板列表（管理员）")
async def list_boards(
    admin: AdminUserDep, service: BoardServiceDep
) -> list[BoardSummary]:
    return await service.list_all()


@router.post(
    "",
    response_model=BoardSummary,
    status_code=http_status.HTTP_201_CREATED,
    summary="创建看板（管理员）",
)
async def create_board(
    payload: BoardCreateRequest,
    request: Request,
    admin: AdminUserDep,
    service: BoardServiceDep,
    audit: AuditServiceDep,
) -> BoardSummary:
    board = await service.create(payload)
    await audit.record(
        action="board.create",
        actor=admin,
        target_type="board",
        target_id=board.id,
        detail={"slug": board.slug, "name": board.name, "is_public": board.is_public},
        ip=request_ip(request),
    )
    return board


@router.patch(
    "/{board_id}",
    response_model=BoardSummary,
    summary="修改看板（管理员）",
)
async def update_board(
    board_id: int,
    payload: BoardUpdateRequest,
    request: Request,
    admin: AdminUserDep,
    service: BoardServiceDep,
    audit: AuditServiceDep,
) -> BoardSummary:
    board = await service.update(board_id, payload)
    await audit.record(
        action="board.update",
        actor=admin,
        target_type="board",
        target_id=board_id,
        detail=payload.model_dump(exclude_unset=True),
        ip=request_ip(request),
    )
    return board


@router.delete(
    "/{board_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除看板（管理员；非空需 force）",
)
async def delete_board(
    board_id: int,
    request: Request,
    admin: AdminUserDep,
    service: BoardServiceDep,
    audit: AuditServiceDep,
    force: bool = False,
) -> Response:
    await service.delete(board_id, force=force)
    await audit.record(
        action="board.delete",
        actor=admin,
        target_type="board",
        target_id=board_id,
        detail={"force": force},
        ip=request_ip(request),
    )
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
