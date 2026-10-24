# frontend

Vite 8 + Vue 3.5 + TypeScript。面向 PC Web，不处理移动端适配。
P1 读路径 + P2 写路径（匿名直传、发帖、投票）已接入。

## 本地运行

```bash
pnpm install
pnpm dev      # http://127.0.0.1:5173
```

- `/api` 代理到 `http://127.0.0.1:8000`，可用 `VITE_API_PROXY_TARGET` 覆盖。
- `/storage` 代理到本机 RustFS（`http://127.0.0.1:9000`，`VITE_STORAGE_PROXY_TARGET` 可覆盖），不重写路径、透传 Host 与 Range，与生产 Nginx 行为一致。
- 媒体由后端 `scripts/seed_dev.py` 生成并上传 RustFS。

```bash
pnpm build    # vue-tsc 类型检查 + 产物构建
```

## 页面

| 路由 | 说明 |
|---|---|
| `/` | 公开看板列表 + 服务状态 |
| `/b/:slug` | 看板详情与反馈列表（每页 10 条，加载更多走 keyset 游标） |
| `/b/:slug/new` | 匿名发帖：Tiptap 编辑器 + 图片 / MP4 直传 |
| `/post/:id` | 反馈详情，富文本渲染与投票（乐观更新、失败回滚） |
| `/changelog` | 已发布更新日志 |
| `/changelog/:id` | 更新日志详情 |

## 浏览器冒烟测试

覆盖「编辑器插入图片 → presign 直传 → 发布 → 详情渲染 → 投票 / 取消」全链路：

```bash
pnpm smoke:p2
```

默认使用本机 Edge（`EDGE_PATH` 覆盖）。若当前环境不允许由 Node 直接拉起浏览器，
可先手动启动带调试端口的 Edge，再通过 `CDP_URL` 复用：

```powershell
msedge.exe --headless=new --remote-debugging-port=9333 --user-data-dir=<临时目录> about:blank
$env:CDP_URL="http://127.0.0.1:9333"; pnpm smoke:p2
```

## 目录

```
src/
  api/          fetch 封装（统一 { detail, code } 错误）与接口模块
  components/   RichTextRenderer、PostEditor、VoteButton、PostCard、StatusBadge、EmptyState
  composables/  useStorageUrl（object key → /storage/）、useUpload（presign + PUT）
  editor/       Tiptap 扩展：StorageImage、VideoNode
  router/       路由表与 meta.requiresAdmin 守卫（非管理员 → 404）
  stores/       Pinia：auth（P3 接入 SSO 后填充）
  types/        Tiptap JSON 类型
  utils/        日期格式化
  views/        页面级组件
  styles/       P2 写路径样式（编辑器、表单、投票）
```

约定：

- 富文本只按白名单节点渲染，未知节点仅渲染子节点，全程插值不使用 `v-html`。
- 编辑器 JSON 中媒体只存 object key，展示时由 `storageUrl()` 拼 `/storage/`。
- 不引入 Google Fonts，字体使用系统栈（构建产物已确认无外部字体请求）。
- 首期不引 TanStack Query，页面 `setup` 直接调用 `api/`。
- 图标统一使用 `@tabler/icons-vue`。
