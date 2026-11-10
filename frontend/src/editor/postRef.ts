import { mergeAttributes, Node } from '@tiptap/core';

/**
 * 正文里引用另一条反馈：只存 id 与标题快照，渲染时按库里最新标题展示，
 * 引用到的反馈被删除或转为非公开看板后不再显示。
 */
export const PostRef = Node.create({
  name: 'postRef',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      id: { default: null },
      title: { default: '' },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-post-ref]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-post-ref': HTMLAttributes.id,
        class: 'rt-post-ref',
      }),
      `→ ${HTMLAttributes.title}`,
    ];
  },
});
