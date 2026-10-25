# API 与权限说明

前缀 `/api/v1`（SSO 为 `/api/sso`）。所有错误统一为：

```json
{ "detail": "看板不存在", "code": "BOARD_NOT_FOUND" }
```

## 1. 身份模型

| 身份 | 来源 | 能做什么 |
|---|---|---|
| 未识别 | 无 cookie | 只读公开内容 |
| 匿名 | 首次写操作签发 `feedlog_anonymous`（HttpOnly 签名 cookie） | 发帖 / 投票 / 评论（受看板匿名开关限制）、上传 |
| 登录用户 | SSO 签发 access + refresh cookie | 匿名全部能力 + 编辑/关闭自己的反馈 |
| 管理员 | `ADMIN_EMAILS` 命中的登录用户 | 状态任意流转、编辑任意反馈、更新日志全部写操作 |

登录用户的角色每次请求从数据库读取，不依赖 JWT 中的 role 声明。

## 2. 权限矩阵

| 操作 | 未识别 | 匿名 | 登录用户 | 管理员 |
|---|---|---|---|---|
| 浏览公开看板 / 反馈 / 已发布日志 | ✅ | ✅ | ✅ | ✅ |
| 浏览草稿日志 | ❌ | ❌ | ❌ | ✅ |
| 发帖 | ❌ | 看板 `allow_guest_posting` | ✅ | ✅ |
| 投票 / 取消 | ❌ | 看板 `allow_guest_voting` | ✅ | ✅ |
| 评论 | ❌ | 看板 `allow_guest_commenting` | ✅ | ✅ |
| 编辑自己的反馈 / 标签 | ❌ | ❌（匿名无作者身份） | 非 closed 时 ✅ | ✅（含 closed） |
| 变更状态 | ❌ | ❌ | 仅单向关闭自己的反馈 | 任意流转（含重开） |
| 维护内置标签 | ❌ | ❌ | ❌ | ✅ |
| 查看审计日志 / 清理上传对象 | ❌ | ❌ | ❌ | ✅ |
| 更新日志写 / 发布 | ❌ | ❌ | ❌ | ✅ |

未登录访问管理员前端路由返回 **404**（不暴露入口）；后端返回 403 `ADMIN_REQUIRED`。

## 3. Post 状态机

状态：`open / planned / in_progress / completed / closed`。

| 当前状态 | 管理员可转为 | 作者可转为 |
|---|---|---|
| open | 任意 | closed |
| planned | 任意 | closed |
| in_progress | 任意 | closed |
| completed | 任意 | closed |
| closed | 任意（含重开 open） | ❌ |

- 匿名 Post 没有作者，只有管理员能改状态。
- `closed` 冻结：不可编辑、不可新投票、不可新评论；已有数据保留，管理员重开后恢复。
- 状态变化只更新 `status` 与 `updated_at`，不保留逐条版本历史；管理员与作者的状态变更会写入审计日志（`post.status`）。

## 4. 标签

- 发帖与编辑请求都接受 `tags: string[]`（≤5 个，单个 ≤24 字符）；发帖时匿名作者也可直接创建标签。
- 标签名按 `casefold` 归一化去重，展示保留首次写入的写法；同名标签全局复用。
- 作者可修改自己反馈的标签（`closed` 除外）；管理员可修改任意反馈的标签。
- 管理员可在 `/admin/tags` 维护**内置标签**；内置标签会出现在发布/编辑反馈的推荐列表中，普通标签不会。
- 公开接口 `GET /tags` 默认只返回内置标签；`GET /tags?include_custom=true` 返回全部标签，
  供列表筛选器使用。管理员 `GET /admin/tags` 同样返回全部标签及使用数。
- `post_count` 只统计**公开看板**的反馈；带 `board=<slug>` 时只统计该看板的反馈
  （筛选器 badge 因此与当前看板一致，不再显示全站计数）。
- 删除标签会从所有反馈上移除关联，但不会删除反馈本身。

### 标签筛选

反馈列表（`/posts` 与 `/boards/{slug}/posts`）支持重复查询参数 `tag=`：

```http
GET /api/v1/posts?tag=Bug&tag=%E6%80%A7%E8%83%BD&sort=recent
```

- 标签名按 `casefold` 匹配，大小写不敏感；最多同时选 5 个，超过返回 `400 TAG_LIMIT`。
- 多个标签之间是 **OR**（命中任一标签即返回），可与 `status`、`q`、`sort`、`board` 组合。
- 不存在的标签返回空列表，不报错。
- 切换筛选条件时必须丢弃旧 `cursor`。

## 5. 更新日志语义

- 创建即为草稿：`is_published=false`、`published_at=null`，仅管理员可见。
- 发布：`is_published=true`、`published_at=now()`。
- 撤回：`is_published=false`，**保留 `published_at`** 供审计。
- 编辑即覆盖，无版本历史。

