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
      path: '/b/:slug',
      name: 'board',
      component: () => import('@/views/BoardView.vue'),
    },
    {
      path: '/b/:slug/new',
      name: 'new-post',
      component: () => import('@/views/NewPostView.vue'),
    },
    {
      path: '/post/:id',
      name: 'post',
      component: () => import('@/views/PostDetailView.vue'),
    },
    {
      path: '/changelog',
      name: 'changelog',
      component: () => import('@/views/ChangelogListView.vue'),
    },
    {
      path: '/changelog/:id',
      name: 'changelog-detail',
      component: () => import('@/views/ChangelogDetailView.vue'),
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

const APP_NAME = 'FeedLog'

router.afterEach((to) => {
  const titles: Record<string, string> = {
    home: '反馈',
    board: '看板',
    'new-post': '发布反馈',
    post: '反馈详情',
    changelog: '更新日志',
    'changelog-detail': '更新日志',
    'not-found': '页面不存在',
  }
  const label = typeof to.name === 'string' ? titles[to.name] : undefined
  document.title = label ? `${label} · ${APP_NAME}` : APP_NAME
})

export default router
