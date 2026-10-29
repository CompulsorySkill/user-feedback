<script setup lang="ts">
import {
  IconDeviceFloppy,
  IconLoader2,
  IconPencil,
  IconPlus,
  IconRefresh,
  IconTrash,
  IconX,
} from '@tabler/icons-vue';
import { onMounted, ref } from 'vue';

import { createBoard, deleteBoard, listAdminBoards, updateBoard } from '@/api/boards';
import { ApiError } from '@/api/client';
import type { Board } from '@/api/types';

interface BoardForm {
  slug: string;
  name: string;
  description: string;
  is_public: boolean;
  allow_guest_posting: boolean;
  allow_guest_voting: boolean;
  allow_guest_commenting: boolean;
}

const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])$/;

function emptyForm(): BoardForm {
  return {
    slug: '',
    name: '',
    description: '',
    is_public: true,
    allow_guest_posting: true,
    allow_guest_voting: true,
    allow_guest_commenting: true,
  };
}

const boards = ref<Board[]>([]);
const loading = ref(true);
const errorMessage = ref('');
const actionError = ref('');

const formOpen = ref(false);
const editingId = ref<number | null>(null);
const form = ref<BoardForm>(emptyForm());
const saving = ref(false);
const deletingId = ref<number | null>(null);

async function load(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    boards.value = await listAdminBoards();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : '加载看板失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
}

function openCreate(): void {
  editingId.value = null;
  form.value = emptyForm();
  formOpen.value = true;
  actionError.value = '';
}

function openEdit(board: Board): void {
  editingId.value = board.id;
  form.value = {
    slug: board.slug,
    name: board.name,
    description: board.description ?? '',
    is_public: board.is_public,
    allow_guest_posting: board.allow_guest_posting,
    allow_guest_voting: board.allow_guest_voting,
    allow_guest_commenting: board.allow_guest_commenting,
  };
  formOpen.value = true;
  actionError.value = '';
}

function closeForm(): void {
  formOpen.value = false;
  editingId.value = null;
  actionError.value = '';
}

async function save(): Promise<void> {
  if (saving.value) return;
  actionError.value = '';
  const slug = form.value.slug.trim().toLowerCase();
  const name = form.value.name.trim();
  if (!SLUG_RE.test(slug) || slug.length < 2) {
    actionError.value = '标识需为 2–64 位小写字母、数字或中划线，且不能以中划线开头或结尾。';
    return;
  }
  if (!name) {
    actionError.value = '请填写看板名称。';
    return;
  }

  saving.value = true;
  const payload = {
    slug,
    name,
    description: form.value.description.trim() || null,
    is_public: form.value.is_public,
    allow_guest_posting: form.value.allow_guest_posting,
    allow_guest_voting: form.value.allow_guest_voting,
    allow_guest_commenting: form.value.allow_guest_commenting,
  };
  try {
    if (editingId.value === null) {
      await createBoard(payload);
    } else {
      await updateBoard(editingId.value, payload);
    }
    closeForm();
    await load();
  } catch (error) {
    actionError.value = error instanceof ApiError ? error.message : '保存失败，请稍后重试。';
  } finally {
    saving.value = false;
  }
}

