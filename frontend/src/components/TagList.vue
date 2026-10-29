<script setup lang="ts">
import type { TagRef } from '@/api/types';

defineProps<{ tags: TagRef[] }>();
</script>

<template>
  <div v-if="tags.length" class="tag-list">
    <span v-for="tag in tags" :key="tag.id" class="tag-pill">
      {{ tag.name }}
    </span>
  </div>
</template>
