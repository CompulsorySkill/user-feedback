# backend

FastAPI + SQLAlchemy 2.x（async）+ Alembic。schema 唯一权威是 Alembic，**禁止 `create_all`**。

## 目录

```
app/
  api/          路由层（/api/health、/api/v1/*）
  core/         config / db / errors / pagination
  models/       SQLAlchemy 模型（8 张表）
  schemas/      Pydantic v2 响应模式
  services/     业务规则（公开性、分页、草稿可见性）
  repositories/ 数据访问（SQLAlchemy 查询）
  main.py       应用入口
alembic/        迁移环境与版本
scripts/        开发种子数据
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

种子数据（看板 / 18 条反馈 / 更新日志，含本地演示图片与 MP4）：

```bash
uv run python -m scripts.seed_dev          # 已有数据则跳过
uv run python -m scripts.seed_dev --reset  # 清空业务表后重建
```

## 读路径接口（P1）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/boards` | 公开看板 + 反馈数 |
| GET | `/api/v1/boards/{slug}` | 看板详情（私有/不存在 → 404 `BOARD_NOT_FOUND`） |
| GET | `/api/v1/boards/{slug}/posts` | keyset 分页，`limit` ≤ 100，`cursor` 为上一页 `next_cursor` |
| GET | `/api/v1/posts/{id}` | 反馈详情，私有看板内反馈同样 404 |
| GET | `/api/v1/changelogs` | 仅已发布；P1 无鉴权，`include_drafts` 不生效 |
| GET | `/api/v1/changelogs/{id}` | 草稿 → 404 `CHANGELOG_NOT_FOUND` |

游标编码见 `app/core/pagination.py`：`base64url({"t": 创建时间, "i": UUID})`，按 `(created_at, id) DESC` 做 keyset，无效游标返回 400 `INVALID_CURSOR`。

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

用例覆盖：`/api/health` 正常与数据库不可用（503 契约）、初始迁移全表与降级、Vote 部分唯一索引去重、Post 状态 CheckConstraint、`created_at` 服务端默认值，以及 P1 读路径的公开性过滤、keyset 分页无重复无遗漏、游标错误、草稿隐藏、富文本 JSON 原样返回。
