import { api } from './client'
import type { PostDetail } from './types'

export function getPost(id: string): Promise<PostDetail> {
  return api.get<PostDetail>(`/v1/posts/${encodeURIComponent(id)}`)
}
