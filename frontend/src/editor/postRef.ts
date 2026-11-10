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

  // 编辑器内用 emoji 前缀（@tabler 图标写进 renderHTML 会因 viewBox 被小写化而 0×0）；
  // 只读渲染走 RichTextRenderer，用真正的 IconLink。
  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-post-ref': HTMLAttributes.id,
        class: 'rt-post-ref',
      }),
      `🔗 ${HTMLAttributes.title}`,
    ];
  },
});
