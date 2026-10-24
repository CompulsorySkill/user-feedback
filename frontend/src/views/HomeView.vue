<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  IconArrowUpRight,
  IconChecklist,
  IconCircleCheck,
  IconCloudOff,
  IconInbox,
  IconLoader2,
  IconRefresh,
  IconSpeakerphone,
  IconUserOff,
} from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getHealth, type HealthResponse } from '@/api/health'

type LoadState = 'loading' | 'ok' | 'error'

const state = ref<LoadState>('loading')
const health = ref<HealthResponse | null>(null)
const errorMessage = ref('')

async function loadHealth(): Promise<void> {
  state.value = 'loading'
  errorMessage.value = ''
  try {
    health.value = await getHealth()
    state.value = 'ok'
  } catch (error) {
    health.value = null
    state.value = 'error'
    errorMessage.value =
      error instanceof ApiError ? `${error.message}` : '无法连接后端服务，请确认 uvicorn 已启动。'
  }
}

onMounted(loadHealth)

const modules = [
  {
    icon: IconInbox,
    title: '反馈（Post）',
    description: '看板归属、状态流转、富文本与投票，读路径在 P1 落地。',
    phase: 'P1 · P2',
  },
  {
    icon: IconSpeakerphone,
    title: '更新日志',
    description: '草稿与发布分离，仅管理员可编辑，与反馈状态互不联动。',
    phase: 'P1 · P3',
  },
  {
    icon: IconUserOff,
    title: '匿名身份',
    description: '默认全开的匿名读写，登录后在同一事务内合并匿名数据。',
    phase: 'P2 · P3',
  },
]
</script>

<template>
  <div class="container">
    <section class="hero">
      <p class="eyebrow"><IconChecklist :size="15" :stroke-width="2" /> P0 骨架已就绪</p>
      <h1>让每一条反馈，<br />都有迹可循。</h1>
      <p class="hero-lead">
        集中收集用户意见、公开回应进展、按版本发布更新日志。前后端分离、匿名优先、
        单机可部署。
      </p>
      <div class="hero-actions">
        <a class="button button-primary" href="#health">
          查看服务状态
          <IconArrowUpRight :size="16" :stroke-width="2" />
        </a>
        <RouterLink class="button button-ghost" to="/changelog">浏览更新日志</RouterLink>
      </div>
    </section>

    <section id="health" class="health-panel" aria-live="polite">
      <div class="health-head">
        <div>
          <h2>运行状态</h2>
          <p class="muted">前端经由 Vite 的 <code>/api</code> 代理访问后端健康检查。</p>
        </div>
        <span class="health-badge" :class="`is-${state}`">
          <IconLoader2 v-if="state === 'loading'" class="spin" :size="14" :stroke-width="2" />
          <IconCircleCheck v-else-if="state === 'ok'" :size="14" :stroke-width="2" />
          <IconCloudOff v-else :size="14" :stroke-width="2" />
          {{ state === 'loading' ? '检测中' : state === 'ok' ? '服务正常' : '连接失败' }}
        </span>
      </div>

      <dl v-if="health" class="health-grid">
        <div>
          <dt>应用</dt>
          <dd>{{ health.name }}</dd>
        </div>
        <div>
          <dt>版本</dt>
          <dd>v{{ health.version }}</dd>
        </div>
        <div>
          <dt>数据库</dt>
          <dd><span class="dot dot-ok" />{{ health.database }}</dd>
        </div>
        <div>
          <dt>环境</dt>
          <dd>{{ health.environment }}</dd>
        </div>
      </dl>

      <div v-else-if="state === 'error'" class="health-error">
        <p>{{ errorMessage }}</p>
        <button class="button button-ghost button-small" type="button" @click="loadHealth">
          <IconRefresh :size="15" :stroke-width="2" />
          重试
        </button>
      </div>
    </section>

    <section class="modules">
      <div class="section-head">
        <h2>模块进度</h2>
        <p class="muted">P0 只交付骨架，业务能力按阶段增量落地。</p>
      </div>
      <div class="module-grid">
        <article v-for="item in modules" :key="item.title" class="module-card">
          <span class="module-icon"><component :is="item.icon" :size="20" :stroke-width="1.8" /></span>
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
          <span class="phase-tag">{{ item.phase }}</span>
        </article>
      </div>
    </section>
  </div>
</template>
