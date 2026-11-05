<script setup lang="ts">
import { IconLoader2, IconLock } from '@tabler/icons-vue';
import { computed, ref } from 'vue';

import { ApiError } from '@/api/client';
import { updatePostStatus } from '@/api/postActions';
import type { PostDetail, PostStatus } from '@/api/types';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useConfirm } from '@/composables/useConfirm';
import { useAuthStore } from '@/stores/auth';

const confirm = useConfirm();

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
  if (
    target === 'closed' &&
    !(await confirm({
      title: '确认关闭这条反馈？',
      message: '关闭后不能自行重开。',
      confirmText: '关闭',
    }))
  ) {
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
      <span class="status-select-label">状态</span>
      <Select
        :model-value="post.status"
        :disabled="pending"
        @update:model-value="(value) => applyStatus(value as PostStatus)"
      >
        <SelectTrigger aria-label="修改反馈状态">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="option in STATUS_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </SelectItem>
        </SelectContent>
      </Select>
      <IconLoader2 v-if="pending" class="spin" :size="15" :stroke-width="2" />
    </template>

    <Button
      v-else-if="canAuthorClose"
      type="button"
      :disabled="pending"
      @click="applyStatus('closed')"
      variant="ghost"
      size="lg"
    >
      <IconLoader2 v-if="pending" class="spin" :size="15" :stroke-width="2" />
      <IconLock v-else :size="15" :stroke-width="2" />
      关闭反馈
    </Button>

    <span v-if="error" class="status-error">{{ error }}</span>
  </div>
</template>
