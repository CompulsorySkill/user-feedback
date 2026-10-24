# 用户意见反馈系统（FeedLog-like）

反馈（Post）与更新日志（Changelog）两大核心模块的自托管实现。完整方案见 [docs/实施方案.md](docs/实施方案.md)。
产品面向 PC Web 用户，不考虑移动端适配。

## 仓库结构

```
backend/    FastAPI + SQLAlchemy 2.x async + Alembic
frontend/   Vite 8 + Vue 3.5 + TypeScript
deploy/     配置单一来源（deploy/.env）与后续 Compose / Nginx 部署产物
docs/       方案、API / SSO 文档与生产运维手册
```

## 本地开发

前置：Python 3.12、[uv](https://docs.astral.sh/uv/)、Node 24、pnpm，以及本机 RustFS（S3 兼容，默认 `127.0.0.1:9000`）。

### 1. 配置

```bash
cp deploy/.env.example deploy/.env
```

`deploy/.env` 是唯一配置来源（不存在 `backend/.env`）。本地默认 SQLite，并需要填写：

```dotenv
PUBLIC_ORIGIN=http://127.0.0.1:5173
RUSTFS_ENDPOINT_INTERNAL=http://127.0.0.1:9000
RUSTFS_ENDPOINT_PUBLIC=http://127.0.0.1:5173
RUSTFS_ACCESS_KEY=...
RUSTFS_SECRET_KEY=...
```

`RUSTFS_ENDPOINT_PUBLIC` 必须与浏览器实际访问的站点同源，否则 SigV4 签名对不上。

### 2. 后端

```bash
cd backend
uv sync
uv run alembic upgrade head            # 唯一 schema 权威，禁止 create_all
uv run python -m scripts.bootstrap_storage  # 建 bucket=storage 并开启匿名只读
uv run python -m scripts.seed_dev      # 可选：种子数据 + 演示图片/MP4 上传 RustFS
uv run uvicorn app.main:app --reload --port 8000
```

验证：<http://127.0.0.1:8000/api/health>、<http://127.0.0.1:8000/api/docs>

### 3. 前端

```bash
cd frontend
pnpm install
pnpm dev
```

访问 <http://127.0.0.1:5173>（`/api` 代理后端，`/storage` 代理 RustFS 并透传 Range）。

本地联调 SSO：用 `deploy/.env` 里的密钥签发 5 分钟 token，再打开
`/api/sso/jwt?token=<token>&return_to=/b/product`，登录成功后头部会显示用户名与管理员徽标。
`ADMIN_EMAILS` 中的邮箱登录即为管理员。

### 4. 测试

```bash
cd backend && uv run pytest
cd frontend && pnpm build
cd frontend && pnpm smoke:p2   # 浏览器冒烟：直传 + 发帖 + 投票（需本地服务与 Edge）
cd frontend && pnpm smoke:p3   # 浏览器冒烟：SSO 登录 + 状态流转 + 评论 + 更新日志发布
```

## 分阶段进度

| 阶段 | 状态 | 说明 |
|---|---|---|
| P0 骨架 | ✅ 本地 | Alembic 初始迁移（SQLite 已验证 / Postgres 方言离线渲染）、API 骨架与 `/api/health`、Vite + Vue 骨架；Docker Compose 与 Nginx 反代按计划延后 |
| P1 读路径 | ✅ 本地 | 看板 / 反馈 / 更新日志列表与详情、keyset 分页、Tiptap JSON 白名单渲染（含图片与 MP4）、匿名可读全部公开内容 |
| P2 写路径 + 匿名 + 视频 | ✅ 本地 | 匿名签名 cookie、RustFS presign 直传（图片 / MP4）、匿名发帖、投票与取消、数据库限流、富文本媒体归属校验；Docker / Nginx 仍延后 |
| P3 SSO + 角色 + 状态机 + 评论 | ✅ 本地 | HS256 SSO 登录与会话、`ADMIN_EMAILS` 角色、匿名数据合并、Post 状态机与编辑权限、更新日志管理员写、3 层楼中楼评论 |
| P4 加固 + CI | ✅ 本地（Docker 镜像待启用） | 安全头 / SSO 日志脱敏 / 富文本白名单与体积上限、限流清理、8.2 验收补齐、Postgres 迁移演练（16.9 实跑 upgrade/downgrade + API 冒烟）、双 CI workflow（镜像任务随 Docker 阶段启用）、`docs/sso.md` 与 `docs/api.md` |

近期加固（A2–A5）：会话自动续期（`X-Session-Expired` + refresh 重放）、POST SSO 登录（token 不进 URL）、
匿名合并失败降级、生产配置/备份恢复演练。运维步骤见 [docs/ops.md](docs/ops.md)。

## 已实现接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查（含数据库探活） |
| GET | `/api/v1/boards` | 公开看板列表（含反馈数） |
| GET | `/api/v1/boards/{slug}` | 看板详情 |
| GET | `/api/v1/boards/{slug}/posts?limit=&cursor=` | 看板内反馈列表，keyset 分页；支持 `status=` 筛选与 `sort=recent\|top` |
| POST | `/api/v1/boards/{slug}/posts` | 发布反馈（`201`，匿名或登录）；可带自定义昵称与浏览器环境信息 |
| GET | `/api/v1/posts/{id}` | 反馈详情（含 Tiptap JSON、看板、`is_author`） |
| PATCH | `/api/v1/posts/{id}` | 编辑反馈（作者非关闭态 / 管理员） |
| PATCH | `/api/v1/posts/{id}/status` | 状态流转（管理员任意，作者仅单向关闭） |
| POST | `/api/v1/posts/{id}/vote` | 投票（幂等，关闭后拒绝） |
| DELETE | `/api/v1/posts/{id}/vote` | 取消投票（幂等） |
| GET | `/api/v1/posts/{id}/comments` | 评论扁平列表（含 `parent_id`） |
| POST | `/api/v1/posts/{id}/comments` | 发表评论（≤3 层，超出挂根并「回复 @xxx」） |
| POST | `/api/v1/uploads/presign` | 获取 presigned PUT（图片 / MP4，≤100MB） |
| GET | `/api/v1/changelogs?limit=&cursor=` | 已发布更新日志列表；管理员可用 `include_drafts=true` |
| POST/PATCH/DELETE | `/api/v1/changelogs[/{id}]` | 更新日志写（仅管理员） |
| POST | `/api/v1/changelogs/{id}/publish`、`/unpublish` | 发布 / 撤回（仅管理员） |
| GET | `/api/sso/jwt?token=&return_to=` | SSO 跳转登录（失败降级匿名） |
| POST | `/api/sso/jwt` | SSO 登录（token 走 body，不进 URL） |
| GET/POST | `/api/v1/auth/me`、`/refresh`、`/logout` | 当前身份、刷新、登出 |
| GET/POST | `/api/v1/auth/capabilities`、`/dev-login` | 登录能力；开发环境快速登录（生产 404） |

错误统一为 `{ "detail": ..., "code": ... }`；分页游标无效返回 400 `INVALID_CURSOR`，
限流返回 429 `RATE_LIMITED`，伪造媒体引用返回 400 `INVALID_CONTENT`。

权限矩阵、状态机、上传契约见 [docs/api.md](docs/api.md)；SSO 对接与管理员维护见 [docs/sso.md](docs/sso.md)。

前端 `/login` 提供两种登录方式：SSO token 粘贴（生产可用）与开发环境快速登录（仅 `ENVIRONMENT=development`，邮箱命中 `ADMIN_EMAILS` 即管理员）。

## Postgres 迁移演练（P4）

`DATABASE_URL` 指向 Postgres 后直接运行迁移链，无需改代码：

```bash
$env:DATABASE_URL="postgresql+asyncpg://postgres:test@127.0.0.1:5432/feedback"
uv run alembic upgrade head
uv run alembic downgrade base && uv run alembic upgrade head
```

CI 的 backend workflow 使用 `postgres:16-alpine` service 执行同样的 upgrade / downgrade 往返，再跑 SQLite 测试。
