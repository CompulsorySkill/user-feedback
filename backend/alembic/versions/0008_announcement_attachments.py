"""公告附件表

Revision ID: 0008_announcement_attachments
Revises: 0007_announcements
Create Date: 2026-10-26 11:00:00.000000

- announcement_attachments：公告附件元数据，引用 uploads.object_key
- 与更新日志附件一致：任意类型文件仅管理员上传，下载强制 attachment
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_announcement_attachments"
down_revision: str | None = "0007_announcements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "announcement_attachments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("announcement_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["announcement_id"],
            ["announcements.id"],
            name=op.f("fk_announcement_attachments_announcement_id_announcements"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["object_key"],
            ["uploads.object_key"],
            name=op.f("fk_announcement_attachments_object_key_uploads"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_announcement_attachments")),
        sa.UniqueConstraint(
            "announcement_id",
            "object_key",
            name="uq_announcement_attachments_announcement_object",
        ),
    )
    op.create_index(
        "ix_announcement_attachments_announcement_id",
        "announcement_attachments",
        ["announcement_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_announcement_attachments_announcement_id",
        table_name="announcement_attachments",
    )
    op.drop_table("announcement_attachments")
