<script setup lang="ts">
import { IconLoader2, IconRefresh, IconSearch } from '@tabler/icons-vue';
import { onMounted, ref } from 'vue';

import { ApiError } from '@/api/client';
import type { AdminUserItem } from '@/api/types';
import { listAdminUsers } from '@/api/users';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { formatDateTime } from '@/utils/date';

const PAGE_SIZE = 30;

const users = ref<AdminUserItem[]>([]);
const nextCursor = ref<number | null>(null);
const loading = ref(true);
const loadingMore = ref(false);
const errorMessage = ref('');
const searchInput = ref('');
const searchQuery = ref('');
const roleFilter = ref<'all' | 'user' | 'admin'>('all');

function onRoleChange(value: unknown): void {
  roleFilter.value = String(value ?? 'all') as 'all' | 'user' | 'admin';
  void load();
}

async function load(): Promise<void> {
  searchQuery.value = searchInput.value.trim();
  loading.value = true;
  errorMessage.value = '';
  try {
    const page = await listAdminUsers({
      limit: PAGE_SIZE,
      q: searchQuery.value || null,
      role: roleFilter.value === 'all' ? null : roleFilter.value,
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
      role: roleFilter.value === 'all' ? null : roleFilter.value,
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
  roleFilter.value = 'all';
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
        <Input
          v-model="searchInput"
          size="sm"
          type="search"
          maxlength="100"
          placeholder="邮箱或显示名"
        />
      </label>
      <label class="admin-filter">
        <span class="field-label">角色</span>
        <Select :model-value="roleFilter" @update:model-value="onRoleChange">
          <SelectTrigger size="sm" class="min-w-[200px]" aria-label="按角色筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部角色</SelectItem>
            <SelectItem value="admin">管理员</SelectItem>
            <SelectItem value="user">普通用户</SelectItem>
          </SelectContent>
        </Select>
      </label>
      <Button type="submit" variant="default" size="lg">
        <IconSearch :size="16" :stroke-width="2" /> 搜索
      </Button>
      <Button type="button" @click="reset" variant="outline" size="lg">
        <IconRefresh :size="14" :stroke-width="2" /> 重置
      </Button>
    </form>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载用户…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <Button type="button" @click="load" variant="outline" size="lg">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </Button>
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
        <Button type="button" :disabled="loadingMore" @click="loadMore" variant="ghost" size="lg">
          <IconLoader2 v-if="loadingMore" class="spin" :size="16" :stroke-width="2" />
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </Button>
      </div>
    </div>
  </div>
</template>
