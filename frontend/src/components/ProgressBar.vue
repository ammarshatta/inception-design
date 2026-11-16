<template>
  <div class="h-2 overflow-hidden rounded bg-[#E9ECE7]" role="progressbar" :aria-valuenow="value" aria-valuemin="0" aria-valuemax="100">
    <div class="h-2 rounded" :style="{ width: Math.min(100, Math.max(0, value)) + '%', background: color }"></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ value: number; color?: string }>(), { color: '#1D6B57' })
</script>
