"""公告表

Revision ID: 0007_announcements
Revises: 0006_changelog_attachments
Create Date: 2026-10-26 10:00:00.000000

- announcements：管理员发布的公告，富文本正文；全局最多一篇置顶（服务层保证）
- author_name：发布时管理员显示名 / 邮箱快照，账号删除或改名后仍可展示
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_announcements"
down_revision: str | None = "0006_changelog_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("excerpt", sa.String(length=500), server_default="", nullable=False),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_name", sa.String(length=320), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_announcements")),
    )
    op.create_index(
        "ix_announcements_published",
        "announcements",
        ["is_published", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_announcements_published", table_name="announcements")
    op.drop_table("announcements")
