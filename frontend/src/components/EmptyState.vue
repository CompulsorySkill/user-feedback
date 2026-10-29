<script setup lang="ts">
import { IconInbox } from '@tabler/icons-vue';

defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <div class="empty-state">
    <span class="empty-icon"><IconInbox :size="22" :stroke-width="1.6" /></span>
    <p class="empty-title">{{ title }}</p>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <slot />
  </div>
</template>
