import { api } from './client';
import type { ChangelogAttachmentInput, ChangelogDetail, ChangelogSummary, Page } from './types';

export interface ChangelogInput {
  title: string;
  content: import('@/types/content').JSONContent;
  attachments?: ChangelogAttachmentInput[];
}

export function listChangelogs(
  options: { limit?: number; cursor?: string | null; includeDrafts?: boolean } = {},
): Promise<Page<ChangelogSummary>> {
  const params = new URLSearchParams();
  params.set('limit', String(options.limit ?? 20));
  if (options.cursor) params.set('cursor', options.cursor);
  if (options.includeDrafts) params.set('include_drafts', 'true');
  return api.get<Page<ChangelogSummary>>(`/v1/changelogs?${params.toString()}`);
}

export function getChangelog(id: string): Promise<ChangelogDetail> {
  return api.get<ChangelogDetail>(`/v1/changelogs/${encodeURIComponent(id)}`);
}

export function createChangelog(input: ChangelogInput): Promise<ChangelogDetail> {
  return api.post<ChangelogDetail>('/v1/changelogs', input);
}

export function updateChangelog(
  id: string,
  input: Partial<ChangelogInput>,
): Promise<ChangelogDetail> {
  return api.patch<ChangelogDetail>(`/v1/changelogs/${encodeURIComponent(id)}`, input);
}

export function publishChangelog(id: string): Promise<ChangelogDetail> {
  return api.post<ChangelogDetail>(`/v1/changelogs/${encodeURIComponent(id)}/publish`);
}

export function unpublishChangelog(id: string): Promise<ChangelogDetail> {
  return api.post<ChangelogDetail>(`/v1/changelogs/${encodeURIComponent(id)}/unpublish`);
}

export function deleteChangelog(id: string): Promise<void> {
  return api.delete<void>(`/v1/changelogs/${encodeURIComponent(id)}`);
}
