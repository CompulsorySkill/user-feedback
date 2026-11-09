import { api } from './client';
import type { AdminTaskItem, Page, TaskState } from './types';

export interface AdminTaskQuery {
  limit?: number;
  before?: string | null;
  taskState?: TaskState | null;
  board?: string | null;
}

/** 管理员任务面板：只返回「@ 了当前管理员」的反馈。 */
export function listAdminTasks(query: AdminTaskQuery = {}): Promise<Page<AdminTaskItem>> {
  const params = new URLSearchParams();
  params.set('limit', String(query.limit ?? 30));
  if (query.before) params.set('before', query.before);
  if (query.taskState) params.set('task_state', query.taskState);
  if (query.board) params.set('board', query.board);
  return api.get<Page<AdminTaskItem>>(`/v1/admin/tasks?${params.toString()}`);
}
