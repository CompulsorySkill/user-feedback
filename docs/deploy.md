# 部署说明（Docker Compose + Caddy）

从零把系统跑起来的步骤。运维（备份恢复、密钥轮换、上传清理、回滚）见
[ops.md](ops.md)，接口契约见 [api.md](api.md)。

## 1. 部署形态

单文件编排：`deploy/docker-compose.yml`，四个服务，只有 Caddy（frontend 容器）
对外暴露端口。

| 服务 | 对外 | 说明 |
|---|---|---|
| `frontend` | `HTTP_PORT` / `HTTPS_PORT` | Caddy：SPA 静态文件 + `/api/*` → `backend:8000` + `/<S3_BUCKET>/*` → `rustfs:9000` |
| `backend` | 仅内网 8000 | FastAPI；启动时自动 `alembic upgrade head` |
| `postgres` | 仅内网 5432 | 生产必须用 Postgres |
| `rustfs` | 仅内网 9000 | 对象存储（S3 兼容），bucket 由 `scripts.bootstrap_storage` 初始化 |

Caddy 同时提供 `http://` 与 `https://` 两个入口，互不跳转。按访问方式选一种部署目标：

| 场景 | `SITE_ADDRESS` | 证书 | 额外配置 |
|---|---|---|---|
| A. 域名 + HTTPS（推荐） | 域名，如 `feedback.example.com` | Let's Encrypt 自动签发 | 开放 TCP 80/443、UDP 443 |
| B. 裸 IP + HTTP（内网 / 试验） | IP，如 `203.0.113.10` | 无 | `COOKIE_SECURE=false`，只开放 80 |
| C. 裸 IP + HTTPS（内网自签） | IP | Caddy 内置 CA 自签 | `CADDY_LOCAL_CERTS=local_certs`，客户端需信任根证书 |
| D. 公司 TLS + 路径前缀反代（推荐于内网/公司环境） | 内网可达的主机名 | 公司反代负责 | `BASE_PATH=/feedback` + `PUBLIC_ORIGIN` 带前缀，只暴露 `HTTP_PORT`；见 §3「企业路径前缀部署」 |

## 2. 前置条件

- 目标机装好 Docker Engine + Compose v2（`docker compose version` 可用）。
- 场景 A：域名 DNS 已指向目标机，公网开放 TCP 80/443 与 UDP 443（HTTP-01 / TLS-ALPN）。
- 场景 B/C：事先确定宿主机端口是否被占用（默认 80/443）。
- 拿到代码或镜像：仓库检出（本机构建）或 GHCR 镜像（见 §5）。

## 3. 配置 `deploy/.env`

`.env` 是唯一配置来源（不存在 `backend/.env`），`deploy/.env` 不入库。

```bash
cd deploy
cp .env.example .env
```

模板值就是生产部署用的；本地开发只需改 `ENVIRONMENT` / `DATABASE_URL` / `PUBLIC_ORIGIN`
三行（见 README「本地开发 → 1. 配置」）。

**必改项**

| 变量 | 说明 |
|---|---|
| `POSTGRES_PASSWORD` | 强密码；`DATABASE_URL` 里的密码保持与之一致（Compose 会用 `POSTGRES_PASSWORD` 重新拼连接串） |
| `SSO_SECRETS` | 64 位 hex 数组，新的在前；对接方式见 [sso.md](sso.md) |
| `SESSION_JWT_SECRET` | 与 SSO 密钥分离的随机值 |
| `ADMIN_EMAILS` | 至少一名管理员邮箱（逗号分隔） |
| `ADMIN_PASSWORD` | 管理员邮箱 + 密码登录；留空则该入口关闭，只走 SSO |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | RustFS 的访问密钥，不要用示例值 |
| `S3_BUCKET` | 默认 `storage`；改名会同时改变媒体公开路径（`/<bucket>/<key>`），需重建 bucket 并迁移旧对象 |
| `BASE_PATH` | 子路径部署用（见下节），根部署留空 |

**按场景改**

