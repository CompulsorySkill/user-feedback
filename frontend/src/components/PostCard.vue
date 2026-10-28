<script setup lang="ts">
import { IconMessage } from '@tabler/icons-vue'
import { RouterLink } from 'vue-router'
import AuthorTag from '@/components/AuthorTag.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import TagList from '@/components/TagList.vue'
import VoteButton from '@/components/VoteButton.vue'
import type { PostSummary } from '@/api/types'
import { formatDateTime, formatRelative } from '@/utils/date'

withDefaults(defineProps<{ post: PostSummary; showBoard?: boolean }>(), {
  showBoard: false,
})
</script>

<template>
  <article class="post-card">
    <div class="post-card-head">
      <StatusBadge :status="post.status" />
      <RouterLink
        v-if="showBoard"
        :to="`/b/${post.board_slug}`"
        class="post-board-chip"
        :title="`前往看板：${post.board_name}`"
      >
        {{ post.board_name }}
      </RouterLink>
      <span class="post-time" :title="formatDateTime(post.created_at)">
        {{ formatRelative(post.created_at) }}
      </span>
    </div>

    <RouterLink :to="`/post/${post.id}`" class="post-title-link">
      <h3>{{ post.title }}</h3>
    </RouterLink>

    <p v-if="post.excerpt" class="post-excerpt">{{ post.excerpt }}</p>

    <TagList v-if="post.tags.length" :tags="post.tags" class="post-card-tags" />

    <div class="post-card-foot">
      <div class="post-card-meta">
        <AuthorTag :post="post" />
        <span class="meta-item">
          <IconMessage :size="14" :stroke-width="1.8" />
          {{ post.comment_count }} 条评论
        </span>
      </div>
      <VoteButton :post-id="post.id" :initial-count="post.vote_count" compact />
    </div>
  </article>
</template>
