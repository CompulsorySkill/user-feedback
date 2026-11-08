<script setup lang="ts">
import { IconCheck } from '@tabler/icons-vue';
import { reactiveOmit } from '@vueuse/core';
import { cn } from 'cn';
import type { SelectItemProps } from 'reka-ui';
import { SelectItem, SelectItemIndicator, SelectItemText, useForwardProps } from 'reka-ui';
import type { HTMLAttributes } from 'vue';

const props = withDefaults(
  defineProps<SelectItemProps & { class?: HTMLAttributes['class']; size?: 'sm' | 'default' }>(),
  { size: 'default' },
);

const delegatedProps = reactiveOmit(props, 'class', 'size');

const forwardedProps = useForwardProps(delegatedProps);
</script>

<template>
  <SelectItem
    data-slot="select-item"
    :data-size="size"
    v-bind="forwardedProps"
    :class="
      cn(
        'focus:bg-accent focus:text-accent-foreground not-data-[variant=destructive]:focus:**:text-accent-foreground gap-2 rounded-md px-2.5 py-1.5 data-[size=default]:min-h-8 data-[size=default]:text-base data-[size=sm]:min-h-8 data-[size=sm]:px-2 data-[size=sm]:text-xs [&_svg:not([class*=size-])]:size-4 *:[span]:last:flex *:[span]:last:items-center *:[span]:last:gap-2 relative flex w-full cursor-default items-center outline-hidden select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0',
        props.class,
      )
    "
  >
    <span class="pointer-events-none absolute right-2 flex items-center justify-center">
      <SelectItemIndicator>
        <slot name="indicator-icon">
          <IconCheck class="pointer-events-none" />
        </slot>
      </SelectItemIndicator>
    </span>

    <SelectItemText>
      <slot />
    </SelectItemText>
  </SelectItem>
</template>
