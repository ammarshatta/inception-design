<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-28">
    <header class="px-5 pb-2 pt-5"><h1 class="text-[22px] font-bold">{{ __('الدفعات') }}</h1></header>
    <p v-if="error" class="px-5 text-sm text-[#B42318]">{{ error }}</p>
    <template v-if="data">
      <section class="mx-4 mb-3 grid grid-cols-3 gap-2 rounded-2xl bg-white p-3.5">
        <div class="flex flex-col"><span class="text-xs text-[#5B6661]">{{ __('قيمة العقد') }}</span><span class="num text-base font-bold">{{ money(data.total) }}</span></div>
        <div class="flex flex-col"><span class="text-xs text-[#5B6661]">{{ __('اتدفع') }}</span><span class="num text-base font-bold text-[#14503F]">{{ money(data.paid) }}</span></div>
        <div class="flex flex-col"><span class="text-xs text-[#5B6661]">{{ __('متبقي') }}</span><span class="num text-base font-bold">{{ money(data.remaining) }}</span></div>
        <span v-if="data.currency" class="col-span-3 text-xs text-[#5B6661]">{{ __('المبالغ بالـ {0}', [data.currency]) }}</span>
      </section>
      <section class="flex flex-col gap-2 px-4">
        <article
          v-for="m in data.milestones"
          :key="m.name"
          class="flex flex-col gap-2 rounded-[14px] border-2 bg-white px-3.5 py-3"
          :class="m.status === 'Due' ? 'border-[#E9B872]' : 'border-transparent'"
          data-testid="milestone"
        >
          <div class="flex items-center justify-between gap-2">
            <div class="flex min-w-0 flex-col">
              <span class="text-[15px] font-semibold">{{ m.label }}</span>
              <span v-if="m.due_date" class="text-xs text-[#5B6661]">{{ shortDate(m.due_date) }}</span>
            </div>
            <div class="flex shrink-0 flex-col items-end gap-1">
              <span class="num text-[15px] font-bold">{{ money(m.amount) }}</span>
              <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :style="pill(m.status)">{{ STATUS[m.status]?.[0] || m.status }}</span>
            </div>
          </div>
          <a
            v-if="m.has_invoice"
            :href="`/api/method/construction_core.api.portal.invoice_pdf?milestone=${encodeURIComponent(m.name)}`"
            class="text-[13px] font-semibold text-[#1D6B57]"
            data-testid="invoice-pdf"
          >{{ __('الفاتورة PDF') }}</a>
        </article>
      </section>
    </template>
    <ClientNav :project="project" active="payments" />
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import { shortDate } from '@/lib/format'
import { money } from '@/lib/money'
import ClientNav from '@/components/ClientNav.vue'

const STATUS: Record<string, [string, string, string]> = {
  Paid: ['اتدفعت', '#E3F0EB', '#14503F'],
  Due: ['مستحقة', '#FBEFDF', '#8A4A0C'],
  Invoiced: ['اتعملت فاتورة', '#E4ECF8', '#1F4687'],
  Upcoming: ['جاية', '#EEF0EC', '#4A5550'],
}
function pill(s: string) {
  const e = STATUS[s] || [s, '#EEF0EC', '#4A5550']
  return { background: e[1], color: e[2] }
}

const props = defineProps<{ project: string }>()
const project = props.project
const data = ref<any>(null)
const error = ref('')
onMounted(async () => {
  try {
    data.value = await call('construction_core.api.portal.payments', { project })
  } catch (e: any) {
    error.value = e.message
  }
})
</script>
