<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { IconLoader2, IconPlus, IconRefresh } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getBoard, listBoards } from '@/api/boards'
import type { Board } from '@/api/types'
import BoardSidebar from '@/components/BoardSidebar.vue'
import PostFeed from '@/components/PostFeed.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const boards = ref<Board[]>([])
const board = ref<Board | null>(null)
const loading = ref(true)
const errorMessage = ref('')

const totalCount = computed(() =>
  boards.value.reduce((sum, item) => sum + item.post_count, 0),
)

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
  try {
    board.value = await getBoard(slug())
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

onMounted(() => {
  void loadBoards()
  void load()
})

watch(() => route.params.slug, load)
</script>

<template>
  <div class="container">
    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载反馈…
    </p>

    <div v-else-if="board" class="board-layout" :class="{ 'board-layout-single': !boards.length }">
      <BoardSidebar
        :boards="boards"
        :active-slug="board.slug"
        :total-count="totalCount"
      />

      <div class="board-main">
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

        <PostFeed :board-slug="board.slug" />
      </div>
    </div>

    <div v-else class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>
  </div>
</template>
