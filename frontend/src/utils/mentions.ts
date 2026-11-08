import type { CommentItem } from '@/api/comments';
import type { PostDetail } from '@/api/types';
import type { JSONContent } from '@/types/content';
import { authorLabel } from '@/utils/author';

export interface MentionSource {
  kind: '正文' | '评论';
  by: string;
}

export interface MentionedUser {
  label: string;
  sources: MentionSource[];
}

function collectLabels(node: JSONContent | null, labels: string[]): void {
  if (!node) return;
  if (node.type === 'mention') {
    const label = node.attrs?.label;
    if (typeof label === 'string' && label.trim()) labels.push(label.trim());
    return;
  }
  for (const child of node.content ?? []) collectLabels(child, labels);
}

function commentAuthor(comment: CommentItem): string {
  if (comment.is_anonymous) return '匿名用户';
  return comment.author_name?.trim() || '用户';
}

/** 按首次出现顺序汇总正文与评论中的 mention，同一用户合并来源。 */
export function collectMentions(post: PostDetail, comments: CommentItem[]): MentionedUser[] {
  const users = new Map<string, MentionedUser>();
  const seenSources = new Map<string, Set<string>>();

  function add(label: string, source: MentionSource): void {
    let user = users.get(label);
    if (!user) {
      user = { label, sources: [] };
      users.set(label, user);
      seenSources.set(label, new Set());
    }
    const key = `${source.kind}:${source.by}`;
    if (seenSources.get(label)?.has(key)) return;
    seenSources.get(label)?.add(key);
    user.sources.push(source);
  }

  const postLabels: string[] = [];
  collectLabels(post.content, postLabels);
  for (const label of postLabels) add(label, { kind: '正文', by: authorLabel(post) });

  for (const comment of comments) {
    const labels: string[] = [];
    collectLabels(comment.content, labels);
    for (const label of labels) add(label, { kind: '评论', by: commentAuthor(comment) });
  }

  return [...users.values()];
}
