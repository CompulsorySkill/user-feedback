"""看板与看板内反馈列表（只读）。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import BoardServiceDep, PostServiceDep
from app.schemas.board import BoardSummary
from app.schemas.common import Page
from app.schemas.post import PostSummary

router = APIRouter(prefix="/boards", tags=["boards"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
CursorQuery = Annotated[str | None, Query(description="上一页返回的 next_cursor")]


@router.get("", response_model=list[BoardSummary], summary="公开看板列表")
async def list_boards(service: BoardServiceDep) -> list[BoardSummary]:
    return await service.list_public()


@router.get("/{slug}", response_model=BoardSummary, summary="看板详情")
async def get_board(slug: str, service: BoardServiceDep) -> BoardSummary:
    return await service.get_by_slug(slug)


@router.get(
    "/{slug}/posts",
    response_model=Page[PostSummary],
    summary="看板内反馈列表（keyset 分页）",
)
async def list_board_posts(
    slug: str,
    service: PostServiceDep,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
) -> Page[PostSummary]:
    return await service.list_for_board(slug, limit=limit, cursor_raw=cursor)
