# AGENTS.md

本文件面向在本仓库工作的 AI / 自动化代理，适用于整个仓库。开始修改前先读本文件；
涉及具体接口、部署或 SSO 时，再读对应文档与代码。若本文件与代码不一致，以代码和实际脚本为准，
并顺手修正文档。

## 1. 项目概览

自托管的用户意见反馈系统（FeedLog-like），包含两大模块：

- **反馈（Post）**：看板、状态流转、富文本（图片 / MP4）、匿名或登录发布、投票、三层评论。
- **更新日志（Changelog）**：管理员草稿 / 发布、富文本、任意类型附件下载。

产品面向 **PC Web**，不做移动端适配。单仓结构：

```text
backend/    FastAPI + SQLAlchemy 2.x async + Alembic + pytest
frontend/   Vite 8 + Vue 3.5 + TypeScript + Pinia + Tiptap + Vitest
deploy/     唯一配置来源 deploy/.env，Docker Compose 生产编排
docs/       实施方案、API、SSO、运维文档
```

生产拓扑：Caddy 在 frontend 容器内同域提供 SPA，并反代 `/api/*` 到 backend、
`/storage/*` 到 RustFS；Postgres、RustFS、backend 不直接暴露公网。

## 2. 工具链基线

- Python **3.12**（`>=3.12,<3.13`），依赖与虚拟环境用 **uv** 管理。
- Node **24**，包管理器 **pnpm 11**，锁文件为 `frontend/pnpm-lock.yaml`。
- 前端格式化和静态检查统一用 **OXC**：`oxfmt` + `oxlint`，不要引入 ESLint / Prettier。
- 后端格式遵循 `black`（line-length 88）；测试用 pytest（async mode）。
- 配置只来自环境变量与仓库根 `deploy/.env`，**不存在 `backend/.env`**。

## 3. 常用命令

### 本地准备

```bash
cp deploy/.env.example deploy/.env
# 填写 S3_ACCESS_KEY / S3_SECRET_KEY 等；本地默认 SQLite
```

### 后端

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run python -m scripts.bootstrap_storage   # 初始化 RustFS bucket，首次或换环境时
uv run uvicorn app.main:app --reload --port 8000
```

- 健康检查：`http://127.0.0.1:8000/api/health`
- OpenAPI：`http://127.0.0.1:8000/api/docs`
- 种子数据：`uv run python -m scripts.seed_dev`（`--reset` 清空业务表）

### 前端

```bash
cd frontend
pnpm install
pnpm dev          # http://127.0.0.1:5173
```

`/api` 代理到 `127.0.0.1:8000`，`/storage` 代理到 `127.0.0.1:9000`；
`/storage` 不重写路径、透传 Host 与 Range，签名相关行为不要改。

### 测试与检查

```bash
# 后端（不依赖 Postgres / RustFS / 本地服务）
cd backend && uv run pytest -q

# 前端
cd frontend
pnpm test
pnpm lint
pnpm format:check
pnpm build
```

Windows PowerShell 下设置临时环境变量用 `$env:NAME="value"`。后端测试开启了
`filterwarnings = ["error::DeprecationWarning"]`，不要在测试里全局屏蔽警告。

## 4. 后端结构与约定

### 4.1 分层

```text
app/api/           路由与依赖装配（薄）
app/services/      业务规则、权限校验、事务提交、审计调用
app/repositories/  纯数据访问（SQLAlchemy 查询，不提交事务）
app/models/        ORM 模型
app/schemas/       Pydantic v2 请求 / 响应
app/core/          config / db / errors / pagination / identity / rate_limit / storage
alembic/           迁移环境与版本
scripts/           bootstrap_storage / seed_dev / cleanup_uploads
tests/             每个用例独立 SQLite 库，schema 由迁移链构建
```

规则：

- 路由只做参数解析、调用 service、组织响应；业务规则不要堆在路由里。
- Repository 不 `commit`；由 service 控制事务边界。现有代码中 service 在写操作末尾提交。
- 全链路 async；禁止在请求路径使用同步 SQLAlchemy Session。
- 业务异常统一抛 `AppException(status_code, code="STABLE_CODE", detail="...")`，
  不要抛裸 `HTTPException`。错误响应固定为 `{"detail": ..., "code": ...}`。
- 出参必须声明 Pydantic `response_model`；含时间字段的响应继承 `UTCModel`。
- 业务时间统一 UTC。数据库会话按 UTC 处理，SQLite 存 naive UTC，出参由
  `schemas/common.py` 补上 UTC 时区，不要让前端按本地时间猜测。
