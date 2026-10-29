<script setup lang="ts">
import { IconLoader2, IconThumbUp } from '@tabler/icons-vue';
import { useStorage } from '@vueuse/core';
import { ref } from 'vue';

import { ApiError } from '@/api/client';
import { unvotePost, votePost } from '@/api/posts';

const props = withDefaults(
  defineProps<{
    postId: string;
    initialCount: number;
    compact?: boolean;
    disabled?: boolean;
  }>(),
  { compact: false, disabled: false },
);

const STORAGE_KEY = 'feedback:voted-posts';

/** 已投票记录；隐私模式下 useStorage 自动降级为内存 ref，不抛错。 */
const votedIds = useStorage<string[]>(STORAGE_KEY, []);

/** 存储可能被手工改坏，只信任字符串数组。 */
function sanitize(ids: unknown): string[] {
  return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === 'string') : [];
}

const count = ref(props.initialCount);
const voted = ref(sanitize(votedIds.value).includes(props.postId));
const pending = ref(false);
const error = ref('');

async function toggle(): Promise<void> {
  if (pending.value || props.disabled) return;

  const wasVoted = voted.value;
  const previousCount = count.value;

  pending.value = true;
  error.value = '';
  voted.value = !wasVoted;
  count.value = Math.max(0, previousCount + (wasVoted ? -1 : 1));

  try {
    const result = wasVoted ? await unvotePost(props.postId) : await votePost(props.postId);
    count.value = result.vote_count;
    voted.value = result.voted;
    const others = sanitize(votedIds.value).filter((id) => id !== props.postId);
    votedIds.value = result.voted ? [...others, props.postId] : others;
  } catch (err) {
    voted.value = wasVoted;
    count.value = previousCount;
    error.value = err instanceof ApiError ? err.message : '操作失败，请稍后重试';
  } finally {
    pending.value = false;
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
