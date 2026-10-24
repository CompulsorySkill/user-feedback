import { api } from './client'
import type {
  Board,
  Page,
  PostCreateInput,
  PostDetail,
  PostStatus,
  PostSummary,
} from './types'

export function listBoards(): Promise<Board[]> {
  return api.get<Board[]>('/v1/boards')
}

export function getBoard(slug: string): Promise<Board> {
  return api.get<Board>(`/v1/boards/${encodeURIComponent(slug)}`)
}

export type PostSort = 'recent' | 'top'

export interface ListPostsOptions {
  limit?: number
  cursor?: string | null
  status?: PostStatus | null
  sort?: PostSort
}

export function listBoardPosts(
  slug: string,
  options: ListPostsOptions = {},
): Promise<Page<PostSummary>> {
  const params = new URLSearchParams()
  params.set('limit', String(options.limit ?? 10))
  if (options.cursor) params.set('cursor', options.cursor)
  if (options.status) params.set('status', options.status)
  params.set('sort', options.sort ?? 'recent')
  return api.get<Page<PostSummary>>(
    `/v1/boards/${encodeURIComponent(slug)}/posts?${params.toString()}`,
  )
}

export function createPost(
  slug: string,
  input: PostCreateInput,
): Promise<PostDetail> {
  return api.post<PostDetail>(`/v1/boards/${encodeURIComponent(slug)}/posts`, input)
}
