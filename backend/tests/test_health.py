"""/api/health 契约测试。"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from app.core.db import get_session
from app.main import app


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
