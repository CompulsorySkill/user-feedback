<script setup lang="ts">
import { IconLoader2, IconPlus, IconRefresh, IconTrash } from '@tabler/icons-vue';
import { onMounted, ref } from 'vue';

import { ApiError } from '@/api/client';
import { createBuiltinTag, deleteTag, listAdminTags } from '@/api/tags';
import type { TagSummary } from '@/api/types';

const tags = ref<TagSummary[]>([]);
const loading = ref(true);
const errorMessage = ref('');
const actionError = ref('');
const name = ref('');
const creating = ref(false);
const deletingId = ref<number | null>(null);

async function load(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    tags.value = await listAdminTags();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载标签失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
}

async function create(): Promise<void> {
  if (creating.value) return;
  const value = name.value.trim();
  if (!value) {
    actionError.value = '请填写标签名称。';
    return;
  }
  creating.value = true;
  actionError.value = '';
  try {
    await createBuiltinTag(value);
    name.value = '';
    await load();
  } catch (error) {
    actionError.value = error instanceof ApiError ? error.message : '创建失败，请稍后重试。';
  } finally {
    creating.value = false;
  }
}

async function remove(tag: TagSummary): Promise<void> {
  if (deletingId.value !== null) return;
  const warning =
    tag.post_count > 0
      ? `标签「${tag.name}」正被 ${tag.post_count} 条反馈使用，删除后会从这些反馈上移除。确认删除？`
      : `确认删除标签「${tag.name}」？`;
  if (!window.confirm(warning)) return;
  deletingId.value = tag.id;
  actionError.value = '';
  try {
    await deleteTag(tag.id);
    await load();
  } catch (error) {
    actionError.value = error instanceof ApiError ? error.message : '删除失败，请稍后重试。';
  } finally {
    deletingId.value = null;
  }
}

onMounted(load);
</script>

<template>
  <div class="container">
    <header class="page-header">
      <p class="eyebrow">Admin</p>
      <h1>标签管理</h1>
      <p class="hero-lead">
        内置标签会出现在发布 / 编辑反馈的推荐列表中；作者也可以直接输入新标签。
      </p>
    </header>

    <form class="compose tag-admin-form" @submit.prevent="create">
      <div class="field">
        <span class="field-label">新增内置标签</span>
        <div class="tag-admin-input">
          <input
            v-model="name"
            class="field-input"
            maxlength="24"
            placeholder="例如：功能请求、性能、文档"
          />
          <button class="button button-primary" type="submit" :disabled="creating">
            <IconLoader2 v-if="creating" class="spin" :size="16" :stroke-width="2" />
            <IconPlus v-else :size="16" :stroke-width="2" />
            添加
          </button>
        </div>
        <span class="tag-hint">最多 24 个字符；同名标签会复用已有定义并转为内置。</span>
      </div>
      <p v-if="actionError" class="inline-error">{{ actionError }}</p>
    </form>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载标签…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>

    <div v-else class="tag-admin-list">
      <div v-for="tag in tags" :key="tag.id" class="tag-admin-item">
        <div class="tag-admin-main">
          <span class="tag-pill">{{ tag.name }}</span>
          <span v-if="tag.is_builtin" class="admin-badge">内置</span>
          <span v-else class="anon-badge">用户创建</span>
        </div>
        <span class="tag-admin-count">{{ tag.post_count }} 条反馈</span>
        <button
          class="button button-ghost button-small button-danger"
          type="button"
          :disabled="deletingId !== null"
          @click="remove(tag)"
        >
          <IconLoader2 v-if="deletingId === tag.id" class="spin" :size="14" :stroke-width="2" />
          <IconTrash v-else :size="14" :stroke-width="2" />
          删除
        </button>
      </div>

      <p v-if="tags.length === 0" class="tag-admin-empty">还没有标签，先添加一个内置标签吧。</p>
    </div>
  </div>
</template>
