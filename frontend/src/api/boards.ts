import { api } from './client'
import type {
  Board,
  BoardInput,
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
  q?: string | null
}

function postQuery(options: ListPostsOptions): string {
  const params = new URLSearchParams()
  params.set('limit', String(options.limit ?? 10))
  if (options.cursor) params.set('cursor', options.cursor)
  if (options.status) params.set('status', options.status)
  params.set('sort', options.sort ?? 'recent')
  if (options.q) params.set('q', options.q)
  return params.toString()
}

export function listBoardPosts(
  slug: string,
  options: ListPostsOptions = {},
): Promise<Page<PostSummary>> {
  return api.get<Page<PostSummary>>(
    `/v1/boards/${encodeURIComponent(slug)}/posts?${postQuery(options)}`,
  )
}

/** 根页面：全部公开看板的反馈汇总。 */
export function listAllPosts(
  options: ListPostsOptions & { board?: string | null } = {},
): Promise<Page<PostSummary>> {
  const params = new URLSearchParams(postQuery(options))
  if (options.board) params.set('board', options.board)
  return api.get<Page<PostSummary>>(`/v1/posts?${params.toString()}`)
}

export function createPost(
  slug: string,
  input: PostCreateInput,
): Promise<PostDetail> {
  return api.post<PostDetail>(`/v1/boards/${encodeURIComponent(slug)}/posts`, input)
}

// --------------------------------------------------------------------------- //
// 管理员看板维护
// --------------------------------------------------------------------------- //

export interface BoardUpdateInput {
  slug?: string
  name?: string
  description?: string | null
  is_public?: boolean
  allow_guest_posting?: boolean
  allow_guest_voting?: boolean
  allow_guest_commenting?: boolean
}

export function listAdminBoards(): Promise<Board[]> {
  return api.get<Board[]>('/v1/admin/boards')
}

export function createBoard(input: BoardInput): Promise<Board> {
  return api.post<Board>('/v1/admin/boards', input)
}

export function updateBoard(id: number, input: BoardUpdateInput): Promise<Board> {
  return api.patch<Board>(`/v1/admin/boards/${id}`, input)
}

export function deleteBoard(id: number, force = false): Promise<void> {
  const query = force ? '?force=true' : ''
  return api.delete<void>(`/v1/admin/boards/${id}${query}`)
}
