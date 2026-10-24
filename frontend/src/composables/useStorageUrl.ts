const STORAGE_PREFIX = '/storage/'

/**
 * 富文本中的图片 / 视频 src 存 object key，渲染时拼上 /storage/。
 * 带协议的绝对地址与 data: 直接透传；写入侧的归属校验在 P2 服务端完成。
 */
export function storageUrl(src: string): string {
  if (/^(https?:)?\/\//i.test(src) || src.startsWith('data:')) {
    return src
  }
  return `${STORAGE_PREFIX}${src.replace(/^\/+/, '')}`
}
