<template>
  <div dir="rtl" lang="ar" class="h-full">
    <OfflineBanner />
    <router-view />
  </div>
</template>

<script setup lang="ts">
import OfflineBanner from '@/components/OfflineBanner.vue'
</script>
