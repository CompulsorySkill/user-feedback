<script setup lang="ts">
import { IconMessageCircle, IconMoon, IconSun } from '@tabler/icons-vue';
import { useDark, useToggle } from '@vueuse/core';
import { defineAsyncComponent, onMounted, onUnmounted } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';

import { site } from '@/config/site';
import { useAuthStore } from '@/stores/auth';

// 弹窗只在真正需要时才加载，避免 reka-ui 进首屏 bundle。
const ConfirmDialog = defineAsyncComponent(() => import('@/components/ConfirmDialog.vue'));

const auth = useAuthStore();
const route = useRoute();
const isDark = useDark();
const toggleDark = useToggle(isDark);

function onSessionChanged(): void {
  void auth.hydrate();
}

onMounted(() => {
  window.addEventListener('feedback:auth-refreshed', onSessionChanged);
  window.addEventListener('feedback:auth-expired', onSessionChanged);
  void auth.hydrate();
});

onUnmounted(() => {
  window.removeEventListener('feedback:auth-refreshed', onSessionChanged);
  window.removeEventListener('feedback:auth-expired', onSessionChanged);
});
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="container header-inner">
        <RouterLink class="brand" to="/">
          <span class="brand-mark"><IconMessageCircle :size="20" :stroke-width="2" /></span>
          <span class="brand-name">{{ site.name }}</span>
        </RouterLink>

        <nav class="site-nav" aria-label="主导航">
          <RouterLink to="/" class="nav-link">反馈</RouterLink>
          <RouterLink to="/changelog" class="nav-link">更新日志</RouterLink>
          <RouterLink v-if="auth.isAdmin" to="/admin/boards" class="nav-link">
            看板管理
          </RouterLink>
          <RouterLink v-if="auth.isAdmin" to="/admin/tags" class="nav-link"> 标签管理 </RouterLink>
          <RouterLink v-if="auth.isAdmin" to="/admin/users" class="nav-link"> 用户管理 </RouterLink>
          <RouterLink v-if="auth.isAdmin" to="/admin/audit" class="nav-link"> 审计日志 </RouterLink>
        </nav>

        <div class="header-meta">
          <button
            type="button"
            class="theme-toggle"
            :aria-label="isDark ? '切换到浅色模式' : '切换到深色模式'"
            :title="isDark ? '切换到浅色模式' : '切换到深色模式'"
            @click="toggleDark()"
          >
            <IconSun v-if="isDark" :size="18" />
            <IconMoon v-else :size="18" />
          </button>
          <template v-if="auth.isAuthenticated">
            <span class="identity">{{ auth.displayName }}</span>
            <span v-if="auth.isAdmin" class="admin-badge">ADMIN</span>
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

    <ConfirmDialog />
  </div>
</template>
