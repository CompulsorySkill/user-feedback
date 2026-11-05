<script setup lang="ts">
import { IconLoader2, IconRefresh, IconSearch, IconX } from '@tabler/icons-vue';
import { useDebounceFn } from '@vueuse/core';
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  listAllPosts,
  listBoardPosts,
  listPostAuthors,
  type ListPostsOptions,
  type PostSort,
} from '@/api/boards';
import { ApiError } from '@/api/client';
import { listFilterTags } from '@/api/tags';
import type { AuthorFacet, PostStatus, PostSummary, TagSummary } from '@/api/types';
import EmptyState from '@/components/EmptyState.vue';
import FilterCombobox from '@/components/FilterCombobox.vue';
import PostCard from '@/components/PostCard.vue';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  normalizeAuthor,
  normalizeSearch,
  normalizeSort,
  normalizeStatuses,
  normalizeTags,
} from '@/utils/postFilters';

const PAGE_SIZE = 10;

interface FilterOption {
  value: string;
  label: string;
  hint?: string | number;
}

const STATUS_FILTERS: FilterOption[] = [
  { value: 'open', label: '待处理' },
  { value: 'planned', label: '已计划' },
  { value: 'in_progress', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'closed', label: '已关闭' },
];
const SORT_OPTIONS: Array<{ value: PostSort; label: string }> = [
  { value: 'recent', label: '最近' },
  { value: 'top', label: '最热' },
];

const props = defineProps<{
  boardSlug?: string | null;
  showBoard?: boolean;
}>();

const route = useRoute();
const router = useRouter();

const posts = ref<PostSummary[]>([]);
const availableTags = ref<TagSummary[]>([]);
const authors = ref<AuthorFacet[]>([]);
const nextCursor = ref<string | null>(null);
const loading = ref(true);
const loadingMore = ref(false);
const errorMessage = ref('');
const loadMoreError = ref('');

const statusFilter = ref<PostStatus[]>(normalizeStatuses(route.query.status));
const sort = ref<PostSort>(normalizeSort(route.query.sort));
const tagFilter = ref<string[]>(normalizeTags(route.query.tag));
const authorFilter = ref<string | null>(normalizeAuthor(route.query.author));
const searchQuery = ref(normalizeSearch(route.query.q));
const searchInput = ref(searchQuery.value);

const tagOptions = computed<FilterOption[]>(() =>
  availableTags.value.map((tag) => ({
    value: tag.name,
    label: tag.name,
    hint: tag.post_count,
  })),
);
const authorOptions = computed<FilterOption[]>(() =>
  authors.value.map((author) => ({
    value: author.name,
    label: author.name,
    hint: author.post_count,
  })),
);

let loadScheduled = false;

function applySearch(): void {
  const value = searchInput.value.trim().slice(0, 100);
  if (value === searchQuery.value) return;
  searchQuery.value = value;
  syncQuery();
}

const runSearch = useDebounceFn(applySearch, 300);

/** 切换看板与重置筛选可能在同一 tick 触发，合并为一次请求。 */
function scheduleLoad(): void {
  if (loadScheduled) return;
  loadScheduled = true;
  queueMicrotask(() => {
    loadScheduled = false;
    void load();
  });
}

const hasFilter = computed(
  () =>
    statusFilter.value.length > 0 ||
    sort.value !== 'recent' ||
    tagFilter.value.length > 0 ||
    authorFilter.value !== null ||
    searchQuery.value !== '',
);

function options(cursor?: string | null): ListPostsOptions & { board?: string | null } {
  return {
    limit: PAGE_SIZE,
    cursor: cursor ?? null,
    status: statusFilter.value,
    author: authorFilter.value,
    sort: sort.value,
    q: searchQuery.value || null,
    tags: tagFilter.value,
    board: props.boardSlug || null,
  };
}

