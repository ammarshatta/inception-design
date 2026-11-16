<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-10">
    <PageHeader :title="__('شغلي')" back="/" />
    <div role="tablist" class="flex gap-2 px-4 pb-3">
      <button v-for="t in tabs" :key="t.key" role="tab" :aria-selected="scope === t.key" class="min-h-[40px] rounded-full border px-4 text-sm font-semibold" :class="scope === t.key ? 'border-[#1D6B57] bg-[#1D6B57] text-white' : 'border-[#E2E5E0] bg-white'" @click="load(t.key)">{{ t.label }}</button>
    </div>
    <p v-if="error" class="px-5 text-sm text-[#B42318]">{{ error }}</p>
    <p v-if="loaded && !rows.length" class="px-5 text-sm text-[#5B6661]">{{ __('مفيش شغل متسجل لفريقك.') }}</p>
    <article v-for="r in rows" :key="r.name" class="mx-4 mb-2 flex flex-col gap-1 rounded-[14px] bg-white p-3.5" data-testid="assignment">
      <span class="text-base font-bold">{{ r.project_name }}</span>
      <span class="text-xs text-[#5B6661]">{{ r.crew }} · {{ r.from_date }} → {{ r.to_date }}</span>
      <span v-if="r.task_subject" class="text-sm">{{ r.task_subject }}</span>
      <span v-if="r.address" class="text-sm">{{ r.address }}</span>
      <a v-if="r.map_url" :href="r.map_url" target="_blank" class="text-sm font-semibold text-[#1D6B57]">{{ __('افتح على الخريطة') }}</a>
    </article>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import { cachedCall } from '@/lib/offline'
import PageHeader from '@/components/PageHeader.vue'

const tabs = [
  { key: 'today', label: 'شغلي النهارده' },
  { key: 'week', label: 'الأسبوع ده' },
]
const scope = ref('today')
const rows = ref<any[]>([])
const loaded = ref(false)
const error = ref('')
async function load(s: string) {
  scope.value = s
  try {
    rows.value = await cachedCall('construction_core.scheduling.foreman_assignments', { scope: s })
    loaded.value = true
  } catch (e: any) {
    error.value = e.message
  }
}
onMounted(() => load('today'))
</script>
