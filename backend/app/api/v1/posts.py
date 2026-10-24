"""反馈详情与投票。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, Response

from app.api.deps import PostServiceDep, VoteServiceDep
from app.core.identity import ensure_anonymous_identity
from app.schemas.post import PostDetail
from app.schemas.vote import VoteResponse

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/{post_id}", response_model=PostDetail, summary="反馈详情")
async def get_post(post_id: uuid.UUID, service: PostServiceDep) -> PostDetail:
    return await service.get(post_id)


@router.post("/{post_id}/vote", response_model=VoteResponse, summary="投票")
async def vote_post(
    post_id: uuid.UUID,
    request: Request,
    response: Response,
    service: VoteServiceDep,
) -> VoteResponse:
    identity = ensure_anonymous_identity(request, response)
    return await service.add(post_id, identity)


@router.delete("/{post_id}/vote", response_model=VoteResponse, summary="取消投票")
async def unvote_post(
    post_id: uuid.UUID,
    request: Request,
    response: Response,
    service: VoteServiceDep,
) -> VoteResponse:
    identity = ensure_anonymous_identity(request, response)
    return await service.remove(post_id, identity)
