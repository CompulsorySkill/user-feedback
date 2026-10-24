"""API 依赖注入：Repository / Service 在此装配。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories.boards import BoardRepository
from app.repositories.changelogs import ChangelogRepository
from app.repositories.posts import PostRepository
from app.services.boards import BoardService
from app.services.changelogs import ChangelogService
from app.services.posts import PostService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_board_repository(session: SessionDep) -> BoardRepository:
    return BoardRepository(session)


def get_post_repository(session: SessionDep) -> PostRepository:
    return PostRepository(session)


def get_changelog_repository(session: SessionDep) -> ChangelogRepository:
    return ChangelogRepository(session)


BoardRepoDep = Annotated[BoardRepository, Depends(get_board_repository)]
PostRepoDep = Annotated[PostRepository, Depends(get_post_repository)]
ChangelogRepoDep = Annotated[ChangelogRepository, Depends(get_changelog_repository)]


def get_board_service(boards: BoardRepoDep) -> BoardService:
    return BoardService(boards)


def get_post_service(posts: PostRepoDep, boards: BoardRepoDep) -> PostService:
    return PostService(posts, boards)


def get_changelog_service(changelogs: ChangelogRepoDep) -> ChangelogService:
    return ChangelogService(changelogs)


BoardServiceDep = Annotated[BoardService, Depends(get_board_service)]
PostServiceDep = Annotated[PostService, Depends(get_post_service)]
ChangelogServiceDep = Annotated[ChangelogService, Depends(get_changelog_service)]
