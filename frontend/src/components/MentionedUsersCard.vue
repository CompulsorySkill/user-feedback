<script setup lang="ts">
import { IconAt } from '@tabler/icons-vue';
import { computed } from 'vue';

import type { CommentItem } from '@/api/comments';
import type { PostDetail } from '@/api/types';
import { collectMentions } from '@/utils/mentions';

const props = defineProps<{ post: PostDetail; comments: CommentItem[] }>();

const users = computed(() => collectMentions(props.post, props.comments));
</script>

<template>
  <section
    v-if="users.length"
    class="mt-6 rounded-lg border border-border bg-card p-4"
    aria-labelledby="mentioned-users"
  >
    <h2
      id="mentioned-users"
      class="flex items-center gap-1.5 text-sm font-semibold text-foreground"
    >
      <IconAt :size="16" :stroke-width="2" />
      提及的用户
    </h2>
    <ul class="mt-3 space-y-2">
      <li v-for="user in users" :key="user.label" class="flex flex-wrap items-center gap-2">
        <span class="text-sm font-medium text-foreground">@{{ user.label }}</span>
        <span
          v-for="source in user.sources"
          :key="`${source.kind}-${source.by}`"
          class="inline-flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs text-accent-foreground"
          :title="`${source.kind} · ${source.by}`"
        >
          {{ source.kind }}
          <span class="opacity-70">· {{ source.by }}</span>
        </span>
      </li>
    </ul>
  </section>
</template>
