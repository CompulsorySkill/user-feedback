import { api } from './client'
import type { TagSummary } from './types'

export function listBuiltinTags(): Promise<TagSummary[]> {
  return api.get<TagSummary[]>('/v1/tags')
}

/** 筛选器使用：内置标签 + 用户创建的标签；传 boardSlug 时计数只统计该看板。 */
export function listFilterTags(boardSlug?: string | null): Promise<TagSummary[]> {
  const query = boardSlug ? `&board=${encodeURIComponent(boardSlug)}` : ''
  return api.get<TagSummary[]>(`/v1/tags?include_custom=true${query}`)
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