| 变量 | 场景 A | 场景 B | 场景 C |
|---|---|---|---|
| `ENVIRONMENT` | `production` | `production` | `production` |
| `SITE_ADDRESS` | 域名 | 裸 IP | 裸 IP |
| `PUBLIC_ORIGIN` | `https://<域名>` | `http://<IP>` | `https://<IP>` |
| `COOKIE_SECURE` | 留空（默认开） | **`false`** | 留空（默认开） |
| `ACME_EMAIL` | 填可收信邮箱 | 不用改 | 不用改 |
| `CADDY_LOCAL_CERTS` | 留空 | 留空 | `local_certs` |
| `HTTP_PORT` / `HTTPS_PORT` | 默认 80/443 | 默认 80 | 默认 |

- `PUBLIC_ORIGIN` 必须与浏览器地址栏的协议 + 主机 + 端口完全一致，否则 CORS 与
  presign 直传都会失败；非 443/80 时带上端口，如 `https://203.0.113.10:8443`。
- `COOKIE_SECURE` 留空时按 `ENVIRONMENT` 推断（生产开）。明文 HTTP 下带 `Secure` 的
  会话 cookie 会被浏览器丢弃，表现为「登录后立刻变回匿名」。
- `S3_ENDPOINT_INTERNAL` 保持 `http://rustfs:9000`（容器内网地址），不要改成域名。

`ENVIRONMENT=production` 会在启动时强校验：`PUBLIC_ORIGIN`、`SSO_SECRETS`、
`SESSION_JWT_SECRET`、`S3_ENDPOINT_INTERNAL`、`S3_ACCESS_KEY`、`S3_SECRET_KEY`
不得为空，且 `DATABASE_URL` 必须指向 Postgres，否则进程直接退出。

### 企业路径前缀部署（子路径 / 公司反代）

适用于浏览器地址带前缀的部署，例如 `https://example.com/feedback/`。
公司反代通常同时终结 TLS、做鉴权和限流，本服务只在内网提供 HTTP。

```
浏览器 ──https──▶ 公司反代（TLS / 鉴权 / 限流） ──http──▶ frontend(Caddy) ──▶ backend / rustfs
                        /feedback/*              （透传或剥前缀，两种都支持）
```

#### 1) 配置 `deploy/.env`

```dotenv
# 浏览器侧前缀（带前导斜杠、无尾斜杠）
BASE_PATH=/feedback
# 必须带同一路径，production 启动时会校验二者一致
PUBLIC_ORIGIN=https://example.com/feedback

# 公司反代终结 TLS：本服务不对外暴露 443，只发布 HTTP_PORT
SITE_ADDRESS=feedback.internal.example.com
HTTP_PORT=8080
# 避免 Caddy 为不可达的 443 反复尝试 ACME（自签不影响公司侧 TLS）
CADDY_LOCAL_CERTS=local_certs
```

- `COOKIE_SECURE` 保持默认（浏览器侧是 https）。`S3_*` / `SSO_*` / `ADMIN_*` 按 §3 的要求填。
- 前缀在**容器启动时**注入 `index.html`（`frontend/docker-entrypoint.sh`）：静态资源 URL、
  前端路由 base、API 前缀都跟着走。**同一份镜像**可以挂到任意前缀，GHCR 预构建镜像同样适用。
- 启动脚本会校验 `BASE_PATH`（空或 `/segment[/segment]`，字符限 `[A-Za-z0-9._~-]`），
  非法值直接退出，不会写进 HTML。

#### 2) 启动

```bash
cd deploy
docker compose up -d                 # 首次本机构建加 --build；用 GHCR 镜像则 pull 后执行
docker compose logs -f frontend      # 看到 "serving initial configuration" 即启动完成
```

- 宿主机防火墙只放行公司反代到 `HTTP_PORT`；443 不对公网暴露。
- 浏览器访问 `/feedback`（无尾斜杠）也能进入，前缀与静态资源路径由 index.html 决定。
- **改前缀后**必须重建容器：`docker compose up -d frontend`（index.html 在启动时生成），
  并让浏览器强刷 / 清掉 CDN 上缓存的 index.html。

