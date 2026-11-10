<script setup lang="ts">
import { IconLoader2, IconSearch } from '@tabler/icons-vue';
import { ref, watch } from 'vue';

import { listAllPosts } from '@/api/boards';
import { ApiError } from '@/api/client';
import type { PostSummary } from '@/api/types';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{
  'update:open': [value: boolean];
  pick: [post: { id: string; title: string }];
}>();

const query = ref('');
const items = ref<PostSummary[]>([]);
const loading = ref(false);
const errorMessage = ref('');
// 打开弹窗时先给最近 8 条，输入后按关键词重查。
let requestId = 0;

async function load(search: string): Promise<void> {
  const current = ++requestId;
  loading.value = true;
  errorMessage.value = '';
  try {
    const page = await listAllPosts({ limit: 8, q: search || null });
    if (current === requestId) items.value = page.items;
  } catch (error) {
    if (current === requestId) {
      errorMessage.value = error instanceof ApiError ? error.message : '搜索失败，请稍后重试。';
    }
  } finally {
    if (current === requestId) loading.value = false;
  }
}

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    query.value = '';
    void load('');
  },
);

function choose(post: PostSummary): void {
  emit('pick', { id: post.id, title: post.title });
  emit('update:open', false);
}
</script>

<template>
  <Dialog :open="open" @update:open="(value) => emit('update:open', value)">
    <DialogContent class="sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>引用其他反馈</DialogTitle>
        <DialogDescription>
          选择一条反馈插入正文，保存后会在正文末尾列出它的链接。
        </DialogDescription>
      </DialogHeader>

      <form class="flex items-center gap-2" @submit.prevent="load(query.trim())">
        <Input
          v-model="query"
          type="search"
          size="sm"
          placeholder="搜索标题或摘要…"
          aria-label="搜索要引用的反馈"
        />
        <Button type="submit" variant="outline" size="lg" :disabled="loading">
          <IconLoader2 v-if="loading" class="spin" :size="15" :stroke-width="2" />
          <IconSearch v-else :size="15" :stroke-width="2" />
          搜索
        </Button>
      </form>

      <p v-if="errorMessage" class="text-xs text-destructive">{{ errorMessage }}</p>

      <ul class="flex max-h-[320px] flex-col gap-1 overflow-y-auto">
        <li v-for="item in items" :key="item.id">
          <button
            type="button"
            class="flex w-full flex-col gap-0.5 rounded-md px-2 py-1.5 text-left hover:bg-accent"
            @click="choose(item)"
          >
            <span class="truncate text-sm text-foreground">{{ item.title }}</span>
            <span class="truncate text-xs text-muted-foreground">
              {{ item.board_name }} · {{ item.excerpt || '暂无摘要' }}
            </span>
          </button>
        </li>
      </ul>
      <p v-if="!loading && items.length === 0" class="text-xs text-muted-foreground">
        没有匹配的反馈。
      </p>
    </DialogContent>
  </Dialog>
</template>
