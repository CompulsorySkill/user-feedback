"""Alembic 环境：URL 来自 ``deploy/.env``，支持 SQLite / Postgres。"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# ``%`` 在 configparser 中需转义。CLI 未显式给出 URL 时使用 deploy/.env。
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

target_metadata = Base.metadata


def _configure(connection: Connection | None, *, url: str | None = None) -> None:
    target_url = url or (settings.database_url if connection is None else None)
    is_sqlite = (target_url or settings.database_url).startswith("sqlite")
    context.configure(
        connection=connection,
        url=target_url,
        target_metadata=target_metadata,
        compare_type=True,
        # SQLite 不支持大部分 ALTER，用 batch 模式保证后续迁移可执行。
        render_as_batch=is_sqlite,
        literal_binds=connection is None,
        dialect_opts={"paramstyle": "named"} if connection is None else {},
    )


def run_migrations_offline() -> None:
    _configure(None)
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
