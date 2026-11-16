<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-28">
    <header class="px-5 pb-2 pt-5"><h1 class="text-[22px] font-bold">{{ __('المراحل') }}</h1></header>
    <p v-if="error" class="px-5 text-sm text-[#B42318]">{{ error }}</p>
    <section v-if="stages" class="flex flex-col gap-2 px-4">
      <article v-for="s in stages" :key="s.name" class="flex flex-col gap-1.5 rounded-xl bg-white px-3.5 py-3" data-testid="timeline-row">
        <div class="flex items-center justify-between gap-2">
          <span class="text-sm font-semibold">{{ s.stage_name }}</span>
          <StatusPill :status="s.status" />
        </div>
        <ProgressBar :value="s.progress" />
        <div class="flex flex-wrap justify-between gap-x-3 text-xs text-[#5B6661]">
          <span v-if="s.planned_start || s.planned_end">{{ __('المخطط: {0} ← {1}', [shortDate(s.planned_start), shortDate(s.planned_end)]) }}</span>
          <span v-if="s.actual_start">{{ __('الفعلي: {0} ← {1}', [shortDate(s.actual_start), s.actual_end ? shortDate(s.actual_end) : '…']) }}</span>
        </div>
        <span v-if="s.delay_days > 0" class="self-start rounded-full bg-[#FDE8E6] px-2 text-xs font-bold text-[#B42318]" data-testid="delay">
          {{ __('متأخرة {0} يوم', [s.delay_days]) }}
        </span>
      </article>
    </section>
    <ClientNav :project="project" active="timeline" />
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import { shortDate } from '@/lib/format'
import ProgressBar from '@/components/ProgressBar.vue'
import StatusPill from '@/components/StatusPill.vue'
import ClientNav from '@/components/ClientNav.vue'

const props = defineProps<{ project: string }>()
const project = props.project
const stages = ref<any[] | null>(null)
const error = ref('')
onMounted(async () => {
  try {
    stages.value = (await call('construction_core.api.portal.timeline', { project })).stages
  } catch (e: any) {
    error.value = e.message
  }
})
</script>
