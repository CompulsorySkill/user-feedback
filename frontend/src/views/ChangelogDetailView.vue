<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { IconArrowLeft, IconLoader2, IconRefresh } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getChangelog } from '@/api/changelogs'
import type { ChangelogDetail } from '@/api/types'
import RichTextRenderer from '@/components/RichTextRenderer.vue'
import { formatDate } from '@/utils/date'

const route = useRoute()
const entry = ref<ChangelogDetail | null>(null)
const loading = ref(true)
const errorMessage = ref('')

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  entry.value = null
  try {
    entry.value = await getChangelog(String(route.params.id ?? ''))
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

      <article class="changelog-detail">
        <header class="post-detail-head">
          <span class="changelog-date">{{ formatDate(entry.published_at) }}</span>
          <h1>{{ entry.title }}</h1>
        </header>
        <section class="rich-text">
          <RichTextRenderer :node="entry.content" />
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
