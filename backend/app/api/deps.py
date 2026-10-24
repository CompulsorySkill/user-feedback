"""API 依赖注入：Repository / Service / Storage / 身份在此装配。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppException
from app.core.identity import (
    AuthenticatedUser,
    Identity,
    ensure_anonymous_identity,
    get_anonymous_identity,
)
from app.core.security import ACCESS_COOKIE, decode_session_token
from app.core.storage import S3Storage, get_storage
from app.models import User
from app.repositories.boards import BoardRepository
from app.repositories.changelogs import ChangelogRepository
from app.repositories.comments import CommentRepository
from app.repositories.posts import PostRepository
from app.repositories.tags import TagRepository
from app.repositories.uploads import UploadRepository
from app.repositories.votes import VoteRepository
from app.services.boards import BoardService
from app.services.changelogs import ChangelogService
from app.services.comments import CommentService
from app.services.posts import PostService
from app.services.tags import TagService
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


def get_comment_repository(session: SessionDep) -> CommentRepository:
    return CommentRepository(session)


def get_tag_repository(session: SessionDep) -> TagRepository:
    return TagRepository(session)


BoardRepoDep = Annotated[BoardRepository, Depends(get_board_repository)]
PostRepoDep = Annotated[PostRepository, Depends(get_post_repository)]
ChangelogRepoDep = Annotated[ChangelogRepository, Depends(get_changelog_repository)]
UploadRepoDep = Annotated[UploadRepository, Depends(get_upload_repository)]
VoteRepoDep = Annotated[VoteRepository, Depends(get_vote_repository)]
CommentRepoDep = Annotated[CommentRepository, Depends(get_comment_repository)]
TagRepoDep = Annotated[TagRepository, Depends(get_tag_repository)]


def get_storage_backend() -> S3Storage:
    return get_storage()


StorageDep = Annotated[S3Storage, Depends(get_storage_backend)]


# --------------------------------------------------------------------------- #
# 身份
# --------------------------------------------------------------------------- #


async def get_current_identity(request: Request, session: SessionDep) -> Identity:
    """优先识别 access cookie，其次匿名 cookie，最后为 None。"""
    access = request.cookies.get(ACCESS_COOKIE)
    if access:
        try:
            payload = decode_session_token(access, expected_type="access")
        except AppException:
            payload = None
        if payload is not None:
            user = await session.get(User, int(payload["sub"]))
            if user is not None:
                return AuthenticatedUser(user=user)
    return get_anonymous_identity(request)


IdentityDep = Annotated[Identity, Depends(get_current_identity)]


async def require_admin(identity: IdentityDep) -> User:
    if not isinstance(identity, AuthenticatedUser) or not identity.is_admin:
        raise AppException(403, code="ADMIN_REQUIRED", detail="需要管理员权限")
    return identity.user


AdminUserDep = Annotated[User, Depends(require_admin)]


def resolve_write_identity(
    identity: Identity, request: Request, response: Response
) -> Identity:
    """写操作：登录用户直接用会话身份，否则签发/复用匿名 cookie。"""
    if identity is not None:
        return identity
    return ensure_anonymous_identity(request, response)


# --------------------------------------------------------------------------- #
# 服务装配
# --------------------------------------------------------------------------- #


def get_board_service(session: SessionDep, boards: BoardRepoDep) -> BoardService:
    return BoardService(session, boards)


def get_post_service(
    session: SessionDep,
    posts: PostRepoDep,
    boards: BoardRepoDep,
    uploads: UploadRepoDep,
    tags: TagRepoDep,
) -> PostService:
    return PostService(session, posts, boards, uploads, tags)


def get_tag_service(session: SessionDep, tags: TagRepoDep) -> TagService:
    return TagService(session, tags)


def get_changelog_service(
    session: SessionDep,
    changelogs: ChangelogRepoDep,
    uploads: UploadRepoDep,
) -> ChangelogService:
    return ChangelogService(session, changelogs, uploads)


def get_upload_service(session: SessionDep, storage: StorageDep) -> UploadService:
    return UploadService(session, storage)


def get_vote_service(
    session: SessionDep, posts: PostRepoDep, votes: VoteRepoDep
) -> VoteService:
    return VoteService(session, posts, votes)


def get_comment_service(
    session: SessionDep,
    posts: PostRepoDep,
    comments: CommentRepoDep,
    uploads: UploadRepoDep,
) -> CommentService:
    return CommentService(session, posts, comments)


BoardServiceDep = Annotated[BoardService, Depends(get_board_service)]
PostServiceDep = Annotated[PostService, Depends(get_post_service)]
TagServiceDep = Annotated[TagService, Depends(get_tag_service)]
ChangelogServiceDep = Annotated[ChangelogService, Depends(get_changelog_service)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
VoteServiceDep = Annotated[VoteService, Depends(get_vote_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
