import { api } from './client';
import type { PostDetail, PostStatus } from './types';

export interface PostUpdateInput {
  title?: string;
  content?: import('@/types/content').JSONContent;
  tags?: string[];
}

export function updatePostStatus(id: string, status: PostStatus): Promise<PostDetail> {
  return api.patch<PostDetail>(`/v1/posts/${encodeURIComponent(id)}/status`, { status });
}

export function acceptPostTask(id: string): Promise<PostDetail> {
  return api.post<PostDetail>(`/v1/posts/${encodeURIComponent(id)}/task/accept`, {});
}

export function completePostTask(id: string): Promise<PostDetail> {
  return api.post<PostDetail>(`/v1/posts/${encodeURIComponent(id)}/task/complete`, {});
}

export function updatePost(id: string, input: PostUpdateInput): Promise<PostDetail> {
  return api.patch<PostDetail>(`/v1/posts/${encodeURIComponent(id)}`, input);
}
