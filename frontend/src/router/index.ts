import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/changelog',
      name: 'changelog',
      component: () => import('@/views/ChangelogListView.vue'),
    },
    {
      path: '/404',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/404',
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

// 管理员入口对非管理员返回 404，避免暴露管理功能存在。
router.beforeEach((to) => {
  if (to.meta.requiresAdmin && !useAuthStore().isAdmin) {
    return { name: 'not-found' }
  }
})

export default router
