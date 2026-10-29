import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 本地开发：/api 反代后端；媒体前缀（默认 /storage，可随 S3_BUCKET 改）反代本机 RustFS。
// 子路径前缀是容器启动期注入的（见 docker-entrypoint.sh），构建产物本身与前缀无关。
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'
const storageTarget = process.env.VITE_STORAGE_PROXY_TARGET ?? 'http://127.0.0.1:9000'
const storagePrefix = process.env.S3_BUCKET ?? 'storage'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: false,
      },
      // 与生产 Caddy 一致：不重写路径、透传 Host，保证 SigV4 的 canonical URI
      // 与浏览器实际请求（/<bucket>/<key>）完全一致；Range 请求原样透传。
      [`/${storagePrefix}`]: {
        target: storageTarget,
        changeOrigin: false,
      },
    },
  },
})
