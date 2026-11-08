import type { JSONContent } from '@/types/content';

import { api } from './client';

export interface CommentItem {
  id: string;
  post_id: string;
  parent_id: string | null;
  content: JSONContent;
  author_name: string | null;
  is_anonymous: boolean;
  created_at: string;
}

export interface CommentList {
  items: CommentItem[];
  total: number;
}

export function listComments(postId: string): Promise<CommentList> {
  return api.get<CommentList>(`/v1/posts/${encodeURIComponent(postId)}/comments`);
}

export function createComment(
  postId: string,
  input: { content: JSONContent; parent_id?: string | null },
): Promise<CommentItem> {
  return api.post<CommentItem>(`/v1/posts/${encodeURIComponent(postId)}/comments`, input);
}

export function deleteComment(postId: string, commentId: string): Promise<void> {
  return api.delete<void>(
    `/v1/posts/${encodeURIComponent(postId)}/comments/${encodeURIComponent(commentId)}`,
  );
}
