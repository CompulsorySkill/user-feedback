import { describe, expect, it } from 'vitest'
import {
  buildPostQuery,
  normalizeSearch,
  normalizeSort,
  normalizeStatus,
  normalizeTags,
} from '@/utils/postFilters'

describe('postFilters', () => {
  it('normalizes status and sort with safe defaults', () => {
    expect(normalizeStatus('in_progress')).toBe('in_progress')
    expect(normalizeStatus('done')).toBe('')
    expect(normalizeStatus(null)).toBe('')
    expect(normalizeSort('top')).toBe('top')
    expect(normalizeSort('oldest')).toBe('recent')
  })

  it('trims, deduplicates and limits tag filters', () => {
    expect(normalizeTags([' Bug ', 'bug', 'UI'])).toEqual(['Bug', 'UI'])
    expect(normalizeTags('性能')).toEqual(['性能'])
    expect(normalizeTags(undefined)).toEqual([])
    expect(normalizeTags(['a', 'b', 'c', 'd', 'e', 'f'])).toEqual(['a', 'b', 'c', 'd', 'e'])
  })

  it('builds repeated tag query params and omits empty filters', () => {
    const query = new URLSearchParams(
      buildPostQuery({
        status: 'open',
        sort: 'top',
        q: '  登录  ',
        tags: ['Bug', '体验'],
      }),
    )

    expect(query.get('limit')).toBe('10')
    expect(query.get('status')).toBe('open')
    expect(query.get('sort')).toBe('top')
    expect(query.get('q')).toBe('登录')
    expect(query.getAll('tag')).toEqual(['Bug', '体验'])
    expect(query.get('cursor')).toBeNull()
  })

  it('normalizes search length', () => {
    expect(normalizeSearch('  hello  ')).toBe('hello')
    expect(normalizeSearch('x'.repeat(120))).toHaveLength(100)
    expect(normalizeSearch(42)).toBe('')
  })
})
