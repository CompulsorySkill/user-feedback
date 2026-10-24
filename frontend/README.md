# frontend

Vite 8 + Vue 3.5 + TypeScript，Feature-First 结构。

## 本地运行

```bash
pnpm install
pnpm dev      # http://localhost:5173
```

`/api` 由 Vite dev server 代理到 `http://127.0.0.1:8000`，可用 `VITE_API_PROXY_TARGET` 覆盖。
`/storage` 在 Docker/Nginx 反代落地后接入 RustFS。

```bash
pnpm build    # vue-tsc 类型检查 + 产物构建
```

## 目录

```
src/
  api/          fetch 封装（统一 { detail, code } 错误）与接口模块
  router/       路由表与 meta.requiresAdmin 守卫（非管理员 → 404）
  stores/       Pinia：auth（P3 接入 SSO 后填充）
  views/        页面级组件
  style.css     设计变量与全局样式
```

约定：

- 不引入 Google Fonts，字体使用系统栈。
- 首期不引 TanStack Query，页面 `setup` 直接调用 `api/`。
- 图标统一使用 `@tabler/icons-vue`。