## 6. 分页

keyset 分页。响应：

```json
{ "items": [ ... ], "next_cursor": "eyJ0IjoiMjAyNi0xMC0yNFQxMjowMDowMCIsImkiOiJ1dWlkIn0" }
```

- `limit` 1–100（默认 20；前端反馈列表用 10）。
- 下一页传 `cursor=<next_cursor>`；`next_cursor=null` 表示结束。
- 游标无效返回 `400 INVALID_CURSOR`。

反馈列表额外支持：

| 参数 | 值 | 说明 |
|---|---|---|
| `status` | `open / planned / in_progress / completed / closed` | 按状态筛选；非法值 422 |
| `sort` | `recent`（默认）/ `top` | `recent` 按 `(created_at, id)`；`top` 按 `(vote_count, id)` 降序 |
| `q` | 1–100 字符 | 按标题与摘要做大小写不敏感模糊匹配；`%`/`_` 按字面量处理 |
| `tag` | 可重复，≤5 个 | 标签筛选，大小写不敏感，多个标签为 OR |

两种排序各自使用对应的 keyset 游标，切换排序或筛选时必须丢弃旧 `cursor`。搜索、状态、标签与排序可以组合使用，游标同样需要丢弃。

## 7. 限流

固定窗口 + 数据库计数表（无 Redis），多 worker 共享：

| action | 窗口 | 上限 | 触发接口 |
|---|---|---|---|
| vote | 1 分钟 | 20 | POST/DELETE `/posts/{id}/vote` |
| post | 10 分钟 | 5 | POST `/boards/{slug}/posts` |
| comment | 1 分钟 | 10 | POST `/posts/{id}/comments` |

超限返回 `429 RATE_LIMITED`，事务回滚；每小时清理 1 小时前的窗口。

## 8. 上传与富文本

### presign

`POST /api/v1/uploads/presign`

```json
{ "filename": "cover.png", "content_type": "image/png", "purpose": "post_image", "size": 123456 }
```

- purpose：`post_image` / `post_video` / `changelog_image` / `changelog_video` / `changelog_attachment`
- 图片：PNG / JPEG / WebP / GIF；视频：仅 `video/mp4`；单文件 ≤ `UPLOAD_MAX_BYTES`（默认 100MB）
- `changelog_attachment` 仅管理员可用，**不限制 content-type**；对象以 `application/octet-stream` 存储，
  下载走受控接口并强制 `Content-Disposition: attachment`
- 返回 `object_key`、`upload_url`、`method: "PUT"`、`headers`
- 浏览器 `PUT` 时必须原样携带返回的 `Content-Type`（参与 SigV4 签名）；`object_key` 由服务端生成

### 更新日志附件

创建 / 编辑更新日志时传 `attachments`（最多 10 个），先通过 presign 上传，再提交元数据：

```json
{
  "title": "v1.1 发布说明",
  "content": { "type": "doc", "content": [] },
  "attachments": [
    { "object_key": "uploads/<uuid>.bin", "filename": "release.zip" }
  ]
}
```

- 附件必须是**当前管理员**的 `Upload`，且 purpose 为 `changelog_attachment`；否则 400 `INVALID_ATTACHMENT`
- `filename` 仅作下载展示，服务端会去掉路径与控制字符；真实类型 / 大小取自 Upload 记录
- 附件下载：`GET /v1/changelogs/{id}/attachments/{attachment_id}`
  - 强制 `application/octet-stream` + `attachment`，防止 HTML/SVG 等在同源内联执行
  - 草稿附件仅管理员可下载；已发布日志的附件公开可下载
  - 公开详情响应不返回 `object_key`，避免绕过受控下载接口

### 富文本校验

- 顶层必须 `doc`；payload ≤ 256KB；深度 ≤ 8；节点 ≤ 2000；单文本 ≤ 20000 字符
- 节点与 mark 白名单（未知节点 / 标记直接拒绝）；链接仅 http(s)
- `image` / `video` 的 `src` 必须是**当前身份**的 `Upload`，且 purpose / content_type 匹配，否则 `400 INVALID_CONTENT`
- 编辑时允许保留原内容中已存在的媒体 key（历史数据或他人上传），新增媒体仍必须是编辑者自己的 `Upload`

### 未引用对象清理

`POST /api/v1/admin/uploads/cleanup?dry_run=false&grace_hours=24`（管理员）

- 扫描 `uploads` 表中创建超过 `grace_hours`（默认 24，最大 720）的记录；
- 只保留在反馈 / 更新日志富文本或 `changelog_attachments` 中出现的 object key；
- 未引用对象从 RustFS 删除，并删除对应 `Upload` 行；单次最多删除 200 条，
  但会继续向后扫描（已引用记录不会阻塞后续孤儿对象）；
- `dry_run=true` 只返回可清理数量，不删除任何对象；
- 也可用 CLI `python -m scripts.cleanup_uploads` 执行并写入 `upload.cleanup` 审计记录。

