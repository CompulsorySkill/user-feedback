# backend

FastAPI + SQLAlchemy 2.x（async）+ Alembic。schema 唯一权威是 Alembic，**禁止 `create_all`**。

## 目录

```
app/
  api/          路由层（/api/health、/api/v1/*）
  core/         config / db / errors / pagination / identity / rate_limit / storage
  models/       SQLAlchemy 模型（12 张表）
  schemas/      Pydantic v2 请求 / 响应模式
  services/     业务规则（公开性、分页、匿名写、富文本校验、投票）
  repositories/ 数据访问（SQLAlchemy 查询）
  main.py       应用入口（lifespan 内启停限流清理任务）
alembic/        迁移环境与版本
scripts/        RustFS 初始化、开发种子数据与上传对象清理
tests/          pytest（独立 SQLite 库 + 完整迁移链）
```

## 本地运行

配置来自仓库根的 `deploy/.env`（由 `pydantic-settings` 的 `env_file` 指向，不存在 `backend/.env`）。
本地需要先启动 RustFS（默认 `http://127.0.0.1:9000`）并填好凭证。

```bash
uv sync
uv run alembic upgrade head
uv run python -m scripts.bootstrap_storage  # bucket=storage + 匿名只读策略
uv run uvicorn app.main:app --reload --port 8000
```

- 健康检查：<http://127.0.0.1:8000/api/health>
- OpenAPI：<http://127.0.0.1:8000/api/docs>

种子数据（看板 / 18 条反馈 / 更新日志，含演示图片与 MP4，会一并上传 RustFS）：

```bash
uv run python -m scripts.seed_dev          # 已有数据则跳过
uv run python -m scripts.seed_dev --reset  # 清空业务表后重建
```

清理超过 24 小时且未被任何反馈 / 更新日志引用的上传记录与 RustFS 对象（建议每日 cron；
单次最多删除 200 条，继续向后扫描）：

```bash
uv run python -m scripts.cleanup_uploads --dry-run   # 只统计
uv run python -m scripts.cleanup_uploads             # 删除记录 + 对象
```

只处理 `uploads` 表中有 presign 记录的对象，不做 bucket 全量扫描；管理员也可在
`/admin/audit` 或 `POST /api/v1/admin/uploads/cleanup` 手动触发。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/boards` | 公开看板 + 反馈数 |
| GET | `/api/v1/boards/{slug}` | 看板详情（私有/不存在 → 404 `BOARD_NOT_FOUND`） |
| GET | `/api/v1/boards/{slug}/posts` | keyset 分页；`status=`、`sort=recent\|top`、`q=`、重复 `tag=`（OR） |
| POST | `/api/v1/boards/{slug}/posts` | 匿名发帖；校验富文本、媒体归属与标签（≤5），`201` |
| GET | `/api/v1/posts` | 全部公开看板聚合列表；`board=` / `status=` / `sort=` / `q=` / 重复 `tag=`，keyset 分页 |
| GET | `/api/v1/site` | 站点名称（`APP_NAME`） |
| GET | `/api/v1/tags` | 内置标签（含使用数）；`include_custom=true` 返回全部标签 |
| GET / POST / DELETE | `/api/v1/admin/tags[/{id}]` | 管理员标签维护；删除会解除全部帖子关联 |
| GET | `/api/v1/admin/audit-logs` | 审计日志（`before_id` keyset、`action=` 筛选） |
| POST | `/api/v1/admin/uploads/cleanup` | 清理超期未引用上传对象（`dry_run` 可预演） |
| GET | `/api/v1/admin/boards` | 管理员看板列表（含未公开） |
| POST / PATCH / DELETE | `/api/v1/admin/boards[/{id}]` | 管理员增改删；slug 冲突 409 `BOARD_SLUG_TAKEN`；非空看板默认 409 `BOARD_NOT_EMPTY`，`?force=true` 级联删除反馈/评论/投票 |
| GET | `/api/v1/posts/{id}` | 反馈详情，私有看板内反馈同样 404 |
| POST | `/api/v1/posts/{id}/vote` | 匿名投票（幂等；`closed` → 403 `POST_CLOSED`） |
| DELETE | `/api/v1/posts/{id}/vote` | 取消投票（幂等） |
| POST | `/api/v1/uploads/presign` | presigned PUT（图片 / MP4；附件任意类型仅管理员，≤100MB） |
| GET | `/api/v1/changelogs` | 已发布；管理员可用 `include_drafts=true` |
| GET | `/api/v1/changelogs/{id}` | 草稿 → 404（非管理员）；含附件元数据 |
| GET | `/api/v1/changelogs/{id}/attachments/{attachment_id}` | 下载附件；草稿仅管理员，强制 attachment |
| GET | `/api/v1/auth/capabilities` | 登录能力（是否开放开发快速登录 / 管理员密码登录） |
| POST | `/api/v1/auth/dev-login` | 仅 development 环境；生产 404 |
| POST | `/api/v1/auth/admin-login` | 管理员邮箱 + 密码登录；需 `ADMIN_EMAILS` + `ADMIN_PASSWORD`，未配置 404 |

游标编码见 `app/core/pagination.py`：`recent` 用 `base64url({"t": created_at, "i": uuid})`，`top` 用 `{"v": vote_count, "i": uuid}`；两种排序各自维护游标，切换排序/筛选时必须丢弃旧游标。无效游标返回 400 `INVALID_CURSOR`。

## 匿名身份与写路径（P2）

- **匿名 cookie**：`feedlog_anonymous=<token>.<hmac>`，`HttpOnly; SameSite=Lax`，生产加 `Secure`；DB 只存 `anon:<token>`，不依赖 IP / UA。
- **上传**：`POST /uploads/presign` 校验 purpose / content-type / size 后，用站点同源地址（`PUBLIC_ORIGIN`）+ path-style + `s3v4` 生成 URL，并写入 `Uploads` 归属；key 由服务端生成（`uploads/{uuid}.<ext>`）。
- **更新日志附件**：`changelog_attachment` purpose 仅管理员可用，不限制 content-type；对象按
  `application/octet-stream` 存储，附件表记录原文件名/类型/大小。下载接口强制
  `Content-Disposition: attachment`，草稿附件仅管理员可访问；公开详情不返回 object_key。
- **富文本校验**：`doc` 顶层、深度 ≤ 8、节点 ≤ 2000；`image` / `video` 的 `src` 必须是当前身份的 `Upload` 记录且 purpose/类型匹配，否则 400 `INVALID_CONTENT`。
- **限流**：`rate_limit_counters` 固定窗口 UPSERT，vote 20/min、post 5/10min、comment 10/min、管理员密码登录 10/5min；每小时清理 1 小时前的窗口。
- **投票**：匿名唯一索引去重，计数与投票同事务维护；`closed` 与关闭访客投票的看板直接拒绝。
- **上传清理**：`Upload` 仅代表 presign 归属；清理任务扫描反馈 / 更新日志 JSON 与
  `changelog_attachments`，删除超过 `UPLOAD_CLEANUP_GRACE_HOURS`（默认 24）仍未被引用的
  RustFS 对象与 `Upload` 行。

## SSO / 会话 / 权限（P3）

- `GET /api/sso/jwt`：HS256 多密钥（`SSO_SECRETS`），要求 `exp` + `email`；`return_to` 仅站内相对路径，非法值回退默认；校验失败不阻断，降级匿名并记 warning。
- JIT 用户 + `ADMIN_EMAILS` 同步 role；登录时在同一事务内合并匿名反馈与匿名票，并清除匿名 cookie。
- access（15 分钟）/ refresh（7 天）均为 HttpOnly cookie；`/api/v1/auth/me`、`/refresh`（轮换）、`/logout`。
- Post 状态机：管理员任意流转、作者仅单向关闭；`closed` 冻结编辑 / 投票 / 评论，管理员可重开。
- 更新日志写端点全部 `require_admin`；草稿仅管理员可见，撤回保留 `published_at`。
- 评论：扁平返回 `parent_id`，深度 ≤3，超出挂到根评论并前缀「回复 @xxx」；关闭与访客开关校验、计数同事务、10/min 限流。
- 审计：管理员对看板 / 标签 / 更新日志 / 反馈的写操作与上传清理写入 `audit_logs`
  （actor 邮箱快照、IP、目标、detail）；失败 best-effort，不阻塞主流程。查询接口仅管理员可用。

## 数据库

`DATABASE_URL` 单变量驱动：

| 环境 | 值 |
|---|---|
| 本地 | `sqlite+aiosqlite:///./feedback.db` |
| 生产 | `postgresql+asyncpg://...` |

