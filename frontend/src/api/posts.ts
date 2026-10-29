import { api } from './client';
import type { PostDetail, VoteResult } from './types';

export function getPost(id: string): Promise<PostDetail> {
  return api.get<PostDetail>(`/v1/posts/${encodeURIComponent(id)}`);
}

export function votePost(id: string): Promise<VoteResult> {
  return api.post<VoteResult>(`/v1/posts/${encodeURIComponent(id)}/vote`);
}

export function unvotePost(id: string): Promise<VoteResult> {
  return api.delete<VoteResult>(`/v1/posts/${encodeURIComponent(id)}/vote`);
}

export function deletePost(id: string): Promise<void> {
  return api.delete<void>(`/v1/posts/${encodeURIComponent(id)}`);
}
