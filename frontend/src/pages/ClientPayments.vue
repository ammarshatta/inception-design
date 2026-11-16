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
          <template v-if="['Due', 'Invoiced'].includes(m.status) && pay">
            <p v-if="pendingFor(m.name)" class="text-xs font-semibold text-[#8A4A0C]" data-testid="pay-pending">{{ pendingFor(m.name) }}</p>
            <div v-else class="flex flex-col gap-1.5">
              <div v-if="pay.online_enabled && (pay.card || pay.wallet)" class="flex gap-2">
                <button v-if="pay.card" class="min-h-[44px] flex-1 rounded-xl bg-[#1D6B57] text-sm font-bold text-white disabled:opacity-50" :disabled="!!busy" data-testid="pay-card" @click="payOnline(m.name, 'Card')">{{ __('ادفع دلوقتي بالكارت') }}</button>
                <button v-if="pay.wallet" class="min-h-[44px] flex-1 rounded-xl border border-[#1D6B57] text-sm font-bold text-[#1D6B57] disabled:opacity-50" :disabled="!!busy" data-testid="pay-wallet" @click="payOnline(m.name, 'Wallet')">{{ __('محفظة موبايل') }}</button>
              </div>
              <details v-if="pay.bank_transfer_details || pay.instapay_details" class="text-sm">
                <summary class="cursor-pointer font-semibold text-[#1D6B57]">{{ __('حوّلت؟ ارفع الإيصال') }}</summary>
                <p v-if="pay.instapay_details" class="mt-1 whitespace-pre-line text-xs text-[#5B6661]">{{ __('إنستاباي') }}: {{ pay.instapay_details }}</p>
                <p v-if="pay.bank_transfer_details" class="mt-1 whitespace-pre-line text-xs text-[#5B6661]">{{ __('تحويل بنكي') }}: {{ pay.bank_transfer_details }}</p>
                <div class="mt-2 flex gap-2">
                  <select v-model="transferMethod" class="min-h-[40px] rounded-lg border border-[#E2E5E0] bg-white px-2 text-xs">
                    <option value="InstaPay">{{ __('إنستاباي') }}</option>
                    <option value="Bank Transfer">{{ __('تحويل بنكي') }}</option>
                  </select>
                  <label class="flex min-h-[40px] flex-1 cursor-pointer items-center justify-center rounded-lg border border-dashed border-[#1D6B57] text-xs font-semibold text-[#1D6B57]">
                    {{ busy === m.name ? __('بيترفع…') : __('صورة الإيصال') }}
                    <input type="file" accept="image/*" class="hidden" data-testid="transfer-proof" @change="uploadProof($event, m.name)" />
                  </label>
                </div>
              </details>
            </div>
          </template>
          <a
            v-for="p in receiptsFor(m.name)"
            :key="p.name"
            :href="`/api/method/construction_core.payments.online.receipt_pdf?payment=${encodeURIComponent(p.name)}`"
            class="text-[13px] font-semibold text-[#1D6B57]"
            data-testid="receipt-pdf"
          >{{ __('إيصال الدفع PDF') }}</a>
        </article>
      </section>
    </template>
    <ClientNav :project="project" active="payments" />
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { call, uploadFile } from '@/lib/api'
import { resizePhoto } from '@/lib/media'
import { __ } from '@/translate'
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
const pay = ref<any>(null)
const error = ref('')
const busy = ref('')
const transferMethod = ref('InstaPay')
const route = useRoute()

function pendingFor(milestone: string) {
  const p = pay.value?.payments.find((x: any) => x.payment_milestone === milestone && ['Pending', 'Awaiting Confirmation'].includes(x.status))
  if (!p) return ''
  return p.status === 'Pending' ? __('الدفع لسه مستني تأكيد البوابة…') : __('الإيصال وصل وهيتراجع من الحسابات')
}
function receiptsFor(milestone: string) {
  return (pay.value?.payments || []).filter((x: any) => x.payment_milestone === milestone && x.status === 'Paid')
}

async function load() {
  try {
    const ref_ = route.query.ref as string | undefined
    if (ref_) await call('construction_core.payments.online.payment_status', { reference: ref_ }).catch(() => null)
    ;[data.value, pay.value] = await Promise.all([
      call('construction_core.api.portal.payments', { project }),
      call('construction_core.payments.online.project_payments', { project }),
    ])
  } catch (e: any) {
    error.value = e.message
  }
}

async function payOnline(milestone: string, method: string) {
  busy.value = milestone
  error.value = ''
  try {
    const res = await call('construction_core.payments.online.start_checkout', { milestone, method }, true)
    window.location.href = res.url
  } catch (e: any) {
    error.value = e.message
    busy.value = ''
  }
}

async function uploadProof(ev: Event, milestone: string) {
  const file = (ev.target as HTMLInputElement).files?.[0]
  if (!file) return
  busy.value = milestone
  error.value = ''
  try {
    const blob = await resizePhoto(file)
    const up = await uploadFile(blob, 'transfer.jpg', '', '', () => {})
    await call('construction_core.payments.online.submit_transfer', { milestone, method: transferMethod.value, file_url: up.file_url }, true)
    await load()
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = ''
  }
}

onMounted(load)
</script>
