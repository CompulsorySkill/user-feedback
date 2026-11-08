<script setup lang="ts">
import { IconCircleCheck, IconLoader2, IconUserCheck } from '@tabler/icons-vue';
import { computed, ref } from 'vue';

import { ApiError } from '@/api/client';
import { acceptPostTask, completePostTask } from '@/api/postActions';
import type { PostDetail, PostStatus, PostTimelineEvent } from '@/api/types';
import StatusBadge from '@/components/StatusBadge.vue';
import { Button } from '@/components/ui/button';
import { formatDateTime, formatRelative } from '@/utils/date';

const props = defineProps<{ post: PostDetail }>();
const emit = defineEmits<{ updated: [post: PostDetail] }>();

const pending = ref<'accept' | 'complete' | null>(null);
const error = ref('');

const statusLabels: Record<PostStatus, string> = {
  open: '待处理',
  planned: '已计划',
  in_progress: '进行中',
  completed: '已完成',
  closed: '已关闭',
};

const isTaskCompleted = computed(() => Boolean(props.post.task?.completed_at));

function eventLabel(event: PostTimelineEvent): string {
  if (event.event_type === 'created') return '提出反馈';
  if (event.event_type === 'task_accepted') return '接受任务';
  if (event.event_type === 'task_completed') return '完成任务';
  return event.to_status ? statusLabels[event.to_status] : '状态更新';
}

function actorVerb(event: PostTimelineEvent): string {
  if (event.event_type === 'created') return '提出';
  if (event.event_type === 'task_accepted') return '接受';
  if (event.event_type === 'task_completed') return '完成';
  return '修改状态';
}

async function run(action: 'accept' | 'complete'): Promise<void> {
  if (pending.value) return;
  pending.value = action;
  error.value = '';
  try {
    const updated =
      action === 'accept'
        ? await acceptPostTask(props.post.id)
        : await completePostTask(props.post.id);
    emit('updated', updated);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '操作失败，请稍后重试';
  } finally {
    pending.value = null;
  }
}
</script>

<template>
  <section
    class="mt-6 rounded-lg border border-border bg-card p-4"
    aria-labelledby="post-timeline-title"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="post-timeline-title" class="text-sm font-semibold text-foreground">进度时间线</h2>
      <div class="flex flex-wrap items-center gap-2">
        <Button
          v-if="post.can_accept_task"
          type="button"
          variant="default"
          size="lg"
          :disabled="pending !== null"
          @click="run('accept')"
        >
          <IconLoader2 v-if="pending === 'accept'" class="spin" :size="14" :stroke-width="2" />
          <IconUserCheck v-else :size="14" :stroke-width="2" />
          接受任务
        </Button>
        <Button
          v-if="post.can_complete_task"
          type="button"
          variant="outline"
          size="lg"
          :disabled="pending !== null"
          @click="run('complete')"
        >
          <IconLoader2 v-if="pending === 'complete'" class="spin" :size="14" :stroke-width="2" />
          <IconCircleCheck v-else :size="14" :stroke-width="2" />
          完成任务
        </Button>
      </div>
    </div>

    <div
      v-if="post.task"
      class="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground"
    >
      <span>
        任务接受人：<span class="text-foreground">{{ post.task.assignee_name }}</span>
      </span>
      <span class="text-border">·</span>
      <span>{{ isTaskCompleted ? '已完成' : '进行中' }}</span>
    </div>

    <ol v-if="post.timeline.length" class="relative mt-4 space-y-4 border-l border-border pl-5">
      <li v-for="event in post.timeline" :key="event.id" class="relative">
        <span
          class="absolute -left-[25px] top-1.5 size-2 rounded-full bg-primary ring-4 ring-card"
          aria-hidden="true"
        ></span>
        <div class="flex flex-wrap items-center gap-2">
          <template v-if="event.event_type === 'status_changed'">
            <StatusBadge v-if="event.to_status" :status="event.to_status" />
          </template>
          <template v-else>
            <StatusBadge
              v-if="event.event_type !== 'created' && event.to_status"
              :status="event.to_status"
            />
            <span class="text-sm font-medium text-foreground">{{ eventLabel(event) }}</span>
          </template>
          <time
            class="ml-auto text-xs text-muted-foreground"
            :title="formatDateTime(event.created_at)"
          >
            {{ formatRelative(event.created_at) }}
          </time>
        </div>
        <p class="mt-1 text-xs text-muted-foreground">
          {{ event.actor_name || '系统' }} {{ actorVerb(event) }}
        </p>
      </li>
    </ol>
    <p v-else class="mt-3 text-xs text-muted-foreground">暂无进度记录。</p>

    <p v-if="error" class="mt-3 text-xs text-destructive">{{ error }}</p>
  </section>
</template>
