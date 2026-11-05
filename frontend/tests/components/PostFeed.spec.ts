import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PostSummary, TagSummary } from '@/api/types';

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  route: { query: {} as Record<string, unknown> },
  listAllPosts: vi.fn(),
  listBoardPosts: vi.fn(),
  listFilterTags: vi.fn(),
  listPostAuthors: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ replace: mocks.replace }),
}));
vi.mock('@/api/boards', () => ({
  listAllPosts: mocks.listAllPosts,
  listBoardPosts: mocks.listBoardPosts,
  listPostAuthors: mocks.listPostAuthors,
}));
vi.mock('@/api/tags', () => ({ listFilterTags: mocks.listFilterTags }));
vi.mock('@/components/PostCard.vue', () => ({
  default: { template: '<div class="post-card-stub" />' },
}));

import FilterCombobox from '@/components/FilterCombobox.vue';
import PostFeed from '@/components/PostFeed.vue';

const post: PostSummary = {
  id: 'post-1',
  board_slug: 'product',
  board_name: '功能建议',
  title: '支持标签筛选',
  excerpt: '正文',
  status: 'open',
  vote_count: 1,
  comment_count: 0,
  author_name: null,
  anonymous_name: null,
  is_anonymous: true,
  created_at: '2026-03-01T12:00:00Z',
  updated_at: '2026-03-01T12:00:00Z',
  tags: [],
};

const tag: TagSummary = {
  id: 1,
  name: 'Bug',
  is_builtin: true,
  post_count: 2,
};

describe('PostFeed tag filter', () => {
  beforeEach(() => {
    mocks.route.query = {};
    mocks.listAllPosts.mockResolvedValue({ items: [post], next_cursor: null });
    mocks.listBoardPosts.mockResolvedValue({ items: [post], next_cursor: null });
    mocks.listFilterTags.mockResolvedValue([tag]);
    mocks.listPostAuthors.mockResolvedValue([{ name: '林小满', post_count: 2 }]);
  });

  it('writes the selected tags into the URL', async () => {
    const wrapper = mount(PostFeed);
    await flushPromises();

    expect(mocks.listAllPosts).toHaveBeenCalledWith(expect.objectContaining({ tags: [] }));

    // 第二个筛选器是标签，选项来自 listFilterTags（含计数）。
    const tagBox = wrapper.findAllComponents(FilterCombobox)[1];
    expect(tagBox.props('options')).toEqual([{ value: 'Bug', label: 'Bug', hint: 2 }]);
    tagBox.vm.$emit('update:modelValue', ['Bug']);

    expect(mocks.replace).toHaveBeenCalledWith({ query: { tag: ['Bug'] } });
    wrapper.unmount();
  });

  it('writes multiple statuses and the author into the URL', async () => {
    const wrapper = mount(PostFeed);
    await flushPromises();

    // 顺序：状态、标签、用户。
    const [statusBox, , authorBox] = wrapper.findAllComponents(FilterCombobox);
    statusBox.vm.$emit('update:modelValue', ['open', 'planned']);
    authorBox.vm.$emit('update:modelValue', ['林小满']);

    expect(mocks.replace).toHaveBeenLastCalledWith({
      query: { status: ['open', 'planned'], author: '林小满' },
    });
    wrapper.unmount();
  });

  it('uses tag params from the initial route', async () => {
    mocks.route.query = { tag: ['Bug', 'bug', '性能'] };
    const wrapper = mount(PostFeed);
    await flushPromises();

    expect(mocks.listAllPosts).toHaveBeenCalledWith(
      expect.objectContaining({ tags: ['Bug', '性能'] }),
    );
    wrapper.unmount();
  });

  it('scopes tag counts to the current board and reloads when it changes', async () => {
    const wrapper = mount(PostFeed, { props: { boardSlug: 'product' } });
    await flushPromises();

    expect(mocks.listFilterTags).toHaveBeenCalledWith('product');

    mocks.listFilterTags.mockClear();
    await wrapper.setProps({ boardSlug: 'other' });
    await flushPromises();

    expect(mocks.listFilterTags).toHaveBeenCalledWith('other');
    wrapper.unmount();
  });
});
