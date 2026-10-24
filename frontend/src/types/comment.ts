import type { CommentItem } from '@/api/comments'

export interface CommentNodeData extends CommentItem {
  children: CommentNodeData[]
}
