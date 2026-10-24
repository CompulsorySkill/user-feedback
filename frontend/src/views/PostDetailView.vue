<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  IconArrowLeft,
  IconLoader2,
  IconMessage,
  IconRefresh,
} from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getPost } from '@/api/posts'
import type { PostDetail } from '@/api/types'
import AuthorTag from '@/components/AuthorTag.vue'
import RichTextRenderer from '@/components/RichTextRenderer.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import VoteButton from '@/components/VoteButton.vue'
import { formatDate, formatRelative } from '@/utils/date'

const route = useRoute()
const post = ref<PostDetail | null>(null)
const loading = ref(true)
const errorMessage = ref('')

const isClosed = computed(() => post.value?.status === 'closed')

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  post.value = null
  try {
    post.value = await getPost(String(route.params.id ?? ''))
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError
        ? error.status === 404
          ? '这条反馈不存在或未公开。'
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
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载反馈…
    </p>

    <template v-else-if="post">
      <RouterLink :to="`/b/${post.board.slug}`" class="back-link">
        <IconArrowLeft :size="15" :stroke-width="2" /> {{ post.board.name }}
      </RouterLink>

      <article class="post-detail">
        <header class="post-detail-head">
          <div class="post-badges">
            <StatusBadge :status="post.status" />
            <span class="post-time">{{ formatDate(post.created_at) }}</span>
          </div>
          <h1>{{ post.title }}</h1>
          <div class="post-detail-meta">
            <AuthorTag :post="post" />
            <span class="meta-item">
              <IconMessage :size="15" :stroke-width="1.8" />
              {{ post.comment_count }} 条评论
            </span>
            <span class="meta-item subtle">更新于 {{ formatRelative(post.updated_at) }}</span>
          </div>
        </header>

        <div v-if="isClosed" class="notice notice-closed">
          该反馈已关闭，不再接受新的投票与评论；历史内容仍然保留。
        </div>

        <section class="rich-text">
          <RichTextRenderer :node="post.content" />
        </section>

        <details v-if="post.environment" class="env-panel">
          <summary>发布者附带的浏览器 / 操作系统信息</summary>
          <dl class="env-grid">
            <div v-if="post.environment.user_agent">
              <dt>User Agent</dt>
              <dd>{{ post.environment.user_agent }}</dd>
            </div>
            <div v-if="post.environment.platform">
              <dt>平台</dt>
              <dd>{{ post.environment.platform }}</dd>
            </div>
            <div v-if="post.environment.language">
              <dt>语言</dt>
              <dd>{{ post.environment.language }}</dd>
            </div>
            <div v-if="post.environment.viewport">
              <dt>视口</dt>
              <dd>{{ post.environment.viewport }}</dd>
            </div>
            <div v-if="post.environment.timezone">
              <dt>时区</dt>
              <dd>{{ post.environment.timezone }}</dd>
            </div>
          </dl>
        </details>

        <footer class="post-detail-foot">
          <VoteButton
            :post-id="post.id"
            :initial-count="post.vote_count"
            :disabled="isClosed"
          />
          <span class="action-hint">
            {{ isClosed ? '反馈已关闭' : '匿名即可投票 · 评论将在 P3 开放' }}
          </span>
        </footer>
      </article>

      <section class="comments-placeholder">
        <h2>评论（{{ post.comment_count }}）</h2>
        <p class="muted">楼中楼评论将在 P3 上线，当前仅展示计数。</p>
      </section>
    </template>

    <div v-else class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>
  </div>
</template>
