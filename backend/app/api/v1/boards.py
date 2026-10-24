"""看板、看板内反馈列表与匿名发帖。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi import status as http_status

from app.api.deps import BoardServiceDep, PostServiceDep
from app.core.identity import ensure_anonymous_identity
from app.schemas.board import BoardSummary
from app.schemas.common import Page
from app.schemas.post import PostCreateRequest, PostDetail, PostSummary

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


@router.post(
    "/{slug}/posts",
    response_model=PostDetail,
    status_code=http_status.HTTP_201_CREATED,
    summary="匿名发布反馈",
)
async def create_post(
    slug: str,
    payload: PostCreateRequest,
    request: Request,
    response: Response,
    service: PostServiceDep,
) -> PostDetail:
    identity = ensure_anonymous_identity(request, response)
    return await service.create(slug, payload, identity)
