<script setup lang="ts">
import { IconArrowUpRight, IconLoader2, IconPlus, IconRefresh } from '@tabler/icons-vue';
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';

import { listChangelogs } from '@/api/changelogs';
import { ApiError } from '@/api/client';
import type { ChangelogSummary } from '@/api/types';
import EmptyState from '@/components/EmptyState.vue';
import { useAuthStore } from '@/stores/auth';
import { formatDate } from '@/utils/date';

const auth = useAuthStore();
const entries = ref<ChangelogSummary[]>([]);
const loading = ref(true);
const errorMessage = ref('');

async function load(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    if (!auth.me) await auth.hydrate();
    const page = await listChangelogs({ limit: 20, includeDrafts: auth.isAdmin });
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
        <p class="eyebrow">Changelog</p>
        <h1>更新日志</h1>
        <p class="hero-lead">每个版本做了什么，都在这里。仅展示已发布内容。</p>
      </div>
      <RouterLink v-if="auth.isAdmin" to="/changelog/new" class="button button-primary">
        <IconPlus :size="16" :stroke-width="2" />
        新建更新日志
      </RouterLink>
    </header>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载更新日志…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>

    <EmptyState
      v-else-if="entries.length === 0"
      title="还没有更新日志"
      description="管理员发布版本说明后，会在这里展示。"
    />

    <div v-else class="changelog-list">
      <RouterLink
        v-for="entry in entries"
        :key="entry.id"
        :to="`/changelog/${entry.id}`"
        class="changelog-item"
      >
        <div class="changelog-date">
          {{ entry.is_published ? formatDate(entry.published_at ?? entry.created_at) : '草稿' }}
        </div>
        <div class="changelog-body">
          <h2>
            {{ entry.title }}
            <span v-if="!entry.is_published" class="anon-badge">草稿</span>
          </h2>
          <p>{{ entry.excerpt }}</p>
        </div>
        <IconArrowUpRight class="changelog-arrow" :size="18" :stroke-width="1.8" />
      </RouterLink>
    </div>
  </div>
</template>
