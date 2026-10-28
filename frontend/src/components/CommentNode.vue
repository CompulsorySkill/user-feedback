<script setup lang="ts">
import { computed, ref } from 'vue'
import { IconChevronDown, IconChevronUp, IconCornerUpLeft, IconTrash } from '@tabler/icons-vue'
import type { CommentNodeData } from '@/types/comment'
import { formatDateTime, formatRelative } from '@/utils/date'

const props = defineProps<{ node: CommentNodeData; depth: number; canDelete?: boolean }>()
const emit = defineEmits<{
  reply: [node: CommentNodeData]
  delete: [node: CommentNodeData]
}>()

const expanded = ref(props.depth < 2)
const hasChildren = computed(() => props.node.children.length > 0)
const author = computed(() =>
  props.node.is_anonymous ? '匿名用户' : props.node.author_name?.trim() || '用户',
)
</script>

<template>
  <div class="comment-node" :class="`depth-${Math.min(depth, 3)}`">
    <div class="comment-card">
      <div class="comment-head">
        <span class="comment-author">{{ author }}</span>
        <span v-if="node.is_anonymous" class="anon-badge">匿名</span>
        <span class="comment-time" :title="formatDateTime(node.created_at)">
          {{ formatRelative(node.created_at) }}
        </span>
      </div>
      <p class="comment-content">{{ node.content }}</p>
      <div class="comment-actions">
        <button type="button" class="comment-action" @click="emit('reply', node)">
          <IconCornerUpLeft :size="13" :stroke-width="2" />
          回复
        </button>
        <button
          v-if="canDelete"
          type="button"
          class="comment-action comment-action-danger"
          @click="emit('delete', node)"
        >
          <IconTrash :size="13" :stroke-width="2" />
          删除
        </button>
        <button
          v-if="hasChildren"
          type="button"
          class="comment-action"
          @click="expanded = !expanded"
        >
          <component
            :is="expanded ? IconChevronUp : IconChevronDown"
            :size="13"
            :stroke-width="2"
          />
          {{ expanded ? '收起回复' : `展开 ${node.children.length} 条回复` }}
        </button>
      </div>
    </div>

    <div v-if="hasChildren && expanded" class="comment-children">
      <CommentNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :can-delete="canDelete"
        @reply="emit('reply', $event)"
        @delete="emit('delete', $event)"
      />
    </div>
  </div>
</template>
