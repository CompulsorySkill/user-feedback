"""/api/health 契约测试。"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import get_session
from app.main import app
from tests.conftest import sqlite_url


@pytest.fixture
async def client(db_path) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(sqlite_url(db_path))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_health_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["name"] == "FeedLog"
    assert body["version"]
    assert body["environment"] == "development"


async def test_health_returns_503_when_database_unavailable(
    client: AsyncClient,
) -> None:
    class BrokenSession:
        async def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("database is gone"))

    async def broken_session():
        yield BrokenSession()

    app.dependency_overrides[get_session] = broken_session
    response = await client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "DATABASE_UNAVAILABLE",
        "code": "DATABASE_UNAVAILABLE",
    }
