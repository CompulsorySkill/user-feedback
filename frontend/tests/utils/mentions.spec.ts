import { describe, expect, it } from 'vitest';

import type { CommentItem } from '@/api/comments';
import type { PostDetail } from '@/api/types';
import type { JSONContent } from '@/types/content';
import { collectMentions } from '@/utils/mentions';

const stamp = '2026-03-01T12:00:00Z';

function mention(label: string): JSONContent {
  return { type: 'mention', attrs: { id: '1', label } };
}

function doc(...labels: string[]): JSONContent {
  return {
    type: 'doc',
    content: [
      {
        type: 'paragraph',
        content: labels.flatMap((label) => [mention(label), { type: 'text', text: ' ' }]),
      },
    ],
  };
}

function post(content: JSONContent): PostDetail {
  return {
    id: 'post-1',
    board_slug: 'general',
    board_name: 'General',
    title: '标题',
    excerpt: '',
    status: 'open',
    vote_count: 0,
    comment_count: 3,
    author_name: 'Alice',
    anonymous_name: null,
    is_anonymous: false,
    created_at: stamp,
    updated_at: stamp,
    tags: [],
    board: { id: 1, slug: 'general', name: 'General' },
    content,
    environment: null,
    is_author: false,
  };
}

function comment(
  id: string,
  content: JSONContent,
  author: string | null,
  anonymous = false,
): CommentItem {
  return {
    id,
    post_id: 'post-1',
    parent_id: null,
    content,
    author_name: author,
    is_anonymous: anonymous,
    created_at: stamp,
  };
}

describe('collectMentions', () => {
  it('汇总正文与评论提及，并标注来源和提及者', () => {
    const users = collectMentions(post(doc('Bob', 'Carol', 'Bob')), [
      comment('c1', doc('Bob', 'Carol'), 'Erin'),
      comment('c2', doc('Dave'), null, true),
      comment('c3', doc('Bob', 'Dave'), 'Erin'),
    ]);

    expect(users).toEqual([
      {
        label: 'Bob',
        sources: [
          { kind: '正文', by: 'Alice' },
          { kind: '评论', by: 'Erin' },
        ],
      },
      {
        label: 'Carol',
        sources: [
          { kind: '正文', by: 'Alice' },
          { kind: '评论', by: 'Erin' },
        ],
      },
      {
        label: 'Dave',
        sources: [
          { kind: '评论', by: '匿名用户' },
          { kind: '评论', by: 'Erin' },
        ],
      },
    ]);
  });

  it('没有提及时返回空列表', () => {
    expect(collectMentions(post({ type: 'doc', content: [{ type: 'paragraph' }] }), [])).toEqual(
      [],
    );
  });
});
