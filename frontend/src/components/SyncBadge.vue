<template>
  <RouterLink v-if="pending" to="/sync" class="flex min-h-[40px] items-center gap-2 rounded-full bg-[#FBEFDF] px-3 text-sm font-semibold text-[#8A4A0C]" data-testid="sync-badge">
    <span class="num rounded-full bg-[#8A4A0C] px-2 text-xs text-white">{{ pending }}</span>
    {{ online ? __('بيتبعت…') : __('مستني النت') }}
  </RouterLink>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { pending } from '@/lib/queue'

const online = ref(navigator.onLine)
const set = () => (online.value = navigator.onLine)
onMounted(() => {
  window.addEventListener('online', set)
  window.addEventListener('offline', set)
})
onBeforeUnmount(() => {
  window.removeEventListener('online', set)
  window.removeEventListener('offline', set)
})
</script>
