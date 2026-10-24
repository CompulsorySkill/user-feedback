import { api } from './client'
import type { TagSummary } from './types'

export function listBuiltinTags(): Promise<TagSummary[]> {
  return api.get<TagSummary[]>('/v1/tags')
}

export function listAdminTags(): Promise<TagSummary[]> {
  return api.get<TagSummary[]>('/v1/admin/tags')
}

export function createBuiltinTag(name: string): Promise<TagSummary> {
  return api.post<TagSummary>('/v1/admin/tags', { name })
}

export function deleteTag(id: number): Promise<void> {
  return api.delete<void>(`/v1/admin/tags/${id}`)
}
