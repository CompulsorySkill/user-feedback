"""标签表与帖子标签关联

Revision ID: 0003_tags
Revises: 0002_guest_name_env
Create Date: 2026-10-24 23:30:00.000000

- tags：全局标签（内置 / 发帖时自动创建），normalized 唯一
- post_tags：帖子 ↔ 标签多对多
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_tags"
down_revision: str | None = "0002_guest_name_env"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("normalized", sa.String(length=128), nullable=False),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_tags_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint("normalized", name=op.f("uq_tags_normalized")),
    )

    op.create_table(
        "post_tags",
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            name=op.f("fk_post_tags_post_id_posts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_post_tags_tag_id_tags"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("post_id", "tag_id", name=op.f("pk_post_tags")),
    )
    op.create_index("ix_post_tags_tag_id", "post_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_post_tags_tag_id", table_name="post_tags")
    op.drop_table("post_tags")
    op.drop_table("tags")
