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

export interface BoardRef {
  id: number
  slug: string
  name: string
}

export type PostStatus = 'open' | 'planned' | 'in_progress' | 'completed' | 'closed'

export interface PostSummary {
  id: string
  board_slug: string
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

export interface ChangelogDetail extends ChangelogSummary {
  content: import('@/types/content').JSONContent
}

export interface Page<T> {
  items: T[]
  next_cursor: string | null
}

export type UploadPurpose =
  | 'post_image'
  | 'post_video'
  | 'changelog_image'
  | 'changelog_video'

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
}
