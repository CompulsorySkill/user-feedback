import type { PostStatus } from '@/api/types';

export type PostSort = 'recent' | 'top';

export const POST_STATUSES: PostStatus[] = [
  'open',
  'planned',
  'in_progress',
  'completed',
  'closed',
];

const VALID_STATUSES = new Set<string>(POST_STATUSES);
export const MAX_FILTER_TAGS = 5;

export function normalizeStatus(value: unknown): PostStatus | '' {
  return typeof value === 'string' && VALID_STATUSES.has(value) ? (value as PostStatus) : '';
}

export function normalizeSearch(value: unknown): string {
  return typeof value === 'string' ? value.trim().slice(0, 100) : '';
}

/** URL 中 tag 可能是单个字符串（?tag=a）或数组（?tag=a&tag=b）。 */
export function normalizeTags(value: unknown): string[] {
  const raw = Array.isArray(value) ? value : value === undefined || value === null ? [] : [value];
  const seen = new Set<string>();
  const tags: string[] = [];
  for (const item of raw) {
    if (typeof item !== 'string') continue;
    const name = item.trim().slice(0, 24);
    const key = name.toLocaleLowerCase();
    if (!name || seen.has(key)) continue;
    seen.add(key);
    tags.push(name);
    if (tags.length >= MAX_FILTER_TAGS) break;
  }
  return tags;
}

export function normalizeSort(value: unknown): PostSort {
  return value === 'top' ? 'top' : 'recent';
}

export interface PostQueryOptions {
  limit?: number;
  cursor?: string | null;
  status?: PostStatus | null;
  sort?: PostSort;
  q?: string | null;
  tags?: string[];
  board?: string | null;
}

export function buildPostQuery(options: PostQueryOptions): string {
  const params = new URLSearchParams();
  params.set('limit', String(options.limit ?? 10));
  if (options.cursor) params.set('cursor', options.cursor);
  if (options.status) params.set('status', options.status);
  params.set('sort', options.sort ?? 'recent');
  if (options.q) params.set('q', options.q.trim());
  for (const tag of normalizeTags(options.tags)) params.append('tag', tag);
  if (options.board) params.set('board', options.board);
  return params.toString();
}
