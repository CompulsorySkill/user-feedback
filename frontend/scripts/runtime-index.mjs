// 构建后生成 index 模板：容器启动时用它注入部署前缀（BASE_PATH），
// 这样同一份镜像可以挂到任意子路径，不必为每个前缀重新构建。
import { readFileSync, writeFileSync } from 'node:fs'

const file = new URL('../dist/index.html', import.meta.url)
const html = readFileSync(file, 'utf8')
const marker = "<script>window.__FEEDLOG_BASE__='__BASE__';</script>"

if (html.includes('__FEEDLOG_BASE__')) {
  throw new Error('dist/index.html 已包含运行时注入标记，重复构建？')
}
if (!html.includes('</head>')) {
  throw new Error('dist/index.html 缺少 </head>，无法注入运行时 base')
}

writeFileSync(
  new URL('../dist/index.template.html', import.meta.url),
  html.replace('</head>', `${marker}</head>`),
)
console.log('dist/index.template.html written')
