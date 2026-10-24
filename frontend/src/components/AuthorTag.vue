<script setup lang="ts">
import { computed } from 'vue'
import { IconUser } from '@tabler/icons-vue'
import type { PostSummary } from '@/api/types'
import { authorLabel } from '@/utils/author'

const props = defineProps<{ post: PostSummary }>()

const label = computed(() => authorLabel(props.post))
</script>

<template>
  <span class="author-tag">
    <IconUser :size="14" :stroke-width="1.8" />
    <span class="author-name">{{ label }}</span>
    <span v-if="post.is_anonymous" class="anon-badge" title="匿名发布，非登录身份">匿名</span>
  </span>
</template>
