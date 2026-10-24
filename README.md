# 用户意见反馈系统（FeedLog-like）

反馈（Post）与更新日志（Changelog）两大核心模块的自托管实现。完整方案见 [docs/实施方案.md](docs/实施方案.md)。

## 仓库结构

```
backend/    FastAPI + SQLAlchemy 2.x async + Alembic
frontend/   Vite 8 + Vue 3.5 + TypeScript
deploy/     配置单一来源（deploy/.env）与后续 Compose / Nginx 部署产物
docs/       方案与接口文档
```

## 本地开发

前置：Python 3.12、[uv](https://docs.astral.sh/uv/)、Node 24、pnpm。

### 1. 配置

```bash
cp deploy/.env.example deploy/.env
```

`deploy/.env` 是唯一配置来源（不存在 `backend/.env`），本地默认使用 SQLite。

### 2. 后端

```bash
cd backend
uv sync
uv run alembic upgrade head        # 唯一 schema 权威，禁止 create_all
uv run python -m scripts.seed_dev  # 可选：写入开发种子数据与演示媒体
uv run uvicorn app.main:app --reload --port 8000
```

验证：<http://127.0.0.1:8000/api/health>、<http://127.0.0.1:8000/api/docs>

### 3. 前端

```bash
cd frontend
pnpm install
pnpm dev
```

验证：<http://localhost:5173>（`/api` 由 Vite 代理到 `http://127.0.0.1:8000`）。

### 4. 测试

```bash
cd backend && uv run pytest
cd frontend && pnpm build
```

## 分阶段进度

| 阶段 | 状态 | 说明 |
|---|---|---|
| P0 骨架 | ✅ 本地 | Alembic 初始迁移（SQLite 已验证 / Postgres 方言离线渲染）、API 骨架与 `/api/health`、Vite + Vue 骨架；Docker Compose 与 Nginx 反代按计划延后 |
| P1 读路径 | ✅ 本地 | 看板 / 反馈 / 更新日志列表与详情、keyset 分页、Tiptap JSON 白名单渲染（含图片与 MP4）、匿名可读全部公开内容；Docker / Nginx 仍延后 |
| P2 写路径 + 匿名 + 视频 | ⬜ | |
| P3 SSO + 角色 + 状态机 + 评论 | ⬜ | |
| P4 加固 + CI | ⬜ | |

## 已实现接口（P1）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查（含数据库探活） |
| GET | `/api/v1/boards` | 公开看板列表（含反馈数） |
| GET | `/api/v1/boards/{slug}` | 看板详情 |
| GET | `/api/v1/boards/{slug}/posts?limit=&cursor=` | 看板内反馈列表，keyset 分页 |
| GET | `/api/v1/posts/{id}` | 反馈详情（含 Tiptap JSON 与看板信息） |
| GET | `/api/v1/changelogs?limit=&cursor=` | 已发布更新日志列表（草稿对匿名不可见） |
| GET | `/api/v1/changelogs/{id}` | 更新日志详情 |

错误统一为 `{ "detail": ..., "code": ... }`；分页游标无效返回 400 `INVALID_CURSOR`。
