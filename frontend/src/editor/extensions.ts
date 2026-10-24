import { mergeAttributes, Node } from '@tiptap/core'
import Image from '@tiptap/extension-image'
import { storageUrl } from '@/composables/useStorageUrl'

/** 编辑器内把 object key 渲染成 /storage/...，但 JSON 中仍保存 key。 */
export const StorageImage = Image.extend({
  renderHTML({ HTMLAttributes }) {
    const src =
      typeof HTMLAttributes.src === 'string' ? storageUrl(HTMLAttributes.src) : ''
    return ['img', mergeAttributes(HTMLAttributes, { src })]
  },
})

export const VideoNode = Node.create({
  name: 'video',
  group: 'block',
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      src: { default: null },
      poster: { default: null },
    }
  },

  parseHTML() {
    return [{ tag: 'video[src]' }]
  },

  renderHTML({ HTMLAttributes }) {
    const src =
      typeof HTMLAttributes.src === 'string' ? storageUrl(HTMLAttributes.src) : ''
    return [
      'video',
      mergeAttributes(HTMLAttributes, {
        src,
        controls: 'true',
        preload: 'metadata',
      }),
    ]
  },
})
