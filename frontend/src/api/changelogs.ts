import { api } from './client'
import type { ChangelogDetail, ChangelogSummary, Page } from './types'

export function listChangelogs(
  options: { limit?: number; cursor?: string | null } = {},
): Promise<Page<ChangelogSummary>> {
  const params = new URLSearchParams()
  params.set('limit', String(options.limit ?? 20))
  if (options.cursor) params.set('cursor', options.cursor)
  return api.get<Page<ChangelogSummary>>(`/v1/changelogs?${params.toString()}`)
}

export function getChangelog(id: string): Promise<ChangelogDetail> {
  return api.get<ChangelogDetail>(`/v1/changelogs/${encodeURIComponent(id)}`)
}