- 列表分页使用 keyset cursor（`limit + 1` 判断 `next_cursor`）。切换排序、筛选或搜索时
  必须丢弃旧游标；无效游标返回 400 `INVALID_CURSOR`。
- 权限必须在服务端校验，不能只靠前端隐藏入口。管理员接口使用 `AdminUserDep`；
  `/admin/*` 页面守卫对非管理员返回 404，是前端的产品选择，不是 API 授权依据。

### 4.2 配置

- 配置字段集中在 `app/core/config.py` 的 `Settings`，读取 `deploy/.env`。
- 新增配置时同步更新 `deploy/.env.example` 与 `deploy/.env.production.example`，
  并在 `docs/ops.md` 或相关文档说明。
- `ENVIRONMENT=production` 会强制校验 Postgres、SSO、session、RustFS 配置；
  不要绕过该校验，也不要把开发默认值带进生产。
- 密钥、token、cookie 值不得写入日志、提交记录或前端产物。
- SSO 新代码优先使用 `POST /api/sso/jwt`，避免 token 进入 URL。

### 4.3 数据库与迁移

- **Alembic 是 schema 唯一权威，禁止 `create_all`，禁止启动时自动建表。**
- 修改模型后生成迁移，保持数字前缀命名（当前 head 为 `0006_changelog_attachments`）：

```bash
cd backend
uv run alembic revision --autogenerate --rev-id 0007_<snake_case_name> -m "describe change"
uv run alembic upgrade head
uv run alembic check
```

- 新迁移必须实现可用的 `downgrade()`。在临时库验证 `upgrade head → downgrade base → upgrade head`，
  不要对开发库直接执行 `downgrade base`。
- 使用方言感知类型（`sa.Uuid()`、`DateTime(timezone=True)`、`sa.JSON`），
  部分索引显式提供 `sqlite_where` / `postgresql_where`。
- 模型遵循已有命名约定；新表需明确外键 `ondelete`（如附件 CASCADE，上传对象 RESTRICT）。
- 不引入 `PostRevision` / `ChangelogRevision`；编辑即覆盖。

### 4.4 上传、附件与安全

- 上传走 `POST /api/v1/uploads/presign` + 浏览器直传 RustFS，不让文件流经 backend。
  `object_key` 由服务端生成，presign 时写入 `uploads` 归属记录。
- 富文本只允许白名单节点；`image` / `video` 的 `src` 必须对应当前身份的 Upload，
  且 purpose / content-type 匹配。编辑器里只存 object key。
- 更新日志附件：
  - purpose 为 `changelog_attachment`，**仅管理员**可 presign，不限制 content-type；
  - 存储用 `application/octet-stream`，元数据记录原文件名 / 类型 / 大小；
  - 每条最多 10 个，单文件不超过 `UPLOAD_MAX_BYTES`；
  - 下载走 `GET /api/v1/changelogs/{id}/attachments/{attachment_id}`，强制
    `Content-Disposition: attachment` 与 `nosniff`；
  - 草稿附件仅管理员可下载；公开详情不返回 `object_key`。
- 上传清理只删除超过保留期且未被富文本或 `changelog_attachments` 引用的对象；
  新增引用方式时必须同步更新 `services/upload_cleanup.py`。
- 安全响应头、CORS 白名单、HttpOnly cookie、限流（数据库固定窗口）不要弱化。
- 管理写操作应写审计日志（actor 邮箱快照、IP、target、detail）；审计失败不阻塞主流程。

## 5. 前端结构与约定

### 5.1 分层与数据流

- 页面在 `src/views/`，通用组件在 `src/components/`，组合式逻辑在 `src/composables/`。
- 统一通过 `src/api/client.ts` 发请求；它负责 `{detail, code}` 错误、204、以及
  `X-Session-Expired` 的单次 refresh 重放。不要在页面里另写裸 `fetch('/api/...')`。
  唯一例外是按 presign ticket 直传对象存储。
- 接口类型集中在 `src/api/types.ts`；不要从后端 OpenAPI 自动生成并入库。
- 认证状态在 Pinia `stores/auth`；会话凭证是 HttpOnly cookie，不要写入 localStorage。
- 富文本只按白名单渲染，**禁止 `v-html`**；未知节点只渲染子节点。
- 媒体 JSON 只存 object key，展示统一经 `storageUrl()` 拼 `/storage/`。
- 图标统一 `@tabler/icons-vue`；不引入 Google Fonts，使用系统字体栈。
- 首期不引入 TanStack Query；页面 `setup` 中直接调用 `api/`。

### 5.2 UI 与样式

- 全站只允许 3 档字号：`--fs-display` 32px、`--fs-body` 16px、`--fs-caption` 13px。
  不要在组件里写死 `font-size`；按现有类归入 `styles/typography.css`。
