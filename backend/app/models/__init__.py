"""模型包：导入顺序保证 ``Base.metadata`` 完整，Alembic 依赖此入口。"""

from app.models.audit import AuditLog
from app.models.base import Base
from app.models.board import Board
from app.models.changelog import ChangelogEntry
from app.models.changelog_attachment import ChangelogAttachment
from app.models.comment import Comment
from app.models.post import Post
from app.models.rate_limit import RateLimitCounter
from app.models.tag import PostTag, Tag
from app.models.upload import Upload
from app.models.user import User
from app.models.vote import Vote

__all__ = [
    "AuditLog",
    "Base",
    "Board",
    "ChangelogAttachment",
    "ChangelogEntry",
    "Comment",
    "Post",
    "PostTag",
    "RateLimitCounter",
    "Tag",
    "Upload",
    "User",
    "Vote",
]
