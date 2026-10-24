<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { IconArrowLeft, IconLoader2, IconPlus, IconRefresh } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getBoard, listBoardPosts, type PostSort } from '@/api/boards'
import type { Board, PostStatus, PostSummary } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import PostCard from '@/components/PostCard.vue'
import { useAuthStore } from '@/stores/auth'

const PAGE_SIZE = 10

const STATUS_FILTERS: Array<{ value: PostStatus | ''; label: string }> = [
  { value: '', label: '全部' },
  { value: 'open', label: '待处理' },
  { value: 'planned', label: '已计划' },
  { value: 'in_progress', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'closed', label: '已关闭' },
]
const SORT_OPTIONS: Array<{ value: PostSort; label: string }> = [
  { value: 'recent', label: '最近' },
  { value: 'top', label: '最热' },
]
const VALID_STATUSES = new Set<string>(
  STATUS_FILTERS.map((item) => item.value).filter(Boolean),
)

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const board = ref<Board | null>(null)
const posts = ref<PostSummary[]>([])
const nextCursor = ref<string | null>(null)

const loading = ref(true)
const loadingMore = ref(false)
const errorMessage = ref('')
const loadMoreError = ref('')

const statusFilter = ref<PostStatus | ''>(normalizeStatus(route.query.status))
const sort = ref<PostSort>(route.query.sort === 'top' ? 'top' : 'recent')

const hasFilter = computed(() => statusFilter.value !== '' || sort.value !== 'recent')

function normalizeStatus(value: unknown): PostStatus | '' {
  return typeof value === 'string' && VALID_STATUSES.has(value)
    ? (value as PostStatus)
    : ''
}

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
    const page = await listBoardPosts(slug(), {
      limit: PAGE_SIZE,
      status: statusFilter.value || null,
      sort: sort.value,
    })
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
      status: statusFilter.value || null,
      sort: sort.value,
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

function syncQuery(): void {
  const query: Record<string, string> = {}
  if (statusFilter.value) query.status = statusFilter.value
  if (sort.value !== 'recent') query.sort = sort.value
  void router.replace({ query })
}

function setStatus(value: PostStatus | ''): void {
  if (statusFilter.value === value) return
  statusFilter.value = value
  syncQuery()
}

function setSort(value: PostSort): void {
  if (sort.value === value) return
  sort.value = value
  syncQuery()
}

function clearFilters(): void {
  statusFilter.value = ''
  sort.value = 'recent'
  syncQuery()
}

onMounted(load)
watch(() => route.params.slug, load)
watch(
  () => [route.query.status, route.query.sort],
  () => {
    statusFilter.value = normalizeStatus(route.query.status)
    sort.value = route.query.sort === 'top' ? 'top' : 'recent'
    void load()
  },
)
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
        <div class="board-header-main">
          <span class="board-slug">/{{ board.slug }}</span>
          <h1>{{ board.name }}</h1>
          <p class="board-description">{{ board.description ?? '暂无描述' }}</p>
          <div class="board-meta">
            <span>{{ board.post_count }} 条反馈</span>
            <span v-if="board.allow_guest_voting">匿名可投票</span>
            <span v-if="board.allow_guest_commenting">匿名可评论</span>
            <span v-if="!board.allow_guest_posting && !auth.isAuthenticated">发布需登录</span>
          </div>
        </div>
        <RouterLink
          v-if="board.allow_guest_posting || auth.isAuthenticated"
          :to="`/b/${board.slug}/new`"
          class="button button-primary"
        >
          <IconPlus :size="16" :stroke-width="2" />
          发布反馈
        </RouterLink>
      </header>

      <div class="list-toolbar">
        <div class="filter-group" role="group" aria-label="状态筛选">
          <button
            v-for="item in STATUS_FILTERS"
            :key="item.label"
            type="button"
            class="filter-chip"
            :class="{ 'is-active': statusFilter === item.value }"
            @click="setStatus(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="sort-group" role="group" aria-label="排序">
          <button
            v-for="item in SORT_OPTIONS"
            :key="item.value"
            type="button"
            class="sort-button"
            :class="{ 'is-active': sort === item.value }"
            @click="setSort(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>

      <div v-if="posts.length === 0" class="empty-wrap">
        <EmptyState
          :title="hasFilter ? '没有匹配的反馈' : '这里还没有反馈'"
          :description="
            hasFilter ? '试试切换状态或排序，或清除筛选。' : '该看板暂时没有公开的反馈内容。'
          "
        >
          <button
            v-if="hasFilter"
            class="button button-ghost button-small"
            type="button"
            @click="clearFilters"
          >
            清除筛选
          </button>
        </EmptyState>
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
