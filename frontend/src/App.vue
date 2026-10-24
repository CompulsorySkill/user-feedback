<script setup lang="ts">
import { IconMessageCircle, IconSpeakerphone } from '@tabler/icons-vue'
import { RouterLink, RouterView } from 'vue-router'
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
          <RouterLink to="/" class="nav-link">反馈</RouterLink>
          <RouterLink to="/changelog" class="nav-link">更新日志</RouterLink>
        </nav>

        <div class="header-meta">
          <span class="env-pill">本地开发</span>
          <span class="identity">匿名访问</span>
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
