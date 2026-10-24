# backend

FastAPI + SQLAlchemy 2.x（async）+ Alembic。schema 唯一权威是 Alembic，**禁止 `create_all`**。

## 目录

```
app/
  api/          路由层（当前 /api/health）
  core/         config / db / errors
  models/       SQLAlchemy 模型（8 张表）
  schemas/      Pydantic v2
  services/     业务规则（P1 起填充）
  repositories/ 数据访问（P1 起填充）
  main.py       应用入口
alembic/        迁移环境与版本
tests/          pytest（独立 SQLite 库 + 完整迁移链）
```

## 本地运行

配置来自仓库根的 `deploy/.env`（由 `pydantic-settings` 的 `env_file` 指向，不存在 `backend/.env`）。

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

- 健康检查：<http://127.0.0.1:8000/api/health>
- OpenAPI：<http://127.0.0.1:8000/api/docs>

## 数据库

`DATABASE_URL` 单变量驱动：

| 环境 | 值 |
|---|---|
| 本地 | `sqlite+aiosqlite:///./feedback.db` |
| 生产 | `postgresql+asyncpg://...` |

SQLite 连接自动附加 `check_same_thread=False`、`journal_mode=WAL`、`busy_timeout=5000`、`foreign_keys=ON`。
迁移使用方言感知类型（`Uuid` / `DateTime(timezone=True)` / `JSON`）与 `sqlite_where` / `postgresql_where` 渲染部分唯一索引。

```bash
# 生成迁移（改完模型后）
uv run alembic revision --autogenerate -m "describe change"
# 校验模型与迁移是否一致
uv run alembic check
# 离线渲染 Postgres DDL（无需数据库）
$env:DATABASE_URL="postgresql+asyncpg://feedback:pw@localhost:5432/feedback"
uv run alembic upgrade head --sql
```

## 测试

```bash
uv run pytest -q
```

用例覆盖：`/api/health` 正常与数据库不可用（503 契约）、初始迁移全表与降级、Vote 部分唯一索引去重、Post 状态 CheckConstraint、`created_at` 服务端默认值。
