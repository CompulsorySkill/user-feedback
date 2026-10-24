"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-24 16:40:00.000000

P0 初始 schema：Board / Post / Comment / Vote / ChangelogEntry / User /
Upload / RateLimitCounter 八张表，以及 keyset 分页索引与 Vote 部分唯一索引。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "boards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "allow_guest_posting", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            "allow_guest_voting", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            "allow_guest_commenting",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_boards")),
    )
    op.create_index(op.f("ix_boards_slug"), "boards", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column(
            "role", sa.String(length=10), server_default="user", nullable=False
        ),
        sa.Column("sso_provider", sa.String(length=64), nullable=True),
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
        sa.CheckConstraint("role IN ('user', 'admin')", name=op.f("ck_users_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("board_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("excerpt", sa.String(length=500), server_default="", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("anonymous_token", sa.String(length=64), nullable=True),
        sa.Column("vote_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("comment_count", sa.Integer(), server_default="0", nullable=False),
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
        sa.CheckConstraint(
            "status IN ('open', 'planned', 'in_progress', 'completed', 'closed')",
            name=op.f("ck_posts_status"),
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_posts_author_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["board_id"],
            ["boards.id"],
            name=op.f("fk_posts_board_id_boards"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posts")),
    )
    op.create_index("ix_posts_anonymous_token", "posts", ["anonymous_token"])
    op.create_index("ix_posts_author_id", "posts", ["author_id"])
    op.create_index(
        "ix_posts_board_keyset", "posts", ["board_id", "created_at", "id"]
    )
    op.create_index("ix_posts_status", "posts", ["status"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("anonymous_token", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_comments_author_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["comments.id"],
            name=op.f("fk_comments_parent_id_comments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            name=op.f("fk_comments_post_id_posts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])
    op.create_index("ix_comments_post_id", "comments", ["post_id"])

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("anonymous_token", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            name=op.f("fk_votes_post_id_posts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_votes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_votes")),
    )
    op.create_index("ix_votes_post_id", "votes", ["post_id"])
    # 部分唯一索引：登录票与匿名票各自去重，NULL 不参与。
    op.create_index(
        "uq_votes_post_user",
        "votes",
        ["post_id", "user_id"],
        unique=True,
        sqlite_where=sa.text("user_id IS NOT NULL"),
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_votes_post_anonymous",
        "votes",
        ["post_id", "anonymous_token"],
        unique=True,
        sqlite_where=sa.text("anonymous_token IS NOT NULL"),
        postgresql_where=sa.text("anonymous_token IS NOT NULL"),
    )

    op.create_table(
        "changelog_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("excerpt", sa.String(length=500), server_default="", nullable=False),
        sa.Column(
            "is_published", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_changelog_entries")),
    )
    op.create_index(
        "ix_changelog_entries_published",
        "changelog_entries",
        ["is_published", "published_at"],
    )

    op.create_table(
        "uploads",
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("identity", sa.String(length=128), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("object_key", name=op.f("pk_uploads")),
    )
    op.create_index("ix_uploads_identity", "uploads", ["identity"])

    op.create_table(
        "rate_limit_counters",
        sa.Column("identity_key", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint(
            "identity_key",
            "action",
            "window_start",
            name=op.f("pk_rate_limit_counters"),
        ),
    )


def downgrade() -> None:
    op.drop_table("rate_limit_counters")
    op.drop_index("ix_uploads_identity", table_name="uploads")
    op.drop_table("uploads")
    op.drop_index("ix_changelog_entries_published", table_name="changelog_entries")
    op.drop_table("changelog_entries")
    op.drop_index("uq_votes_post_anonymous", table_name="votes")
    op.drop_index("uq_votes_post_user", table_name="votes")
    op.drop_index("ix_votes_post_id", table_name="votes")
    op.drop_table("votes")
    op.drop_index("ix_comments_post_id", table_name="comments")
    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_posts_status", table_name="posts")
    op.drop_index("ix_posts_board_keyset", table_name="posts")
    op.drop_index("ix_posts_author_id", table_name="posts")
    op.drop_index("ix_posts_anonymous_token", table_name="posts")
    op.drop_table("posts")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_boards_slug"), table_name="boards")
    op.drop_table("boards")
