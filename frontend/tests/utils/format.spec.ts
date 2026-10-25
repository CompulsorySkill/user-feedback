import { describe, expect, it } from 'vitest'
import { formatBytes } from '@/utils/format'

describe('formatBytes', () => {
  it('formats common sizes', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2.00 KB')
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.00 MB')
  })
})
