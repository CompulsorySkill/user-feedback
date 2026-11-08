"""评论正文改为 Tiptap JSON

Revision ID: 0009_comment_rich_content
Revises: 0008_announcement_attachments
Create Date: 2026-10-26 12:00:00.000000

- comments.content 从纯文本改为 JSON，与反馈 / 更新日志 / 公告一致
- 历史纯文本包装为单段落 doc；downgrade 只保留第一段纯文本
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_comment_rich_content"
down_revision: str | None = "0008_announcement_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQLITE_WRAP = """
UPDATE comments
SET content = json_object(
    'type', 'doc',
    'content', json_array(
        json_object(
            'type', 'paragraph',
            'content', json_array(
                json_object('type', 'text', 'text', content)
            )
        )
    )
)
"""

_SQLITE_UNWRAP = """
UPDATE comments
SET content = COALESCE(json_extract(content, '$.content[0].content[0].text'), '')
"""

_POSTGRES_WRAP = """
json_build_object(
    'type', 'doc',
    'content', json_build_array(
        json_build_object(
            'type', 'paragraph',
            'content', json_build_array(
                json_build_object('type', 'text', 'text', content)
            )
        )
    )
)::json
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(sa.text(_SQLITE_WRAP))
        with op.batch_alter_table("comments") as batch_op:
            batch_op.alter_column(
                "content",
                existing_type=sa.Text(),
                type_=sa.JSON(),
                existing_nullable=False,
            )
    else:
        op.alter_column(
            "comments",
            "content",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            existing_nullable=False,
            postgresql_using=_POSTGRES_WRAP,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(sa.text(_SQLITE_UNWRAP))
        with op.batch_alter_table("comments") as batch_op:
            batch_op.alter_column(
                "content",
                existing_type=sa.JSON(),
                type_=sa.Text(),
                existing_nullable=False,
            )
    else:
        op.alter_column(
            "comments",
            "content",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            existing_nullable=False,
            postgresql_using="COALESCE(content->'content'->0->'content'->0->>'text', '')",
        )
