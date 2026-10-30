<script setup lang="ts">
import { IconLoader2, IconRefresh, IconSearch } from '@tabler/icons-vue';
import { onMounted, ref } from 'vue';

import { ApiError } from '@/api/client';
import type { AdminUserItem } from '@/api/types';
import { listAdminUsers } from '@/api/users';
import { formatDateTime } from '@/utils/date';

const PAGE_SIZE = 30;

const users = ref<AdminUserItem[]>([]);
const nextCursor = ref<number | null>(null);
const loading = ref(true);
const loadingMore = ref(false);
const errorMessage = ref('');
const searchInput = ref('');
const searchQuery = ref('');
const roleFilter = ref<'' | 'user' | 'admin'>('');

async function load(): Promise<void> {
  searchQuery.value = searchInput.value.trim();
  loading.value = true;
  errorMessage.value = '';
  try {
    const page = await listAdminUsers({
      limit: PAGE_SIZE,
      q: searchQuery.value || null,
      role: roleFilter.value || null,
    });
    users.value = page.items;
    nextCursor.value = page.next_cursor ? Number(page.next_cursor) : null;
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载用户目录失败。';
  } finally {
    loading.value = false;
  }
}

async function loadMore(): Promise<void> {
  if (!nextCursor.value || loadingMore.value) return;
  loadingMore.value = true;
  try {
    const page = await listAdminUsers({
      limit: PAGE_SIZE,
      before_id: nextCursor.value,
      q: searchQuery.value || null,
      role: roleFilter.value || null,
    });
    const seen = new Set(users.value.map((item) => item.id));
    users.value = [...users.value, ...page.items.filter((item) => !seen.has(item.id))];
    nextCursor.value = page.next_cursor ? Number(page.next_cursor) : null;
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载更多失败。';
  } finally {
    loadingMore.value = false;
  }
}

async function reset(): Promise<void> {
  searchInput.value = '';
  roleFilter.value = '';
  await load();
}

onMounted(load);
</script>

<template>
  <div class="container">
    <header class="page-header">
      <p class="eyebrow">Admin</p>
      <h1>用户管理</h1>
      <p class="hero-lead">
        这里只列出登录过的账号（SSO 首次登录时自动创建）。角色由环境变量 ADMIN_EMAILS
        在每次登录时决定，因此本页只读。
      </p>
    </header>

    <form class="admin-toolbar" @submit.prevent="load">
      <label class="admin-filter">
        <span class="field-label">搜索</span>
        <input
          v-model="searchInput"
          class="field-input"
          type="search"
          maxlength="100"
          placeholder="邮箱或显示名"
        />
      </label>
      <label class="admin-filter">
        <span class="field-label">角色</span>
        <select v-model="roleFilter" class="field-input" @change="load">
          <option value="">全部角色</option>
          <option value="admin">管理员</option>
          <option value="user">普通用户</option>
        </select>
      </label>
      <button class="button button-primary" type="submit">
        <IconSearch :size="16" :stroke-width="2" /> 搜索
      </button>
      <button class="button button-ghost button-small" type="button" @click="reset">
        <IconRefresh :size="14" :stroke-width="2" /> 重置
      </button>
    </form>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载用户…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>

    <div v-else class="admin-list">
      <div v-for="user in users" :key="user.id" class="admin-item">
        <div class="admin-item-main">
          <span class="admin-item-title">{{ user.email }}</span>
          <span v-if="user.display_name" class="admin-item-sub">{{ user.display_name }}</span>
          <span v-if="user.role === 'admin'" class="admin-badge">ADMIN</span>
        </div>
        <span class="admin-item-count">
          {{ user.post_count }} 反馈 · {{ user.comment_count }} 评论
        </span>
        <time class="admin-item-count">{{ formatDateTime(user.created_at) }}</time>
      </div>

      <p v-if="users.length === 0" class="admin-empty">
        {{ searchQuery ? `没有找到匹配「${searchQuery}」的用户。` : '还没有登录过的用户。' }}
      </p>

      <div v-if="nextCursor" class="load-more">
        <button class="button button-ghost" type="button" :disabled="loadingMore" @click="loadMore">
          <IconLoader2 v-if="loadingMore" class="spin" :size="16" :stroke-width="2" />
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>
