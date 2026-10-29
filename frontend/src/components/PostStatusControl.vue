<script setup lang="ts">
import { IconChevronDown, IconLock, IconLoader2 } from '@tabler/icons-vue';
import { computed, ref } from 'vue';

import { ApiError } from '@/api/client';
import { updatePostStatus } from '@/api/postActions';
import type { PostDetail, PostStatus } from '@/api/types';
import { useAuthStore } from '@/stores/auth';

const props = defineProps<{ post: PostDetail }>();
const emit = defineEmits<{ updated: [post: PostDetail] }>();

const auth = useAuthStore();
const pending = ref(false);
const error = ref('');

const STATUS_OPTIONS: Array<{ value: PostStatus; label: string }> = [
  { value: 'open', label: '待处理' },
  { value: 'planned', label: '已计划' },
  { value: 'in_progress', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'closed', label: '已关闭' },
];

const isAuthor = computed(() => auth.isAuthenticated && props.post.is_author);
// 最终权限以后端状态机为准，这里只控制入口显隐。
const canAuthorClose = computed(() => isAuthor.value && props.post.status !== 'closed');

async function applyStatus(target: PostStatus): Promise<void> {
  if (pending.value || target === props.post.status) return;
  if (target === 'closed' && !window.confirm('确认关闭这条反馈？关闭后不能自行重开。')) {
    return;
  }

  pending.value = true;
  error.value = '';
  try {
    const updated = await updatePostStatus(props.post.id, target);
    emit('updated', updated);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '状态更新失败';
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <div class="status-control">
    <template v-if="auth.isAdmin">
      <label class="status-select-wrap">
        <span class="status-select-label">状态</span>
        <select
          class="status-select"
          :value="post.status"
          :disabled="pending"
          @change="applyStatus(($event.target as HTMLSelectElement).value as PostStatus)"
        >
          <option v-for="option in STATUS_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <IconChevronDown class="status-select-icon" :size="14" :stroke-width="2" />
      </label>
      <IconLoader2 v-if="pending" class="spin" :size="15" :stroke-width="2" />
    </template>

    <button
      v-else-if="canAuthorClose"
      type="button"
      class="button button-ghost button-small"
      :disabled="pending"
      @click="applyStatus('closed')"
    >
      <IconLoader2 v-if="pending" class="spin" :size="15" :stroke-width="2" />
      <IconLock v-else :size="15" :stroke-width="2" />
      关闭反馈
    </button>

    <span v-if="error" class="status-error">{{ error }}</span>
  </div>
</template>
