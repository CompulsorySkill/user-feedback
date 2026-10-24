<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { IconMessageCircle, IconSpeakerphone } from '@tabler/icons-vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()

function onSessionChanged(): void {
  void auth.hydrate()
}

onMounted(() => {
  window.addEventListener('feedlog:auth-refreshed', onSessionChanged)
  window.addEventListener('feedlog:auth-expired', onSessionChanged)
  void auth.hydrate()
})

onUnmounted(() => {
  window.removeEventListener('feedlog:auth-refreshed', onSessionChanged)
  window.removeEventListener('feedlog:auth-expired', onSessionChanged)
})
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="container header-inner">
        <RouterLink class="brand" to="/">
          <span class="brand-mark"><IconMessageCircle :size="20" :stroke-width="2" /></span>
          <span class="brand-name">FeedLog</span>
        </RouterLink>

        <nav class="site-nav" aria-label="主导航">
          <RouterLink to="/" class="nav-link">看板</RouterLink>
          <RouterLink to="/changelog" class="nav-link">更新日志</RouterLink>
        </nav>

        <div class="header-meta">
          <span class="env-pill">本地开发</span>
          <template v-if="auth.isAuthenticated">
            <span class="identity">{{ auth.displayName }}</span>
            <span v-if="auth.isAdmin" class="admin-badge">管理员</span>
            <button type="button" class="link-button" @click="auth.logout()">退出</button>
          </template>
          <template v-else>
            <span class="identity">匿名访问</span>
            <RouterLink
              class="login-link"
              :to="{ name: 'login', query: { redirect: route.fullPath } }"
            >
              登录
            </RouterLink>
          </template>
        </div>
      </div>
    </header>

    <main class="site-main">
      <RouterView />
    </main>

    <footer class="site-footer">
      <div class="container footer-inner">
        <span>FeedLog · 用户意见反馈系统</span>
        <span class="footer-stack">FastAPI · Vue 3.5 · Vite 8</span>
        <span class="footer-note">
          <IconSpeakerphone :size="14" :stroke-width="2" />
          字体全部本地系统栈，无第三方字体请求
        </span>
      </div>
    </footer>
  </div>
</template>
