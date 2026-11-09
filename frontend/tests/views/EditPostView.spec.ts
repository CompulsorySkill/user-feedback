import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Board, PostDetail } from '@/api/types';
import { Select } from '@/components/ui/select';

const mocks = vi.hoisted(() => ({
  params: {} as Record<string, string>,
  getPost: vi.fn(),
  updatePost: vi.fn(),
  listBoards: vi.fn(),
  listBuiltinTags: vi.fn(),
  getMe: vi.fn(),
  push: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: mocks.params }),
  useRouter: () => ({ push: mocks.push }),
  RouterLink: { props: ['to'], template: '<a :data-to="to"><slot /></a>' },
}));
vi.mock('@/api/boards', () => ({ listBoards: mocks.listBoards }));
vi.mock('@/api/posts', () => ({ getPost: mocks.getPost }));
vi.mock('@/api/postActions', () => ({ updatePost: mocks.updatePost }));
vi.mock('@/api/tags', () => ({ listBuiltinTags: mocks.listBuiltinTags }));
vi.mock('@/api/auth', () => ({ getMe: mocks.getMe }));
vi.mock('@/components/PostEditor.vue', () => ({
  default: {
    template: '<div class="editor-stub" />',
    methods: {
      getJSON: () => ({ type: 'doc', content: [] }),
      isEmpty: () => false,
    },
  },
}));

import EditPostView from '@/views/EditPostView.vue';

beforeEach(() => {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
    Element.prototype.setPointerCapture = () => {};
    Element.prototype.releasePointerCapture = () => {};
  }
});

function board(overrides: Partial<Board> = {}): Board {
  return {
    id: 1,
    slug: 'product',
    name: '功能需求',
    description: null,
    is_public: true,
    allow_guest_posting: true,
    allow_guest_voting: true,
    allow_guest_commenting: true,
    post_count: 3,
    created_at: '2026-03-01T12:00:00Z',
    ...overrides,
  };
}

function post(overrides: Partial<PostDetail> = {}): PostDetail {
  return {
    id: 'post-1',
    board_slug: 'product',
    board_name: '功能需求',
    title: '希望支持导出',
    excerpt: '正文',
    status: 'open',
    vote_count: 0,
    comment_count: 0,
    author_name: 'Alice',
    anonymous_name: null,
    is_anonymous: false,
    created_at: '2026-03-01T12:00:00Z',
    updated_at: '2026-03-01T12:00:00Z',
    tags: [],
    board: { id: 1, slug: 'product', name: '功能需求' },
    content: { type: 'doc', content: [] },
    is_author: true,
    ...overrides,
  } as PostDetail;
}

function mountView() {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(EditPostView, { global: { plugins: [pinia] } });
}

async function chooseBoard(wrapper: VueWrapper, slug: string): Promise<void> {
  wrapper.findComponent(Select).vm.$emit('update:model-value', slug);
  await flushPromises();
}

describe('EditPostView 所属板块', () => {
  beforeEach(() => {
    mocks.params = { id: 'post-1' };
    mocks.getPost.mockResolvedValue(post());
    mocks.updatePost.mockResolvedValue(post());
    mocks.listBuiltinTags.mockResolvedValue([]);
    mocks.listBoards.mockResolvedValue([board(), board({ id: 2, slug: 'bugs', name: '问题反馈' })]);
    mocks.getMe.mockResolvedValue({ authenticated: true, is_admin: false });
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('默认显示当前所属板块', async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.get('[data-slot="select-trigger"]').text().trim()).toBe('功能需求');
    wrapper.unmount();
  });

  it('切换板块后提交 board_slug', async () => {
    const wrapper = mountView();
    await flushPromises();

    await chooseBoard(wrapper, 'bugs');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(mocks.updatePost).toHaveBeenCalledWith(
      'post-1',
      expect.objectContaining({ board_slug: 'bugs' }),
    );
    wrapper.unmount();
  });

  it('没切换板块时不提交 board_slug', async () => {
    const wrapper = mountView();
    await flushPromises();

    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(mocks.updatePost).toHaveBeenCalledTimes(1);
    expect(mocks.updatePost.mock.calls[0][1]).not.toHaveProperty('board_slug');
    wrapper.unmount();
  });

  it('当前板块已转非公开时仍显示在原选项里', async () => {
    mocks.getPost.mockResolvedValue(
      post({
        board_slug: 'archived',
        board: { id: 9, slug: 'archived', name: '已归档' },
      }),
    );
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.get('[data-slot="select-trigger"]').text().trim()).toBe('已归档');
    wrapper.unmount();
  });
});
