<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { IconLoader2, IconRefresh, IconSend, IconX } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import {
  createComment,
  listComments,
  type CommentItem,
} from '@/api/comments'
import CommentNode from '@/components/CommentNode.vue'
import type { CommentNodeData } from '@/types/comment'

const props = defineProps<{ postId: string; closed: boolean }>()

const items = ref<CommentItem[]>([])
const loading = ref(true)
const error = ref('')
const submitting = ref(false)
const draft = ref('')
const replyTo = ref<CommentNodeData | null>(null)

const tree = computed<CommentNodeData[]>(() => {
  const nodes = new Map<string, CommentNodeData>()
  for (const item of items.value) {
    nodes.set(item.id, { ...item, children: [] })
  }
  const roots: CommentNodeData[] = []
  for (const node of nodes.values()) {
    if (node.parent_id && nodes.has(node.parent_id)) {
      nodes.get(node.parent_id)!.children.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
})

const replyLabel = computed(() => {
  if (!replyTo.value) return ''
  return replyTo.value.is_anonymous
    ? '匿名用户'
    : replyTo.value.author_name?.trim() || '用户'
})

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await listComments(props.postId)
    items.value = response.items
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '评论加载失败'
  } finally {
    loading.value = false
  }
}

function startReply(node: CommentNodeData): void {
  replyTo.value = node
  document.querySelector<HTMLTextAreaElement>('.comment-form textarea')?.focus()
}

async function submit(): Promise<void> {
  const content = draft.value.trim()
  if (!content || submitting.value) return

  submitting.value = true
  error.value = ''
  try {
    await createComment(props.postId, {
      content,
      parent_id: replyTo.value?.id ?? null,
    })
    draft.value = ''
    replyTo.value = null
    await load()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '评论失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="comments-section">
    <div class="comments-head">
      <h2>评论（{{ items.length }}）</h2>
      <button type="button" class="comment-action" :disabled="loading" @click="load">
        <IconRefresh :size="13" :stroke-width="2" />
        刷新
      </button>
    </div>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="15" :stroke-width="2" /> 正在加载评论…
    </p>

    <p v-else-if="error && items.length === 0" class="inline-error">{{ error }}</p>

    <p v-else-if="tree.length === 0" class="muted comments-empty">
      还没有评论，来补充第一条背景或复现步骤。
    </p>

    <div v-else class="comment-tree">
      <CommentNode
        v-for="node in tree"
        :key="node.id"
        :node="node"
        :depth="1"
        @reply="startReply"
      />
    </div>

    <form v-if="!closed" class="comment-form" @submit.prevent="submit">
      <div v-if="replyTo" class="reply-chip">
        回复 @{{ replyLabel }}
        <button type="button" class="reply-cancel" @click="replyTo = null">
          <IconX :size="12" :stroke-width="2" />
        </button>
      </div>
      <textarea
        v-model="draft"
        rows="3"
        maxlength="2000"
        placeholder="写下你的补充、复现步骤或看法（支持匿名）"
      ></textarea>
      <div class="comment-form-foot">
        <span class="muted">{{ draft.length }} / 2000</span>
        <button
          type="submit"
          class="button button-primary button-small"
          :disabled="submitting || !draft.trim()"
        >
          <IconLoader2 v-if="submitting" class="spin" :size="14" :stroke-width="2" />
          <IconSend v-else :size="14" :stroke-width="2" />
          发表评论
        </button>
      </div>
      <p v-if="error" class="inline-error">{{ error }}</p>
    </form>

    <p v-else class="notice notice-closed">反馈已关闭，不再接受新评论。</p>
  </section>
</template>
