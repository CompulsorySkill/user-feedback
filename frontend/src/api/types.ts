export interface Board {
  id: number
  slug: string
  name: string
  description: string | null
  is_public: boolean
  allow_guest_posting: boolean
  allow_guest_voting: boolean
  allow_guest_commenting: boolean
  post_count: number
  created_at: string
}

export interface BoardInput {
  slug: string
  name: string
  description: string | null
  is_public: boolean
  allow_guest_posting: boolean
  allow_guest_voting: boolean
  allow_guest_commenting: boolean
}

export interface BoardRef {
  id: number
  slug: string
  name: string
}

export type PostStatus = 'open' | 'planned' | 'in_progress' | 'completed' | 'closed'

export interface TagRef {
  id: number
  name: string
  is_builtin: boolean
}

export interface TagSummary extends TagRef {
  post_count: number
}

export interface PostSummary {
  id: string
  board_slug: string
  board_name: string
  title: string
  excerpt: string
  status: PostStatus
  vote_count: number
  comment_count: number
  author_name: string | null
  anonymous_name: string | null
  is_anonymous: boolean
  created_at: string
  updated_at: string
  tags: TagRef[]
}

export interface ClientEnvironment {
  user_agent?: string | null
  platform?: string | null
  language?: string | null
  viewport?: string | null
  timezone?: string | null
}

export interface PostDetail extends PostSummary {
  board: BoardRef
  content: import('@/types/content').JSONContent
  environment: ClientEnvironment | null
  is_author: boolean
}

export interface ChangelogSummary {
  id: string
  title: string
  excerpt: string
  is_published: boolean
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface ChangelogAttachment {
  id: number
  object_key: string | null
  filename: string
  content_type: string
  size: number
  download_url: string
}

export interface ChangelogAttachmentInput {
  object_key: string
  filename: string
}

export interface ChangelogDetail extends ChangelogSummary {
  content: import('@/types/content').JSONContent
  attachments: ChangelogAttachment[]
}

export interface Page<T> {
  items: T[]
  next_cursor: string | null
}

export interface AuditLogItem {
  id: number
  actor_email: string | null
  action: string
  target_type: string | null
  target_id: string | null
  detail: Record<string, unknown> | null
  ip: string | null
  created_at: string
}

export interface UploadCleanupResult {
  dry_run: boolean
  grace_hours: number
  scanned: number
  referenced: number
  deleted: number
  failed: number
  errors: string[]
}

export type UploadPurpose =
  | 'post_image'
  | 'post_video'
  | 'changelog_image'
  | 'changelog_video'
  | 'changelog_attachment'

export interface UploadTicket {
  object_key: string
  upload_url: string
  method: 'PUT'
  expires_in: number
  headers: Record<string, string>
}

export interface VoteResult {
  voted: boolean
  vote_count: number
}

export interface PostCreateInput {
  title: string
  content: import('@/types/content').JSONContent
  anonymous_name?: string | null
  environment?: ClientEnvironment | null
  tags?: string[]
}
