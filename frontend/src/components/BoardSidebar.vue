<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Board } from '@/api/types'

defineProps<{
  boards: Board[]
  activeSlug?: string | null
  totalCount: number
}>()
</script>

<template>
  <aside v-if="boards.length" class="board-sidebar">
    <p class="sidebar-title">全部看板</p>
    <nav class="board-nav" aria-label="看板列表">
      <RouterLink to="/" class="board-nav-item" :class="{ 'is-active': !activeSlug }">
        <span class="board-nav-name">全部反馈</span>
        <span class="board-nav-count">{{ totalCount }}</span>
      </RouterLink>
      <RouterLink
        v-for="item in boards"
        :key="item.slug"
        :to="`/b/${item.slug}`"
        class="board-nav-item"
        :class="{ 'is-active': item.slug === activeSlug }"
      >
        <span class="board-nav-name">{{ item.name }}</span>
        <span class="board-nav-count">{{ item.post_count }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>
