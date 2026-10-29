import { reactive } from 'vue';

import { getSiteInfo } from '@/api/site';
import { setStoragePrefix } from '@/composables/useStorageUrl';

/** 站点名称由后端读取 ENV / deploy/.env 的 APP_NAME，构建期无需注入。 */
export const site = reactive({ name: 'Feedback' });

export async function loadSiteName(): Promise<void> {
  try {
    const info = await getSiteInfo();
    if (info.name.trim()) site.name = info.name.trim();
    // 媒体前缀来自 S3_BUCKET（默认 /storage），与 Caddy 反代路径一致。
    if (info.storage_prefix) setStoragePrefix(info.storage_prefix);
  } catch {
    // 后端不可用时保留兜底名称与 /storage 前缀，不影响页面渲染。
  }
}
