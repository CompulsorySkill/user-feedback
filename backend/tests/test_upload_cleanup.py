"""上传对象清理：保留被引用对象，删除超期未引用记录。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Upload
from app.services.upload_cleanup import UploadCleanupService
from tests.conftest import (
    FakeStorage,
    insert_board,
    insert_changelog,
    insert_post,
    insert_upload,
    sqlite_url,
)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


def content_with(key: str) -> dict:
    return {
        "type": "doc",
        "content": [
            {
                "type": "image",
                "attrs": {"src": key},
            }
        ],
    }


async def test_cleanup_keeps_referenced_and_deletes_orphan(
    db_path, sqlite_conn
) -> None:
    board_id = insert_board(sqlite_conn)
    insert_post(
        sqlite_conn,
        board_id=board_id,
        title="引用图片",
        created_at=NOW - timedelta(hours=2),
        content=content_with("uploads/keep.png"),
    )
    insert_upload(
        sqlite_conn,
        object_key="uploads/keep.png",
        created_at=NOW - timedelta(hours=48),
    )
    insert_upload(
        sqlite_conn,
        object_key="uploads/orphan.png",
        created_at=NOW - timedelta(hours=48),
    )
    # 宽限期内的对象即使未引用也不能删除。
    insert_upload(
        sqlite_conn,
        object_key="uploads/fresh.png",
        created_at=NOW - timedelta(hours=1),
    )

    engine = create_async_engine(sqlite_url(db_path))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    storage = FakeStorage()
    try:
        async with sessionmaker() as session:
            service = UploadCleanupService(session, storage)
            dry = await service.run(grace_hours=24, dry_run=True)
            assert dry.scanned == 2
            assert dry.referenced == 1
            assert dry.deleted == 1
            assert storage.deleted == []

            result = await service.run(grace_hours=24)
            assert result.deleted == 1
            assert result.failed == 0
            assert storage.deleted == ["uploads/orphan.png"]

        async with sessionmaker() as session:
            keys = set((await session.execute(select(Upload.object_key))).scalars())
        assert keys == {"uploads/keep.png", "uploads/fresh.png"}
    finally:
        await engine.dispose()


async def test_cleanup_keeps_changelog_attachment(db_path, sqlite_conn) -> None:
    changelog_id = insert_changelog(
        sqlite_conn,
        title="带附件的更新日志",
        created_at=NOW - timedelta(hours=2),
    )
    insert_upload(
        sqlite_conn,
        object_key="uploads/release.zip",
        created_at=NOW - timedelta(hours=48),
        purpose="changelog_attachment",
        content_type="application/zip",
    )
    sqlite_conn.execute(
        "INSERT INTO changelog_attachments"
        " (changelog_id, object_key, filename, content_type, size)"
        " VALUES (?, 'uploads/release.zip', 'release.zip', 'application/zip', 10)",
        (changelog_id,),
    )
    sqlite_conn.commit()

    engine = create_async_engine(sqlite_url(db_path))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    storage = FakeStorage()
    try:
        async with sessionmaker() as session:
            result = await UploadCleanupService(session, storage).run(grace_hours=24)
        assert result.referenced == 1
        assert result.deleted == 0
        assert storage.deleted == []
    finally:
        await engine.dispose()


async def test_cleanup_keeps_row_when_storage_delete_fails(
    db_path, sqlite_conn
) -> None:
    insert_upload(
        sqlite_conn,
        object_key="uploads/broken.png",
        created_at=NOW - timedelta(hours=48),
    )

    class FailingStorage(FakeStorage):
        def delete_object(self, object_key: str) -> None:
            raise RuntimeError("RustFS unavailable")

    engine = create_async_engine(sqlite_url(db_path))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessionmaker() as session:
            result = await UploadCleanupService(session, FailingStorage()).run(
                grace_hours=24
            )
        assert result.failed == 1
        assert "RustFS unavailable" in result.errors[0]

        async with sessionmaker() as session:
            keys = set((await session.execute(select(Upload.object_key))).scalars())
        assert keys == {"uploads/broken.png"}
    finally:
        await engine.dispose()
