import { describe, expect, it } from 'vitest'
import { auditActionLabel, formatAuditDetail } from '@/utils/audit'

describe('audit utils', () => {
  it('maps known actions and falls back to the raw code', () => {
    expect(auditActionLabel('board.create')).toBe('创建看板')
    expect(auditActionLabel('upload.cleanup')).toBe('清理上传对象')
    expect(auditActionLabel('custom.action')).toBe('custom.action')
  })

  it('flattens audit details for display', () => {
    expect(formatAuditDetail(null)).toBe('')
    expect(formatAuditDetail({ slug: 'product', force: false, count: 2 })).toBe(
      'slug: product · force: false · count: 2',
    )
  })
})
