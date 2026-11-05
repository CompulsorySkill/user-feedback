import { describe, expect, it } from 'vitest';

import {
  buildPostQuery,
  normalizeAuthor,
  normalizeSearch,
  normalizeSort,
  normalizeStatuses,
  normalizeTags,
} from '@/utils/postFilters';

describe('postFilters', () => {
  it('normalizes status and sort with safe defaults', () => {
    expect(normalizeStatuses('in_progress')).toEqual(['in_progress']);
    expect(normalizeStatuses(['open', 'done', 'open'])).toEqual(['open']);
    expect(normalizeStatuses(null)).toEqual([]);
    expect(normalizeSort('top')).toBe('top');
    expect(normalizeSort('oldest')).toBe('recent');
  });

  it('normalizes the author filter', () => {
    expect(normalizeAuthor(' 林小满 ')).toBe('林小满');
    expect(normalizeAuthor('')).toBeNull();
    expect(normalizeAuthor(undefined)).toBeNull();
  });

  it('trims, deduplicates and limits tag filters', () => {
    expect(normalizeTags([' Bug ', 'bug', 'UI'])).toEqual(['Bug', 'UI']);
    expect(normalizeTags('性能')).toEqual(['性能']);
    expect(normalizeTags(undefined)).toEqual([]);
    expect(normalizeTags(['a', 'b', 'c', 'd', 'e', 'f'])).toEqual(['a', 'b', 'c', 'd', 'e']);
  });

  it('builds repeated tag query params and omits empty filters', () => {
    const query = new URLSearchParams(
      buildPostQuery({
        status: ['open', 'planned'],
        author: '林小满',
        sort: 'top',
        q: '  登录  ',
        tags: ['Bug', '体验'],
      }),
    );

    expect(query.get('limit')).toBe('10');
    expect(query.getAll('status')).toEqual(['open', 'planned']);
    expect(query.get('author')).toBe('林小满');
    expect(query.get('sort')).toBe('top');
    expect(query.get('q')).toBe('登录');
    expect(query.getAll('tag')).toEqual(['Bug', '体验']);
    expect(query.get('cursor')).toBeNull();
  });

  it('normalizes search length', () => {
    expect(normalizeSearch('  hello  ')).toBe('hello');
    expect(normalizeSearch('x'.repeat(120))).toHaveLength(100);
    expect(normalizeSearch(42)).toBe('');
  });
});
