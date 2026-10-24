"""对齐 tags.normalized 长度

Revision ID: 0005_tag_norm_len
Revises: 0004_audit_logs
Create Date: 2026-10-25 00:50:00.000000

模型将归一化键定义为 128（casefold 可能扩展字符），0003 建表时为 64。
生产尚未部署，这里补齐迁移链，避免 ``alembic check`` 长期漂移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_tag_norm_len"
down_revision: str | None = "0004_audit_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column(
            "normalized",
            existing_type=sa.String(length=64),
            type_=sa.String(length=128),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column(
            "normalized",
            existing_type=sa.String(length=128),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
