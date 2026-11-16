<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-10">
    <PageHeader :title="data?.title || '…'" :subtitle="statusLabel" back="/" />
    <p v-if="error" class="mx-4 mb-2 rounded-lg bg-[#FDE8E6] px-3 py-2 text-sm text-[#B42318]" role="alert" data-testid="sign-error">{{ error }}</p>
    <section v-if="data" class="flex flex-col gap-3 px-4">
      <div class="overflow-hidden rounded-[14px] border border-[#E2E5E0] bg-white">
        <iframe :src="pdfUrl" class="h-[420px] w-full" :title="data.title"></iframe>
      </div>
      <a :href="pdfUrl" target="_blank" class="text-sm font-semibold text-[#1D6B57]">{{ __('افتح الملف في صفحة لوحده') }}</a>

      <template v-if="data.status === 'Signed'">
        <div class="rounded-[14px] bg-[#E3F0EB] p-4 text-[#14503F]" data-testid="signed-banner">
          <b>{{ __('اتوقّع ✓') }}</b>
          <p class="text-sm">{{ __('النسخة الموقّعة محفوظة ومش ممكن تتغير.') }}</p>
        </div>
        <RouterLink v-if="project" :to="`/c/${encodeURIComponent(project)}`" class="flex min-h-[48px] items-center justify-center rounded-[14px] bg-[#1D6B57] font-bold text-white" data-testid="open-project">{{ __('افتح المشروع') }}</RouterLink>
      </template>

      <template v-else-if="open">
        <section class="flex flex-col gap-2 rounded-[14px] bg-white p-3.5">
          <h2 class="text-sm font-bold">{{ __('التوقيع') }}</h2>
          <button v-if="!otpSent" class="min-h-[48px] rounded-[12px] bg-[#1D6B57] font-bold text-white" data-testid="request-otp" :disabled="busy" @click="requestOtp">
            {{ __('ابعتلي كود التوقيع') }}
          </button>
          <template v-else>
            <label class="flex flex-col gap-1 text-[13px] font-semibold">
              {{ __('الكود اللي وصلك على الإيميل (صالح 10 دقايق)') }}
              <input v-model="code" inputmode="numeric" maxlength="6" dir="ltr" class="min-h-[44px] rounded-[10px] border border-[#C9CFC9] px-3 text-center text-lg tracking-[6px]" data-testid="otp-input" />
            </label>
            <span class="text-[13px] font-semibold">{{ __('ارسم توقيعك') }}</span>
            <SignaturePad @change="signature = $event" />
            <button class="min-h-[52px] rounded-[14px] bg-[#1D6B57] text-base font-bold text-white disabled:opacity-60" data-testid="sign" :disabled="busy || code.length !== 6 || !signature" @click="doSign">
              {{ __('وقّع') }}
            </button>
            <button class="text-xs font-semibold text-[#1D6B57]" :disabled="busy" @click="requestOtp">{{ __('ابعت كود جديد') }}</button>
          </template>
        </section>
        <details class="rounded-[14px] bg-white p-3.5">
          <summary class="text-sm font-semibold">{{ __('مش موافق؟') }}</summary>
          <textarea v-model="reason" rows="3" :placeholder="__('اكتب السبب')" class="mt-2 w-full rounded-[10px] border border-[#C9CFC9] p-2 text-sm"></textarea>
          <button class="mt-2 min-h-[44px] w-full rounded-[10px] border border-[#B42318] text-sm font-semibold text-[#B42318]" :disabled="busy || !reason.trim()" @click="doDecline">{{ __('ارفض') }}</button>
        </details>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import { me } from '@/data/me'
import PageHeader from '@/components/PageHeader.vue'
import SignaturePad from '@/components/SignaturePad.vue'

const props = defineProps<{ name: string }>()
const data = ref<any>(null)
const error = ref('')
const busy = ref(false)
const otpSent = ref(false)
const code = ref('')
const signature = ref('')
const reason = ref('')
const project = ref('')

const LABELS: Record<string, string> = {
  Sent: 'مستني توقيعك',
  Viewed: 'مستني توقيعك',
  Signed: 'اتوقّع',
  Declined: 'اترفض',
  Expired: 'انتهت صلاحيته',
  Locked: 'مقفول: كلّم المكتب',
}
const statusLabel = computed(() => (data.value ? LABELS[data.value.status] || data.value.status : ''))
const open = computed(() => ['Sent', 'Viewed'].includes(data.value?.status))
const pdfUrl = computed(() => (data.value ? data.value.signed_pdf || data.value.document_pdf : ''))

async function load() {
  data.value = await call('construction_core.esign.get_request', { request: props.name })
  otpSent.value = data.value.otp_sent
}

async function run(fn: () => Promise<void>) {
  busy.value = true
  error.value = ''
  try {
    await fn()
  } catch (e: any) {
    error.value = e.message
    await load().catch(() => {})
  } finally {
    busy.value = false
  }
}

const requestOtp = () => run(async () => {
  await call('construction_core.esign.request_otp', { request: props.name }, true)
  otpSent.value = true
})
const doSign = () => run(async () => {
  const res = await call('construction_core.esign.sign', { request: props.name, code: code.value, signature: signature.value }, true)
  project.value = me.data?.roles?.subcontractor && !me.data?.roles?.client ? '' : res.project || ''
  await load()
})
const doDecline = () => run(async () => {
  await call('construction_core.esign.decline', { request: props.name, reason: reason.value }, true)
  await load()
})

onMounted(() => run(load))
</script>
