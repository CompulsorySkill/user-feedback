"""反馈帖详情（只读）。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import PostServiceDep
from app.schemas.post import PostDetail

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/{post_id}", response_model=PostDetail, summary="反馈详情")
async def get_post(post_id: uuid.UUID, service: PostServiceDep) -> PostDetail:
    return await service.get(post_id)
