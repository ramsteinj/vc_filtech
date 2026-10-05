import { createRouter, createWebHistory } from 'vue-router'

import DashboardView from '@/views/DashboardView.vue'

// Route guards (auth, role, LLM configured) are added in Phase 2 (specs/11 §3.1).
const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', name: 'dashboard', component: DashboardView }],
})

export default router
