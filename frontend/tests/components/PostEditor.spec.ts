import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/api/site', () => ({
  listAdminMentions: vi.fn().mockResolvedValue([{ id: 1, name: 'Alice' }]),
}));

import PostEditor from '@/components/PostEditor.vue';

describe('PostEditor @ 按钮', () => {
  it('插入 @ 并打开管理员候选浮层', async () => {
    const wrapper = mount(PostEditor);
    await flushPromises();

    const button = wrapper
      .findAll('button')
      .find((item) => item.attributes('title') === '提及管理员');
    expect(button).toBeTruthy();
    await button?.trigger('click');
    await flushPromises();

    expect(wrapper.find('.tiptap').text()).toContain('@');
    expect(document.querySelector('.mention-popup')).toBeTruthy();
    expect(document.querySelector('.mention-popup')?.textContent).toContain('@Alice');

    wrapper.unmount();
  });
});
