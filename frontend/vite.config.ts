import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig, type Plugin } from 'vite'

// 本地开发：/api 反代到本机后端；/storage 由下面的中间件模拟 Nginx + RustFS。
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'
const storageRoot = fileURLToPath(new URL('../backend/.dev-storage', import.meta.url))

const MIME_TYPES: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
}

/**
 * 开发期以 `/storage/` 提供 seed 生成的演示媒体，保留 Range 语义，
 * 与生产 Nginx `proxy_pass http://rustfs:9000;` 的路径行为一致。
 */
function devStorage(): Plugin {
  return {
    name: 'feedlog-dev-storage',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/storage', (req, res, next) => {
        const requestPath = decodeURIComponent((req.url ?? '/').split('?')[0] ?? '/')
        const filePath = path.join(storageRoot, requestPath)
        if (!filePath.startsWith(storageRoot)) {
          res.statusCode = 403
          res.end('forbidden')
          return
        }

        fs.stat(filePath, (error, stat) => {
          if (error || !stat.isFile()) {
            next()
            return
          }

          res.setHeader('Content-Type', MIME_TYPES[path.extname(filePath)] ?? 'application/octet-stream')
          res.setHeader('Accept-Ranges', 'bytes')
          res.setHeader('Cache-Control', 'no-cache')

          const range = req.headers.range
          if (range) {
            const match = /^bytes=(\d*)-(\d*)$/.exec(range)
            if (match) {
              const start = match[1] ? Number(match[1]) : stat.size - Number(match[2])
              const end = match[2] && match[1] ? Number(match[2]) : stat.size - 1
              if (Number.isNaN(start) || Number.isNaN(end) || start > end || start >= stat.size) {
                res.statusCode = 416
                res.setHeader('Content-Range', `bytes */${stat.size}`)
                res.end()
                return
              }
              res.statusCode = 206
              res.setHeader('Content-Range', `bytes ${start}-${end}/${stat.size}`)
              res.setHeader('Content-Length', end - start + 1)
              fs.createReadStream(filePath, { start, end }).pipe(res)
              return
            }
          }

          res.setHeader('Content-Length', stat.size)
          if (req.method === 'HEAD') {
            res.end()
            return
          }
          fs.createReadStream(filePath).pipe(res)
        })
      })
    },
  }
}

export default defineConfig({
  plugins: [vue(), devStorage()],
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
    },
  },
})
