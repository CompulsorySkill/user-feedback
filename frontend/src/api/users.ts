import { api } from './client';
import type { AdminUserItem, Page } from './types';

export interface AdminUserQuery {
  limit?: number;
  before_id?: number | null;
  q?: string | null;
  role?: 'user' | 'admin' | null;
}

/** 用户目录（管理员）：id 倒序 keyset 分页，与审计日志同一套游标语义。 */
export function listAdminUsers(query: AdminUserQuery = {}): Promise<Page<AdminUserItem>> {
  const params = new URLSearchParams();
  params.set('limit', String(query.limit ?? 30));
  if (query.before_id) params.set('before_id', String(query.before_id));
  if (query.q) params.set('q', query.q);
  if (query.role) params.set('role', query.role);
  return api.get<Page<AdminUserItem>>(`/v1/admin/users?${params.toString()}`);
}
