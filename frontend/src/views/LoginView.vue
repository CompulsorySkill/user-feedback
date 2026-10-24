<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { IconArrowLeft, IconLoader2, IconLogin } from '@tabler/icons-vue'
import { ApiError } from '@/api/client'
import {
  devLogin,
  getAuthCapabilities,
  ssoLogin,
  type AuthCapabilities,
} from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const caps = ref<AuthCapabilities | null>(null)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')

const token = ref('')
const email = ref('admin@example.com')
const name = ref('管理员')

const redirectTo = computed(() => {
  const raw = route.query.redirect
  if (typeof raw !== 'string' || !raw.startsWith('/') || raw.startsWith('//')) return '/'
  return raw
})

async function load(): Promise<void> {
  loading.value = true
  try {
    caps.value = await getAuthCapabilities()
    if (!auth.me) await auth.hydrate()
  } finally {
    loading.value = false
  }
}

async function loginWithSso(): Promise<void> {
  if (!token.value.trim()) {
    error.value = '请粘贴 SSO token'
    return
  }
  if (submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    // POST 提交 token，由后端下发 HttpOnly 会话；token 不进入 URL / 历史记录。
    const result = await ssoLogin(token.value.trim(), redirectTo.value)
    await auth.hydrate()
    await router.replace(result.redirect_to)
  } catch (err) {
    error.value =
      err instanceof ApiError
        ? err.status === 401
          ? 'SSO token 无效或已过期'
          : err.message
        : 'SSO 登录失败'
  } finally {
    submitting.value = false
  }
}

async function loginAsDev(): Promise<void> {
  if (!email.value.trim() || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    await devLogin(email.value.trim(), name.value.trim() || undefined)
    await auth.hydrate()
    await router.replace(redirectTo.value)
  } catch (err) {
    error.value =
      err instanceof ApiError
        ? err.status === 404
          ? '当前环境未开启快速登录，请走 SSO'
          : err.message
        : '登录失败'
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container container-narrow">
    <RouterLink to="/" class="back-link">
      <IconArrowLeft :size="15" :stroke-width="2" /> 返回全部看板
    </RouterLink>

    <header class="page-header">
      <p class="eyebrow">Login</p>
      <h1>登录</h1>
      <p class="hero-lead">
        本系统通过产品侧 SSO 跳转登录；登录后管理员可管理状态与更新日志。
      </p>
    </header>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在检查登录能力…
    </p>

    <div v-else-if="auth.isAuthenticated" class="login-card">
      <p class="login-title">
        已登录为 <strong>{{ auth.displayName }}</strong>
        <span v-if="auth.isAdmin" class="admin-badge">管理员</span>
      </p>
      <div class="login-actions">
        <RouterLink :to="redirectTo" class="button button-primary">继续</RouterLink>
        <button type="button" class="button button-ghost" @click="auth.logout()">退出登录</button>
      </div>
    </div>

    <div v-else class="login-grid">
      <section class="login-card">
        <h2>SSO 跳转</h2>
        <p class="muted">
          由产品侧签发 HS256 JWT。粘贴后经 POST 换取 HttpOnly 会话，token 不会出现在 URL
          或浏览器历史中；也兼容产品侧直接跳转
          <code>/api/sso/jwt?token=…&amp;return_to=…</code>。
        </p>
        <textarea
          v-model="token"
          class="login-token"
          rows="4"
          placeholder="粘贴 SSO 签发的 JWT"
        ></textarea>
        <button
          class="button button-primary"
          type="button"
          :disabled="submitting"
          @click="loginWithSso"
        >
          <IconLoader2 v-if="submitting" class="spin" :size="16" :stroke-width="2" />
          <IconLogin v-else :size="16" :stroke-width="2" />
          使用 SSO token 登录
        </button>
      </section>

      <section v-if="caps?.dev_login" class="login-card">
        <h2>开发环境快速登录</h2>
        <p class="muted">
          仅 `ENVIRONMENT=development` 开启；生产环境该接口返回 404。邮箱命中
          `ADMIN_EMAILS` 时即为管理员。
        </p>
        <label class="field">
          <span class="field-label">邮箱</span>
          <input v-model="email" class="field-input" type="email" maxlength="320" />
        </label>
        <label class="field">
          <span class="field-label">显示名（可选）</span>
          <input v-model="name" class="field-input" maxlength="128" />
        </label>
        <button
          class="button button-ghost"
          type="button"
          :disabled="submitting"
          @click="loginAsDev"
        >
          <IconLoader2 v-if="submitting" class="spin" :size="16" :stroke-width="2" />
          快速登录
        </button>
      </section>
    </div>

    <p v-if="error" class="inline-error login-error">{{ error }}</p>
  </div>
</template>
