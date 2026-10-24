from app.schemas.auth import (
    AuthCapabilities,
    DevLoginRequest,
    MeResponse,
    UserInfo,
)
from app.schemas.board import BoardRef, BoardSummary
from app.schemas.changelog import (
    ChangelogCreateRequest,
    ChangelogDetail,
    ChangelogSummary,
    ChangelogUpdateRequest,
)
from app.schemas.comment import CommentCreateRequest, CommentItem, CommentList
from app.schemas.common import Page
from app.schemas.health import HealthResponse
from app.schemas.post import (
    ClientEnvironment,
    PostCreateRequest,
    PostDetail,
    PostStatusUpdate,
    PostSummary,
    PostUpdateRequest,
)
from app.schemas.upload import (
    UploadPresignRequest,
    UploadPresignResponse,
    UploadPurpose,
)
from app.schemas.vote import VoteResponse

__all__ = [
    "AuthCapabilities",
    "BoardRef",
    "BoardSummary",
    "ChangelogCreateRequest",
    "ChangelogDetail",
    "ChangelogSummary",
    "ChangelogUpdateRequest",
    "ClientEnvironment",
    "CommentCreateRequest",
    "CommentItem",
    "CommentList",
    "DevLoginRequest",
    "HealthResponse",
    "MeResponse",
    "Page",
    "PostCreateRequest",
    "PostDetail",
    "PostStatusUpdate",
    "PostSummary",
    "PostUpdateRequest",
    "UploadPresignRequest",
    "UploadPresignResponse",
    "UploadPurpose",
    "UserInfo",
    "VoteResponse",
]
