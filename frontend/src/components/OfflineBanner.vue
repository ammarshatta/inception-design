<template>
  <div v-if="servedFromCache" class="sticky top-0 z-10 bg-[#17201D] px-4 py-2 text-center text-xs text-white" role="status" data-testid="offline-banner">
    {{ __('من غير نت — آخر تحديث: {0}', [when]) }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { servedFromCache } from '@/lib/offline'

const when = computed(() => {
  if (!servedFromCache.value) return ''
  const d = new Date(servedFromCache.value)
  return d.toLocaleString('ar-EG-u-nu-latn', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
})
</script>
