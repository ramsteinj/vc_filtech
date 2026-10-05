<script setup>
import AppNavbar from '@/components/AppNavbar.vue'
</script>

<template>
  <div class="min-vh-100 d-flex flex-column">
    <AppNavbar />
    <main class="container-fluid py-4 flex-grow-1">
      <slot />
    </main>
  </div>
</template>