function fetchPage(
  cursor?: string | null,
): Promise<{ items: PostSummary[]; next_cursor: string | null }> {
  return props.boardSlug
    ? listBoardPosts(props.boardSlug, options(cursor))
    : listAllPosts(options(cursor));
}

async function load(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  posts.value = [];
  nextCursor.value = null;
  try {
    const page = await fetchPage();
    posts.value = page.items;
    nextCursor.value = page.next_cursor;
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError
        ? error.status === 404
          ? '看板不存在或未公开。'
          : error.message
        : '加载失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
}

async function loadMore(): Promise<void> {
  if (!nextCursor.value || loadingMore.value) return;
  loadingMore.value = true;
  loadMoreError.value = '';
  try {
    const page = await fetchPage(nextCursor.value);
    const seen = new Set(posts.value.map((post) => post.id));
    posts.value = [...posts.value, ...page.items.filter((post) => !seen.has(post.id))];
    nextCursor.value = page.next_cursor;
  } catch (error) {
    loadMoreError.value = error instanceof ApiError ? error.message : '加载更多失败，请重试。';
  } finally {
    loadingMore.value = false;
  }
}

function syncQuery(): void {
  const query: Record<string, string | string[]> = {};
  if (statusFilter.value.length) query.status = statusFilter.value;
  if (authorFilter.value) query.author = authorFilter.value;
  if (sort.value !== 'recent') query.sort = sort.value;
  if (tagFilter.value.length) query.tag = tagFilter.value;
  if (searchQuery.value) query.q = searchQuery.value;
  void router.replace({ query });
}

function setStatuses(values: string[]): void {
  const next = normalizeStatuses(values) as PostStatus[];
  if (next.join() === statusFilter.value.join()) return;
  statusFilter.value = next;
  syncQuery();
}

function setTags(values: string[]): void {
  // 超过 5 个的部分由 normalizeTags 截断（后端同样只接受 5 个）。
  const next = normalizeTags(values);
  if (next.join() === tagFilter.value.join()) return;
  tagFilter.value = next;
  syncQuery();
}

function setAuthor(values: string[]): void {
  const next = normalizeAuthor(values[0]);
  if (next === authorFilter.value) return;
  authorFilter.value = next;
  syncQuery();
}

function setSort(value: unknown): void {
  const next = normalizeSort(value);
  if (sort.value === next) return;
  sort.value = next;
  syncQuery();
}

function onSearchInput(): void {
  runSearch();
}

/** 输入框右侧的搜索按钮：跳过防抖立刻查一次。 */
function submitSearch(): void {
  runSearch.cancel();
  applySearch();
}

function clearSearch(): void {
  searchInput.value = '';
  runSearch.cancel();
  if (!searchQuery.value) return;
  searchQuery.value = '';
  syncQuery();
}

function clearFilters(): void {
  statusFilter.value = [];
  sort.value = 'recent';
  tagFilter.value = [];
  authorFilter.value = null;
  searchInput.value = '';
  searchQuery.value = '';
  syncQuery();
}

async function loadTags(): Promise<void> {
  try {
    const tags = await listFilterTags(props.boardSlug);
    // 只有被使用中的标签才值得出现在筛选器里（计数已限定在当前看板）。
    availableTags.value = tags.filter((tag) => tag.post_count > 0);
  } catch {
    // 标签筛选是增强功能，失败不影响反馈列表。
    availableTags.value = [];
  }
}

async function loadAuthors(): Promise<void> {
  try {
    authors.value = await listPostAuthors(props.boardSlug);
  } catch {
    // 作者筛选同属增强功能，失败只是下拉为空。
    authors.value = [];
  }
}

onMounted(() => {
  void loadTags();
  void loadAuthors();
  void load();
});
onUnmounted(() => {
  // 防抖不随组件作用域释放，卸载后仍可能触发一次 syncQuery 改写路由。
  runSearch.cancel();
});

watch(
  () => props.boardSlug,
  () => {
    void loadTags();
    void loadAuthors();
    scheduleLoad();
  },
);
watch(
  () => [route.query.status, route.query.sort, route.query.tag, route.query.q, route.query.author],
  () => {
    statusFilter.value = normalizeStatuses(route.query.status);
    sort.value = normalizeSort(route.query.sort);
    tagFilter.value = normalizeTags(route.query.tag);
    authorFilter.value = normalizeAuthor(route.query.author);
    const query = normalizeSearch(route.query.q);
    searchQuery.value = query;
    // URL 变化（返回/前进/清除筛选）时同步输入框，但不打断正在输入的内容。
    if (document.activeElement?.tagName !== 'INPUT') searchInput.value = query;
    scheduleLoad();
  },
);
</script>

<template>
  <section class="board-main">
    <div class="filter-bar">
      <div class="search-box">
        <Input
          v-model="searchInput"
          type="search"
          maxlength="100"
          placeholder="搜索标题或摘要…"
          aria-label="搜索反馈"
          class="h-8 pr-8"
          @input="onSearchInput"
          @keydown.enter.prevent="submitSearch"
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
      <Button
        type="button"
        variant="outline"
        size="icon-lg"
        aria-label="搜索"
        @click="submitSearch"
      >
        <IconSearch :size="16" :stroke-width="2" />
      </Button>
    </div>

    <div class="filter-bar filter-bar-options">
      <FilterCombobox
        label="状态"
        multiple
        :model-value="statusFilter"
        :options="STATUS_FILTERS"
        @update:model-value="setStatuses"
      />
      <FilterCombobox
        label="标签"
        multiple
        :model-value="tagFilter"
        :options="tagOptions"
        search-placeholder="搜索标签…"
        @update:model-value="setTags"
      />

      <span class="filter-bar-spacer" />

      <FilterCombobox
        label="用户"
        :model-value="authorFilter ? [authorFilter] : []"
        :options="authorOptions"
        search-placeholder="搜索用户…"
        @update:model-value="setAuthor"
      />
      <Select :model-value="sort" @update:model-value="setSort">
        <SelectTrigger size="lg" aria-label="排序">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="item in SORT_OPTIONS" :key="item.value" :value="item.value">
            {{ item.label }}
          </SelectItem>
        </SelectContent>
      </Select>
      <Button v-if="hasFilter" type="button" variant="ghost" size="lg" @click="clearFilters">
        重置
      </Button>
    </div>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载反馈…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <Button type="button" @click="load" variant="ghost" size="lg">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </Button>
    </div>

    <div v-else-if="posts.length === 0" class="empty-wrap">
      <EmptyState
        :title="hasFilter ? '没有匹配的反馈' : '这里还没有反馈'"
        :description="
          searchQuery
            ? `没有找到匹配「${searchQuery}」的反馈，试试其他关键词。`
            : hasFilter
              ? '试试切换状态、标签、用户或排序，或清除筛选。'
              : showBoard
                ? '所有看板暂时都没有公开的反馈内容。'
                : '该看板暂时没有公开的反馈内容。'
        "
      >
        <Button v-if="hasFilter" type="button" @click="clearFilters" variant="ghost" size="lg">
          清除筛选
        </Button>
      </EmptyState>
    </div>

    <div v-else class="post-list">
      <PostCard v-for="post in posts" :key="post.id" :post="post" :show-board="showBoard" />

      <div class="load-more">
        <Button
          v-if="nextCursor"
          type="button"
          :disabled="loadingMore"
          @click="loadMore"
          variant="ghost"
          size="lg"
        >
          <IconLoader2 v-if="loadingMore" class="spin" :size="16" :stroke-width="2" />
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </Button>
        <span v-else class="list-end">已经到底了</span>
        <p v-if="loadMoreError" class="inline-error">{{ loadMoreError }}</p>
      </div>
    </div>
  </section>
</template>
