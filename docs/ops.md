# 生产运维手册（P4 / A5 / Docker + Caddy）

本文件记录生产配置、备份恢复与回滚流程。Docker Compose 与 Caddy 交付物已落在
`deploy/`、`backend/Dockerfile`、`frontend/Dockerfile`、`frontend/Caddyfile`。
当前开发机没有 Docker Engine，容器运行验收需在目标 Docker 主机执行。

## 1. 启动前检查清单

- [ ] `deploy/.env` 由 `.env.production.example` 复制并填好；`ENVIRONMENT=production`
- [ ] `APP_NAME` 已按站点品牌修改（前端头部与浏览器标题读取此值）
- [ ] `SITE_ADDRESS` 为真实域名，DNS 已指向目标机，公网开放 TCP 80/443 与 UDP 443
  （裸 IP HTTPS 见 §2 的说明，改用内置 CA 自签）
- [ ] `ACME_EMAIL` 可接收证书到期通知
- [ ] `POSTGRES_PASSWORD` 足够强；`DATABASE_URL` 中的密码与之一致
- [ ] `SSO_SECRETS` 至少一项，64 位 hex；`SESSION_JWT_SECRET` 独立随机值
- [ ] `ADMIN_EMAILS` 至少保留一名有效管理员
- [ ] `ADMIN_PASSWORD` 已设置（否则只能走 SSO）且足够强，或确认已改为空、只允许 SSO
- [ ] `PUBLIC_ORIGIN` 与 `https://SITE_ADDRESS` 完全同源（CORS、cookie、上传签名共用）
- [ ] `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` 已替换默认值
- [ ] RustFS bucket 已执行 `docker compose run --rm backend python -m scripts.bootstrap_storage`
- [ ] Caddy 自动申请 TLS；确认 `feedlog_access` / `feedlog_refresh` 带 `Secure`
- [ ] 已配置每日上传清理任务（`UPLOAD_CLEANUP_GRACE_HOURS` 默认 24）

启动校验由 `app/core/config.py` 的 production validator 完成：缺少 SSO/RustFS 配置、
或 `DATABASE_URL` 非 Postgres 时，进程直接报错退出，不会带开发默认值上线。

## 2. 首次部署

```bash
cd deploy
cp .env.production.example .env
# 编辑 .env（至少改 SITE_ADDRESS / ACME_EMAIL / POSTGRES_PASSWORD / SSO / RustFS）

docker compose up -d --build
docker compose ps
docker compose logs -f backend
docker compose run --rm backend python -m scripts.bootstrap_storage
curl -fsS https://<SITE_ADDRESS>/api/health
```

- Caddy 首次启动会自动申请证书，数据保存在 `caddy-data` 卷。
- 只在本机验证 Caddy 配置而不部署时，可设置 `SITE_ADDRESS=:80`，并同步把
  `PUBLIC_ORIGIN` 改为对应的 `http://` 地址。
- 裸 IP HTTPS：公信 CA 不签发裸 IP 证书，`SITE_ADDRESS` 填 IP（不要带 `https://`
  前缀），并设 `CADDY_LOCAL_CERTS=local_certs` 让 Caddy 用内置 CA 自签；
  `PUBLIC_ORIGIN` 同步改为 `https://<IP>`。
  内置 CA 不被客户端默认信任，需把根证书分发给访问方：
  `docker compose cp frontend:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt`。
  若改用自有 IP SAN 证书，则在 `frontend/Caddyfile` 的 site 块加
  `tls /certs/fullchain.pem /certs/key.pem`，并在 compose 中把证书目录挂到 `/certs:ro`。
- 宿主机端口冲突时可改 `.env` 的 `HTTP_PORT` / `HTTPS_PORT`（容器内仍为 80/443）；
  非 443 时 `PUBLIC_ORIGIN` 必须带上端口，否则 CORS 与
  签名 Host 不匹配。另外域名 + ACME 部署请保持 `HTTPS_PORT=443`，否则 TLS-ALPN
  验证端口不通，只能靠 `HTTP_PORT=80` 的 HTTP-01（两者都要改则无法签证书）。
- 若使用 GHCR 镜像：在 `.env` 设置 `BACKEND_IMAGE` / `FRONTEND_IMAGE` 为固定版本
  （如 `…/backend:1.0.0`），先 `docker login ghcr.io`，再
  `docker compose pull && docker compose up -d`，无需 `--build`。
- 迁移随 backend 启动执行；多副本部署时改为独立一次性任务：
  `docker compose run --rm backend alembic upgrade head`。

## 3. 数据库 schema 升级与回滚

```bash
# Compose
cd deploy
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1   # 谨慎

# 非 Compose
cd backend
uv run alembic upgrade head
```

生产发布建议顺序：备份 → 迁移 → 启动新镜像 → 健康检查。

## 4. 备份与恢复

```bash
# 备份（Compose）
cd deploy
docker compose exec -T postgres pg_dump -Fc -U feedback -d feedback \
  > feedback_$(date +%Y%m%d).dump

# 恢复到新库（先在空库上恢复，验证后再切流量）
docker compose exec -T postgres createdb -U feedback feedback_restore
docker compose exec -T postgres pg_restore -U feedback -d feedback_restore --no-owner \
  < feedback_20260101.dump

# 验收
docker compose exec -T postgres psql -U feedback -d feedback_restore \
  -tAc "select version_num from alembic_version"
```

