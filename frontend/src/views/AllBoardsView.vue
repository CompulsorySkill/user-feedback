<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  IconArrowUpRight,
  IconLoader2,
  IconRefresh,
} from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { listBoards } from '@/api/boards'
import type { Board } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'

const boards = ref<Board[]>([])
const loading = ref(true)
const errorMessage = ref('')

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
    <header class="page-header">
      <p class="eyebrow">All boards</p>
      <h1>全部看板</h1>
      <p class="hero-lead">
        按主题收集反馈、公开跟进状态；匿名即可阅读全部公开内容，无需登录。
      </p>
    </header>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载看板…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>

    <EmptyState
      v-else-if="boards.length === 0"
      title="还没有公开看板"
      description="管理员创建看板后，这里会展示所有公开内容。"
    />

    <div v-else class="board-grid">
      <RouterLink
        v-for="board in boards"
        :key="board.id"
        :to="`/b/${board.slug}`"
        class="board-card"
      >
        <div class="board-card-top">
          <span class="board-slug">/{{ board.slug }}</span>
          <IconArrowUpRight :size="16" :stroke-width="1.8" />
        </div>
        <h3>{{ board.name }}</h3>
        <p>{{ board.description ?? '暂无描述' }}</p>
        <div class="board-card-foot">
          <span>{{ board.post_count }} 条反馈</span>
          <span class="board-policy">
            {{ board.allow_guest_posting ? '允许匿名发布' : '仅登录发布' }}
          </span>
        </div>
      </RouterLink>
    </div>
  </div>
</template>
