# 生产运维手册（P4 / A5）

本文件记录已在本地演练过的生产配置、备份恢复与回滚流程。Docker Compose 与 Nginx
仍未交付，相关章节会标注“待 Docker 阶段”。

## 1. 启动前检查清单

- [ ] `deploy/.env` 由 `.env.production.example` 复制并填好；`ENVIRONMENT=production`
- [ ] `APP_NAME` 已按站点品牌修改（前端头部、页脚与浏览器标题读取此值）
- [ ] `DATABASE_URL` 指向 Postgres（SQLite 会被启动校验拒绝）
- [ ] `SSO_SECRETS` 至少一项，64 位 hex；`SESSION_JWT_SECRET` 独立随机值
- [ ] `ADMIN_EMAILS` 至少保留一名有效管理员
- [ ] `RUSTFS_ENDPOINT_PUBLIC` 与浏览器访问站点完全同源（协议 + 域名 + 端口）
- [ ] `RustFS` bucket 已执行 `python -m scripts.bootstrap_storage`
- [ ] TLS 由 Nginx/网关终止，站点为 HTTPS（后端按 `Secure` 下发 cookie）

启动校验由 `app/core/config.py` 的 production validator 完成：缺少 SSO/RustFS 配置、
或 `DATABASE_URL` 非 Postgres 时，进程直接报错退出，不会带开发默认值上线。

本地已用 Postgres 16.9 + 自签名证书实跑过：
`ENVIRONMENT=production` 启动、HTTPS `/api/health`、SSO 登录、`/auth/me`，
确认 `feedlog_access` / `feedlog_refresh` 均带 `HttpOnly; SameSite=lax; Secure`。

## 2. 数据库 schema 升级与回滚

```bash
cd backend
uv run alembic upgrade head        # 升级
uv run alembic current             # 查看当前版本
uv run alembic downgrade -1        # 回滚一个版本（谨慎）
```

生产发布建议顺序：备份 → 迁移 → 启动新镜像 → 健康检查。

## 3. 备份与恢复（已演练）

```bash
# 备份（Postgres 16）
pg_dump -Fc -h <host> -U feedback -d feedback -f feedback_$(date +%Y%m%d).dump

# 恢复到新库（先在空库上恢复，验证后再切流量）
createdb -h <host> -U postgres feedback_restore
pg_restore -h <host> -U postgres -d feedback_restore --no-owner feedback_20260101.dump

# 验收
psql -d feedback_restore -tAc "select version_num from alembic_version"
psql -d feedback_restore -tAc "select count(*) from posts"
```

本地演练结果（2026-10-24，Postgres 16.9）：`feedback_test` 备份 28,924 字节，
恢复到 `feedback_restore` 后版本为 `0002_guest_name_env`，19 条 posts / 4 个用户，
两条 Vote 部分唯一索引均存在。

回滚策略：

1. 数据错误：停止写入 → 恢复最近备份到新库 → 切换 `DATABASE_URL` → 重启；
2. 版本错误：镜像回退到上一个 `sha-*` tag（Docker 阶段）并 `alembic downgrade` 到对应版本；
3. 配置错误：还原 `deploy/.env` 并重启，配置校验会阻止不完整配置启动。

## 4. 密钥与管理员变更

- **SSO_SECRETS 轮换**：见 [sso.md](sso.md) 第 4 节（新密钥在前 → 通知签发方 → 等 ≥5 分钟 → 移除旧密钥）。
- **SESSION_JWT_SECRET 轮换**：直接替换并重启，所有用户会话失效，需要重新 SSO 登录；建议低峰执行。
- **ADMIN_EMAILS**：改环境变量并重启；下一次 SSO 登录或 access 过期重登时同步 role。已用测试覆盖“加入即升管理员、移除即降级”。

## 5. 健康检查与观测

```bash
curl -fsS https://feedback.example.com/api/health
```

期望：`{"status":"ok","database":"ok",...}`。失败时按序检查：
Nginx → backend 进程 → `DATABASE_URL` 连通性 → 迁移版本。

限流计数表每小时自动清理 1 小时前的窗口；`alembic_version` 与 `docs/api.md` 的版本需保持一致。

## 6. 待 Docker 阶段补充

- 四服务 Compose 拓扑与 `restart: unless-stopped`
- Nginx 三路由（`/`、`/api/`、`/storage/`）与 Range/大文件配置
- GHCR 镜像 tag 回滚（`TAG=sha-... docker compose up -d`）
- RustFS 容量告警与未引用对象清理
