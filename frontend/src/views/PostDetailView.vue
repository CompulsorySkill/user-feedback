<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  IconArrowLeft,
  IconEdit,
  IconLoader2,
  IconMessage,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { deletePost, getPost } from '@/api/posts'
import type { PostDetail } from '@/api/types'
import AuthorTag from '@/components/AuthorTag.vue'
import CommentSection from '@/components/CommentSection.vue'
import PostStatusControl from '@/components/PostStatusControl.vue'
import RichTextRenderer from '@/components/RichTextRenderer.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import TagList from '@/components/TagList.vue'
import VoteButton from '@/components/VoteButton.vue'
import { useAuthStore } from '@/stores/auth'
import { formatDate, formatDateTime, formatRelative } from '@/utils/date'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const post = ref<PostDetail | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const deleting = ref(false)
const actionError = ref('')

const isClosed = computed(() => post.value?.status === 'closed')
const canEdit = computed(() => {
  if (!post.value) return false
  if (auth.isAdmin) return true
  return post.value.is_author && post.value.status !== 'closed'
})

function onPostUpdated(updated: PostDetail): void {
  post.value = updated
}

async function removePost(): Promise<void> {
  if (!post.value || deleting.value) return
  if (!window.confirm('确认删除这条反馈？其评论与投票会一并删除，且不可恢复。')) return
  deleting.value = true
  actionError.value = ''
  const boardSlug = post.value.board.slug
  try {
    await deletePost(post.value.id)
    await router.push(`/b/${boardSlug}`)
  } catch (error) {
    actionError.value = error instanceof ApiError ? error.message : '删除失败，请稍后重试。'
  } finally {
    deleting.value = false
  }
}

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
  <div class="container">
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
            <span class="post-time" :title="formatDateTime(post.created_at)">
              {{ formatDate(post.created_at) }}
            </span>
          </div>
          <h1>{{ post.title }}</h1>
          <TagList v-if="post.tags.length" :tags="post.tags" class="post-detail-tags" />
          <div class="post-detail-meta">
            <AuthorTag :post="post" />
            <span class="meta-item">
              <IconMessage :size="15" :stroke-width="1.8" />
              {{ post.comment_count }} 条评论
            </span>
            <span class="meta-item subtle" :title="formatDateTime(post.updated_at)">
              更新于 {{ formatRelative(post.updated_at) }}
            </span>
          </div>
          <div class="post-detail-actions">
            <PostStatusControl :post="post" @updated="onPostUpdated" />
            <RouterLink
              v-if="canEdit"
              :to="`/post/${post.id}/edit`"
              class="button button-ghost button-small"
            >
              <IconEdit :size="15" :stroke-width="2" />
              编辑反馈
            </RouterLink>
            <button
              v-if="auth.isAdmin"
              type="button"
              class="button button-ghost button-small button-danger"
              :disabled="deleting"
              @click="removePost"
            >
              <IconLoader2 v-if="deleting" class="spin" :size="15" :stroke-width="2" />
              <IconTrash v-else :size="15" :stroke-width="2" />
              删除反馈
            </button>
          </div>
          <p v-if="actionError" class="inline-error">{{ actionError }}</p>
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
          <span class="action-hint">
            {{ isClosed ? '反馈已关闭' : '匿名即可投票 · 评论支持 3 层回复' }}
          </span>
          <VoteButton :post-id="post.id" :initial-count="post.vote_count" :disabled="isClosed" />
        </footer>
      </article>

      <CommentSection :post-id="post.id" :closed="isClosed" @count="post.comment_count = $event" />
    </template>

    <div v-else class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>
  </div>
</template>
