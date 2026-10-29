<script setup lang="ts">
import { IconArrowLeft, IconLoader2, IconSend } from '@tabler/icons-vue';
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';

import { createPost, listBoards } from '@/api/boards';
import { ApiError } from '@/api/client';
import { listBuiltinTags } from '@/api/tags';
import type { Board, TagSummary } from '@/api/types';
import PostEditor from '@/components/PostEditor.vue';
import TagPicker from '@/components/TagPicker.vue';
import { useAuthStore } from '@/stores/auth';
import type { JSONContent } from '@/types/content';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const boards = ref<Board[]>([]);
const board = ref<Board | null>(null);
const boardSlug = ref('');
const selectableBoards = computed(() =>
  boards.value.filter(
    (item) => item.allow_guest_posting || auth.isAuthenticated || item.slug === board.value?.slug,
  ),
);
const canPost = computed(() =>
  Boolean(board.value && (board.value.allow_guest_posting || auth.isAuthenticated)),
);
const loading = ref(true);
const loadError = ref('');
const title = ref('');
const tags = ref<string[]>([]);
const tagSuggestions = ref<TagSummary[]>([]);
const nickname = ref('');
const attachEnvironment = ref(true);
const editorRef = ref<InstanceType<typeof PostEditor> | null>(null);
const uploading = ref(false);
const submitting = ref(false);
const submitError = ref('');

function collectEnvironment() {
  return {
    user_agent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    viewport: `${window.innerWidth}×${window.innerHeight}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

async function loadTags(): Promise<void> {
  try {
    tagSuggestions.value = await listBuiltinTags();
  } catch {
    tagSuggestions.value = [];
  }
}

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = '';
  try {
    boards.value = await listBoards();
    const routed = String(route.params.slug ?? '');
    // 看板页进来沿用 URL；否则默认第一个可访客发布的看板。
    const initial = routed
      ? boards.value.find((item) => item.slug === routed)
      : (boards.value.find((item) => item.allow_guest_posting) ?? boards.value[0]);
    if (!initial) {
      loadError.value = routed ? '看板不存在或未公开。' : '还没有可发布的看板。';
      return;
    }
    board.value = initial;
    boardSlug.value = initial.slug;
  } catch (error) {
    loadError.value =
      error instanceof ApiError
        ? error.status === 404
          ? '看板不存在或未公开。'
          : error.message
        : '加载失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
}

watch(boardSlug, (slug) => {
  const next = boards.value.find((item) => item.slug === slug);
  if (!next) return;
  board.value = next;
  void router.replace({ name: 'new-post-board', params: { slug } });
});

async function submit(): Promise<void> {
  if (submitting.value || uploading.value || !board.value || !canPost.value) return;

  const trimmedTitle = title.value.trim();
  if (!trimmedTitle) {
    submitError.value = '请填写标题';
    return;
  }
  const content = editorRef.value?.getJSON();
  if (!content || editorRef.value?.isEmpty()) {
    submitError.value = '请填写正文';
    return;
  }

  submitting.value = true;
  submitError.value = '';
  try {
    const created = await createPost(board.value.slug, {
      title: trimmedTitle,
      content: content as JSONContent,
      anonymous_name: nickname.value.trim() || null,
      environment: attachEnvironment.value ? collectEnvironment() : null,
      tags: tags.value,
    });
    await router.push(`/post/${created.id}`);
  } catch (error) {
    submitError.value = error instanceof ApiError ? error.message : '发布失败，请稍后重试。';
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  void load();
  void loadTags();
});
</script>

<template>
  <div class="container">
    <RouterLink :to="board ? `/b/${board.slug}` : '/'" class="back-link">
      <IconArrowLeft :size="15" :stroke-width="2" />
      {{ board ? board.name : '返回' }}
    </RouterLink>

    <p v-if="loading" class="loading-line">
      <IconLoader2 class="spin" :size="16" :stroke-width="2" /> 正在加载…
    </p>

    <div v-else-if="loadError" class="inline-error">{{ loadError }}</div>

    <template v-else-if="board">
      <header class="page-header">
        <p class="eyebrow">New feedback</p>
        <h1>发布反馈</h1>
        <p class="muted">匿名发布，无需登录；可自定义昵称，展示时仍会标注匿名。</p>
      </header>

      <div v-if="!canPost" class="notice notice-closed">
        该看板已关闭匿名发布，请先登录或改选其他看板。
      </div>

      <form class="compose" @submit.prevent="submit">
        <label class="field">
          <span class="field-label">发布到</span>
          <select v-model="boardSlug" class="field-input" aria-label="选择发布到哪个看板">
            <option v-for="item in selectableBoards" :key="item.slug" :value="item.slug">
              {{ item.name }}
            </option>
          </select>
        </label>

        <div class="field">
          <span class="field-label">昵称（可选）</span>
          <input
            v-model="nickname"
            class="field-input"
            type="text"
            maxlength="50"
            placeholder="例如：路过的产品经理（展示为「昵称 · 匿名」）"
          />
        </div>

        <label class="field">
          <span class="field-label">标题</span>
          <input
            v-model="title"
            class="field-input"
            type="text"
            maxlength="200"
            placeholder="一句话说明你的建议或问题"
          />
        </label>

        <div class="field">
          <span class="field-label">标签（可选）</span>
          <TagPicker v-model="tags" :suggestions="tagSuggestions" />
        </div>

        <div class="field">
          <span class="field-label">正文</span>
          <PostEditor ref="editorRef" @update:uploading="uploading = $event" />
        </div>

        <p v-if="submitError" class="inline-error">{{ submitError }}</p>

        <div class="compose-actions">
          <label class="env-toggle">
            <input v-model="attachEnvironment" type="checkbox" />
            附带浏览器 / 操作系统信息
          </label>
          <div class="compose-buttons">
            <RouterLink :to="`/b/${board.slug}`" class="button button-ghost">取消</RouterLink>
            <button
              class="button button-primary"
              type="submit"
              :disabled="submitting || uploading || !canPost"
            >
              <IconLoader2 v-if="submitting" class="spin" :size="16" :stroke-width="2" />
              <IconSend v-else :size="16" :stroke-width="2" />
              {{ submitting ? '发布中…' : uploading ? '等待上传完成…' : '发布反馈' }}
            </button>
          </div>
        </div>
      </form>
    </template>
  </div>
</template>
