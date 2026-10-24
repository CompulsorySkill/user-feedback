from fastapi import APIRouter

from app.api.v1 import admin_boards, auth, boards, changelogs, posts, uploads

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth.router)
v1_router.include_router(boards.router)
v1_router.include_router(admin_boards.router)
v1_router.include_router(posts.router)
v1_router.include_router(changelogs.router)
v1_router.include_router(uploads.router)

__all__ = ["v1_router"]
