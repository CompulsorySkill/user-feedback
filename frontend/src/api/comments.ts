import { api } from './client'

export interface CommentItem {
  id: string
  post_id: string
  parent_id: string | null
  content: string
  author_name: string | null
  is_anonymous: boolean
  created_at: string
}

export interface CommentList {
  items: CommentItem[]
  total: number
}

export function listComments(postId: string): Promise<CommentList> {
  return api.get<CommentList>(`/v1/posts/${encodeURIComponent(postId)}/comments`)
}

export function createComment(
  postId: string,
  input: { content: string; parent_id?: string | null },
): Promise<CommentItem> {
  return api.post<CommentItem>(`/v1/posts/${encodeURIComponent(postId)}/comments`, input)
}
