declare global {
  interface Window {
    __FEEDBACK_BASE__?: string
  }
}

/**
 * 部署前缀，由容器启动脚本按 BASE_PATH 注入到 index.html：
 * 根部署为 ""，子路径部署为 "/feedback"。镜像构建期不再需要指定。
 */
export function appBase(): string {
  return (window.__FEEDBACK_BASE__ ?? '').replace(/\/+$/, '')
}
