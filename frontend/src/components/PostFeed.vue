<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { IconLoader2, IconRefresh, IconSearch, IconX } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { listAllPosts, listBoardPosts, type ListPostsOptions, type PostSort } from '@/api/boards'
import { listFilterTags } from '@/api/tags'
import type { PostStatus, PostSummary, TagSummary } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import PostCard from '@/components/PostCard.vue'
import {
  MAX_FILTER_TAGS,
  normalizeSearch,
  normalizeSort,
  normalizeStatus,
  normalizeTags,
} from '@/utils/postFilters'

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

const props = defineProps<{
  boardSlug?: string | null
  showBoard?: boolean
}>()

const route = useRoute()
const router = useRouter()

const posts = ref<PostSummary[]>([])
const availableTags = ref<TagSummary[]>([])
const nextCursor = ref<string | null>(null)
const loading = ref(true)
const loadingMore = ref(false)
const errorMessage = ref('')
const loadMoreError = ref('')

const statusFilter = ref<PostStatus | ''>(normalizeStatus(route.query.status))
const sort = ref<PostSort>(normalizeSort(route.query.sort))
const tagFilter = ref<string[]>(normalizeTags(route.query.tag))
const searchQuery = ref(normalizeSearch(route.query.q))
const searchInput = ref(searchQuery.value)

let searchTimer: ReturnType<typeof setTimeout> | null = null
let loadScheduled = false

/** 切换看板与重置筛选可能在同一 tick 触发，合并为一次请求。 */
function scheduleLoad(): void {
  if (loadScheduled) return
  loadScheduled = true
  queueMicrotask(() => {
    loadScheduled = false
    void load()
  })
}

const hasFilter = computed(
  () =>
    statusFilter.value !== '' ||
    sort.value !== 'recent' ||
    tagFilter.value.length > 0 ||
    searchQuery.value !== '',
)

function options(cursor?: string | null): ListPostsOptions & { board?: string | null } {
  return {
    limit: PAGE_SIZE,
    cursor: cursor ?? null,
    status: statusFilter.value || null,
    sort: sort.value,
    q: searchQuery.value || null,
    tags: tagFilter.value,
    board: props.boardSlug || null,
  }
}

function fetchPage(
  cursor?: string | null,
): Promise<{ items: PostSummary[]; next_cursor: string | null }> {
  return props.boardSlug
    ? listBoardPosts(props.boardSlug, options(cursor))
    : listAllPosts(options(cursor))
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  posts.value = []
  nextCursor.value = null
  try {
    const page = await fetchPage()
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
    const page = await fetchPage(nextCursor.value)
    const seen = new Set(posts.value.map((post) => post.id))
    posts.value = [...posts.value, ...page.items.filter((post) => !seen.has(post.id))]
    nextCursor.value = page.next_cursor
  } catch (error) {
    loadMoreError.value = error instanceof ApiError ? error.message : '加载更多失败，请重试。'
  } finally {
    loadingMore.value = false
  }
}

function syncQuery(): void {
  const query: Record<string, string | string[]> = {}
  if (statusFilter.value) query.status = statusFilter.value
  if (sort.value !== 'recent') query.sort = sort.value
  if (tagFilter.value.length) query.tag = tagFilter.value
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

function isTagActive(name: string): boolean {
  return tagFilter.value.some((tag) => tag.toLocaleLowerCase() === name.toLocaleLowerCase())
}

function toggleTag(name: string): void {
  if (isTagActive(name)) {
    tagFilter.value = tagFilter.value.filter(
      (tag) => tag.toLocaleLowerCase() !== name.toLocaleLowerCase(),
    )
  } else {
    if (tagFilter.value.length >= MAX_FILTER_TAGS) return
    tagFilter.value = [...tagFilter.value, name]
  }
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
  tagFilter.value = []
  searchInput.value = ''
  searchQuery.value = ''
  syncQuery()
}

async function loadTags(): Promise<void> {
  try {
    const tags = await listFilterTags()
    // 只有被使用中的标签才值得出现在筛选器里。
    availableTags.value = tags.filter((tag) => tag.post_count > 0)
  } catch {
    // 标签筛选是增强功能，失败不影响反馈列表。
    availableTags.value = []
  }
}

onMounted(() => {
  void loadTags()
  void load()
})
onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

watch(
  () => props.boardSlug,
  () => {
    scheduleLoad()
  },
)
watch(
  () => [route.query.status, route.query.sort, route.query.tag, route.query.q],
  () => {
    statusFilter.value = normalizeStatus(route.query.status)
    sort.value = normalizeSort(route.query.sort)
    tagFilter.value = normalizeTags(route.query.tag)
    const query = normalizeSearch(route.query.q)
    searchQuery.value = query
    // URL 变化（返回/前进/清除筛选）时同步输入框，但不打断正在输入的内容。
    if (document.activeElement?.tagName !== 'INPUT') searchInput.value = query
    scheduleLoad()
  },
)
</script>

<template>
  <section class="board-main">
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

    <div v-if="availableTags.length" class="tag-filter" role="group" aria-label="标签筛选">
      <span class="tag-filter-label">标签</span>
      <div class="filter-group">
        <button
          v-for="tag in availableTags"
          :key="tag.id"
          type="button"
          class="filter-chip"
          :class="{ 'is-active': isTagActive(tag.name) }"
          :disabled="!isTagActive(tag.name) && tagFilter.length >= MAX_FILTER_TAGS"
          :title="`${tag.name} · ${tag.post_count} 条反馈`"
          @click="toggleTag(tag.name)"
        >
          {{ tag.name }}
          <span class="tag-filter-count">{{ tag.post_count }}</span>
        </button>
      </div>
    </div>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载反馈…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>

    <div v-else-if="posts.length === 0" class="empty-wrap">
      <EmptyState
        :title="hasFilter ? '没有匹配的反馈' : '这里还没有反馈'"
        :description="
          searchQuery
            ? `没有找到匹配「${searchQuery}」的反馈，试试其他关键词。`
            : hasFilter
              ? '试试切换状态、标签或排序，或清除筛选。'
              : showBoard
                ? '所有看板暂时都没有公开的反馈内容。'
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
      <PostCard v-for="post in posts" :key="post.id" :post="post" :show-board="showBoard" />

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
</template>
