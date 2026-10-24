<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  IconArrowUpRight,
  IconCircleCheck,
  IconCloudOff,
  IconLoader2,
  IconMessageCircle,
  IconRefresh,
} from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { listBoards } from '@/api/boards'
import { getHealth, type HealthResponse } from '@/api/health'
import type { Board } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'

const boards = ref<Board[]>([])
const loading = ref(true)
const errorMessage = ref('')

const health = ref<HealthResponse | null>(null)
const healthState = ref<'loading' | 'ok' | 'error'>('loading')
const healthError = ref('')

async function loadBoards(): Promise<void> {
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

async function loadHealth(): Promise<void> {
  healthState.value = 'loading'
  healthError.value = ''
  try {
    health.value = await getHealth()
    healthState.value = 'ok'
  } catch (error) {
    health.value = null
    healthState.value = 'error'
    healthError.value = error instanceof ApiError ? error.message : '后端不可达'
  }
}

onMounted(() => {
  void loadBoards()
  void loadHealth()
})
</script>

<template>
  <div class="container">
    <section class="hero hero-compact">
      <p class="eyebrow"><IconMessageCircle :size="15" :stroke-width="2" /> 公开反馈板</p>
      <h1>把用户的声音，<br />变成可追踪的路线。</h1>
      <p class="hero-lead">
        浏览各看板的反馈与进展，查看版本更新日志。匿名即可阅读全部公开内容，无需登录。
      </p>
    </section>

    <section class="boards-section">
      <div class="section-head">
        <h2>看板</h2>
        <p class="muted">按主题收集反馈，状态与投票公开可见。</p>
      </div>

      <p v-if="loading" class="loading-line">
        <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载看板…
      </p>

      <div v-else-if="errorMessage" class="inline-error">
        <span>{{ errorMessage }}</span>
        <button class="button button-ghost button-small" type="button" @click="loadBoards">
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
    </section>

    <section class="service-strip" aria-live="polite">
      <span class="service-label">服务状态</span>
      <span class="health-badge" :class="`is-${healthState}`">
        <IconLoader2 v-if="healthState === 'loading'" class="spin" :size="14" :stroke-width="2" />
        <IconCircleCheck v-else-if="healthState === 'ok'" :size="14" :stroke-width="2" />
        <IconCloudOff v-else :size="14" :stroke-width="2" />
        {{ healthState === 'loading' ? '检测中' : healthState === 'ok' ? 'API 与数据库正常' : '连接失败' }}
      </span>
      <span v-if="health" class="service-meta">
        {{ health.name }} v{{ health.version }} · {{ health.environment }}
      </span>
      <span v-else-if="healthError" class="service-meta service-error">{{ healthError }}</span>
    </section>
  </div>
</template>
