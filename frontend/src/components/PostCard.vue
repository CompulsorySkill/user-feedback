<script setup lang="ts">
import { IconMessage, IconThumbUp, IconUser } from '@tabler/icons-vue'
import { RouterLink } from 'vue-router'
import StatusBadge from '@/components/StatusBadge.vue'
import type { PostSummary } from '@/api/types'
import { formatRelative } from '@/utils/date'

defineProps<{ post: PostSummary }>()
</script>

<template>
  <article class="post-card">
    <div class="post-card-head">
      <StatusBadge :status="post.status" />
      <span class="post-time">{{ formatRelative(post.created_at) }}</span>
    </div>

    <RouterLink :to="`/post/${post.id}`" class="post-title-link">
      <h3>{{ post.title }}</h3>
    </RouterLink>

    <p v-if="post.excerpt" class="post-excerpt">{{ post.excerpt }}</p>

    <div class="post-card-foot">
      <span class="meta-item">
        <IconUser :size="14" :stroke-width="1.8" />
        {{ post.author_name ?? '匿名用户' }}
      </span>
      <span class="meta-item">
        <IconThumbUp :size="14" :stroke-width="1.8" />
        {{ post.vote_count }} 票
      </span>
      <span class="meta-item">
        <IconMessage :size="14" :stroke-width="1.8" />
        {{ post.comment_count }} 条评论
      </span>
    </div>
  </article>
</template>
