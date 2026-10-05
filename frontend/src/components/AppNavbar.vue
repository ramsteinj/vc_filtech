<script setup>
import { useAuthStore } from '@/stores/auth'

import HeaderLoginBox from './HeaderLoginBox.vue'

const auth = useAuthStore()
</script>

<template>
  <nav class="navbar navbar-expand navbar-dark bg-dark">
    <div class="container-fluid">
      <router-link class="navbar-brand" to="/">
        <i class="bi bi-funnel me-2"></i>FilTech Bid Assistant
      </router-link>
      <ul v-if="auth.isAuthenticated" class="navbar-nav me-auto">
        <li class="nav-item">
          <router-link class="nav-link" to="/" exact-active-class="active">대시보드</router-link>
        </li>
        <template v-if="auth.isAdmin">
          <li class="nav-item">
            <router-link class="nav-link" to="/admin/users" active-class="active">
              사용자
            </router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" to="/admin/settings/llm" active-class="active">
              LLM 설정
            </router-link>
          </li>
        </template>
      </ul>
      <div class="ms-auto">
        <HeaderLoginBox />
      </div>
    </div>
  </nav>
</template>
