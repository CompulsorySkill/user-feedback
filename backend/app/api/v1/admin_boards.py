"""管理员看板维护。"""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi import status as http_status

from app.api.deps import AdminUserDep, BoardServiceDep
from app.schemas.board import (
    BoardCreateRequest,
    BoardSummary,
    BoardUpdateRequest,
)

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
    admin: AdminUserDep,
    service: BoardServiceDep,
) -> BoardSummary:
    return await service.create(payload)


@router.patch(
    "/{board_id}",
    response_model=BoardSummary,
    summary="修改看板（管理员）",
)
async def update_board(
    board_id: int,
    payload: BoardUpdateRequest,
    admin: AdminUserDep,
    service: BoardServiceDep,
) -> BoardSummary:
    return await service.update(board_id, payload)


@router.delete(
    "/{board_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除看板（管理员；非空需 force）",
)
async def delete_board(
    board_id: int,
    admin: AdminUserDep,
    service: BoardServiceDep,
    force: bool = False,
) -> Response:
    await service.delete(board_id, force=force)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
