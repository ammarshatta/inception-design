<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col">
    <PageHeader :title="data?.project_name || '…'" :subtitle="data ? __('الإنجاز {0}', [pct(data.weighted_progress)]) : ''" back="/" />
    <p v-if="error" class="px-5 text-sm text-[#B42318]">{{ error }}</p>
    <section v-if="data" class="flex flex-col gap-2 px-4 pb-28">
      <div class="rounded-[14px] bg-white p-3.5">
        <ProgressBar :value="data.weighted_progress" />
      </div>
      <RouterLink
        v-for="s in data.stages"
        :key="s.name"
        :to="`/stages/${encodeURIComponent(s.name)}`"
        data-testid="stage-row"
        class="flex flex-col gap-1.5 rounded-xl bg-white px-3.5 py-3 text-[#17201D]"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="text-sm font-semibold">{{ s.stage_name }}</span>
          <StatusPill :status="s.status" />
        </div>
        <div class="flex items-center gap-2">
          <div class="flex-1"><ProgressBar :value="s.progress" /></div>
          <span class="num w-10 text-left text-xs text-[#5B6661]">{{ pct(s.progress) }}</span>
        </div>
      </RouterLink>
    </section>
    <div v-if="data?.can_post" class="fixed inset-x-0 bottom-0 mx-auto max-w-md bg-[#F4F5F2] px-4 pb-5 pt-3">
      <RouterLink
        :to="`/projects/${encodeURIComponent(data.name)}/update`"
        data-testid="new-update"
        class="flex min-h-[52px] items-center justify-center rounded-[14px] bg-[#1D6B57] text-base font-bold text-white"
      >
        {{ __('+ تحديث جديد') }}
      </RouterLink>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import { pct } from '@/lib/format'
import PageHeader from '@/components/PageHeader.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import StatusPill from '@/components/StatusPill.vue'

const props = defineProps<{ name: string }>()
const data = ref<any>(null)
const error = ref('')

onMounted(async () => {
  try {
    data.value = await call('construction_core.api.portal.project_detail', { project: props.name })
  } catch (e: any) {
    error.value = e.message
  }
})
</script>
