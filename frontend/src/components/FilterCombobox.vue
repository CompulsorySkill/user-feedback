<script setup lang="ts">
import { IconCheck, IconChevronDown, IconX } from '@tabler/icons-vue';
import {
  ComboboxAnchor,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxItemIndicator,
  ComboboxPortal,
  ComboboxRoot,
  ComboboxTrigger,
  ComboboxViewport,
} from 'reka-ui';
import { computed } from 'vue';

import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface FilterOption {
  value: string;
  label: string;
  hint?: string | number;
}

const props = withDefaults(
  defineProps<{
    /** 触发器文案，例如「状态」「标签」。 */
    label: string;
    modelValue: string[];
    options: FilterOption[];
    multiple?: boolean;
    searchPlaceholder?: string;
  }>(),
  { multiple: false, searchPlaceholder: '搜索…' },
);

const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>();

const selectedLabel = computed(() => {
  const count = props.modelValue.length;
  if (!count) return props.label;
  if (count === 1) {
    const hit = props.options.find((option) => option.value === props.modelValue[0]);
    return hit ? `${props.label} · ${hit.label}` : `${props.label} · 1`;
  }
  return `${props.label} · ${count}`;
});

function onSelect(value: unknown): void {
  if (props.multiple) {
    emit('update:modelValue', Array.isArray(value) ? value.map(String) : []);
    return;
  }
  emit('update:modelValue', typeof value === 'string' && value ? [value] : []);
}

function clear(event: MouseEvent): void {
  // 触发器本身就是按钮，不阻止冒泡会把弹层打开。
  event.stopPropagation();
  event.preventDefault();
  emit('update:modelValue', []);
}
</script>

<template>
  <ComboboxRoot
    :model-value="multiple ? modelValue : (modelValue[0] ?? '')"
    :multiple="multiple"
    :reset-search-term-on-select="multiple"
    :open-on-click="true"
    @update:model-value="onSelect"
  >
    <ComboboxAnchor class="inline-flex">
      <ComboboxTrigger
        :class="
          cn(
            buttonVariants({ variant: 'outline', size: 'lg' }),
            'font-normal',
            modelValue.length && 'text-foreground',
          )
        "
        data-slot="button"
        tabindex="0"
      >
        {{ selectedLabel }}
        <span
          v-if="modelValue.length"
          class="-mr-1 inline-flex size-4 items-center justify-center rounded-sm hover:bg-muted"
          role="button"
          tabindex="-1"
          :aria-label="`清除${label}筛选`"
          @click="clear"
        >
          <IconX class="size-3" :stroke-width="2" />
        </span>
        <IconChevronDown class="size-3.5 opacity-50" :stroke-width="2" />
      </ComboboxTrigger>
    </ComboboxAnchor>

    <ComboboxPortal>
      <ComboboxContent
        position="popper"
        :side-offset="4"
        class="z-50 w-[min(280px,var(--reka-combobox-trigger-width))] min-w-56 rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md"
      >
        <ComboboxInput
          :placeholder="searchPlaceholder"
          class="mb-1 w-full rounded-sm border border-input bg-input/30 px-2 py-1 text-xs/relaxed outline-none placeholder:text-muted-foreground focus-visible:border-ring"
        />
        <ComboboxViewport class="max-h-64 overflow-y-auto">
          <ComboboxEmpty class="py-4 text-center text-xs text-muted-foreground">
            没有匹配项
          </ComboboxEmpty>
          <ComboboxItem
            v-for="option in options"
            :key="option.value"
            :value="option.value"
            class="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1 text-xs/relaxed outline-none select-none data-[highlighted]:bg-muted data-[state=checked]:font-medium"
          >
            <ComboboxItemIndicator class="flex size-3.5 items-center justify-center">
              <IconCheck class="size-3.5" :stroke-width="2.5" />
            </ComboboxItemIndicator>
            <span class="flex-1 truncate">{{ option.label }}</span>
            <span v-if="option.hint !== undefined" class="text-muted-foreground">
              {{ option.hint }}
            </span>
          </ComboboxItem>
        </ComboboxViewport>
      </ComboboxContent>
    </ComboboxPortal>
  </ComboboxRoot>
</template>
