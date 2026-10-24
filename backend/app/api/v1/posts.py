"""反馈详情、编辑、状态流转、投票与评论。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, Response
from fastapi import status as http_status

from app.api.deps import (
    CommentServiceDep,
    IdentityDep,
    PostServiceDep,
    VoteServiceDep,
    resolve_write_identity,
)
from app.schemas.comment import CommentCreateRequest, CommentItem, CommentList
from app.schemas.post import (
    PostDetail,
    PostStatusUpdate,
    PostUpdateRequest,
)
from app.schemas.vote import VoteResponse

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/{post_id}", response_model=PostDetail, summary="反馈详情")
async def get_post(post_id: uuid.UUID, service: PostServiceDep) -> PostDetail:
    return await service.get(post_id)


@router.patch("/{post_id}", response_model=PostDetail, summary="编辑反馈")
async def update_post(
    post_id: uuid.UUID,
    payload: PostUpdateRequest,
    identity: IdentityDep,
    service: PostServiceDep,
) -> PostDetail:
    return await service.update(post_id, payload, identity)


@router.patch(
    "/{post_id}/status", response_model=PostDetail, summary="变更反馈状态"
)
async def change_status(
    post_id: uuid.UUID,
    payload: PostStatusUpdate,
    identity: IdentityDep,
    service: PostServiceDep,
) -> PostDetail:
    return await service.change_status(post_id, payload.status, identity)


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
async def list_comments(
    post_id: uuid.UUID, service: CommentServiceDep
) -> CommentList:
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
