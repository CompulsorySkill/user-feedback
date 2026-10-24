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
  created_at: string
  updated_at: string
}

export interface PostDetail extends PostSummary {
  board: BoardRef
  content: import('@/types/content').JSONContent
}

export interface ChangelogSummary {
  id: string
  title: string
  excerpt: string
  published_at: string | null
  created_at: string
}

export interface ChangelogDetail extends ChangelogSummary {
  content: import('@/types/content').JSONContent
}

export interface Page<T> {
  items: T[]
  next_cursor: string | null
}
