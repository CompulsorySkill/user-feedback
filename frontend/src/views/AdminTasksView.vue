<script setup lang="ts">
import { IconLoader2, IconRefresh } from '@tabler/icons-vue';
import { onMounted, ref } from 'vue';

import { listAdminTasks } from '@/api/adminTasks';
import { listBoards } from '@/api/boards';
import { ApiError } from '@/api/client';
import type { AdminTaskItem, Board, TaskState } from '@/api/types';
import StatusBadge from '@/components/StatusBadge.vue';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { formatDateTime } from '@/utils/date';

const PAGE_SIZE = 30;

const TASK_STATES: Array<{ value: TaskState; label: string; hint: string }> = [
  { value: 'pending', label: '待接受', hint: '还没人接' },
  { value: 'active', label: '进行中', hint: '已接受未完成' },
  { value: 'done', label: '已完成', hint: '已完成任务' },
];

const tasks = ref<AdminTaskItem[]>([]);
const boards = ref<Board[]>([]);
const nextCursor = ref<string | null>(null);
const loading = ref(true);
const loadingMore = ref(false);
const errorMessage = ref('');
const taskFilter = ref<'all' | TaskState>('all');
const boardFilter = ref('all');

function stateLabel(state: TaskState): string {
  return TASK_STATES.find((item) => item.value === state)?.label ?? state;
}

function onTaskChange(value: unknown): void {
  taskFilter.value = String(value ?? 'all') as 'all' | TaskState;
  void load();
}

function onBoardChange(value: unknown): void {
  boardFilter.value = String(value ?? 'all');
  void load();
}

/** 切换筛选必须丢旧游标，否则 keyset 会按旧条件下的位置继续取。 */
async function load(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    const page = await listAdminTasks({
      limit: PAGE_SIZE,
      taskState: taskFilter.value === 'all' ? null : taskFilter.value,
      board: boardFilter.value === 'all' ? null : boardFilter.value,
    });
    tasks.value = page.items;
    nextCursor.value = page.next_cursor;
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载任务面板失败。';
  } finally {
    loading.value = false;
  }
}

async function loadMore(): Promise<void> {
  if (!nextCursor.value || loadingMore.value) return;
  loadingMore.value = true;
  try {
    const page = await listAdminTasks({
      limit: PAGE_SIZE,
      before: nextCursor.value,
      taskState: taskFilter.value === 'all' ? null : taskFilter.value,
      board: boardFilter.value === 'all' ? null : boardFilter.value,
    });
    const seen = new Set(tasks.value.map((item) => item.post_id));
    tasks.value = [...tasks.value, ...page.items.filter((item) => !seen.has(item.post_id))];
    nextCursor.value = page.next_cursor;
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载更多失败。';
  } finally {
    loadingMore.value = false;
  }
}

async function reset(): Promise<void> {
  taskFilter.value = 'all';
  boardFilter.value = 'all';
  await load();
}

onMounted(async () => {
  await load();
  try {
    boards.value = await listBoards();
  } catch {
    // 看板列表拿不到只影响筛选下拉，不影响主列表。
  }
});
</script>

<template>
  <div class="container">
    <header class="page-header">
      <p class="eyebrow">Admin</p>
      <h1>任务管理</h1>
      <p class="hero-lead">
        这里列出正文或评论里 @ 了你的反馈，以及它们的任务进度。只看得到提及自己的反馈；
        反馈的接受与完成仍在详情页操作。
      </p>
    </header>

    <div class="admin-toolbar">
      <label class="admin-filter">
        <span class="field-label">任务状态</span>
        <Select :model-value="taskFilter" @update:model-value="onTaskChange">
          <SelectTrigger size="sm" class="min-w-[160px]" aria-label="按任务状态筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" size="sm">全部任务</SelectItem>
            <SelectItem v-for="item in TASK_STATES" :key="item.value" :value="item.value" size="sm">
              {{ item.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </label>
      <label class="admin-filter">
        <span class="field-label">看板</span>
        <Select :model-value="boardFilter" @update:model-value="onBoardChange">
          <SelectTrigger size="sm" class="min-w-[200px]" aria-label="按看板筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" size="sm">全部看板</SelectItem>
            <SelectItem v-for="board in boards" :key="board.slug" :value="board.slug" size="sm">
              {{ board.name }}
            </SelectItem>
          </SelectContent>
        </Select>
      </label>
      <Button
        v-if="taskFilter !== 'all' || boardFilter !== 'all'"
        type="button"
        variant="outline"
        size="lg"
        @click="reset"
      >
        <IconRefresh :size="14" :stroke-width="2" /> 重置
      </Button>
    </div>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载任务…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <Button type="button" @click="load" variant="outline" size="lg">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </Button>
    </div>

    <div v-else class="flex flex-col gap-2">
      <div
        v-for="task in tasks"
        :key="task.post_id"
        class="flex items-start gap-3 rounded-lg border border-border bg-card px-4 py-3"
      >
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <RouterLink
            :to="`/post/${task.post_id}`"
            class="truncate text-sm font-medium text-foreground hover:underline"
          >
            {{ task.title }}
          </RouterLink>
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span>{{ task.board_name }}</span>
            <StatusBadge :status="task.status" />
            <span>@ 于 {{ formatDateTime(task.mentioned_at) }}</span>
          </div>
        </div>
        <div class="flex shrink-0 flex-col items-end gap-1 text-xs">
          <span
            class="rounded-md px-2 py-0.5 font-medium"
            :class="
              task.task_state === 'pending'
                ? 'bg-accent text-accent-foreground'
                : task.task_state === 'active'
                  ? 'bg-primary/10 text-primary'
                  : 'bg-muted text-muted-foreground'
            "
          >
            {{ stateLabel(task.task_state) }}
          </span>
          <span class="text-muted-foreground">
            {{
              task.assignee_name
                ? `${task.assignee_name} · ${formatDateTime(task.accepted_at)}`
                : '无人接受'
            }}
          </span>
        </div>
      </div>

      <p v-if="tasks.length === 0" class="admin-empty">
        还没有人 @ 你。被提及后，对应反馈会出现在这里。
      </p>

      <div v-if="nextCursor" class="load-more">
        <Button type="button" :disabled="loadingMore" @click="loadMore" variant="ghost" size="lg">
          <IconLoader2 v-if="loadingMore" class="spin" :size="16" :stroke-width="2" />
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </Button>
      </div>
    </div>
  </div>
</template>
