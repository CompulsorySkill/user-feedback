"""API 依赖注入：Repository / Service / Storage 在此装配。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.identity import AnonymousIdentity, get_anonymous_identity
from app.core.storage import S3Storage, get_storage
from app.repositories.boards import BoardRepository
from app.repositories.changelogs import ChangelogRepository
from app.repositories.posts import PostRepository
from app.repositories.uploads import UploadRepository
from app.repositories.votes import VoteRepository
from app.services.boards import BoardService
from app.services.changelogs import ChangelogService
from app.services.posts import PostService
from app.services.uploads import UploadService
from app.services.votes import VoteService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_board_repository(session: SessionDep) -> BoardRepository:
    return BoardRepository(session)


def get_post_repository(session: SessionDep) -> PostRepository:
    return PostRepository(session)


def get_changelog_repository(session: SessionDep) -> ChangelogRepository:
    return ChangelogRepository(session)


def get_upload_repository(session: SessionDep) -> UploadRepository:
    return UploadRepository(session)


def get_vote_repository(session: SessionDep) -> VoteRepository:
    return VoteRepository(session)


BoardRepoDep = Annotated[BoardRepository, Depends(get_board_repository)]
PostRepoDep = Annotated[PostRepository, Depends(get_post_repository)]
ChangelogRepoDep = Annotated[ChangelogRepository, Depends(get_changelog_repository)]
UploadRepoDep = Annotated[UploadRepository, Depends(get_upload_repository)]
VoteRepoDep = Annotated[VoteRepository, Depends(get_vote_repository)]


def get_storage_backend() -> S3Storage:
    return get_storage()


StorageDep = Annotated[S3Storage, Depends(get_storage_backend)]


def get_board_service(boards: BoardRepoDep) -> BoardService:
    return BoardService(boards)


def get_post_service(
    session: SessionDep,
    posts: PostRepoDep,
    boards: BoardRepoDep,
    uploads: UploadRepoDep,
) -> PostService:
    return PostService(session, posts, boards, uploads)


def get_changelog_service(changelogs: ChangelogRepoDep) -> ChangelogService:
    return ChangelogService(changelogs)


def get_upload_service(session: SessionDep, storage: StorageDep) -> UploadService:
    return UploadService(session, storage)


def get_vote_service(
    session: SessionDep, posts: PostRepoDep, votes: VoteRepoDep
) -> VoteService:
    return VoteService(session, posts, votes)


BoardServiceDep = Annotated[BoardService, Depends(get_board_service)]
PostServiceDep = Annotated[PostService, Depends(get_post_service)]
ChangelogServiceDep = Annotated[ChangelogService, Depends(get_changelog_service)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
VoteServiceDep = Annotated[VoteService, Depends(get_vote_service)]


def get_optional_identity(request: Request) -> AnonymousIdentity | None:
    """读接口不签发 cookie，仅尝试识别已有匿名身份。"""
    return get_anonymous_identity(request)
