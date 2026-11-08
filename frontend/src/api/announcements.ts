import { api } from './client';
import type {
  AnnouncementDetail,
  AnnouncementSummary,
  ChangelogAttachmentInput,
  Page,
} from './types';

export interface AnnouncementInput {
  title: string;
  content: import('@/types/content').JSONContent;
  attachments?: ChangelogAttachmentInput[];
}

export function listAnnouncements(
  options: { limit?: number; cursor?: string | null; includeDrafts?: boolean } = {},
): Promise<Page<AnnouncementSummary>> {
  const params = new URLSearchParams();
  params.set('limit', String(options.limit ?? 20));
  if (options.cursor) params.set('cursor', options.cursor);
  if (options.includeDrafts) params.set('include_drafts', 'true');
  return api.get<Page<AnnouncementSummary>>(`/v1/announcements?${params.toString()}`);
}

export function getAnnouncement(id: string): Promise<AnnouncementDetail> {
  return api.get<AnnouncementDetail>(`/v1/announcements/${encodeURIComponent(id)}`);
}

export function createAnnouncement(input: AnnouncementInput): Promise<AnnouncementDetail> {
  return api.post<AnnouncementDetail>('/v1/announcements', input);
}

export function updateAnnouncement(
  id: string,
  input: Partial<AnnouncementInput>,
): Promise<AnnouncementDetail> {
  return api.patch<AnnouncementDetail>(`/v1/announcements/${encodeURIComponent(id)}`, input);
}

export function publishAnnouncement(id: string): Promise<AnnouncementDetail> {
  return api.post<AnnouncementDetail>(`/v1/announcements/${encodeURIComponent(id)}/publish`);
}

export function unpublishAnnouncement(id: string): Promise<AnnouncementDetail> {
  return api.post<AnnouncementDetail>(`/v1/announcements/${encodeURIComponent(id)}/unpublish`);
}

export function pinAnnouncement(id: string): Promise<AnnouncementDetail> {
  return api.post<AnnouncementDetail>(`/v1/announcements/${encodeURIComponent(id)}/pin`);
}

export function unpinAnnouncement(id: string): Promise<AnnouncementDetail> {
  return api.post<AnnouncementDetail>(`/v1/announcements/${encodeURIComponent(id)}/unpin`);
}

export function deleteAnnouncement(id: string): Promise<void> {
  return api.delete<void>(`/v1/announcements/${encodeURIComponent(id)}`);
}
