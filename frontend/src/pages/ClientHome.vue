<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-28">
    <p v-if="error" class="p-5 text-sm text-[#B42318]">{{ error }}</p>
    <template v-if="data">
      <header class="flex flex-col gap-0.5 px-5 pb-3 pt-5">
        <span class="text-[13px] text-[#5B6661]" data-testid="greeting">{{ me.data ? __('أهلاً، {0}', [me.data.full_name]) : '' }}</span>
        <h1 class="text-lg font-bold" data-testid="client-project-name">{{ data.project_name }}</h1>
      </header>
      <section class="mx-4 flex flex-col gap-3 rounded-2xl bg-white p-[18px]">
        <div class="flex items-baseline justify-between">
          <span class="text-sm text-[#5B6661]">{{ __('نسبة الإنجاز') }}</span>
          <span v-if="data.expected_end_date" class="text-[13px] text-[#5B6661]">{{ __('التسليم المتوقع: {0}', [shortDate(data.expected_end_date)]) }}</span>
        </div>
        <span class="num text-[44px] font-bold leading-none" data-testid="client-progress">{{ pct(data.weighted_progress) }}</span>
        <ProgressBar :value="data.weighted_progress" />
        <div v-if="data.current_stage" class="text-sm">{{ __('المرحلة الحالية:') }} <strong>{{ data.current_stage }}</strong></div>
      </section>

      <RouterLink
        v-for="a in data.pending_approvals"
        :key="a.name"
        :to="`/c/${encodeURIComponent(project)}/chat`"
        class="mx-4 mt-3 flex flex-col gap-2 rounded-2xl bg-[#FBEFDF] p-4 text-[#17201D]"
      >
        <span class="text-xs font-bold text-[#8A4A0C]">{{ __('مطلوب منك') }}</span>
        <span class="text-[15px] font-semibold">{{ a.approval_title }}</span>
      </RouterLink>

      <section class="mx-4 mt-3 flex flex-col gap-3 rounded-2xl bg-white p-4">
        <div class="flex items-center justify-between">
          <span class="text-[15px] font-bold">{{ __('آخر التحديثات') }}</span>
          <RouterLink :to="`/c/${encodeURIComponent(project)}/gallery`" class="text-[13px] text-[#1D6B57]">{{ __('كل الصور') }}</RouterLink>
        </div>
        <p v-if="!data.updates.length" class="text-sm text-[#5B6661]">{{ __('مفيش تحديثات لسه.') }}</p>
        <div v-for="u in data.updates" :key="u.name" class="flex items-center gap-3" data-testid="client-update">
          <img v-if="firstPhoto(u)" :src="firstPhoto(u)" class="h-14 w-14 shrink-0 rounded-[10px] object-cover" alt="" />
          <div v-else class="h-14 w-14 shrink-0 rounded-[10px] bg-[#DCE1DB]"></div>
          <div class="flex min-w-0 flex-col gap-0.5">
            <span class="truncate text-sm font-semibold">{{ u.text || __('تحديث بالصور') }}</span>
            <span class="text-xs text-[#5B6661]">{{ u.author }} · {{ shortDate(u.creation) }} · {{ __('{0} صور', [u.media.length]) }}</span>
          </div>
        </div>
      </section>

      <RouterLink
        v-if="data.next_payment"
        :to="`/c/${encodeURIComponent(project)}/payments`"
        class="mx-4 mt-3 flex items-center justify-between rounded-2xl bg-white p-4 text-[#17201D]"
      >
        <div class="flex flex-col gap-0.5">
          <span class="text-[13px] text-[#5B6661]">{{ __('الدفعة الجاية · {0}', [data.next_payment.label]) }}</span>
          <span class="num text-xl font-bold" data-testid="next-payment">{{ money(data.next_payment.amount) }}</span>
        </div>
        <span aria-hidden="true">‹</span>
      </RouterLink>
    </template>
    <ClientNav :project="project" active="home" />
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { me } from '@/data/me'
import { call } from '@/lib/api'
import { pct, shortDate } from '@/lib/format'
import { money } from '@/lib/money'
import ProgressBar from '@/components/ProgressBar.vue'
import ClientNav from '@/components/ClientNav.vue'

const props = defineProps<{ project: string }>()
const project = props.project
const data = ref<any>(null)
const error = ref('')

function firstPhoto(u: any): string {
  return u.media.find((m: any) => m.kind === 'Photo')?.file || ''
}

me.fetch()
onMounted(async () => {
  try {
    data.value = await call('construction_core.api.portal.client_home', { project })
  } catch (e: any) {
    error.value = e.message
  }
})
</script>
