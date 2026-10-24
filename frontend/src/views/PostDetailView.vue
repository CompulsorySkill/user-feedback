<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  IconArrowLeft,
  IconLoader2,
  IconMessage,
  IconRefresh,
  IconUser,
} from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getPost } from '@/api/posts'
import type { PostDetail } from '@/api/types'
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
            <span class="meta-item">
              <IconUser :size="15" :stroke-width="1.8" />
              {{ post.author_name ?? '匿名用户' }}
            </span>
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
