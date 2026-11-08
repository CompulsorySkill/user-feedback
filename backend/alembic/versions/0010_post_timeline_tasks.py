"""反馈时间线与任务

Revision ID: 0010_post_timeline_tasks
Revises: 0009_comment_rich_content
Create Date: 2026-10-27 10:00:00.000000

- post_timeline_events：状态流转、提出反馈、接受 / 完成任务的审计时间线
- post_tasks：每篇反馈最多一条，记录任务接受者与接受 / 完成时间
- 为既有反馈回填一条 created 事件
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_post_timeline_tasks"
down_revision: str | None = "0009_comment_rich_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "post_timeline_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_name", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            name=op.f("fk_post_timeline_events_post_id_posts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_post_timeline_events_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_post_timeline_events")),
    )
    op.create_index(
        "ix_post_timeline_events_post_created",
        "post_timeline_events",
        ["post_id", "created_at"],
    )

    op.create_table(
        "post_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("assignee_name", sa.String(length=120), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["post_id"],
            ["posts.id"],
            name=op.f("fk_post_tasks_post_id_posts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name=op.f("fk_post_tasks_assignee_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_post_tasks")),
        sa.UniqueConstraint("post_id", name=op.f("uq_post_tasks_post_id")),
    )

    op.execute(sa.text("""
            INSERT INTO post_timeline_events
                (post_id, event_type, from_status, to_status, actor_id,
                 actor_name, created_at)
            SELECT p.id, 'created', NULL, 'open', p.author_id,
                   COALESCE(NULLIF(u.display_name, ''), u.email,
                            p.anonymous_name, '匿名用户'),
                   p.created_at
            FROM posts p
            LEFT JOIN users u ON u.id = p.author_id
            """))


def downgrade() -> None:
    op.drop_table("post_tasks")
    op.drop_index(
        "ix_post_timeline_events_post_created",
        table_name="post_timeline_events",
    )
    op.drop_table("post_timeline_events")
