<script setup lang="ts">
import { computed } from 'vue';

import type { PostStatus } from '@/api/types';

const props = defineProps<{ status: PostStatus }>();

const labels: Record<PostStatus, string> = {
  open: '待处理',
  planned: '已计划',
  in_progress: '进行中',
  completed: '已完成',
  closed: '已关闭',
};

const label = computed(() => labels[props.status] ?? props.status);
</script>

<template>
  <span class="status-badge" :class="`status-${status}`">
    <span class="status-dot" />
    {{ label }}
  </span>
</template>
