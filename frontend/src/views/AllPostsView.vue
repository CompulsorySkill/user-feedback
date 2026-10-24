<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { IconLoader2, IconRefresh } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { listBoards } from '@/api/boards'
import type { Board } from '@/api/types'
import BoardSidebar from '@/components/BoardSidebar.vue'
import PostFeed from '@/components/PostFeed.vue'

const boards = ref<Board[]>([])
const loading = ref(true)
const errorMessage = ref('')

const totalCount = computed(() => boards.value.reduce((sum, item) => sum + item.post_count, 0))

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    boards.value = await listBoards()
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '无法加载看板，请确认后端已启动。'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container">
    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载看板…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>

    <div v-else class="board-layout" :class="{ 'board-layout-single': !boards.length }">
      <BoardSidebar :boards="boards" :total-count="totalCount" />

      <div class="board-main">
        <header class="board-header">
          <div class="board-header-main">
            <span class="board-slug">ALL FEEDBACK</span>
            <h1>全部反馈</h1>
            <div class="board-meta">
              <span>{{ totalCount }} 条反馈</span>
              <span>{{ boards.length }} 个看板</span>
            </div>
          </div>
        </header>

        <PostFeed show-board />
      </div>
    </div>
  </div>
</template>