回滚策略：

1. 数据错误：停止写入 → 恢复最近备份到新库 → 切换 `DATABASE_URL` → 重启；
2. 版本错误：镜像回退到上一个 semver（如 `1.0.0`）或 `sha-*` tag，并 `alembic downgrade` 到对应版本；
3. 配置错误：还原 `deploy/.env` 并重启，配置校验会阻止不完整配置启动。

## 5. 密钥与管理员变更

- **SSO_SECRETS 轮换**：见 [sso.md](sso.md) 第 4 节（新密钥在前 → 通知签发方 → 等 ≥5 分钟 → 移除旧密钥）。
- **SESSION_JWT_SECRET 轮换**：直接替换并重启，所有用户会话失效，需要重新 SSO 登录；建议低峰执行。
- **ADMIN_EMAILS**：改环境变量并重启；下一次 SSO 登录或 access 过期重登时同步 role。
- **ADMIN_PASSWORD**：改环境变量并重启；为空时关闭邮箱 + 密码登录（`/api/v1/auth/admin-login` 返回 404），只保留 SSO。

## 6. 健康检查与观测

```bash
curl -fsS https://<SITE_ADDRESS>/api/health
cd deploy && docker compose ps
docker compose logs -f frontend
```

失败时按序检查：Caddy（frontend）→ backend 进程/健康检查 → Postgres 连通性 →
RustFS 连通性 → 迁移版本。Caddy 访问日志默认关闭（避免 GET SSO token 进入 URL 日志），
错误日志由 Compose 收集；后端 Uvicorn 访问日志已脱敏。

限流计数表每小时自动清理 1 小时前的窗口；`alembic_version` 与 `docs/api.md` 的版本需保持一致。
管理操作可在 `/admin/audit` 或 `GET /api/v1/admin/audit-logs` 查询（仅追加，actor 删除后保留邮箱快照）。

## 7. Docker/Caddy 运维

- 四个服务：`postgres`、`rustfs`、`backend`、`frontend`（Caddy），均 `restart: unless-stopped`。
- Caddy 路由：`/api/*` → `backend:8000`，`/storage/*` → `rustfs:9000`（不重写路径），
  其余静态文件回退到 `index.html`。
- Caddy 证书与配置：`caddy-data` / `caddy-config` 卷；迁移前先备份。
- RustFS 数据：`rustfs-data` 卷；Postgres 数据：`postgres-data` 卷。
- 镜像构建仅由 `v*` Git tag 触发：生成 `1.0.0`、`1.0`、`sha-<commit>`，
  稳定版同时更新 `latest`（预发布 tag 不更新）；普通 `main` push 不触发。
  镜像为多架构（`linux/amd64` + `linux/arm64`）。
- 构建完成后 workflow 会把两个架构的单架构镜像导出为 `backend-<版本>-linux-<架构>.tar.gz`
  与 `frontend-<版本>-linux-<架构>.tar.gz`，附到同名 GitHub Release（Release 不存在时自动创建）。
  离线部署：`docker load -i backend-1.0.2-linux-arm64.tar.gz`，加载后的镜像名为
  `ghcr.io/<owner>/<repo>/backend:1.0.2`，可直接用作 `BACKEND_IMAGE`。
- 发布新版本：`git tag -a v1.1.0 -m "v1.1.0" && git push origin v1.1.0`。
- 镜像回滚：设置 `BACKEND_IMAGE` / `FRONTEND_IMAGE` 到上一个 semver 或 `sha-*` tag，
  `docker compose pull && docker compose up -d`。
- RustFS 容量告警仍需在宿主机 / 监控侧配置；清理任务只删除超过保留期且未被引用的对象。

## 8. 上传对象清理

presign 会先写 `uploads` 记录，只有在反馈 / 更新日志富文本或更新日志附件表中出现过的 object key 才算被引用。
超过 `UPLOAD_CLEANUP_GRACE_HOURS`（默认 24 小时）仍未引用的对象会被清理，覆盖：

- presign 后浏览器从未成功 PUT；
- 编辑反馈/日志时删除了图片 / 视频；
- 看板被级联删除后遗留的媒体。

先预演，再执行：

```bash
cd deploy
docker compose exec -T backend python -m scripts.cleanup_uploads --dry-run
docker compose exec -T backend python -m scripts.cleanup_uploads --grace-hours 24
```

管理员也可在 `/admin/audit` 页面点「预演清理 / 清理上传对象」，或调用
`POST /api/v1/admin/uploads/cleanup`。单次最多删除 200 条；已引用记录不会阻塞后续扫描，孤儿对象多于 200 条时由 cron 多次执行。
建议每日低峰运行一次，例如宿主机 cron：

```cron
15 4 * * * cd /srv/user-feedback/deploy && docker compose exec -T backend python -m scripts.cleanup_uploads >> /var/log/feedback-cleanup.log 2>&1
```

清理动作会写入 `audit_logs`（`upload.cleanup`），包含扫描数、删除数、失败数与错误摘要。
只处理 `uploads` 表中有记录的对象，**不会**扫描 bucket 删除运维手动放入的文件。
