import { api } from './client'
import type { AuditLogItem, Page, UploadCleanupResult } from './types'

export interface AuditLogQuery {
  limit?: number
  before_id?: number | null
  action?: string | null
}

export function listAuditLogs(query: AuditLogQuery = {}): Promise<Page<AuditLogItem>> {
  const params = new URLSearchParams()
  params.set('limit', String(query.limit ?? 30))
  if (query.before_id) params.set('before_id', String(query.before_id))
  if (query.action) params.set('action', query.action)
  return api.get<Page<AuditLogItem>>(`/v1/admin/audit-logs?${params.toString()}`)
}

export function runUploadCleanup({
  dryRun = false,
  graceHours,
}: { dryRun?: boolean; graceHours?: number } = {}): Promise<UploadCleanupResult> {
  const params = new URLSearchParams({ dry_run: String(dryRun) })
  if (graceHours !== undefined) params.set('grace_hours', String(graceHours))
  return api.post<UploadCleanupResult>(`/v1/admin/uploads/cleanup?${params.toString()}`)
}
