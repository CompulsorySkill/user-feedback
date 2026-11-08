<script setup lang="ts">
import { IconArrowUpRight, IconLoader2, IconPin, IconPlus, IconRefresh } from '@tabler/icons-vue';
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';

import { listAnnouncements } from '@/api/announcements';
import { ApiError } from '@/api/client';
import type { AnnouncementSummary } from '@/api/types';
import EmptyState from '@/components/EmptyState.vue';
import { Button, buttonVariants } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth';
import { formatDate } from '@/utils/date';

const auth = useAuthStore();
const entries = ref<AnnouncementSummary[]>([]);
const loading = ref(true);
const errorMessage = ref('');

async function load(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    if (!auth.me) await auth.hydrate();
    const page = await listAnnouncements({ limit: 20, includeDrafts: auth.isAdmin });
    entries.value = page.items;
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="container">
    <header class="page-header page-header-row">
      <div>
        <p class="eyebrow">Announcements</p>
        <h1>公告</h1>
        <p class="hero-lead">站点通知与重要事项，置顶公告排在最前。</p>
      </div>
      <RouterLink
        v-if="auth.isAdmin"
        to="/announcements/new"
        data-slot="button"
        :class="buttonVariants({ variant: 'default', size: 'lg' })"
      >
        <IconPlus :size="16" :stroke-width="2" />
        新建公告
      </RouterLink>
    </header>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载公告…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <Button type="button" @click="load" variant="ghost" size="lg">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </Button>
    </div>

    <EmptyState
      v-else-if="entries.length === 0"
      title="还没有公告"
      description="管理员发布公告后，会在这里展示。"
    />

    <div v-else class="changelog-list">
      <RouterLink
        v-for="entry in entries"
        :key="entry.id"
        :to="`/announcements/${entry.id}`"
        class="changelog-item"
      >
        <div class="changelog-date">
          {{ entry.is_published ? formatDate(entry.published_at ?? entry.created_at) : '草稿' }}
        </div>
        <div class="changelog-body">
          <h2>
            <span v-if="entry.is_pinned" class="pinned-badge">
              <IconPin :size="12" :stroke-width="2" /> 置顶
            </span>
            {{ entry.title }}
            <span v-if="!entry.is_published" class="anon-badge">草稿</span>
          </h2>
          <p>{{ entry.excerpt }}</p>
          <p v-if="entry.author_name" class="announcement-author">作者：{{ entry.author_name }}</p>
        </div>
        <IconArrowUpRight class="changelog-arrow" :size="18" :stroke-width="1.8" />
      </RouterLink>
    </div>
  </div>
</template>
