import { api } from './client'
import type { Board, Page, PostSummary } from './types'

export function listBoards(): Promise<Board[]> {
  return api.get<Board[]>('/v1/boards')
}

export function getBoard(slug: string): Promise<Board> {
  return api.get<Board>(`/v1/boards/${encodeURIComponent(slug)}`)
}

export interface ListPostsOptions {
  limit?: number
  cursor?: string | null
}

export function listBoardPosts(
  slug: string,
  options: ListPostsOptions = {},
): Promise<Page<PostSummary>> {
  const params = new URLSearchParams()
  params.set('limit', String(options.limit ?? 10))
  if (options.cursor) params.set('cursor', options.cursor)
  return api.get<Page<PostSummary>>(
    `/v1/boards/${encodeURIComponent(slug)}/posts?${params.toString()}`,
  )
}