#### 3) 公司反代配置（两种接入方式任选）

Caddy 同时接受「带前缀」与「已剥前缀」的请求，`BASE_PATH` 都保持 `/feedback`。

**方式一：透传前缀**（推荐，反代配置最简单）

```nginx
location /feedback/ {
    proxy_pass http://10.0.0.12:8080;          # 结尾无斜杠：保留 /feedback
    proxy_set_header Host $host;               # 上传 SigV4 依赖原始 Host
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    client_max_body_size 100m;                 # 与 UPLOAD_MAX_BYTES 一致
    proxy_request_buffering off;               # 大文件直传不落盘
    proxy_buffering off;                       # 视频 Range 透传
}
```

**方式二：反代剥掉前缀**

```nginx
location /feedback/ {
    proxy_pass http://10.0.0.12:8080/;         # 结尾带斜杠：/feedback 被剥掉
    # 其余指令同上
}
```

两种方式都只暴露 `/feedback/*` 一个前缀；`/<前缀>/storage/*` 也在这个 location 内，
不需要额外规则（媒体直传与读取都走它）。

#### 4) 验收

```bash
BASE=https://example.com/feedback
curl -fsS "$BASE/api/health"                          # {"status":"ok",...}

# index.html 里的静态资源地址应带 /feedback 前缀
ASSET=$(curl -fsS "$BASE/" | grep -o '/feedback/assets/index-[^"]*' | head -1)
echo "$ASSET"
curl -sI "https://example.com$ASSET" | head -1              # HTTP/2 200
```

浏览器侧再确认：打开 `$BASE` → 列表正常；发一条带图片的反馈（直传 200）；
刷新后仍是登录态。SSO 回调地址同样要配成 `https://example.com/feedback/...`
（站内 `return_to` 会自动补前缀）。

#### 5) 反代硬性要求

- **保留原始 `Host`**：上传直传的 SigV4 用请求 Host 签名，被改写会 403 `SignatureDoesNotMatch`。
- 透传 `Range` / `Accept-Ranges`，不要缓冲整个响应体（视频拖动依赖）。
- 请求体上限 ≥ 100MB（`UPLOAD_MAX_BYTES`），否则大文件在反代层就 413。
- 可选：`X-Forwarded-Proto` / `X-Forwarded-For`（后端已按代理头解析客户端 IP）。
- 多客户不同前缀：同一份镜像，改 `BASE_PATH` + `PUBLIC_ORIGIN` 后重启 frontend 即可。

#### 6) 前缀变更 = 站点迁移

旧链接（收藏夹、SSO 侧配置的回调地址、外部引用）要同步更新；媒体只存 object key，
历史内容本身不受影响。回滚只需把 `BASE_PATH` / `PUBLIC_ORIGIN` 改回去并重启 frontend。


## 4. 启动

```bash
cd deploy
docker compose up -d --build          # 首次会构建 backend / frontend 镜像
docker compose ps
docker compose logs -f backend        # 看到迁移完成、uvicorn 启动

# 首次或换存储环境时初始化 RustFS bucket
docker compose run --rm backend python -m scripts.bootstrap_storage
```

健康检查：

```bash
curl -fsS https://<SITE_ADDRESS>/api/health   # 场景 B 改成 http://<IP>
# {"status":"ok","database":"ok",...}
```

发布新版本（GHCR 镜像，不在目标机构建）：

```bash
cd deploy
# .env 里固定版本：BACKEND_IMAGE=ghcr.io/<owner>/<repo>/backend:1.0.0
#               FRONTEND_IMAGE=ghcr.io/<owner>/<repo>/frontend:1.0.0
echo "$GHCR_TOKEN" | docker login ghcr.io -u <user> --password-stdin
docker compose pull && docker compose up -d
```

只有推送 `v*` tag 才构建镜像；普通 `main` push 不触发。离线部署用 Release 里的
`backend-<版本>-linux-<架构>.tar.gz` / `frontend-…tar.gz`，`docker load -i` 后再
`docker compose up -d`。

