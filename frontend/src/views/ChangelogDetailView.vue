<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  IconArrowLeft,
  IconDownload,
  IconEdit,
  IconFile,
  IconLoader2,
  IconRefresh,
} from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getChangelog, publishChangelog, unpublishChangelog } from '@/api/changelogs'
import type { ChangelogDetail } from '@/api/types'
import RichTextRenderer from '@/components/RichTextRenderer.vue'
import { useAuthStore } from '@/stores/auth'
import { formatDate } from '@/utils/date'
import { formatBytes } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const entry = ref<ChangelogDetail | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const pending = ref(false)

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  entry.value = null
  try {
    if (!auth.me) await auth.hydrate()
    const data = await getChangelog(String(route.params.id ?? ''))
    // 兼容尚未升级的后端：旧版本详情没有 attachments 字段。
    entry.value = { ...data, attachments: data.attachments ?? [] }
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError
        ? error.status === 404
          ? '这条更新日志不存在或尚未发布。'
          : error.message
        : '加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

async function togglePublish(): Promise<void> {
  if (!entry.value || pending.value) return
  pending.value = true
  try {
    entry.value = entry.value.is_published
      ? await unpublishChangelog(entry.value.id)
      : await publishChangelog(entry.value.id)
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '操作失败'
  } finally {
    pending.value = false
  }
}

watch(() => route.params.id, load, { immediate: true })
</script>

<template>
  <div class="container container-narrow">
    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载…
    </p>

    <template v-else-if="entry">
      <RouterLink to="/changelog" class="back-link">
        <IconArrowLeft :size="15" :stroke-width="2" /> 全部更新日志
      </RouterLink>

      <div v-if="auth.isAdmin" class="detail-admin-bar">
        <span v-if="!entry.is_published" class="anon-badge">草稿（仅管理员可见）</span>
        <span v-else class="muted">已发布</span>
        <div class="detail-admin-actions">
          <RouterLink :to="`/changelog/${entry.id}/edit`" class="button button-ghost button-small">
            <IconEdit :size="14" :stroke-width="2" />
            编辑
          </RouterLink>
          <button
            type="button"
            class="button button-ghost button-small"
            :disabled="pending"
            @click="togglePublish"
          >
            <IconLoader2 v-if="pending" class="spin" :size="14" :stroke-width="2" />
            {{ entry.is_published ? '撤回发布' : '发布' }}
          </button>
        </div>
      </div>

      <article class="changelog-detail">
        <header class="post-detail-head">
          <span class="changelog-date">
            {{ entry.published_at ? formatDate(entry.published_at) : '尚未发布' }}
          </span>
          <h1>{{ entry.title }}</h1>
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
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>
  </div>
</template>
