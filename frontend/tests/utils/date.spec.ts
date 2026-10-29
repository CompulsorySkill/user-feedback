import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { formatDate, formatDateTime, formatRelative } from '@/utils/date';

describe('date utils', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-01T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('formats dates and empty values', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate('2026-03-01T12:00:00Z')).toMatch(/2026/);
    expect(formatDateTime(null)).toBe('—');
    expect(formatDateTime('2026-03-01T12:00:00Z')).toMatch(/2026/);
  });

  it('formats relative minutes, hours and days', () => {
    expect(formatRelative('2026-03-01T11:55:00Z')).toContain('分钟');
    expect(formatRelative('2026-03-01T09:00:00Z')).toContain('小时');
    expect(formatRelative('2026-02-27T12:00:00Z')).toContain('天');
    expect(formatRelative(null)).toBe('—');
  });
});
