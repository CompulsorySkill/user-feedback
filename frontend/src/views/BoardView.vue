<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  IconArrowLeft,
  IconLoader2,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconX,
} from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getBoard, listBoardPosts, listBoards, type PostSort } from '@/api/boards'
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

const boards = ref<Board[]>([])
const board = ref<Board | null>(null)
const posts = ref<PostSummary[]>([])
const nextCursor = ref<string | null>(null)

const loading = ref(true)
const loadingMore = ref(false)
const errorMessage = ref('')
const loadMoreError = ref('')

const statusFilter = ref<PostStatus | ''>(normalizeStatus(route.query.status))
const sort = ref<PostSort>(route.query.sort === 'top' ? 'top' : 'recent')
const searchQuery = ref(normalizeQuery(route.query.q))
const searchInput = ref(searchQuery.value)

let searchTimer: ReturnType<typeof setTimeout> | null = null

const hasFilter = computed(
  () => statusFilter.value !== '' || sort.value !== 'recent' || searchQuery.value !== '',
)

function normalizeStatus(value: unknown): PostStatus | '' {
  return typeof value === 'string' && VALID_STATUSES.has(value)
    ? (value as PostStatus)
    : ''
}

function normalizeQuery(value: unknown): string {
  return typeof value === 'string' ? value.trim().slice(0, 100) : ''
}

function slug(): string {
  return String(route.params.slug ?? '')
}

async function loadBoards(): Promise<void> {
  try {
    boards.value = await listBoards()
  } catch {
    boards.value = []
  }
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
      q: searchQuery.value || null,
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
      q: searchQuery.value || null,
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
  if (searchQuery.value) query.q = searchQuery.value
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

function onSearchInput(): void {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    const value = searchInput.value.trim().slice(0, 100)
    if (value === searchQuery.value) return
    searchQuery.value = value
    syncQuery()
  }, 300)
}

function clearSearch(): void {
  searchInput.value = ''
  if (searchTimer) clearTimeout(searchTimer)
  if (!searchQuery.value) return
  searchQuery.value = ''
  syncQuery()
}

function clearFilters(): void {
  statusFilter.value = ''
  sort.value = 'recent'
  searchInput.value = ''
  searchQuery.value = ''
  syncQuery()
}

onMounted(() => {
  void loadBoards()
  void load()
})
onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

watch(() => route.params.slug, load)
watch(
  () => [route.query.status, route.query.sort, route.query.q],
  () => {
    statusFilter.value = normalizeStatus(route.query.status)
    sort.value = route.query.sort === 'top' ? 'top' : 'recent'
    const query = normalizeQuery(route.query.q)
    searchQuery.value = query
    // URL 变化（返回/前进/清除筛选）时同步输入框，但不打断正在输入的内容。
    if (document.activeElement?.tagName !== 'INPUT') searchInput.value = query
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

    <div v-else-if="board" class="board-layout">
      <aside v-if="boards.length" class="board-sidebar">
        <p class="sidebar-title">全部看板</p>
        <nav class="board-nav" aria-label="看板列表">
          <RouterLink
            v-for="item in boards"
            :key="item.slug"
            :to="`/b/${item.slug}`"
            class="board-nav-item"
            :class="{ 'is-active': item.slug === board.slug }"
          >
            <span class="board-nav-name">{{ item.name }}</span>
            <span class="board-nav-count">{{ item.post_count }}</span>
          </RouterLink>
        </nav>
      </aside>

      <section class="board-main">
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

        <div class="search-box">
          <IconSearch class="search-icon" :size="16" :stroke-width="2" />
          <input
            v-model="searchInput"
            class="search-input"
            type="search"
            maxlength="100"
            placeholder="搜索标题或摘要…"
            aria-label="搜索反馈"
            @input="onSearchInput"
          />
          <button
            v-if="searchInput"
            type="button"
            class="search-clear"
            aria-label="清除搜索"
            @click="clearSearch"
          >
            <IconX :size="14" :stroke-width="2" />
          </button>
        </div>

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
              searchQuery
                ? `没有找到匹配「${searchQuery}」的反馈，试试其他关键词。`
                : hasFilter
                  ? '试试切换状态或排序，或清除筛选。'
                  : '该看板暂时没有公开的反馈内容。'
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
      </section>
    </div>

    <div v-else class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>
  </div>
</template>
