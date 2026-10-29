import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 子路径部署（如 /feedback/）：构建期设置 VITE_BASE=/feedback/，与后端 BASE_PATH 一致。
const base = process.env.VITE_BASE ?? '/'

// 本地开发：/api 反代后端；媒体前缀（默认 /storage，可随 S3_BUCKET 改）反代本机 RustFS。
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'
const storageTarget = process.env.VITE_STORAGE_PROXY_TARGET ?? 'http://127.0.0.1:9000'
const storagePrefix = process.env.S3_BUCKET ?? 'storage'
// Vite 的 proxy 匹配的是浏览器实际请求路径，必须带上 base 前缀。
const basePrefix = base.replace(/\/$/, '')
const stripBase = (path: string): string => path.slice(basePrefix.length) || '/'
const baseProxy = basePrefix ? { rewrite: stripBase } : {}

export default defineConfig({
  base,
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      [`${basePrefix}/api`]: {
        target: apiTarget,
        changeOrigin: false,
        ...baseProxy,
      },
      // 与生产 Caddy 一致：不重写路径、透传 Host，保证 SigV4 的 canonical URI
      // 与浏览器实际请求（/<bucket>/<key>）完全一致；Range 请求原样透传。
      [`${basePrefix}/${storagePrefix}`]: {
        target: storageTarget,
        changeOrigin: false,
        ...baseProxy,
      },
    },
  },
})
