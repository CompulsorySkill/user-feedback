import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { PostSummary } from '@/api/types';

const mocks = vi.hoisted(() => ({ listAllPosts: vi.fn() }));

vi.mock('@/api/boards', () => ({ listAllPosts: mocks.listAllPosts }));

import PostRefPicker from '@/components/PostRefPicker.vue';

function post(overrides: Partial<PostSummary> = {}): PostSummary {
  return {
    id: 'post-1',
    board_slug: 'product',
    board_name: '功能建议',
    title: '导出功能坏了',
    excerpt: '导出 CSV 时报错',
    status: 'open',
    vote_count: 0,
    comment_count: 0,
    author_name: null,
    anonymous_name: null,
    is_anonymous: true,
    created_at: '2026-03-01T12:00:00Z',
    updated_at: '2026-03-01T12:00:00Z',
    tags: [],
    ...overrides,
  };
}

// 弹层 teleport 到 body，只能从 document 取
function row(): HTMLElement {
  return document.querySelector<HTMLElement>('button.w-full')!;
}

describe('PostRefPicker 引用选择器', () => {
  beforeEach(() => {
    mocks.listAllPosts.mockReset();
    mocks.listAllPosts.mockResolvedValue({ items: [post()], next_cursor: null });
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('打开时列出最近反馈，选中后抛出 pick 并关闭', async () => {
    const wrapper = mount(PostRefPicker, { props: { open: false } });
    await wrapper.setProps({ open: true });
    await flushPromises();

    expect(mocks.listAllPosts).toHaveBeenCalledWith({ limit: 8, q: null });
    expect(row().textContent).toContain('导出功能坏了');

    row().click();
    await flushPromises();

    expect(wrapper.emitted('pick')?.[0]).toEqual([{ id: 'post-1', title: '导出功能坏了' }]);
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false]);
    wrapper.unmount();
  });

  it('搜索时带上关键词，无结果时给空态', async () => {
    const wrapper = mount(PostRefPicker, { props: { open: true } });
    await flushPromises();
    mocks.listAllPosts.mockResolvedValue({ items: [], next_cursor: null });

    const input = document.querySelector<HTMLInputElement>('input[type="search"]')!;
    input.value = '登录';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await flushPromises();
    document.querySelector<HTMLFormElement>('form')!.requestSubmit();
    await flushPromises();

    expect(mocks.listAllPosts.mock.calls.at(-1)?.[0]).toEqual({ limit: 8, q: '登录' });
    expect(document.body.textContent).toContain('没有匹配的反馈。');
    wrapper.unmount();
  });
});
