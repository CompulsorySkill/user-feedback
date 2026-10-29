import { appBase } from '@/config/base';

// 兜底用运行时前缀；启动后会用 /v1/site 的 storage_prefix（含 BASE_PATH）覆盖。
let storagePrefix = `${appBase()}/storage/`;

/**
 * 媒体前缀由后端 `GET /v1/site` 的 `storage_prefix` 提供（等于 S3_BUCKET），
 * 启动时设置一次；Caddy 把该前缀原样反代给 RustFS（path-style 签名）。
 */
export function setStoragePrefix(prefix: string): void {
  const normalized = prefix.trim().replace(/^\/+|\/+$/g, '');
  if (normalized) storagePrefix = `/${normalized}/`;
}

/**
 * 富文本中的图片 / 视频 src 存 object key，渲染时拼上媒体前缀。
 * 带协议的绝对地址与 data: 直接透传；写入侧的归属校验在服务端完成。
 */
export function storageUrl(src: string): string {
  if (/^(https?:)?\/\//i.test(src) || src.startsWith('data:')) {
    return src;
  }
  return `${storagePrefix}${src.replace(/^\/+/, '')}`;
}
