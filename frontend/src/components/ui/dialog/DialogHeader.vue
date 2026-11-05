<script setup lang="ts">
import { cn } from 'cn';
import type { HTMLAttributes } from 'vue';

const props = defineProps<{
  class?: HTMLAttributes['class'];
}>();
</script>

<template>
  <div data-slot="dialog-header" :class="cn('gap-1 flex flex-col', props.class)">
    <slot />
  </div>
</template>
