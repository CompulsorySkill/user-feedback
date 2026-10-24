import type { PostSummary } from '@/api/types'

type AuthorFields = Pick<PostSummary, 'is_anonymous' | 'author_name' | 'anonymous_name'>

/** 展示名：匿名时用自定义昵称，回退「匿名用户」；登录用户用显示名。 */
export function authorLabel(post: AuthorFields): string {
  if (post.is_anonymous) {
    return post.anonymous_name?.trim() || '匿名用户'
  }
  return post.author_name?.trim() || '用户'
}