SQLite 连接自动附加 `check_same_thread=False`、`journal_mode=WAL`、`busy_timeout=5000`、`foreign_keys=ON`。
Postgres 连接固定会话时区为 UTC（业务层统一使用 naive UTC）。迁移使用方言感知类型（`Uuid` / `DateTime(timezone=True)` / `JSON`）与 `sqlite_where` / `postgresql_where` 渲染部分唯一索引。

```bash
# 生成迁移（改完模型后）
uv run alembic revision --autogenerate -m "describe change"
# 校验模型与迁移是否一致
uv run alembic check
# 离线渲染 Postgres DDL（无需数据库）
$env:DATABASE_URL="postgresql+asyncpg://feedback:pw@localhost:5432/feedback"
uv run alembic upgrade head --sql
```

P4 已在本机 Postgres 16.9 上实跑 `upgrade head → downgrade base → upgrade head`，并用 PG 实例跑通健康检查、keyset 分页、匿名发帖/投票/评论与管理员更新日志发布。

## 测试

```bash
uv run pytest -q
```

用例覆盖：`/api/health`、初始迁移与降级、Vote 部分唯一索引、Post 状态约束、P1 读路径（公开性过滤 / keyset 分页 / 草稿隐藏 / 时间序列化）、P2 写路径（匿名 cookie 签名与复用、presign 类型与大小校验、发帖媒体归属、伪造 src 拒绝、投票幂等与关闭校验、post/vote 限流）、P3（SSO/角色/return_to/刷新/登出、匿名合并、状态机、编辑冻结、更新日志生命周期、评论层级与限流）、P4 加固（安全头、SSO token 日志脱敏、限流清理、富文本白名单/体积/危险链接、跨身份媒体、管理员重开），以及列表状态筛选 / 最热排序与游标 / 开发快速登录 / 作者编辑与历史媒体保留、标签与站点配置（含按看板限定标签计数、未公开看板不泄露计数）。A2–A5 另覆盖会话过期标记与 refresh、POST SSO、合并失败降级、生产配置校验、Secure cookie、SSO 密钥轮换与 ADMIN_EMAILS 升降级、管理员邮箱+密码登录（开发/生产、显示名可选、错误密码与限流）。当前 **145 passed**。

## Docker

```bash
docker build -t feedback-backend .
```

镜像启动时先执行 `alembic upgrade head`，再以 2 个 worker 启动 uvicorn；
非 root UID 10001 运行，健康检查走 `/api/health`。完整四服务编排见
[`deploy/docker-compose.yml`](../deploy/docker-compose.yml)，入口为 Caddy。
