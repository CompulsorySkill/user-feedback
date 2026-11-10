import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PostDetail } from '@/api/types';

const mocks = vi.hoisted(() => ({
  params: { id: 'post-2' },
  getPost: vi.fn(),
  deletePost: vi.fn(),
  push: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: mocks.params }),
  useRouter: () => ({ push: mocks.push }),
  RouterLink: { props: ['to'], template: '<a :data-to="to"><slot /></a>' },
}));
vi.mock('@/api/posts', () => ({ getPost: mocks.getPost, deletePost: mocks.deletePost }));
vi.mock('@/components/CommentSection.vue', () => ({
  default: { template: '<div class="comments-stub" />' },
}));
vi.mock('@/components/PostTimeline.vue', () => ({
  default: { template: '<div class="timeline-stub" />' },
}));
vi.mock('@/components/RichTextRenderer.vue', () => ({
  default: { template: '<div class="rich-stub" />' },
}));
vi.mock('@/components/PostEditor.vue', () => ({ default: { template: '<div />' } }));
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => async () => true }));

import PostDetailView from '@/views/PostDetailView.vue';

function neighbor(id: string, title: string): { id: string; title: string; created_at: string } {
  return { id, title, created_at: '2026-03-01T12:00:00Z' };
}

function detail(overrides: Partial<PostDetail> = {}): PostDetail {
  return {
    id: 'post-2',
    board_slug: 'product',
    board_name: '功能建议',
    board: { id: 1, slug: 'product', name: '功能建议' },
    title: '当前这条反馈',
    excerpt: '',
    status: 'open',
    vote_count: 0,
    comment_count: 0,
    author_name: null,
    anonymous_name: null,
    is_anonymous: true,
    created_at: '2026-03-01T12:00:00Z',
    updated_at: '2026-03-01T12:00:00Z',
    tags: [],
    content: { type: 'doc', content: [] },
    environment: null,
    is_author: false,
    timeline: [],
    task: null,
    can_accept_task: false,
    can_complete_task: false,
    previous: [],
    next: [],
    ...overrides,
  };
}

async function mountView() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const wrapper = mount(PostDetailView, {
    global: {
      plugins: [pinia],
      stubs: {
        TagList: true,
        AuthorTag: true,
        PostStatusControl: true,
        StatusBadge: true,
        // 组件里靠全局注册的 RouterLink，测试里自己替
        RouterLink: { props: ['to'], template: '<a :data-to="to"><slot /></a>' },
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('PostDetailView 同看板侧栏', () => {
  beforeEach(() => {
    mocks.getPost.mockReset();
  });

  it('左侧列出前后各条并高亮当前反馈，时间线在右侧侧栏', async () => {
    mocks.getPost.mockResolvedValue(
      detail({
        previous: [neighbor('post-1', '更早的一条')],
        next: [neighbor('post-3', '更晚的一条')],
      }),
    );
    const wrapper = await mountView();

    const items = wrapper.findAll('.post-neighbors > li');
    expect(items.map((item) => item.text())).toEqual(['更早的一条', '当前这条反馈', '更晚的一条']);
    expect(wrapper.find('.post-neighbors a[data-to="/post/post-1"]').exists()).toBe(true);
    expect(wrapper.find('.post-neighbors a[data-to="/post/post-3"]').exists()).toBe(true);
    expect(wrapper.find('.post-neighbor-current').attributes('aria-current')).toBe('page');
    // 时间线搬到了右侧 sticky 侧栏，正文列里不再有它
    const sides = wrapper.findAll('.post-detail-side');
    expect(sides).toHaveLength(2);
    expect(sides[1]!.find('.timeline-stub').exists()).toBe(true);
    expect(wrapper.find('.post-detail-main .timeline-stub').exists()).toBe(false);
  });

  it('看板只有这一条反馈时显示空态', async () => {
    mocks.getPost.mockResolvedValue(detail());
    const wrapper = await mountView();

    expect(wrapper.find('.post-neighbors').exists()).toBe(false);
    expect(wrapper.text()).toContain('该看板还没有其他反馈。');
  });
});
