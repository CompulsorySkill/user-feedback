import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 本地开发：/api 反代后端；/storage 反代本机 RustFS。
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'
const storageTarget = process.env.VITE_STORAGE_PROXY_TARGET ?? 'http://127.0.0.1:9000'

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
      // 与生产 Nginx 一致：不重写路径、透传 Host，保证 SigV4 的 canonical URI
      // 与浏览器实际请求（/storage/<key>）完全一致；Range 请求原样透传。
      '/storage': {
        target: storageTarget,
        changeOrigin: false,
      },
    },
  },
})
