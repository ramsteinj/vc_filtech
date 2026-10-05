import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useSystemStore } from '@/stores/system'
import { useToastStore } from '@/stores/toast'
import DashboardView from '@/views/DashboardView.vue'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('@/views/AdminLoginView.vue'),
  },
  { path: '/', name: 'dashboard', component: DashboardView, meta: { requiresAuth: true } },
  {
    path: '/account/password',
    name: 'change-password',
    component: () => import('@/views/ChangePasswordView.vue'),
    meta: { requiresAuth: true },
  },
  { path: '/admin', redirect: '/admin/users' },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('@/views/admin/UserAdminView.vue'),
    meta: { requiresAuth: true, admin: true },
  },
  {
    path: '/admin/settings/llm',
    name: 'admin-llm-settings',
    component: () => import('@/views/admin/LLMSettingsView.vue'),
    meta: { requiresAuth: true, admin: true },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Global guard — order follows specs/11 §3.1.
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const system = useSystemStore()

  try {
    await system.fetchStatus()
  } catch {
    // Backend unreachable: let the page render; API calls will surface the error.
  }

  if (system.loaded && !system.llmConfigured && !auth.isAdmin && to.name !== 'admin-login') {
    return {
      name: 'admin-login',
      query: { redirect: '/admin/settings/llm', reason: 'llm_not_configured' },
    }
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return {
      name: to.meta.admin ? 'admin-login' : 'login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.meta.admin && !auth.isAdmin) {
    useToastStore().error('관리자 권한이 없습니다.')
    return { name: 'dashboard' }
  }

  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
