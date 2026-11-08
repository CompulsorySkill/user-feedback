import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Board } from '@/api/types';
import { Select } from '@/components/ui/select';

const mocks = vi.hoisted(() => ({
  params: {} as Record<string, string>,
  listBoards: vi.fn(),
  createPost: vi.fn(),
  listBuiltinTags: vi.fn(),
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: mocks.params }),
  useRouter: () => ({ replace: mocks.replace, push: mocks.push }),
  RouterLink: { props: ['to'], template: '<a :data-to="to"><slot /></a>' },
}));
vi.mock('@/api/boards', () => ({
  listBoards: mocks.listBoards,
  createPost: mocks.createPost,
}));
vi.mock('@/api/tags', () => ({ listBuiltinTags: mocks.listBuiltinTags }));
vi.mock('@/components/PostEditor.vue', () => ({
  default: {
    template: '<div class="editor-stub" />',
    methods: {
      getJSON: () => ({ type: 'doc', content: [] }),
      isEmpty: () => false,
    },
  },
}));

import NewPostView from '@/views/NewPostView.vue';

// jsdom 没有指针捕获 / PointerEvent 相关 API，reka-ui 的 Select 会用到
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

function mountView() {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(NewPostView, { global: { plugins: [pinia] } });
}

// shadcn Select 的选项渲染在 teleport 到 body 的弹层里，只能从 document 取
async function openBoardOptions(wrapper: VueWrapper): Promise<string[]> {
  const trigger = wrapper.get('[data-slot="select-trigger"]').element as HTMLElement;
  trigger.dispatchEvent(
    new MouseEvent('pointerdown', { bubbles: true, cancelable: true, button: 0 }),
  );
  await flushPromises();
  if (!document.querySelector('[role="option"]')) {
    await wrapper.get('[data-slot="select-trigger"]').trigger('keydown', { key: 'Enter' });
    await flushPromises();
  }
  return [...document.querySelectorAll<HTMLElement>('[role="option"]')].map(
    (el) => el.textContent?.trim() ?? '',
  );
}

async function chooseBoard(wrapper: VueWrapper, slug: string): Promise<void> {
  // 选中动作走 reka 的指针事件，jsdom 下不稳定；这里直接触发 Select 的 v-model，
  // 覆盖的仍是本组件自己的逻辑（boardSlug 与 URL 同步）。
  wrapper.findComponent(Select).vm.$emit('update:model-value', slug);
  await flushPromises();
}

function triggerText(wrapper: VueWrapper): string {
  return wrapper.get('[data-slot="select-trigger"]').text().trim();
}

describe('NewPostView 看板选择', () => {
  beforeEach(() => {
    mocks.params = {};
    mocks.listBoards.mockResolvedValue([
      board(),
      board({ id: 2, slug: 'bugs', name: '问题反馈' }),
      board({ id: 3, slug: 'internal', name: '内部看板', allow_guest_posting: false }),
    ]);
    mocks.listBuiltinTags.mockResolvedValue([]);
    mocks.createPost.mockResolvedValue({ id: 'post-1' });
  });

  afterEach(() => {
    // 弹层 teleport 到 body，不清理会串到下个用例
    document.body.innerHTML = '';
  });

  it('从 /new 进入时默认第一个可匿名发布的看板，隐藏需登录的看板', async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(triggerText(wrapper)).toBe('功能需求');
    expect(await openBoardOptions(wrapper)).toEqual(['功能需求', '问题反馈']);
    const checked = [...document.querySelectorAll<HTMLElement>('[role="option"]')].find(
      (el) => el.getAttribute('data-state') === 'checked',
    );
    expect(checked?.textContent?.trim()).toBe('功能需求');
    wrapper.unmount();
  });

  it('切换看板后表单与 URL 一起更新', async () => {
    const wrapper = mountView();
    await flushPromises();

    await chooseBoard(wrapper, 'bugs');

    expect(mocks.replace).toHaveBeenCalledWith({
      name: 'new-post-board',
      params: { slug: 'bugs' },
    });
    // RouterLink 在测试里被 stub 成 <a :data-to>，用 data-to 定位返回链接
    expect(wrapper.find('a[data-to="/b/bugs"]').text()).toContain('问题反馈');
    expect(triggerText(wrapper)).toBe('问题反馈');
    wrapper.unmount();
  });

  it('提交时发布到所选的看板', async () => {
    const wrapper = mountView();
    await flushPromises();

    await chooseBoard(wrapper, 'bugs');
    await wrapper.find('input[maxlength="200"]').setValue('希望支持导出');
    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(mocks.createPost).toHaveBeenCalledWith('bugs', expect.objectContaining({}));
    expect(mocks.push).toHaveBeenCalledWith('/post/post-1');
    wrapper.unmount();
  });

  it('进入需登录的看板时保留选择并禁用发布', async () => {
    mocks.params = { slug: 'internal' };
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.text()).toContain('该看板已关闭匿名发布');
    expect(triggerText(wrapper)).toBe('内部看板');
    expect(await openBoardOptions(wrapper)).toEqual(['功能需求', '问题反馈', '内部看板']);
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined();
    wrapper.unmount();
  });
});
