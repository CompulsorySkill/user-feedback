export const AUDIT_ACTIONS: Array<{ value: string; label: string }> = [
  { value: 'board.create', label: '创建看板' },
  { value: 'board.update', label: '修改看板' },
  { value: 'board.delete', label: '删除看板' },
  { value: 'tag.create', label: '新增标签' },
  { value: 'tag.delete', label: '删除标签' },
  { value: 'post.update', label: '编辑反馈' },
  { value: 'post.status', label: '变更反馈状态' },
  { value: 'changelog.create', label: '创建更新日志' },
  { value: 'changelog.update', label: '编辑更新日志' },
  { value: 'changelog.delete', label: '删除更新日志' },
  { value: 'changelog.publish', label: '发布更新日志' },
  { value: 'changelog.unpublish', label: '撤回更新日志' },
  { value: 'upload.cleanup', label: '清理上传对象' },
]

const ACTION_LABELS = new Map(AUDIT_ACTIONS.map((item) => [item.value, item.label]))

export function auditActionLabel(action: string): string {
  return ACTION_LABELS.get(action) ?? action
}

export function formatAuditDetail(detail: Record<string, unknown> | null): string {
  if (!detail) return ''
  return Object.entries(detail)
    .map(([key, value]) => `${key}: ${typeof value === 'string' ? value : JSON.stringify(value)}`)
    .join(' · ')
}
