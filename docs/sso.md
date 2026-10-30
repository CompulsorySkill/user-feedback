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

## 5. 管理员维护（ADMIN_EMAILS / ADMIN_PASSWORD）

- 授权路径：`ADMIN_EMAILS="alice@example.com,bob@example.com"`（逗号分隔，trim + 小写比较）。
- 设置 `ADMIN_PASSWORD` 后，开发与生产都可在 `/login` 用「管理员邮箱 + 密码」登录
  （`POST /api/v1/auth/admin-login`）；显示名可留空，沿用账号已有昵称。
  该接口按来源 IP 限流（10 次 / 5 分钟），密码错误只返回 401 `INVALID_CREDENTIALS`。
- 生产环境不想开放密码登录时，把 `ADMIN_PASSWORD` 留空即可（只保留 SSO）。
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

前端提供 `/login` 登录页：

- **管理员密码登录**：配置 `ADMIN_EMAILS` + `ADMIN_PASSWORD` 后可用（开发与生产均可用），显示名可选。
- **开发快速登录**：`ENVIRONMENT=development` 时可用，输入邮箱直接签发会话；邮箱命中 `ADMIN_EMAILS` 即为管理员。生产环境该接口返回 404。
- **SSO token 粘贴**：前端通过 `POST /api/sso/jwt` 提交 `{token, return_to}`，由后端下发
  HttpOnly 会话并返回 `redirect_to`；token 不会进入 URL / 浏览器历史。产品侧原有的
  `GET /api/sso/jwt?token=...` 跳转仍然兼容（访问日志已做 `token=***` 脱敏）。

```bash
# 用 deploy/.env 中的 SSO_SECRETS[0] 签发 5 分钟 token
uv run python -c "import jwt,time; print(jwt.encode({'email':'admin@example.com','name':'管理员','exp':int(time.time())+300}, 'dev-only-sso-secret-0123456789abcdef', algorithm='HS256'))"
```

`ADMIN_EMAILS` 包含该邮箱时，头部显示「管理员」徽标；管理动作会写入 `/admin/audit` 审计日志。
前端 `pnpm test` 覆盖会话续期与筛选等纯逻辑，SSO / 管理链路的端到端验收按根目录 README 的部署清单执行。

## 8. 会话接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/sso/jwt` | 提交 `{token, return_to}` 换取会话（推荐，token 不进 URL） |
| GET | `/api/sso/jwt?token=&return_to=` | 产品侧跳转登录，失败降级匿名 |
| GET | `/api/v1/auth/me` | 当前身份（登录用户 / 匿名 / 未识别） |
| GET | `/api/v1/auth/capabilities` | 登录能力（是否开放开发快速登录 / 管理员密码登录） |
| POST | `/api/v1/auth/dev-login` | 仅 development；生产 404 |
| POST | `/api/v1/auth/admin-login` | `{email, password, name?}`：邮箱命中 `ADMIN_EMAILS` 且密码匹配 `ADMIN_PASSWORD` 即登录，未配置 404 |
| POST | `/api/v1/auth/refresh` | 用 refresh cookie 轮换 access（同时轮换 refresh） |
| POST | `/api/v1/auth/logout` | 清除会话 cookie |

access 过期后不会中断操作：后端在响应头返回 `X-Session-Expired: 1`，前端 API 客户端会
自动调用 `/auth/refresh` 并重放一次原请求（并发请求共享同一次刷新）；刷新失败才降级为匿名并提示重新登录。

匿名合并失败（数据库异常等）不会阻断登录：系统记录日志、保留匿名 cookie 与未合并数据，
会话正常签发；可排查后让用户重新登录完成合并。

## 9. TypeScript 签发示例（对接方）

用 [`jose`](https://github.com/panva/jose) 签发 HS256 token（Node 18+ / Edge Runtime 均可）：

```ts
import { SignJWT } from 'jose';

// 与反馈系统 SSO_SECRETS 中某一项完全一致：64 位 hex 字符串，按 UTF-8 直接使用。
const ssoSecret = process.env.SSO_SECRET;
if (!ssoSecret) throw new Error('缺少 SSO_SECRET');
const key = new TextEncoder().encode(ssoSecret);

/** 生成 5 分钟有效的 SSO token；email 由服务端从当前会话取，绝不回填前端传入值。 */
export async function mintSsoToken(email: string, name?: string): Promise<string> {
  // 反馈系统对缺 @ 的 email 返回 400/降级匿名，先在这里挡住。
  if (!email.includes('@')) throw new Error(`email 不合法: ${email}`);
  return new SignJWT({ email, ...(name ? { name: name.slice(0, 128) } : {}) })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('5m')
    .sign(key);
}

/** return_to 只允许站内相对路径，非法值会导致反馈系统静默回退默认页。 */
function safeReturnTo(input: string | null | undefined): string {
  if (!input) return '/';
  return input.startsWith('/') && !input.startsWith('//') && !input.startsWith('/\\')
    ? input
    : '/';
}

/** 登录跳转：302 到反馈系统，由它校验 token 并下发自己的 HttpOnly 会话 cookie。 */
export async function buildFeedbackLoginUrl(params: {
  origin: string;           // 如 https://feedback.example.com（不带子路径）
  basePath?: string;        // 子路径部署时传 'feedback'，同 deploy/.env 的 BASE_PATH
  email: string;
  name?: string;
  returnTo?: string;
}): Promise<string> {
  const basePath = params.basePath?.replace(/^\/+|\/+$/g, '');
  const base = `${params.origin.replace(/\/+$/, '')}${basePath ? `/${basePath}` : ''}`;
  const token = await mintSsoToken(params.email, params.name);
  const url = new URL(`${base}/api/sso/jwt`);
  url.searchParams.set('token', token);
  url.searchParams.set('return_to', safeReturnTo(params.returnTo));
  return url.toString();
}

// 用法（产品 A 的登录成功回调里）：
// response.redirect(
//   await buildFeedbackLoginUrl({ origin: 'https://feedback.example.com', email, name, returnTo: '/b/product' }),
// );
```

要点：

- 密钥只存在于服务端；token 不落库、不进前端 bundle，有效期控制在 5 分钟内。
- `email` 必须来自产品 A 自己的会话校验结果，不能由请求参数透传（否则等于任意人可登录）。
- 不要在 token 里放 `role` / `is_admin`：反馈系统一律忽略，角色由它自己的 `ADMIN_EMAILS` 计算。
- 若坚持走 `POST /api/sso/jwt` 让 token 不进 URL，需由产品 A 后端转发请求并把响应中的
  `Set-Cookie`（access + refresh）原样回传给浏览器；跳转路径则不需要这层代理。
- 校验签名侧用 `jose.jwtVerify(token, key, { algorithms: ['HS256'] })` 自测即可，
  密钥轮换顺序见第 4 节。
