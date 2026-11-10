import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import RichTextRenderer from '@/components/RichTextRenderer.vue';
import type { JSONContent } from '@/types/content';

describe('RichTextRenderer', () => {
  it('把提及渲染成内联名字，不带链接', () => {
    const node: JSONContent = {
      type: 'doc',
      content: [
        {
          type: 'paragraph',
          content: [
            { type: 'text', text: '请 ' },
            { type: 'mention', attrs: { id: '3', label: 'Alice' } },
          ],
        },
      ],
    };

    const wrapper = mount(RichTextRenderer, { props: { node } });

    expect(wrapper.find('.rt-mention').text()).toBe('@Alice');
    expect(wrapper.find('a').exists()).toBe(false);
  });

  it('把 postRef 渲染成站内链接', () => {
    const node: JSONContent = {
      type: 'doc',
      content: [
        {
          type: 'paragraph',
          content: [
            { type: 'text', text: '参见 ' },
            {
              type: 'postRef',
              attrs: { id: '00000000-0000-4000-8000-000000000001', title: '导出功能坏了' },
            },
          ],
        },
      ],
    };

    const wrapper = mount(RichTextRenderer, {
      props: { node },
      global: {
        stubs: { RouterLink: { props: ['to'], template: '<a :data-to="to"><slot /></a>' } },
      },
    });

    const link = wrapper.get('.rt-post-ref');
    expect(link.attributes('data-to')).toBe('/post/00000000-0000-4000-8000-000000000001');
    expect(link.text()).toBe('→ 导出功能坏了');
  });
});
