<script setup lang="ts">
import { IconClockHour4 } from '@tabler/icons-vue'
</script>

<template>
  <div class="container">
    <section class="placeholder">
      <span class="placeholder-icon"><IconClockHour4 :size="28" :stroke-width="1.6" /></span>
      <h1>更新日志</h1>
      <p>
        列表与详情在 P1 上线。届时匿名访客只能看到已发布内容，草稿仅管理员可见。
      </p>
      <RouterLink class="button button-ghost" to="/">返回反馈</RouterLink>
    </section>
  </div>
</template>
