<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { IconArrowLeft, IconLoader2, IconRefresh } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getBoard, listBoardPosts } from '@/api/boards'
import type { Board, PostSummary } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import PostCard from '@/components/PostCard.vue'

const PAGE_SIZE = 10

const route = useRoute()
const board = ref<Board | null>(null)
const posts = ref<PostSummary[]>([])
const nextCursor = ref<string | null>(null)

const loading = ref(true)
const loadingMore = ref(false)
const errorMessage = ref('')
const loadMoreError = ref('')

function slug(): string {
  return String(route.params.slug ?? '')
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  board.value = null
  posts.value = []
  nextCursor.value = null
  try {
    board.value = await getBoard(slug())
    const page = await listBoardPosts(slug(), { limit: PAGE_SIZE })
    posts.value = page.items
    nextCursor.value = page.next_cursor
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError
        ? error.status === 404
          ? '看板不存在或未公开。'
          : error.message
        : '加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

async function loadMore(): Promise<void> {
  if (!nextCursor.value || loadingMore.value) return
  loadingMore.value = true
  loadMoreError.value = ''
  try {
    const page = await listBoardPosts(slug(), {
      limit: PAGE_SIZE,
      cursor: nextCursor.value,
    })
    const seen = new Set(posts.value.map((post) => post.id))
    posts.value = [...posts.value, ...page.items.filter((post) => !seen.has(post.id))]
    nextCursor.value = page.next_cursor
  } catch (error) {
    loadMoreError.value =
      error instanceof ApiError ? error.message : '加载更多失败，请重试。'
  } finally {
    loadingMore.value = false
  }
}

onMounted(load)
watch(() => route.params.slug, load)
</script>

<template>
  <div class="container">
    <RouterLink to="/" class="back-link">
      <IconArrowLeft :size="15" :stroke-width="2" /> 全部看板
    </RouterLink>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载反馈…
    </p>

    <template v-else-if="board">
      <header class="board-header">
        <span class="board-slug">/{{ board.slug }}</span>
        <h1>{{ board.name }}</h1>
        <p class="board-description">{{ board.description ?? '暂无描述' }}</p>
        <div class="board-meta">
          <span>{{ board.post_count }} 条反馈</span>
          <span v-if="board.allow_guest_voting">匿名可投票</span>
          <span v-if="board.allow_guest_commenting">匿名可评论</span>
          <span v-if="!board.allow_guest_posting">发布需登录</span>
        </div>
      </header>

      <div v-if="posts.length === 0" class="empty-wrap">
        <EmptyState title="这里还没有反馈" description="该看板暂时没有公开的反馈内容。" />
      </div>

      <div v-else class="post-list">
        <PostCard v-for="post in posts" :key="post.id" :post="post" />

        <div class="load-more">
          <button
            v-if="nextCursor"
            class="button button-ghost"
            type="button"
            :disabled="loadingMore"
            @click="loadMore"
          >
            <IconLoader2 v-if="loadingMore" class="spin" :size="16" :stroke-width="2" />
            {{ loadingMore ? '加载中…' : '加载更多' }}
          </button>
          <span v-else class="list-end">已经到底了</span>
          <p v-if="loadMoreError" class="inline-error">{{ loadMoreError }}</p>
        </div>
      </div>
    </template>

    <div v-else class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>
  </div>
</template>
