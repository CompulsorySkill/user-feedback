import { createRouter, createWebHistory } from 'vue-router'
import { site } from '@/config/site'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'feedback',
      component: () => import('@/views/AllPostsView.vue'),
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
      path: '/post/:id/edit',
      name: 'post-edit',
      component: () => import('@/views/EditPostView.vue'),
    },
    {
      path: '/admin/boards',
      name: 'admin-boards',
      component: () => import('@/views/AdminBoardsView.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/tags',
      name: 'admin-tags',
      component: () => import('@/views/AdminTagsView.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/audit',
      name: 'admin-audit',
      component: () => import('@/views/AdminAuditView.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
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
      path: '/changelog/new',
      name: 'changelog-new',
      component: () => import('@/views/ChangelogEditView.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/changelog/:id/edit',
      name: 'changelog-edit',
      component: () => import('@/views/ChangelogEditView.vue'),
      meta: { requiresAdmin: true },
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
router.beforeEach(async (to) => {
  if (!to.meta.requiresAdmin) return true
  const auth = useAuthStore()
  if (!auth.me) await auth.hydrate()
  if (!auth.isAdmin) return { name: 'not-found' }
  return true
})

router.afterEach((to) => {
  const titles: Record<string, string> = {
    feedback: '全部反馈',
    board: '看板',
    'new-post': '发布反馈',
    post: '反馈详情',
    'post-edit': '编辑反馈',
    'admin-boards': '看板管理',
    'admin-tags': '标签管理',
    'admin-audit': '审计日志',
    login: '登录',
    changelog: '更新日志',
    'changelog-detail': '更新日志',
    'changelog-new': '新建更新日志',
    'changelog-edit': '编辑更新日志',
    'not-found': '页面不存在',
  }
  const label = typeof to.name === 'string' ? titles[to.name] : undefined
  document.title = label ? `${label} · ${site.name}` : site.name
})

export default router
