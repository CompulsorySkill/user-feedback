<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { IconLoader2, IconThumbUp } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { unvotePost, votePost } from '@/api/posts'

const props = withDefaults(
  defineProps<{
    postId: string
    initialCount: number
    compact?: boolean
    disabled?: boolean
  }>(),
  { compact: false, disabled: false },
)

const STORAGE_KEY = 'feedlog:voted-posts'

function readVoted(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? (JSON.parse(raw) as unknown) : []
    return new Set(Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string') : [])
  } catch {
    return new Set()
  }
}

function persistVoted(votedIds: Set<string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...votedIds]))
  } catch {
    // 隐私模式等场景忽略
  }
}

const count = ref(props.initialCount)
const voted = ref(false)
const pending = ref(false)
const error = ref('')

onMounted(() => {
  voted.value = readVoted().has(props.postId)
})

async function toggle(): Promise<void> {
  if (pending.value || props.disabled) return

  const wasVoted = voted.value
  const previousCount = count.value
  const votedIds = readVoted()

  pending.value = true
  error.value = ''
  voted.value = !wasVoted
  count.value = Math.max(0, previousCount + (wasVoted ? -1 : 1))

  try {
    const result = wasVoted ? await unvotePost(props.postId) : await votePost(props.postId)
    count.value = result.vote_count
    voted.value = result.voted
    if (result.voted) votedIds.add(props.postId)
    else votedIds.delete(props.postId)
    persistVoted(votedIds)
  } catch (err) {
    voted.value = wasVoted
    count.value = previousCount
    error.value = err instanceof ApiError ? err.message : '操作失败，请稍后重试'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <button
    type="button"
    class="vote-button"
    :class="{ 'is-voted': voted, 'is-compact': compact }"
    :disabled="pending || disabled"
    :aria-pressed="voted"
    :title="error || (voted ? '再次点击取消投票' : '投票')"
    @click.stop.prevent="toggle"
  >
    <IconLoader2 v-if="pending" class="spin" :size="compact ? 14 : 16" :stroke-width="2" />
    <IconThumbUp v-else :size="compact ? 14 : 16" :stroke-width="2" />
    <span class="vote-count">{{ count }}</span>
    <span v-if="!compact" class="vote-label">{{ voted ? '已投票' : '投票' }}</span>
  </button>
</template>
