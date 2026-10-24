import { api } from './client'

export interface SiteInfo {
  name: string
}

export function getSiteInfo(): Promise<SiteInfo> {
  return api.get<SiteInfo>('/v1/site')
}