## 5. 部署后验收

- [ ] `GET /api/health` 返回 `{"status":"ok","database":"ok"}`
- [ ] 首页、看板、反馈详情能打开（`/assets/*` 404 说明 frontend 镜像里没有 dist）
- [ ] 登录：管理员邮箱 + 密码或 SSO 进入后刷新页面仍是登录态
      （立刻掉线 = `COOKIE_SECURE` 不匹配当前协议）
- [ ] 发一条带图片的反馈：图片直传成功（失败见 §7）
- [ ] 场景 A：浏览器证书有效，`Set-Cookie` 带 `Secure`
- [ ] 场景 C：客户端已安装 `caddy-data` 卷里的根证书：
      `docker compose cp frontend:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt`
- [ ] RustFS bucket 已创建（`scripts.bootstrap_storage` 输出「bucket 就绪」）
- [ ] 每日上传清理任务已挂 cron（见 [ops.md](ops.md) §8）

## 6. 迁移

迁移随 `backend` 容器启动执行，一般无需手动操作。多副本部署时应拆成独立一次性任务：

```bash
cd deploy
docker compose run --rm backend alembic upgrade head
```

升级前的备份与回滚流程见 [ops.md](ops.md) §3、§4。

## 7. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 登录成功但刷新后变匿名 | `COOKIE_SECURE` 与访问协议不匹配：http 访问需 `false`；https 保持留空或 `true` |
| CORS 报错 / 401 跨域 | `PUBLIC_ORIGIN` 与实际地址不同源（协议、端口、主机都要一致） |
| 上传返回 403 / `SignatureDoesNotMatch` | 前置反代改写了 `Host` 或没转发 `<前缀>/storage/*`；必须透传浏览器原始 `Host`（nginx 默认即可，别设 `proxy_set_header Host $proxy_host`），并把媒体路径一起转发 |
| 上传 400 / 图片不显示 | RustFS bucket 未初始化：跑 §4 的 `bootstrap_storage` |
| 子路径部署后接口 404 / 白屏 | `BASE_PATH`（Caddy + 启动脚本）与 `PUBLIC_ORIGIN` 路径不一致；改完 `BASE_PATH` 要 `docker compose up -d frontend` 重建容器（index.html 在启动时生成） |
| 改了 `S3_BUCKET` 后旧图片 404 | 对象仍在旧 bucket：先把对象复制到新 bucket，再重启 backend / frontend（Caddy 与前端前缀都会跟着变） |
| Caddy 报签证书失败 | 场景 A 检查 80/443 是否可达、DNS 是否生效；裸 IP 必须走场景 B 或 C（公信 CA 不给 IP 签证书） |
| `https://<IP>` 提示证书不受信任 | 场景 C 的预期行为，需分发内置 CA 根证书给访问方；客户端不信任则改用场景 B |
| 容器起来了但页面打不开 | 只映射了部分端口：重启 `docker compose up -d`，确认 `docker compose ps` 端口映射 |
| 上传 413 / 文件过大 | `UPLOAD_MAX_BYTES`（默认 100MB）与 Caddy `request_body max_size` 都限制为 100MB |
| 改了 `.env` 没生效 | 改完必须 `docker compose up -d` 重建容器（`backend` / `frontend` 不热加载配置） |

## 8. 相关文件

- `deploy/docker-compose.yml`：服务编排、端口映射、卷
- `deploy/.env.example`：唯一配置模板（按子服务分组，生产值）
- `frontend/Caddyfile`：站点路由、安全响应头、缓存策略
- `frontend/Dockerfile`、`backend/Dockerfile`：镜像构建（含 Caddyfile 语法校验与 index 模板生成）
- `frontend/docker-entrypoint.sh`：启动时注入 `BASE_PATH` 到 index.html
- `frontend/scripts/runtime-index.mjs`：构建后生成带前缀占位符的 index 模板
- `docs/ops.md`：备份恢复、密钥轮换、上传清理、镜像回滚
