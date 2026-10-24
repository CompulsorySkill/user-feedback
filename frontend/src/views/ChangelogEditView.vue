<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { IconArrowLeft, IconLoader2, IconSend } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import {
  createChangelog,
  deleteChangelog,
  getChangelog,
  publishChangelog,
  unpublishChangelog,
  updateChangelog,
} from '@/api/changelogs'
import PostEditor from '@/components/PostEditor.vue'
import type { JSONContent } from '@/types/content'

const route = useRoute()
const router = useRouter()

const editingId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : null
})
const loading = ref(Boolean(editingId.value))
const loadError = ref('')
const title = ref('')
const initialContent = ref<JSONContent | null>(null)
const editorRef = ref<InstanceType<typeof PostEditor> | null>(null)
const uploading = ref(false)
const submitting = ref(false)
const error = ref('')
const published = ref(false)

async function load(): Promise<void> {
  if (!editingId.value) return
  loading.value = true
  try {
    const entry = await getChangelog(editingId.value)
    title.value = entry.title
    initialContent.value = entry.content
    published.value = entry.is_published
  } catch (err) {
    loadError.value = err instanceof ApiError ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function payload() {
  const content = editorRef.value?.getJSON()
  if (!title.value.trim()) throw new Error('请填写标题')
  if (!content || editorRef.value?.isEmpty()) throw new Error('请填写正文')
  return { title: title.value.trim(), content: content as JSONContent }
}

async function save(publishAfter = false): Promise<void> {
  if (submitting.value || uploading.value) return
  submitting.value = true
  error.value = ''
  try {
    const data = payload()
    const entry = editingId.value
      ? await updateChangelog(editingId.value, data)
      : await createChangelog(data)
    if (publishAfter) {
      await publishChangelog(entry.id)
    }
    await router.push(`/changelog/${entry.id}`)
  } catch (err) {
    error.value =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : '保存失败'
  } finally {
    submitting.value = false
  }
}

async function togglePublish(): Promise<void> {
  if (!editingId.value || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    const entry = published.value
      ? await unpublishChangelog(editingId.value)
      : await publishChangelog(editingId.value)
    published.value = entry.is_published
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '操作失败'
  } finally {
    submitting.value = false
  }
}

async function remove(): Promise<void> {
  if (!editingId.value || !window.confirm('确认删除这条更新日志？')) return
  submitting.value = true
  try {
    await deleteChangelog(editingId.value)
    await router.push('/changelog')
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '删除失败'
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container container-narrow">
    <RouterLink to="/changelog" class="back-link">
      <IconArrowLeft :size="15" :stroke-width="2" /> 全部更新日志
    </RouterLink>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载…
    </p>
    <div v-else-if="loadError" class="inline-error">{{ loadError }}</div>

    <template v-else>
      <header class="page-header">
        <p class="eyebrow">{{ editingId ? '编辑更新日志' : '新建更新日志' }}</p>
        <h1>{{ editingId ? '编辑更新日志' : '撰写更新日志' }}</h1>
        <p class="muted">
          保存为草稿后仅管理员可见；发布后匿名访客即可浏览。
        </p>
      </header>

      <form class="compose" @submit.prevent="save(false)">
        <label class="field">
          <span class="field-label">标题</span>
          <input v-model="title" class="field-input" maxlength="200" placeholder="v0.4 更新：…" />
        </label>

        <div class="field">
          <span class="field-label">正文</span>
          <PostEditor
            ref="editorRef"
            scope="changelog"
            :initial-content="initialContent"
            @update:uploading="uploading = $event"
          />
        </div>

        <p v-if="error" class="inline-error">{{ error }}</p>

        <div class="compose-actions">
          <button
            v-if="editingId"
            type="button"
            class="button button-ghost button-danger"
            :disabled="submitting"
            @click="remove"
          >
            删除
          </button>
          <div class="compose-buttons">
            <button
              v-if="editingId"
              type="button"
              class="button button-ghost"
              :disabled="submitting"
              @click="togglePublish"
            >
              {{ published ? '撤回发布' : '发布' }}
            </button>
            <button type="submit" class="button button-primary" :disabled="submitting || uploading">
              <IconLoader2 v-if="submitting" class="spin" :size="16" :stroke-width="2" />
              <IconSend v-else :size="16" :stroke-width="2" />
              保存
            </button>
          </div>
        </div>
      </form>
    </template>
  </div>
</template>
