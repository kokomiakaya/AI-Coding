import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../views/chat/ChatView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      component: () => import('../views/admin/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', redirect: '/admin/kb' },
        { path: 'kb', name: 'admin-kb', component: () => import('../views/admin/KbListView.vue') },
        {
          path: 'kb/:id/documents',
          name: 'admin-documents',
          component: () => import('../views/admin/KbDocumentsView.vue'),
        },
        { path: 'users', name: 'admin-users', component: () => import('../views/admin/UsersView.vue') },
        { path: 'stats', name: 'admin-stats', component: () => import('../views/admin/StatsView.vue') },
        { path: 'config', name: 'admin-config', component: () => import('../views/admin/ConfigView.vue') },
      ],
    },
    { path: '/403', name: 'forbidden', component: () => import('../views/ForbiddenView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/chat' },
  ],
})

// 路由守卫：登录校验 + 管理员权限校验
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && auth.user?.role !== 'admin') {
    return { name: 'forbidden' }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isLoggedIn) {
    return { name: 'chat' }
  }
  return true
})

export default router