## 9. 审计日志

`GET /api/v1/admin/audit-logs?limit=50&before_id=&action=`（管理员）

```json
{
  "items": [
    {
      "id": 42,
      "actor_email": "admin@example.com",
      "action": "board.update",
      "target_type": "board",
      "target_id": "3",
      "detail": { "name": "新名称" },
      "ip": "203.0.113.10",
      "created_at": "2026-10-25T00:00:00+00:00"
    }
  ],
  "next_cursor": "42"
}
```

- 仅追加，不随目标对象删除；actor 被删除后保留邮箱快照。
- 记录动作：`board.create/update/delete`、`tag.create/delete`、`post.update`（管理员）、
  `post.status`、`changelog.create/update/delete/publish/unpublish`、`upload.cleanup`。
- `action` 精确筛选；`before_id` 为上一页最后一条的 `id`；按 `id` 倒序。
- 审计写入失败 best-effort：记录服务端日志，不回滚已提交的业务操作。

## 10. 端点一览

| 方法 | 路径 | 权限 |
|---|---|---|
| GET | `/health` | 公开 |
| GET | `/v1/boards`、`/v1/boards/{slug}` | 公开 |
| GET | `/v1/boards/{slug}/posts` | 公开 |
| POST | `/v1/boards/{slug}/posts` | 匿名 / 登录；可带 `tags` |
| GET | `/v1/site` | 公开（`APP_NAME`） |
| GET | `/v1/tags` | 公开；内置标签（`include_custom=true` 含用户标签，`board=<slug>` 限定计数范围） |
| GET | `/v1/admin/tags` | 管理员；全部标签与使用数 |
| GET | `/v1/admin/audit-logs` | 管理员；审计日志 |
| POST | `/v1/admin/uploads/cleanup` | 管理员；清理未引用上传对象 |
| POST | `/v1/admin/tags` | 管理员；新增内置标签 |
| DELETE | `/v1/admin/tags/{id}` | 管理员；删除标签并解除帖子关联 |
| GET | `/v1/posts` | 公开；全部公开看板聚合，支持 `board=`、`status=`、`sort=`、`q=`、`tag=` |
| GET | `/v1/admin/boards` | 管理员 |
| POST / PATCH / DELETE | `/v1/admin/boards[/{id}]` | 管理员；非空看板默认 `409 BOARD_NOT_EMPTY`，带 `force=true` 级联删除 |
| GET | `/v1/posts/{id}` | 公开（返回 `is_author`） |
| PATCH | `/v1/posts/{id}` | 作者 / 管理员 |
| PATCH | `/v1/posts/{id}/status` | 作者（仅关闭）/ 管理员 |
| POST / DELETE | `/v1/posts/{id}/vote` | 匿名 / 登录 |
| GET | `/v1/posts/{id}/comments` | 公开 |
| POST | `/v1/posts/{id}/comments` | 匿名 / 登录 |
| POST | `/v1/uploads/presign` | 图片 / 视频：匿名 / 登录；更新日志附件：仅管理员 |
| GET | `/v1/changelogs`、`/v1/changelogs/{id}` | 公开；草稿仅管理员 |
| POST / PATCH / DELETE | `/v1/changelogs[/{id}]` | 管理员；请求可带 `attachments` |
| GET | `/v1/changelogs/{id}/attachments/{attachment_id}` | 公开（草稿仅管理员）；强制下载 |
| POST | `/v1/changelogs/{id}/publish`、`/unpublish` | 管理员 |
| GET | `/sso/jwt?token=&return_to=` | 公开（产品侧跳转，失败降级匿名） |
| POST | `/sso/jwt` | 公开；`{token, return_to}` 换取会话，返回 `redirect_to` |
| GET | `/v1/auth/me`、`/capabilities` | 公开（按 cookie） |
| POST | `/v1/auth/refresh`、`/logout` | 公开（按 cookie） |
| POST | `/v1/auth/dev-login` | 仅 `ENVIRONMENT=development`；生产返回 404 |
| POST | `/v1/auth/admin-login` | 公开；`{email, password, name?}`，邮箱需命中 `ADMIN_EMAILS`、密码比对 `ADMIN_PASSWORD`；未配置时 404，失败 401 `INVALID_CREDENTIALS`，10 次 / 5 分钟 / IP 限流 |

完整请求/响应模型以运行中的 `/api/docs`（OpenAPI）为准。

## 11. 会话续期

access token 过期（默认 15 分钟）时，携带旧 access cookie 的响应会附加
`X-Session-Expired: 1`。前端收到后调用 `POST /v1/auth/refresh` 并重放原请求一次，
用户无感；刷新失败则降级匿名并显示登录入口。

SSO 登录时若匿名数据合并失败：不阻断登录，记录日志并保留匿名 cookie，
账号会话照常签发，便于后续重试。
