<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { IconLoader2, IconRefresh, IconShieldCheck, IconTrash } from '@tabler/icons-vue'
import { listAuditLogs, runUploadCleanup } from '@/api/audit'
import { ApiError } from '@/api/client'
import type { AuditLogItem, UploadCleanupResult } from '@/api/types'
import { AUDIT_ACTIONS, auditActionLabel, formatAuditDetail } from '@/utils/audit'
import { formatDateTime } from '@/utils/date'

const PAGE_SIZE = 30

const logs = ref<AuditLogItem[]>([])
const nextCursor = ref<number | null>(null)
const loading = ref(true)
const loadingMore = ref(false)
const errorMessage = ref('')
const actionFilter = ref('')
const runningCleanup = ref(false)
const cleanupResult = ref<UploadCleanupResult | null>(null)

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const page = await listAuditLogs({ limit: PAGE_SIZE, action: actionFilter.value || null })
    logs.value = page.items
    nextCursor.value = page.next_cursor ? Number(page.next_cursor) : null
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载审计日志失败。'
  } finally {
    loading.value = false
  }
}

async function loadMore(): Promise<void> {
  if (!nextCursor.value || loadingMore.value) return
  loadingMore.value = true
  try {
    const page = await listAuditLogs({
      limit: PAGE_SIZE,
      before_id: nextCursor.value,
      action: actionFilter.value || null,
    })
    const seen = new Set(logs.value.map((item) => item.id))
    logs.value = [...logs.value, ...page.items.filter((item) => !seen.has(item.id))]
    nextCursor.value = page.next_cursor ? Number(page.next_cursor) : null
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载更多失败。'
  } finally {
    loadingMore.value = false
  }
}

async function cleanup(dryRun: boolean): Promise<void> {
  if (runningCleanup.value) return
  if (!dryRun && !window.confirm('将删除超过保留期且未被任何反馈引用的上传对象，确认执行？')) {
    return
  }
  runningCleanup.value = true
  cleanupResult.value = null
  errorMessage.value = ''
  try {
    cleanupResult.value = await runUploadCleanup({ dryRun })
    await load()
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '清理失败，请稍后重试。'
  } finally {
    runningCleanup.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container">
    <header class="page-header page-header-row">
      <div>
        <p class="eyebrow">Admin</p>
        <h1>审计日志</h1>
        <p class="hero-lead">
          记录管理员对看板、标签、更新日志、反馈状态与上传清理的操作；仅追加，不随目标对象删除。
        </p>
      </div>
      <div class="audit-actions">
        <button
          class="button button-ghost"
          type="button"
          :disabled="runningCleanup"
          title="统计可清理对象，不删除任何数据"
          @click="cleanup(true)"
        >
          <IconLoader2 v-if="runningCleanup" class="spin" :size="16" :stroke-width="2" />
          <IconShieldCheck v-else :size="16" :stroke-width="2" />
          预演清理
        </button>
        <button
          class="button button-ghost button-danger"
          type="button"
          :disabled="runningCleanup"
          @click="cleanup(false)"
        >
          <IconLoader2 v-if="runningCleanup" class="spin" :size="16" :stroke-width="2" />
          <IconTrash v-else :size="16" :stroke-width="2" />
          清理上传对象
        </button>
      </div>
    </header>

    <p v-if="cleanupResult" class="audit-result">
      清理{{ cleanupResult.dry_run ? '预演' : '执行' }}：扫描 {{ cleanupResult.scanned }} 条，
      引用中 {{ cleanupResult.referenced }} 条， {{ cleanupResult.dry_run ? '可删除' : '已删除' }}
      {{ cleanupResult.deleted }} 条， 失败 {{ cleanupResult.failed }} 条。
      <span v-if="cleanupResult.errors.length" class="audit-result-error">
        {{ cleanupResult.errors.join('；') }}
      </span>
    </p>

    <div class="audit-toolbar">
      <label class="audit-filter">
        <span class="field-label">动作</span>
        <select v-model="actionFilter" class="field-input audit-select" @change="load">
          <option value="">全部操作</option>
          <option v-for="action in AUDIT_ACTIONS" :key="action.value" :value="action.value">
            {{ action.label }}
          </option>
        </select>
      </label>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="14" :stroke-width="2" /> 刷新
      </button>
    </div>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载审计日志…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>

    <div v-else class="audit-list">
      <article v-for="entry in logs" :key="entry.id" class="audit-item">
        <div class="audit-item-head">
          <span class="audit-action">{{ auditActionLabel(entry.action) }}</span>
          <span class="audit-actor">{{ entry.actor_email ?? '系统任务' }}</span>
          <time class="audit-time">{{ formatDateTime(entry.created_at) }}</time>
        </div>
        <div class="audit-meta">
          <span v-if="entry.target_type">
            目标：{{ entry.target_type
            }}<template v-if="entry.target_id"> / {{ entry.target_id }}</template>
          </span>
          <span v-if="entry.ip">IP：{{ entry.ip }}</span>
          <span class="audit-code">{{ entry.action }}</span>
        </div>
        <p v-if="entry.detail" class="audit-detail">{{ formatAuditDetail(entry.detail) }}</p>
      </article>

      <p v-if="logs.length === 0" class="audit-empty">还没有审计记录。</p>

      <div v-if="nextCursor" class="load-more">
        <button class="button button-ghost" type="button" :disabled="loadingMore" @click="loadMore">
          <IconLoader2 v-if="loadingMore" class="spin" :size="16" :stroke-width="2" />
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>
