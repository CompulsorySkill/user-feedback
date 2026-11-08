import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const doc = {
  type: 'doc',
  content: [{ type: 'paragraph', content: [{ type: 'text', text: '一条评论' }] }],
};

const mocks = vi.hoisted(() => ({
  listComments: vi.fn(),
  createComment: vi.fn(),
  deleteComment: vi.fn(),
  clear: vi.fn(),
}));

vi.mock('@/api/comments', () => ({
  listComments: mocks.listComments,
  createComment: mocks.createComment,
  deleteComment: mocks.deleteComment,
}));
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isAdmin: false }),
}));
vi.mock('@/components/PostEditor.vue', () => ({
  default: {
    name: 'PostEditor',
    emits: ['update:json', 'update:uploading'],
    template: '<div class="editor-stub" />',
    mounted() {
      this.$emit('update:json', doc);
    },
    methods: {
      getJSON: () => doc,
      isEmpty: () => false,
      clear: mocks.clear,
      focus: () => {},
    },
  },
}));

import CommentSection from '@/components/CommentSection.vue';

describe('CommentSection 评论区', () => {
  beforeEach(() => {
    mocks.listComments.mockReset().mockResolvedValue({
      items: [
        {
          id: 'comment-1',
          post_id: 'post-1',
          parent_id: null,
          content: doc,
          author_name: 'alice',
          is_anonymous: false,
          created_at: '2026-03-01T12:00:00Z',
        },
      ],
      total: 1,
    });
    mocks.createComment.mockReset().mockResolvedValue({});
    mocks.clear.mockReset();
  });

  it('用富文本渲染评论正文', async () => {
    const wrapper = mount(CommentSection, {
      props: { postId: 'post-1', closed: false },
    });
    await flushPromises();

    expect(wrapper.find('.comment-content').text()).toContain('一条评论');
  });

  it('提交编辑器 JSON 并清空输入', async () => {
    const wrapper = mount(CommentSection, {
      props: { postId: 'post-1', closed: false },
    });
    await flushPromises();

    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(mocks.createComment).toHaveBeenCalledWith('post-1', {
      content: doc,
      parent_id: null,
    });
    expect(mocks.clear).toHaveBeenCalled();
  });
});
