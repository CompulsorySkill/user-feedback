<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { IconArrowLeft, IconLoader2, IconSend } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import { getPost } from '@/api/posts'
import { updatePost } from '@/api/postActions'
import type { PostDetail } from '@/api/types'
import PostEditor from '@/components/PostEditor.vue'
import { useAuthStore } from '@/stores/auth'
import type { JSONContent } from '@/types/content'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const post = ref<PostDetail | null>(null)
const loading = ref(true)
const loadError = ref('')
const title = ref('')
const editorRef = ref<InstanceType<typeof PostEditor> | null>(null)
const submitting = ref(false)
const error = ref('')

const canEdit = computed(() => {
  if (!post.value) return false
  if (auth.isAdmin) return true
  return Boolean(post.value.is_author) && post.value.status !== 'closed'
})

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    if (!auth.me) await auth.hydrate()
    post.value = await getPost(String(route.params.id ?? ''))
    title.value = post.value.title
  } catch (err) {
    loadError.value = err instanceof ApiError ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  if (!post.value || submitting.value) return
  const trimmedTitle = title.value.trim()
  if (!trimmedTitle) {
    error.value = '请填写标题'
    return
  }
  const content = editorRef.value?.getJSON() as JSONContent | null
  if (!content || editorRef.value?.isEmpty()) {
    error.value = '请填写正文'
    return
  }

  submitting.value = true
  error.value = ''
  try {
    await updatePost(post.value.id, { title: trimmedTitle, content })
    await router.push(`/post/${post.value.id}`)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '保存失败，请重试'
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container container-narrow">
    <RouterLink
      :to="post ? `/post/${post.id}` : '/'"
      class="back-link"
    >
      <IconArrowLeft :size="15" :stroke-width="2" /> 返回反馈
    </RouterLink>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载…
    </p>
    <div v-else-if="loadError" class="inline-error">{{ loadError }}</div>

    <template v-else-if="post">
      <header class="page-header">
        <p class="eyebrow">编辑反馈</p>
        <h1>编辑反馈</h1>
        <p class="muted">编辑即覆盖，不保留历史版本；已关闭的反馈仅管理员可编辑。</p>
      </header>

      <div v-if="!canEdit" class="notice notice-closed">
        你没有编辑这条反馈的权限（匿名发布或不是作者 / 已关闭）。
      </div>

      <form v-else class="compose" @submit.prevent="submit">
        <label class="field">
          <span class="field-label">标题</span>
          <input v-model="title" class="field-input" maxlength="200" />
        </label>

        <div class="field">
          <span class="field-label">正文</span>
          <PostEditor ref="editorRef" :initial-content="post.content" />
        </div>

        <p v-if="error" class="inline-error">{{ error }}</p>

        <div class="compose-actions">
          <span class="muted">当前状态：{{ post.status }}</span>
          <div class="compose-buttons">
            <RouterLink :to="`/post/${post.id}`" class="button button-ghost">取消</RouterLink>
            <button class="button button-primary" type="submit" :disabled="submitting">
              <IconLoader2 v-if="submitting" class="spin" :size="16" :stroke-width="2" />
              <IconSend v-else :size="16" :stroke-width="2" />
              保存修改
            </button>
          </div>
        </div>
      </form>
    </template>
  </div>
</template>
