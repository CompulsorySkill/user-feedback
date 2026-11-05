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
});
