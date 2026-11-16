<template>
  <header class="flex items-center gap-2 px-4 pb-2 pt-4">
    <RouterLink
      v-if="back"
      :to="back"
      aria-label="رجوع"
      class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[#E2E5E0] bg-white"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#17201D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18l6-6-6-6" /></svg>
    </RouterLink>
    <div class="flex min-w-0 flex-col">
      <h1 class="truncate text-[19px] font-bold">{{ title }}</h1>
      <span v-if="subtitle" class="truncate text-xs text-[#5B6661]">{{ subtitle }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ title: string; subtitle?: string; back?: string }>()
</script>
