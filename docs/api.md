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
| 编辑自己的反馈 | ❌ | ❌（匿名无作者身份） | 非 closed 时 ✅ | ✅（含 closed） |
| 变更状态 | ❌ | ❌ | 仅单向关闭自己的反馈 | 任意流转（含重开） |
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
- 状态变化只更新 `status` 与 `updated_at`，不记录历史。

## 4. 更新日志语义

- 创建即为草稿：`is_published=false`、`published_at=null`，仅管理员可见。
- 发布：`is_published=true`、`published_at=now()`。
- 撤回：`is_published=false`，**保留 `published_at`** 供审计。
- 编辑即覆盖，无版本历史。

## 5. 分页

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

两种排序各自使用对应的 keyset 游标，切换排序或筛选时必须丢弃旧 `cursor`。

## 6. 限流

固定窗口 + 数据库计数表（无 Redis），多 worker 共享：

| action | 窗口 | 上限 | 触发接口 |
|---|---|---|---|
| vote | 1 分钟 | 20 | POST/DELETE `/posts/{id}/vote` |
| post | 10 分钟 | 5 | POST `/boards/{slug}/posts` |
| comment | 1 分钟 | 10 | POST `/posts/{id}/comments` |

超限返回 `429 RATE_LIMITED`，事务回滚；每小时清理 1 小时前的窗口。

## 7. 上传与富文本

### presign

`POST /api/v1/uploads/presign`

```json
{ "filename": "cover.png", "content_type": "image/png", "purpose": "post_image", "size": 123456 }
```

- purpose：`post_image` / `post_video` / `changelog_image` / `changelog_video`
- 图片：PNG / JPEG / WebP / GIF；视频：仅 `video/mp4`；单文件 ≤ `UPLOAD_MAX_BYTES`（默认 100MB）
- 返回 `object_key`、`upload_url`、`method: "PUT"`、`headers`
- 浏览器 `PUT` 时必须原样携带返回的 `Content-Type`（参与 SigV4 签名）；`object_key` 由服务端生成

### 富文本校验

- 顶层必须 `doc`；payload ≤ 256KB；深度 ≤ 8；节点 ≤ 2000；单文本 ≤ 20000 字符
- 节点与 mark 白名单（未知节点 / 标记直接拒绝）；链接仅 http(s)
- `image` / `video` 的 `src` 必须是**当前身份**的 `Upload`，且 purpose / content_type 匹配，否则 `400 INVALID_CONTENT`
- 编辑时允许保留原内容中已存在的媒体 key（历史数据或他人上传），新增媒体仍必须是编辑者自己的 `Upload`

## 8. 端点一览

| 方法 | 路径 | 权限 |
|---|---|---|
| GET | `/health` | 公开 |
| GET | `/v1/boards`、`/v1/boards/{slug}` | 公开 |
| GET | `/v1/boards/{slug}/posts` | 公开 |
| POST | `/v1/boards/{slug}/posts` | 匿名 / 登录 |
| GET | `/v1/posts/{id}` | 公开（返回 `is_author`） |
| PATCH | `/v1/posts/{id}` | 作者 / 管理员 |
| PATCH | `/v1/posts/{id}/status` | 作者（仅关闭）/ 管理员 |
| POST / DELETE | `/v1/posts/{id}/vote` | 匿名 / 登录 |
| GET | `/v1/posts/{id}/comments` | 公开 |
| POST | `/v1/posts/{id}/comments` | 匿名 / 登录 |
| POST | `/v1/uploads/presign` | 匿名 / 登录 |
| GET | `/v1/changelogs`、`/v1/changelogs/{id}` | 公开；草稿仅管理员 |
| POST / PATCH / DELETE | `/v1/changelogs[/{id}]` | 管理员 |
| POST | `/v1/changelogs/{id}/publish`、`/unpublish` | 管理员 |
| GET | `/sso/jwt?token=&return_to=` | 公开 |
| GET | `/v1/auth/me`、`/capabilities` | 公开（按 cookie） |
| POST | `/v1/auth/refresh`、`/logout` | 公开（按 cookie） |
| POST | `/v1/auth/dev-login` | 仅 `ENVIRONMENT=development`；生产返回 404 |

完整请求/响应模型以运行中的 `/api/docs`（OpenAPI）为准。
