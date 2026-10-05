<script setup>
// Menus by role and the top-right admin login box are added in Phase 2 (specs/11 §2).
</script>

<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <router-link class="navbar-brand" to="/">
        <i class="bi bi-funnel me-2"></i>FilTech Bid Assistant
      </router-link>
      <ul class="navbar-nav me-auto">
        <li class="nav-item">
          <router-link class="nav-link" to="/" active-class="active" exact>대시보드</router-link>
        </li>
      </ul>
    </div>
  </nav>
</template>
