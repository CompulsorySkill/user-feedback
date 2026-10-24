# SSO 对接说明（HS256 JWT 跳转）

面向对接方与运维：JWT 规格、跳转流程、`return_to` 规则、密钥轮换与管理员维护。
本系统只信任自己签发的会话，不信任 SSO token 中的任何角色声明。

## 1. 流程

```
产品A 已登录 → 后端签发 HS256 JWT（建议 5min）→ 302 到
  https://feedback.example.com/api/sso/jwt?token={jwt}&return_to=/b/product
产品A 未登录 → 直接 302 到目标页（不带 token，匿名继续）
反馈系统验证 JWT → JIT 用户 + 角色同步 → 签发本系统会话 → 302 到 return_to
```

- 验证失败（过期、签名错误、缺少 `email`）**不阻断**：降级匿名访问，仅记 warning，不向用户暴露原因。
- SSO token 不落库、不写日志；访问日志中的 `token=` 已由过滤器脱敏为 `token=***`。
- 成功后签发：access JWT（15 分钟）+ refresh token（7 天），均为 `HttpOnly; SameSite=Lax` cookie（生产加 `Secure`）。

## 2. JWT 规格

| 项 | 值 |
|---|---|
| 算法 | **仅 HS256**（其他算法一律拒绝） |
| 密钥 | 64 位 hex 字符串，UTF-8 直接使用，不做十六进制解码 |
| `email`（必需） | 含 `@`，服务端 trim + 小写 |
| `exp`（必需） | Unix 秒，建议 300s |
| `name`（可选） | 最长 128 字符，作为 `display_name` |
| 其他声明 | 忽略；**不信任 token 中的 role / admin 之类声明** |

## 3. return_to 规则

仅允许站内相对路径，非法值静默回退 `SSO_RETURN_TO_DEFAULT`（默认 `/`）：

- 必须以单个 `/` 开头
- 拒绝 `//evil.com`、`https://evil.com`、`/\evil.com`、`javascript:...`
- 使用 `urlparse` 再次校验 scheme / netloc

## 4. 密钥轮换（环境变量 + 重启）

1. 生成新密钥，设置 `SSO_SECRETS='["new","old"]'` → 重启 backend。
2. 通知签发方切换到 `new`，等待 **≥ 5 分钟**（覆盖 token 最长有效期）。
3. 设置 `SSO_SECRETS='["new"]'` → 再次重启。
4. 轮换期间旧 token 仍可验签；顺序为「新在前、旧在后」。

## 5. 管理员维护（ADMIN_EMAILS）

- 唯一授权路径：`ADMIN_EMAILS="alice@example.com,bob@example.com"`（逗号分隔，trim + 小写比较）。
- 修改后**必须重启 backend**；下一次 SSO 登录或 access token 过期重登时生效。
- 角色由本系统根据邮箱计算，与签发方无关。
- 运维注意：清空该变量会导致无人可管理，请保留至少一个有效邮箱并纳入变更记录。

## 6. 匿名数据合并

登录成功且请求携带匿名 cookie 时，在同一事务内：

1. 该匿名身份的 `posts.author_id` 置为登录用户，清空 `anonymous_token`（保留自定义昵称与环境信息）；
2. 匿名票尝试转 `user_id`，若该用户已有同一 Post 的登录票则删除匿名票；
3. 清除匿名 cookie。

合并失败不阻断登录（记录日志），下一次写操作会重新签发匿名身份。

## 7. 本地联调

```bash
# 用 deploy/.env 中的 SSO_SECRETS[0] 签发 5 分钟 token
uv run python -c "import jwt,time; print(jwt.encode({'email':'admin@example.com','name':'管理员','exp':int(time.time())+300}, 'dev-only-sso-secret-0123456789abcdef', algorithm='HS256'))"
```

浏览器打开：

```
http://127.0.0.1:5173/api/sso/jwt?token=<token>&return_to=/b/product
```

`ADMIN_EMAILS` 包含该邮箱时，头部显示「管理员」徽标；`pnpm smoke:p3` 覆盖了整条链路。

## 8. 会话接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/auth/me` | 当前身份（登录用户 / 匿名 / 未识别） |
| POST | `/api/v1/auth/refresh` | 用 refresh cookie 轮换 access（同时轮换 refresh） |
| POST | `/api/v1/auth/logout` | 清除会话 cookie |

access 过期后前端调用 `/auth/refresh`；refresh 失效则重新走 SSO 跳转。
