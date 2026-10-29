<script setup lang="ts">
import { IconPlus, IconX } from '@tabler/icons-vue';
import { computed, ref } from 'vue';

import type { TagSummary } from '@/api/types';

const props = withDefaults(
  defineProps<{
    modelValue: string[];
    suggestions?: TagSummary[];
    max?: number;
    disabled?: boolean;
  }>(),
  {
    suggestions: () => [],
    max: 5,
    disabled: false,
  },
);

const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>();

const draft = ref('');
const error = ref('');

const available = computed(() => {
  const selected = new Set(props.modelValue.map((name) => name.toLocaleLowerCase()));
  return props.suggestions.filter((tag) => !selected.has(tag.name.toLocaleLowerCase()));
});

function clean(value: string): string {
  return value.trim().replace(/^#+/, '').replace(/\s+/g, ' ');
}

function addTag(raw: string): void {
  if (props.disabled) return;
  const name = clean(raw);
  if (!name) {
    draft.value = '';
    return;
  }
  if (name.length > 24) {
    error.value = '单个标签不能超过 24 个字符';
    return;
  }
  if (props.modelValue.some((item) => item.toLocaleLowerCase() === name.toLocaleLowerCase())) {
    draft.value = '';
    error.value = '';
    return;
  }
  if (props.modelValue.length >= props.max) {
    error.value = `最多添加 ${props.max} 个标签`;
    return;
  }
  emit('update:modelValue', [...props.modelValue, name]);
  draft.value = '';
  error.value = '';
}

function removeTag(name: string): void {
  emit(
    'update:modelValue',
    props.modelValue.filter((item) => item !== name),
  );
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault();
    addTag(draft.value);
    return;
  }
  if (event.key === 'Backspace' && !draft.value && props.modelValue.length) {
    removeTag(props.modelValue[props.modelValue.length - 1]);
  }
}
</script>

<template>
  <div class="tag-picker" :class="{ 'is-disabled': disabled }">
    <div v-if="modelValue.length" class="tag-list tag-picker-selected">
      <span v-for="tag in modelValue" :key="tag" class="tag-pill">
        {{ tag }}
        <button
          type="button"
          class="tag-remove"
          :disabled="disabled"
          :aria-label="`移除标签 ${tag}`"
          @click="removeTag(tag)"
        >
          <IconX :size="12" :stroke-width="2.2" />
        </button>
      </span>
    </div>

    <input
      v-model="draft"
      class="field-input"
      type="text"
      maxlength="24"
      aria-label="添加标签"
      :disabled="disabled || modelValue.length >= max"
      :placeholder="
        modelValue.length >= max
          ? `已达到 ${max} 个标签上限`
          : '输入标签后按回车添加，可直接创建新标签'
      "
      @keydown="onKeydown"
      @blur="addTag(draft)"
    />

    <div v-if="available.length" class="tag-suggestions">
      <button
        v-for="tag in available"
        :key="tag.id"
        type="button"
        class="tag-suggestion"
        :disabled="disabled || modelValue.length >= max"
        @mousedown.prevent
        @click="addTag(tag.name)"
      >
        <IconPlus :size="12" :stroke-width="2" />
        {{ tag.name }}
      </button>
    </div>
  </div>
</template>
