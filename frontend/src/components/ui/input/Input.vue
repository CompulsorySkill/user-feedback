<script setup lang="ts">
import { useVModel } from '@vueuse/core';
import { cn } from 'cn';
import type { HTMLAttributes } from 'vue';

const props = withDefaults(
  defineProps<{
    defaultValue?: string | number;
    modelValue?: string | number;
    class?: HTMLAttributes['class'];
    /** default 对齐富文本编辑器（16px / 40px）；sm 用于 32px 密集行。 */
    size?: 'sm' | 'default';
  }>(),
  { size: 'default' },
);

const emits = defineEmits<{
  (e: 'update:modelValue', payload: string | number): void;
}>();

const modelValue = useVModel(props, 'modelValue', emits, {
  passive: true,
  defaultValue: props.defaultValue,
});
</script>

<template>
  <input
    v-model="modelValue"
    data-slot="input"
    :data-size="size"
    :class="
      cn(
        'bg-input/20 dark:bg-input/30 border-input focus-visible:border-ring focus-visible:ring-ring/30 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:aria-invalid:border-destructive/50 rounded-md border transition-colors file:h-6 file:text-xs/relaxed file:font-medium focus-visible:ring-2 aria-invalid:ring-2 w-full min-w-0 outline-none file:inline-flex file:border-0 file:bg-transparent file:text-foreground placeholder:text-muted-foreground disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
        'data-[size=default]:h-10 data-[size=default]:px-3 data-[size=default]:text-base data-[size=sm]:h-8 data-[size=sm]:px-2 data-[size=sm]:text-xs',
        props.class,
      )
    "
  />
</template>
