<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconBold,
  IconCode,
  IconH2,
  IconItalic,
  IconList,
  IconListNumbers,
  IconLoader2,
  IconPhoto,
  IconQuote,
  IconStrikethrough,
  IconVideo,
} from '@tabler/icons-vue'
import { StorageImage, VideoNode } from '@/editor/extensions'
import { useUpload } from '@/composables/useUpload'
import type { JSONContent } from '@/types/content'

const props = withDefaults(
  defineProps<{
    scope?: 'post' | 'changelog'
    initialContent?: JSONContent | null
  }>(),
  { scope: 'post', initialContent: null },
)

const emit = defineEmits<{
  'update:json': [value: JSONContent]
  'update:uploading': [value: boolean]
}>()

const { uploading, error: uploadError, upload } = useUpload()

const editor = useEditor({
  content: props.initialContent ?? { type: 'doc', content: [{ type: 'paragraph' }] },
  extensions: [
    StarterKit.configure({ heading: { levels: [2, 3] } }),
    StorageImage.configure({ inline: false, allowBase64: false }),
    VideoNode,
    Placeholder.configure({
      placeholder: '描述你的建议、复现步骤或期望结果…',
    }),
  ],
  editorProps: {
    attributes: {
      class: 'tiptap',
      'aria-label': '反馈正文',
    },
  },
  onCreate: ({ editor: instance }) => emit('update:json', instance.getJSON()),
  onUpdate: ({ editor: instance }) => emit('update:json', instance.getJSON()),
})

watch(uploading, (value) => emit('update:uploading', value))

const fileInput = ref<HTMLInputElement | null>(null)
const pendingPurpose = ref<'image' | 'video'>('image')

const uploadingLabel = computed(() =>
  pendingPurpose.value === 'image' ? '图片上传中…' : '视频上传中…',
)

function pickFile(purpose: 'image' | 'video'): void {
  pendingPurpose.value = purpose
  fileInput.value?.click()
}

async function onFileChange(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !editor.value) return

  const purpose = `${props.scope}_${pendingPurpose.value}` as
    | 'post_image'
    | 'post_video'
    | 'changelog_image'
    | 'changelog_video'
  const key = await upload(file, purpose)
  if (!key) return

  if (pendingPurpose.value === 'image') {
    editor.value.chain().focus().setImage({ src: key, alt: file.name }).run()
  } else {
    editor.value
      .chain()
      .focus()
      .insertContent({ type: 'video', attrs: { src: key, poster: null } })
      .run()
  }
}

defineExpose({
  getJSON: (): JSONContent | null => editor.value?.getJSON() ?? null,
  isEmpty: (): boolean => editor.value?.isEmpty ?? true,
})
</script>

<template>
  <div class="editor-shell">
    <div v-if="editor" class="editor-toolbar" role="toolbar" aria-label="格式工具栏">
      <button
        type="button"
        class="tool-button"
        :class="{ 'is-active': editor.isActive('bold') }"
        title="加粗"
        @click="editor.chain().focus().toggleBold().run()"
      >
        <IconBold :size="16" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="tool-button"
        :class="{ 'is-active': editor.isActive('italic') }"
        title="斜体"
        @click="editor.chain().focus().toggleItalic().run()"
      >
        <IconItalic :size="16" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="tool-button"
        :class="{ 'is-active': editor.isActive('strike') }"
        title="删除线"
        @click="editor.chain().focus().toggleStrike().run()"
      >
        <IconStrikethrough :size="16" :stroke-width="2" />
      </button>

      <span class="tool-sep" />

      <button
        type="button"
        class="tool-button"
        :class="{ 'is-active': editor.isActive('heading', { level: 2 }) }"
        title="二级标题"
        @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
      >
        <IconH2 :size="16" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="tool-button"
        :class="{ 'is-active': editor.isActive('bulletList') }"
        title="无序列表"
        @click="editor.chain().focus().toggleBulletList().run()"
      >
        <IconList :size="16" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="tool-button"
        :class="{ 'is-active': editor.isActive('orderedList') }"
        title="有序列表"
        @click="editor.chain().focus().toggleOrderedList().run()"
      >
        <IconListNumbers :size="16" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="tool-button"
        :class="{ 'is-active': editor.isActive('blockquote') }"
        title="引用"
        @click="editor.chain().focus().toggleBlockquote().run()"
      >
        <IconQuote :size="16" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="tool-button"
        :class="{ 'is-active': editor.isActive('codeBlock') }"
        title="代码块"
        @click="editor.chain().focus().toggleCodeBlock().run()"
      >
        <IconCode :size="16" :stroke-width="2" />
      </button>

      <span class="tool-sep" />

      <button
        type="button"
        class="tool-button"
        title="插入图片（PNG / JPEG / WebP / GIF）"
        :disabled="uploading"
        @click="pickFile('image')"
      >
        <IconPhoto :size="16" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="tool-button"
        title="插入视频（MP4，≤100MB）"
        :disabled="uploading"
        @click="pickFile('video')"
      >
        <IconVideo :size="16" :stroke-width="2" />
      </button>

      <span class="tool-sep" />

      <button
        type="button"
        class="tool-button"
        title="撤销"
        :disabled="!editor.can().undo()"
        @click="editor.chain().focus().undo().run()"
      >
        <IconArrowBackUp :size="16" :stroke-width="2" />
      </button>
      <button
        type="button"
        class="tool-button"
        title="重做"
        :disabled="!editor.can().redo()"
        @click="editor.chain().focus().redo().run()"
      >
        <IconArrowForwardUp :size="16" :stroke-width="2" />
      </button>
    </div>

    <div v-if="uploading" class="editor-uploading">
      <IconLoader2 class="spin" :size="15" :stroke-width="2" />
      {{ uploadingLabel }}
    </div>

    <EditorContent :editor="editor" />

    <p v-if="uploadError" class="editor-error">{{ uploadError }}</p>

    <input
      ref="fileInput"
      class="visually-hidden"
      type="file"
      accept="image/png,image/jpeg,image/webp,image/gif,video/mp4"
      @change="onFileChange"
    />
  </div>
</template>