- 控件高度使用 `--control-height`（40px）和 `--control-height-sm`（32px）；
  输入框 44px。新增按钮 / 筛选器 / 排序器 / 投票按钮复用现有类。
- 已确认的布局约定：
  - 搜索框与最近 / 最热排序在同一行，字号一致；
  - 状态筛选与标签筛选的标签对齐；
  - 保持统一页面宽度与 `scrollbar-gutter: stable`，避免长短页切换时跳动；
  - **不要重新引入全站页脚**（站点底部品牌 / 版权条）；帖子详情的操作区
    `post-detail-foot` 不在此列。
- 桌面端优先，不新增移动端断点或触屏交互。
- 支持系统深色模式（`prefers-color-scheme`），新增颜色优先用 `style.css` 中的 CSS 变量。

### 5.3 前端测试

- Vitest + jsdom + `@vue/test-utils`，不依赖浏览器、后端或 RustFS。
- 测试放 `frontend/tests/`，命名 `*.spec.ts`。
- 纯函数（筛选参数、日期、格式、审计动作）优先单测；组件测试覆盖首屏加载、
  路由写入和关键交互。真实 presign / TLS / Range 由部署验收或后端集成测试覆盖。

## 6. 完成标准

按改动类型至少执行：

| 改动 | 必跑 |
|---|---|
| 后端逻辑 / API | `uv run pytest -q` |
| 后端模型 / 迁移 | 上述 + `uv run alembic upgrade head` + `uv run alembic check` |
| 前端 TS / Vue / 样式 | `pnpm test` + `pnpm lint` + `pnpm format:check` + `pnpm build` |
| 接口契约 | 后端测试 + 更新 `docs/api.md` 与 `frontend/src/api/types.ts` |
| 配置项 | 两份 env example + 相关文档 |
| 部署 / Docker | `docker compose config --quiet`（在 `deploy/`，使用生产模板） |

补充要求：

- 修 bug 时加回归测试，测试要能在旧实现上失败。
- 不要为了让测试通过而删除断言、放宽安全校验或跳过迁移。
- 改动涉及多个模块时，前后端测试都要跑；不要只跑单个测试就宣布完成。
- 前端构建包含 `vue-tsc -b`，类型错误必须修复，不能用 `any` / `@ts-ignore` 掩盖。

## 7. CI、发布与版本

- **普通 push 到 `main` 不触发 GitHub Actions。** push 事件中只有推送 `v*` tag 才运行测试
  并构建镜像；PR 仍会按 path filter 运行测试，但不构建镜像。
- 发布流程（仅在用户明确要求发布时执行）：
  1. 同步版本号：`backend/pyproject.toml`、`backend/app/core/config.py:app_version`、
     `frontend/package.json`；
  2. 提交；
  3. 打 tag 并推送：`git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`。
- 稳定 tag 生成 `X.Y.Z`、`X.Y`、`sha-<commit>` 和 `latest`；预发布 tag 不更新 `latest`。
  镜像为多架构（`linux/amd64` + `linux/arm64`），构建后两个架构的 `.tar.gz` 会自动附到同名
  GitHub Release（不存在则创建）。
- GHCR 镜像名必须全小写（workflow 已处理）。
- 版本或 tag 未获明确要求时，不要自行打 tag、推送镜像或修改 `latest`。
- 依赖变更必须同时提交锁文件：后端 `uv.lock`，前端 `pnpm-lock.yaml`。
  使用 `uv add` / `uv remove` 与 `pnpm add` / `pnpm remove`，不要手改锁文件。

## 8. 文档与协作

- 根 `README.md`：项目入口、本地开发、接口摘要、阶段状态。
- `docs/api.md`：接口契约、权限矩阵、状态机。改 API 必须同步。
- `docs/ops.md`：生产部署、备份恢复、清理、回滚。改部署或运维流程必须同步。
- `docs/sso.md`：SSO 对接与密钥轮换。
- `docs/实施方案.md`：早期设计稿，部分工具 / 目录设想未落地（例如其中的
  pre-commit、ruff、eslint/prettier、`features/` 分层）。**以代码、`pyproject.toml`、
  `package.json` 和实际脚本为准**，不要把设计稿当成现状。
- 提交信息沿用现有风格：`feat:` / `fix:` / `chore:` / `ci:` / `style:` + 简短中文描述。
- 不提交 `deploy/.env`、数据库文件、`.dev-storage/`、`node_modules/`、`dist/`。
- 未获明确要求时不要 commit、push 或创建 tag；完成改动后报告改了哪些文件、
  执行了哪些验证、还有哪些未验证项。
