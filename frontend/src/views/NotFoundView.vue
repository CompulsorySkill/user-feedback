<script setup lang="ts">
import { IconRouteOff } from '@tabler/icons-vue';
</script>

<template>
  <div class="container">
    <section class="placeholder">
      <span class="placeholder-icon"><IconRouteOff :size="28" :stroke-width="1.6" /></span>
      <h1>页面不存在</h1>
      <p>你访问的页面不存在，或没有访问权限。</p>
      <RouterLink class="button button-ghost" to="/">浏览全部反馈</RouterLink>
    </section>
  </div>
</template>
