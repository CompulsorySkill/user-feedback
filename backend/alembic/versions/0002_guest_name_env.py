"""匿名反馈的昵称与环境信息

Revision ID: 0002_guest_name_env
Revises: 0001_initial
Create Date: 2026-10-24 20:40:00.000000

- posts.anonymous_name：匿名发布自定义昵称（展示时仍标注匿名）
- posts.client_env：用户勾选后附带的浏览器 / 操作系统环境信息
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_guest_name_env"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("anonymous_name", sa.String(length=50), nullable=True)
        )
        batch_op.add_column(sa.Column("client_env", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_column("client_env")
        batch_op.drop_column("anonymous_name")
