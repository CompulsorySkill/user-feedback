<script setup lang="ts">
import {
  IconArrowLeft,
  IconDownload,
  IconEdit,
  IconFile,
  IconLoader2,
  IconPin,
  IconRefresh,
} from '@tabler/icons-vue';
import { ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import {
  getAnnouncement,
  pinAnnouncement,
  publishAnnouncement,
  unpinAnnouncement,
  unpublishAnnouncement,
} from '@/api/announcements';
import { ApiError } from '@/api/client';
import type { AnnouncementDetail } from '@/api/types';
import RichTextRenderer from '@/components/RichTextRenderer.vue';
import { Button, buttonVariants } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth';
import { formatDate } from '@/utils/date';
import { formatBytes } from '@/utils/format';

const route = useRoute();
const auth = useAuthStore();
const entry = ref<AnnouncementDetail | null>(null);
const loading = ref(true);
const errorMessage = ref('');
const pending = ref(false);

async function load(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  entry.value = null;
  try {
    if (!auth.me) await auth.hydrate();
    entry.value = await getAnnouncement(String(route.params.id ?? ''));
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError
        ? error.status === 404
          ? '这条公告不存在或尚未发布。'
          : error.message
        : '加载失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
}

async function togglePublish(): Promise<void> {
  if (!entry.value || pending.value) return;
  pending.value = true;
  try {
    entry.value = entry.value.is_published
      ? await unpublishAnnouncement(entry.value.id)
      : await publishAnnouncement(entry.value.id);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '操作失败';
  } finally {
    pending.value = false;
  }
}

async function togglePin(): Promise<void> {
  if (!entry.value || pending.value) return;
  pending.value = true;
  try {
    entry.value = entry.value.is_pinned
      ? await unpinAnnouncement(entry.value.id)
      : await pinAnnouncement(entry.value.id);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '操作失败';
  } finally {
    pending.value = false;
  }
}

watch(() => route.params.id, load, { immediate: true });
</script>

<template>
  <div class="container">
    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载…
    </p>

    <template v-else-if="entry">
      <RouterLink to="/announcements" class="back-link">
        <IconArrowLeft :size="15" :stroke-width="2" /> 全部公告
      </RouterLink>

      <div v-if="auth.isAdmin" class="detail-admin-bar">
        <span v-if="!entry.is_published" class="anon-badge">草稿（仅管理员可见）</span>
        <span v-else-if="entry.is_pinned" class="pinned-badge">
          <IconPin :size="12" :stroke-width="2" /> 已置顶
        </span>
        <span v-else class="muted">已发布</span>
        <div class="detail-admin-actions">
          <RouterLink
            :to="`/announcements/${entry.id}/edit`"
            data-slot="button"
            :class="buttonVariants({ variant: 'ghost', size: 'lg' })"
          >
            <IconEdit :size="14" :stroke-width="2" />
            编辑
          </RouterLink>
          <Button
            v-if="entry.is_published"
            type="button"
            :disabled="pending"
            @click="togglePin"
            variant="ghost"
            size="lg"
          >
            <IconPin :size="14" :stroke-width="2" />
            {{ entry.is_pinned ? '取消置顶' : '置顶' }}
          </Button>
          <Button
            type="button"
            :disabled="pending"
            @click="togglePublish"
            variant="ghost"
            size="lg"
          >
            <IconLoader2 v-if="pending" class="spin" :size="14" :stroke-width="2" />
            {{ entry.is_published ? '撤回发布' : '发布' }}
          </Button>
        </div>
      </div>

      <article class="changelog-detail">
        <header class="post-detail-head">
          <span v-if="entry.is_pinned" class="pinned-badge">
            <IconPin :size="12" :stroke-width="2" /> 置顶
          </span>
          <span class="changelog-date">
            {{ entry.published_at ? formatDate(entry.published_at) : '尚未发布' }}
          </span>
          <h1>{{ entry.title }}</h1>
          <p v-if="entry.author_name" class="announcement-author">作者：{{ entry.author_name }}</p>
        </header>
        <section class="rich-text">
          <RichTextRenderer :node="entry.content" />
        </section>

        <section v-if="entry.attachments.length" class="changelog-attachments">
          <h2>附件</h2>
          <a
            v-for="attachment in entry.attachments"
            :key="attachment.id"
            :href="attachment.download_url"
            :download="attachment.filename"
            class="attachment-item"
          >
            <span class="attachment-icon">
              <IconFile :size="18" :stroke-width="1.8" />
            </span>
            <span class="attachment-main">
              <span class="attachment-name">{{ attachment.filename }}</span>
              <span class="attachment-meta">
                {{ attachment.content_type || '未知类型' }} · {{ formatBytes(attachment.size) }}
              </span>
            </span>
            <IconDownload :size="16" :stroke-width="1.8" class="attachment-download" />
          </a>
        </section>
      </article>
    </template>

    <div v-else class="inline-error">
      <span>{{ errorMessage }}</span>
      <Button type="button" @click="load" variant="ghost" size="lg">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </Button>
    </div>
  </div>
</template>
