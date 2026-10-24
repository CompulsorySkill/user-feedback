# frontend

Vite 8 + Vue 3.5 + TypeScript。面向 PC Web，不处理移动端适配。
P1 读路径 + P2 写路径（匿名直传、发帖、投票）已接入。

## 本地运行

```bash
pnpm install
pnpm dev      # http://127.0.0.1:5173
```

- `/api` 代理到 `http://127.0.0.1:8000`，可用 `VITE_API_PROXY_TARGET` 覆盖。
- `/storage` 代理到本机 RustFS（`http://127.0.0.1:9000`，`VITE_STORAGE_PROXY_TARGET` 可覆盖），不重写路径、透传 Host 与 Range，与生产 Caddy 行为一致。
- 媒体由后端 `scripts/seed_dev.py` 生成并上传 RustFS。
- 生产镜像见 [Dockerfile](Dockerfile) 与 [Caddyfile](Caddyfile)：Vite 产物由 Caddy 同域提供，`/api/` 与 `/storage/` 反代到内网服务。

```bash
pnpm build          # vue-tsc 类型检查 + 产物构建
pnpm test           # Vitest（jsdom + @vue/test-utils）
pnpm test:watch     # Vitest watch
pnpm lint           # oxlint（含 Vue 插件，warning 视为失败）
pnpm format         # oxfmt 格式化 src / tests / 配置
pnpm format:check   # 校验格式（CI 使用）
```

## 代码质量

- 格式化与静态检查统一使用 **OXC**：`oxfmt` + `oxlint`，配置见 [.oxfmtrc.json](.oxfmtrc.json) 与 [.oxlintrc.json](.oxlintrc.json)。
- `oxfmt` 覆盖 `src/`、`tests/`、`index.html`、`vite.config.ts`、`vitest.config.ts`、`package.json`；缩进 2 空格、单引号、无分号、行宽 100。
- `oxlint` 启用 `vue` 插件、correctness/suspicious 规则；CI 在构建前执行 lint 与 format check。

## 样式规范

- **字号只允许 3 档**：`--fs-display` 32px（页面 h1）、`--fs-body` 16px（正文 / 按钮 / 输入）、`--fs-caption` 13px（次要信息 / 徽章 / 代码）；不要在组件里直接写 `font-size`，统一在 [typography.css](src/styles/typography.css) 中归类。
- **控件高度统一**：`.button` / `.button-small` 高度 40px、最小宽度 88px；图标工具按钮、筛选 chips、排序器、投票按钮 32px；输入框 44px。
- 筛选、排序、标签与投票控件的高度由 `--control-height-sm` 统一约束；新增页面时复用这些类，不要在组件里写 `font-size`。

## 页面

| 路由 | 说明 |
|---|---|
| `/` | 全部反馈（根路由）：所有公开看板的反馈聚合列表，左侧看板导航；搜索、状态筛选、多选标签（OR）、最近/最热排序 |
| `/b/:slug` | 看板页：左侧看板列表（含帖子数/高亮），右侧反馈列表（搜索 + 状态 + 标签筛选 + 排序，条件写入 URL，均走 keyset 游标） |
| `/b/:slug/new` | 匿名发帖：Tiptap 编辑器 + 图片 / MP4 直传 + 标签选择（内置标签 / 自定义，最多 5 个） |
| `/post/:id` | 反馈详情：富文本、标签、投票、状态操作（管理员下拉 / 作者关闭）、3 层评论与回复 |
| `/post/:id/edit` | 编辑反馈（作者非关闭态 / 管理员，可增删标签） |
| `/admin/boards` | 看板管理：新建、编辑、删除看板（仅管理员，非管理员 404；删除会二次确认并级联清理反馈） |
| `/admin/tags` | 标签管理：新增 / 删除内置标签（仅管理员；删除会从所有反馈移除） |
| `/admin/audit` | 审计日志：管理操作流水、动作筛选、预演/执行未引用上传对象清理（仅管理员） |
| `/login` | 登录：SSO token 粘贴 + 开发环境快速登录 |
| `/changelog` | 已发布更新日志；管理员可见草稿与「新建」入口 |
| `/changelog/:id` | 更新日志详情 |
| `/changelog/new`、`/changelog/:id/edit` | 管理更新日志（仅管理员，非管理员 404） |

## 单元测试

原来的 `scripts/smoke-*.mjs` / `check-style.mjs` 依赖本机 Edge、后端与 RustFS，维护成本高且不稳定，
已替换为 Vitest + jsdom + `@vue/test-utils`，无需启动任何外部服务：

- `tests/utils/postFilters.spec.ts`：状态/排序/标签/搜索归一化，重复 `tag` 查询参数拼接
- `tests/api/client.spec.ts`：`{ detail, code }` 错误、204、`X-Session-Expired` refresh 重放与失败降级
- `tests/components/PostFeed.spec.ts`：首次加载、URL 初始标签、点击标签写入路由
- `tests/components/TagPicker.spec.ts`：建议标签、自定义标签、去重与数量上限
- `tests/utils/date.spec.ts`、`tests/utils/audit.spec.ts`：日期与审计动作展示

```bash
pnpm test
```

未覆盖的浏览器端到端链路（真实 presign 直传、TLS、RustFS Range）改由部署验收与后端集成测试覆盖；
需要浏览器验收时按根目录 README 的部署验收清单执行，不再保留临时 puppeteer 脚本。

## 目录

```
src/
  api/          fetch 封装（统一 { detail, code } 错误）与接口模块
  components/   RichTextRenderer、PostEditor、VoteButton、AuthorTag、CommentSection、PostStatusControl
  composables/  useStorageUrl（object key → /storage/）、useUpload（presign + PUT）
  editor/       Tiptap 扩展：StorageImage、VideoNode
  router/       路由表与 meta.requiresAdmin 守卫（非管理员 → 404）
  stores/       Pinia：auth（/auth/me 会话与水合）
  types/        Tiptap JSON、评论树类型
  utils/        日期、作者展示、列表筛选参数、审计动作
  views/        页面级组件
  styles/       写路径、标签、审计日志样式
tests/          Vitest 单元 / 组件测试
```

约定：

- 富文本只按白名单节点渲染，未知节点仅渲染子节点，全程插值不使用 `v-html`。
- 编辑器 JSON 中媒体只存 object key，展示时由 `storageUrl()` 拼 `/storage/`。
- 不引入 Google Fonts，字体使用系统栈（构建产物已确认无外部字体请求）。
- 首期不引 TanStack Query，页面 `setup` 直接调用 `api/`。
- 图标统一使用 `@tabler/icons-vue`。
