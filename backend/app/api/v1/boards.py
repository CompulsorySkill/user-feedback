"""看板、看板内反馈列表与发帖。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi import status as http_status

from app.api.deps import (
    BoardServiceDep,
    IdentityDep,
    PostServiceDep,
    resolve_write_identity,
)
from app.schemas.board import BoardSummary
from app.schemas.common import Page
from app.schemas.post import PostCreateRequest, PostDetail, PostSummary

router = APIRouter(prefix="/boards", tags=["boards"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="每页条数")]
CursorQuery = Annotated[str | None, Query(description="上一页返回的 next_cursor")]
StatusQuery = Annotated[
    str | None,
    Query(
        pattern="^(open|planned|in_progress|completed|closed)$",
        description="按状态筛选",
    ),
]
SortQuery = Annotated[
    str,
    Query(pattern="^(recent|top)$", description="recent=最近，top=最热（投票最多）"),
]
SearchQuery = Annotated[
    str | None,
    Query(min_length=1, max_length=100, description="按标题与摘要模糊搜索"),
]


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
    status: StatusQuery = None,
    sort: SortQuery = "recent",
    q: SearchQuery = None,
) -> Page[PostSummary]:
    return await service.list_for_board(
        slug,
        limit=limit,
        cursor_raw=cursor,
        status=status,
        sort=sort,
        query=q,
    )


@router.post(
    "/{slug}/posts",
    response_model=PostDetail,
    status_code=http_status.HTTP_201_CREATED,
    summary="发布反馈（匿名或登录）",
)
async def create_post(
    slug: str,
    payload: PostCreateRequest,
    request: Request,
    response: Response,
    identity: IdentityDep,
    service: PostServiceDep,
) -> PostDetail:
    actor = resolve_write_identity(identity, request, response)
    return await service.create(slug, payload, actor)
