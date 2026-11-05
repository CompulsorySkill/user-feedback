import { api } from './client';
import type { AdminMentionItem } from './types';

export interface SiteInfo {
  name: string;
  storage_prefix: string;
}

export function getSiteInfo(): Promise<SiteInfo> {
  return api.get<SiteInfo>('/v1/site');
}

export function listAdminMentions(): Promise<AdminMentionItem[]> {
  return api.get<AdminMentionItem[]>('/v1/admins');
}
