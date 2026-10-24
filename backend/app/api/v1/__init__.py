from fastapi import APIRouter

from app.api.v1 import boards, changelogs, posts

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(boards.router)
v1_router.include_router(posts.router)
v1_router.include_router(changelogs.router)

__all__ = ["v1_router"]
