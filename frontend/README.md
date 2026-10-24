# frontend

Vite 8 + Vue 3.5 + TypeScript。P1 已接入读路径：看板、反馈、更新日志。

## 本地运行

```bash
pnpm install
pnpm dev      # http://localhost:5173
```

- `/api` 代理到 `http://127.0.0.1:8000`，可用 `VITE_API_PROXY_TARGET` 覆盖。
- `/storage` 由开发中间件从 `../backend/.dev-storage` 提供（支持 Range），模拟生产 Nginx + RustFS；媒体由后端 `scripts/seed_dev.py` 生成。

```bash
pnpm build    # vue-tsc 类型检查 + 产物构建
```

## 页面

| 路由 | 说明 |
|---|---|
| `/` | 公开看板列表 + 服务状态 |
| `/b/:slug` | 看板详情与反馈列表（每页 10 条，加载更多走 keyset 游标） |
| `/post/:id` | 反馈详情，富文本渲染（标题 / 列表 / 引用 / 代码块 / 图片 / MP4） |
| `/changelog` | 已发布更新日志 |
| `/changelog/:id` | 更新日志详情 |

## 目录

```
src/
  api/          fetch 封装（统一 { detail, code } 错误）与接口模块
  components/   RichTextRenderer（Tiptap JSON 白名单渲染）、PostCard、StatusBadge、EmptyState
  composables/  useStorageUrl（object key → /storage/）
  router/       路由表与 meta.requiresAdmin 守卫（非管理员 → 404）
  stores/       Pinia：auth（P3 接入 SSO 后填充）
  types/        Tiptap JSON 类型
  utils/        日期格式化
  views/        页面级组件
  style.css     设计变量与全局样式
```

约定：

- 富文本只按白名单节点渲染，未知节点仅渲染子节点，全程插值不使用 `v-html`。
- 不引入 Google Fonts，字体使用系统栈（构建产物已确认无外部字体请求）。
- 首期不引 TanStack Query，页面 `setup` 直接调用 `api/`。
- 图标统一使用 `@tabler/icons-vue`。
