"""反馈汇总、详情、编辑、状态流转、投票与评论。"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi import status as http_status

from app.api.deps import (
    AdminUserDep,
    AuditServiceDep,
    CommentServiceDep,
    IdentityDep,
    PostServiceDep,
    VoteServiceDep,
    resolve_write_identity,
)
from app.core.identity import AuthenticatedUser
from app.schemas.common import Page
from app.schemas.comment import CommentCreateRequest, CommentItem, CommentList
from app.schemas.post import (
    PostDetail,
    PostStatusUpdate,
    PostSummary,
    PostUpdateRequest,
)
from app.schemas.vote import VoteResponse
from app.services.audit import request_ip

router = APIRouter(prefix="/posts", tags=["posts"])

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
BoardQuery = Annotated[
    str | None,
    Query(min_length=1, max_length=64, description="限定某个公开看板的 slug"),
]
TagQuery = Annotated[
    list[str] | None,
    Query(description="按标签筛选，可重复传参 tag=；多个标签为 OR，最多 5 个"),
]


@router.get("", response_model=Page[PostSummary], summary="全部看板反馈汇总")
async def list_posts(
    service: PostServiceDep,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
    status: StatusQuery = None,
    sort: SortQuery = "recent",
    q: SearchQuery = None,
    board: BoardQuery = None,
    tag: TagQuery = None,
) -> Page[PostSummary]:
    return await service.list_all(
        limit=limit,
        cursor_raw=cursor,
        status=status,
        sort=sort,
        query=q,
        board_slug=board,
        tags=tag,
    )


@router.get("/{post_id}", response_model=PostDetail, summary="反馈详情")
async def get_post(
    post_id: uuid.UUID, identity: IdentityDep, service: PostServiceDep
) -> PostDetail:
    return await service.get(post_id, identity)


@router.delete(
    "/{post_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除反馈及其评论（管理员）",
)
async def delete_post(
    post_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: PostServiceDep,
    audit: AuditServiceDep,
) -> Response:
    title = await service.delete(post_id)
    await audit.record(
        action="post.delete",
        actor=admin,
        target_type="post",
        target_id=post_id,
        detail={"title": title},
        ip=request_ip(request),
    )
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.patch("/{post_id}", response_model=PostDetail, summary="编辑反馈")
async def update_post(
    post_id: uuid.UUID,
    payload: PostUpdateRequest,
    request: Request,
    identity: IdentityDep,
    service: PostServiceDep,
    audit: AuditServiceDep,
) -> PostDetail:
    post = await service.update(post_id, payload, identity)
    if isinstance(identity, AuthenticatedUser) and identity.is_admin:
        await audit.record(
            action="post.update",
            actor=identity.user,
            target_type="post",
            target_id=post_id,
            detail={
                "title": post.title,
                "title_changed": payload.title is not None,
                "content_changed": payload.content is not None,
                "tags_changed": payload.tags is not None,
            },
            ip=request_ip(request),
        )
    return post


@router.patch("/{post_id}/status", response_model=PostDetail, summary="变更反馈状态")
async def change_status(
    post_id: uuid.UUID,
    payload: PostStatusUpdate,
    request: Request,
    identity: IdentityDep,
    service: PostServiceDep,
    audit: AuditServiceDep,
) -> PostDetail:
    post = await service.change_status(post_id, payload.status, identity)
    if isinstance(identity, AuthenticatedUser):
        await audit.record(
            action="post.status",
            actor=identity.user,
            target_type="post",
            target_id=post_id,
            detail={
                "title": post.title,
                "status": post.status,
                "by_admin": identity.is_admin,
            },
            ip=request_ip(request),
        )
    return post


@router.post("/{post_id}/vote", response_model=VoteResponse, summary="投票")
async def vote_post(
    post_id: uuid.UUID,
    request: Request,
    response: Response,
    identity: IdentityDep,
    service: VoteServiceDep,
) -> VoteResponse:
    actor = resolve_write_identity(identity, request, response)
    return await service.add(post_id, actor)


@router.delete("/{post_id}/vote", response_model=VoteResponse, summary="取消投票")
async def unvote_post(
    post_id: uuid.UUID,
    request: Request,
    response: Response,
    identity: IdentityDep,
    service: VoteServiceDep,
) -> VoteResponse:
    actor = resolve_write_identity(identity, request, response)
    return await service.remove(post_id, actor)


@router.get(
    "/{post_id}/comments", response_model=CommentList, summary="评论列表（扁平）"
)
async def list_comments(post_id: uuid.UUID, service: CommentServiceDep) -> CommentList:
    return await service.list(post_id)


@router.post(
    "/{post_id}/comments",
    response_model=CommentItem,
    status_code=http_status.HTTP_201_CREATED,
    summary="发表评论（≤3 层）",
)
async def create_comment(
    post_id: uuid.UUID,
    payload: CommentCreateRequest,
    request: Request,
    response: Response,
    identity: IdentityDep,
    service: CommentServiceDep,
) -> CommentItem:
    actor = resolve_write_identity(identity, request, response)
    return await service.create(post_id, payload, actor)


@router.delete(
    "/{post_id}/comments/{comment_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除评论及其回复（管理员）",
)
async def delete_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    request: Request,
    admin: AdminUserDep,
    service: CommentServiceDep,
    audit: AuditServiceDep,
) -> Response:
    content = await service.delete(post_id, comment_id)
    await audit.record(
        action="comment.delete",
        actor=admin,
        target_type="comment",
        target_id=comment_id,
        detail={"post_id": str(post_id), "content": content[:200]},
        ip=request_ip(request),
    )
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
