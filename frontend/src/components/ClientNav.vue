<template>
  <nav aria-label="القائمة" class="fixed inset-x-0 bottom-0 mx-auto grid max-w-md grid-cols-5 border-t border-[#E2E5E0] bg-white px-1 pb-[18px] pt-1.5">
    <RouterLink
      v-for="t in tabs"
      :key="t.to"
      :to="t.to"
      class="flex min-h-[48px] flex-col items-center justify-center gap-0.5 text-xs"
      :class="active === t.key ? 'font-bold text-[#1D6B57]' : 'font-medium text-[#5B6661]'"
      :data-testid="`tab-${t.key}`"
    >
      <span aria-hidden="true" class="h-1 w-[22px] rounded" :class="active === t.key ? 'bg-[#1D6B57]' : 'bg-transparent'"></span>
      {{ t.label }}
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ project: string; active: string }>()
const base = computed(() => `/c/${encodeURIComponent(props.project)}`)
const tabs = computed(() => [
  { key: 'home', label: 'الرئيسية', to: base.value },
  { key: 'timeline', label: 'المراحل', to: `${base.value}/timeline` },
  { key: 'gallery', label: 'الصور', to: `${base.value}/gallery` },
  { key: 'payments', label: 'الدفعات', to: `${base.value}/payments` },
  { key: 'chat', label: 'الشات', to: `${base.value}/chat` },
])
</script>
