"""更新日志附件表

Revision ID: 0006_changelog_attachments
Revises: 0005_tag_norm_len
Create Date: 2026-10-25 09:20:00.000000

- changelog_attachments：更新日志附件元数据，引用 uploads.object_key
- 任意类型文件只允许管理员上传，下载时由后端强制 Content-Disposition: attachment
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_changelog_attachments"
down_revision: str | None = "0005_tag_norm_len"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "changelog_attachments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("changelog_id", sa.Uuid(), nullable=False),
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
            ["changelog_id"],
            ["changelog_entries.id"],
            name=op.f("fk_changelog_attachments_changelog_id_changelog_entries"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["object_key"],
            ["uploads.object_key"],
            name=op.f("fk_changelog_attachments_object_key_uploads"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_changelog_attachments")),
        sa.UniqueConstraint(
            "changelog_id",
            "object_key",
            name="uq_changelog_attachments_changelog_object",
        ),
    )
    op.create_index(
        "ix_changelog_attachments_changelog_id",
        "changelog_attachments",
        ["changelog_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_changelog_attachments_changelog_id",
        table_name="changelog_attachments",
    )
    op.drop_table("changelog_attachments")
