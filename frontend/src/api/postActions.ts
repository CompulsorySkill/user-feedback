import { api } from './client'
import type { PostDetail, PostStatus } from './types'

export interface PostUpdateInput {
  title?: string
  content?: import('@/types/content').JSONContent
}

export function updatePostStatus(id: string, status: PostStatus): Promise<PostDetail> {
  return api.patch<PostDetail>(`/v1/posts/${encodeURIComponent(id)}/status`, { status })
}

export function updatePost(id: string, input: PostUpdateInput): Promise<PostDetail> {
  return api.patch<PostDetail>(`/v1/posts/${encodeURIComponent(id)}`, input)
}