async function remove(board: Board): Promise<void> {
  if (deletingId.value !== null) return;
  const warning =
    board.post_count > 0
      ? `看板「${board.name}」下有 ${board.post_count} 条反馈，删除会一并清理这些反馈、评论与投票，且不可撤销。确认删除？`
      : `确认删除看板「${board.name}」？此操作不可撤销。`;
  if (!window.confirm(warning)) return;
  deletingId.value = board.id;
  actionError.value = '';
  try {
    await deleteBoard(board.id, board.post_count > 0);
    if (editingId.value === board.id) closeForm();
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
    <header class="page-header page-header-row">
      <div>
        <p class="eyebrow">Admin</p>
        <h1>看板管理</h1>
        <p class="hero-lead">新增、编辑或删除看板；删除看板会连带清理其反馈、评论与投票。</p>
      </div>
      <button class="button button-primary" type="button" @click="openCreate">
        <IconPlus :size="16" :stroke-width="2" />
        新建看板
      </button>
    </header>

    <div v-if="actionError" class="inline-error admin-action-error">
      {{ actionError }}
    </div>

    <form v-if="formOpen" class="compose board-admin-form" @submit.prevent="save">
      <div class="board-admin-form-head">
        <h2>{{ editingId === null ? '新建看板' : '编辑看板' }}</h2>
        <button type="button" class="form-close" aria-label="关闭表单" @click="closeForm">
          <IconX :size="15" :stroke-width="2" />
        </button>
      </div>

      <div class="board-admin-fields">
        <label class="field">
          <span class="field-label">标识（slug）</span>
          <input
            v-model="form.slug"
            class="field-input"
            maxlength="64"
            placeholder="product"
            autocomplete="off"
          />
          <span class="board-admin-hint">用于地址 /b/&lt;slug&gt;，仅小写字母、数字与中划线。</span>
        </label>

        <label class="field">
          <span class="field-label">名称</span>
          <input v-model="form.name" class="field-input" maxlength="128" placeholder="功能建议" />
        </label>
      </div>

      <label class="field">
        <span class="field-label">描述</span>
        <textarea
          v-model="form.description"
          class="field-textarea"
          maxlength="500"
          rows="2"
          placeholder="这个看板收集什么类型的反馈？"
        />
      </label>

      <div class="board-admin-flags">
        <label class="env-toggle">
          <input v-model="form.is_public" type="checkbox" />
          公开看板
        </label>
        <label class="env-toggle">
          <input v-model="form.allow_guest_posting" type="checkbox" />
          允许匿名发布
        </label>
        <label class="env-toggle">
          <input v-model="form.allow_guest_voting" type="checkbox" />
          允许匿名投票
        </label>
        <label class="env-toggle">
          <input v-model="form.allow_guest_commenting" type="checkbox" />
          允许匿名评论
        </label>
      </div>

      <div class="compose-actions">
        <span class="board-admin-hint">未公开看板不会出现在前台列表，但管理员仍可直接访问。</span>
        <div class="compose-buttons">
          <button class="button button-ghost" type="button" @click="closeForm">取消</button>
          <button class="button button-primary" type="submit" :disabled="saving">
            <IconLoader2 v-if="saving" class="spin" :size="16" :stroke-width="2" />
            <IconDeviceFloppy v-else :size="16" :stroke-width="2" />
            保存
          </button>
        </div>
      </div>
    </form>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载看板…
    </p>

    <div v-else-if="errorMessage" class="inline-error">
      <span>{{ errorMessage }}</span>
      <button class="button button-ghost button-small" type="button" @click="load">
        <IconRefresh :size="15" :stroke-width="2" /> 重试
      </button>
    </div>

    <div v-else class="board-admin-list">
      <article v-for="board in boards" :key="board.id" class="board-admin-item">
        <div class="board-admin-main">
          <div class="board-admin-title">
            <h2>{{ board.name }}</h2>
            <span class="board-slug">/{{ board.slug }}</span>
            <span v-if="!board.is_public" class="anon-badge">未公开</span>
          </div>
          <p class="board-admin-desc">{{ board.description ?? '暂无描述' }}</p>
          <div class="board-admin-meta">
            <span>{{ board.post_count }} 条反馈</span>
            <span>{{ board.allow_guest_posting ? '允许匿名发布' : '仅登录发布' }}</span>
            <span>{{ board.allow_guest_voting ? '允许匿名投票' : '仅登录投票' }}</span>
            <span>{{ board.allow_guest_commenting ? '允许匿名评论' : '仅登录评论' }}</span>
          </div>
        </div>
        <div class="board-admin-actions">
          <button class="button button-ghost button-small" type="button" @click="openEdit(board)">
            <IconPencil :size="14" :stroke-width="2" /> 编辑
          </button>
          <button
            class="button button-ghost button-small button-danger"
            type="button"
            :disabled="deletingId !== null"
            :title="board.post_count > 0 ? '删除看板并级联清理其反馈' : '删除看板'"
            @click="remove(board)"
          >
            <IconLoader2 v-if="deletingId === board.id" class="spin" :size="14" :stroke-width="2" />
            <IconTrash v-else :size="14" :stroke-width="2" />
            删除
          </button>
        </div>
      </article>

      <p v-if="boards.length === 0" class="board-admin-empty">
        还没有看板，点击右上角「新建看板」开始。
      </p>
    </div>
  </div>
</template>
