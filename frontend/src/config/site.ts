import { reactive } from 'vue'
import { getSiteInfo } from '@/api/site'

/** 站点名称由后端读取 ENV / deploy/.env 的 APP_NAME，构建期无需注入。 */
export const site = reactive({ name: 'FeedLog' })

export async function loadSiteName(): Promise<void> {
  try {
    const info = await getSiteInfo()
    if (info.name.trim()) site.name = info.name.trim()
  } catch {
    // 后端不可用时保留兜底名称，不影响页面渲染。
  }
}
