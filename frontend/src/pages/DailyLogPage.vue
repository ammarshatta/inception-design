<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-28">
    <PageHeader :title="__('يومية الموقع')" :subtitle="form.log_date" :back="`/projects/${encodeURIComponent(name)}`" />
    <p v-if="error" class="px-5 text-sm text-[#B42318]" data-testid="error">{{ error }}</p>

    <!-- Clock in / out -->
    <section v-if="consentInfo?.enabled" class="mx-4 mb-3 flex flex-col gap-2 rounded-[14px] bg-white p-3.5" data-testid="clock-card">
      <h2 class="text-sm font-bold">{{ __('حضور وانصراف') }}</h2>
      <input v-model="worker" class="min-h-[44px] rounded-lg border border-[#E2E5E0] px-3 text-sm" :placeholder="__('اسم العامل (أو سيبه فاضي لنفسك)')" data-testid="worker" />
      <div class="flex gap-2">
        <button class="min-h-[48px] flex-1 rounded-xl bg-[#1D6B57] font-bold text-white disabled:opacity-50" :disabled="busy" data-testid="clock-in" @click="doClock('In')">{{ __('حضور') }}</button>
        <button class="min-h-[48px] flex-1 rounded-xl border border-[#1D6B57] font-bold text-[#1D6B57] disabled:opacity-50" :disabled="busy" data-testid="clock-out" @click="doClock('Out')">{{ __('انصراف') }}</button>
      </div>
      <p v-if="clockMsg" class="text-sm" :class="clockWarn ? 'text-[#B54708]' : 'text-[#1D6B57]'" data-testid="clock-msg">{{ clockMsg }}</p>
    </section>

    <!-- Daily log -->
    <section class="mx-4 flex flex-col gap-3 rounded-[14px] bg-white p-3.5">
      <div>
        <h2 class="mb-1.5 text-sm font-bold">{{ __('الجو') }}</h2>
        <div class="flex flex-wrap gap-2">
          <button v-for="w in weathers" :key="w" class="min-h-[40px] rounded-full border px-3 text-sm" :class="form.weather === w ? 'border-[#1D6B57] bg-[#1D6B57] text-white' : 'border-[#E2E5E0]'" @click="form.weather = w">{{ __(w) }}</button>
        </div>
      </div>
      <div>
        <h2 class="mb-1.5 text-sm font-bold">{{ __('العمالة') }}</h2>
        <div v-for="(m, i) in form.manpower" :key="i" class="mb-1.5 flex gap-1.5" data-testid="manpower-row">
          <input v-model="m.trade" class="min-h-[40px] min-w-0 flex-1 rounded-lg border border-[#E2E5E0] px-2 text-sm" :placeholder="__('الصنعة')" />
          <input v-model.number="m.headcount" type="number" inputmode="numeric" min="0" class="num min-h-[40px] w-16 rounded-lg border border-[#E2E5E0] px-2 text-sm" :placeholder="__('عدد')" />
          <input v-model.number="m.hours" type="number" inputmode="decimal" min="0" class="num min-h-[40px] w-16 rounded-lg border border-[#E2E5E0] px-2 text-sm" :placeholder="__('ساعات')" />
          <button class="w-8 text-[#B42318]" :aria-label="__('شيل')" @click="form.manpower.splice(i, 1)">×</button>
        </div>
        <button class="text-sm font-semibold text-[#1D6B57]" data-testid="add-manpower" @click="form.manpower.push({ trade: '', headcount: 1, hours: 8 })">{{ __('+ صنعة') }}</button>
      </div>
      <label class="flex flex-col gap-1 text-sm font-bold">{{ __('اتعمل إيه النهارده') }}
        <textarea v-model="form.work_done" rows="3" class="rounded-lg border border-[#E2E5E0] p-2 font-normal" data-testid="work-done" />
      </label>
      <label class="flex flex-col gap-1 text-sm font-bold">{{ __('مشاكل / تأخير') }}
        <textarea v-model="form.issues" rows="2" class="rounded-lg border border-[#E2E5E0] p-2 font-normal" />
      </label>
      <label class="flex items-center gap-2 text-sm">
        <input v-model="form.internal_only" type="checkbox" :true-value="1" :false-value="0" />
        {{ __('داخلي (العميل مش هيشوفه)') }}
      </label>
    </section>

    <div class="fixed inset-x-0 bottom-0 mx-auto max-w-md bg-[#F4F5F2] px-4 pb-5 pt-3">
      <button class="min-h-[52px] w-full rounded-[14px] bg-[#1D6B57] text-base font-bold text-white disabled:opacity-50" :disabled="busy" data-testid="save-log" @click="save">
        {{ saved ? __('اتحفظ ✓') : __('حفظ اليومية') }}
      </button>
    </div>

    <!-- Consent modal (shown before any location is read) -->
    <div v-if="showConsent" class="fixed inset-0 z-20 flex items-end bg-black/40" role="dialog" aria-modal="true" data-testid="consent">
      <div class="mx-auto w-full max-w-md rounded-t-2xl bg-white p-5">
        <h2 class="mb-2 text-base font-bold">{{ __('موافقة على تحديد المكان') }}</h2>
        <p class="mb-4 whitespace-pre-line text-sm text-[#5B6661]">{{ consentInfo?.text || __('هناخد مكانك مرة واحدة بس وقت الحضور والانصراف، علشان نتأكد إنك في الموقع. مش بنتابع مكانك طول اليوم.') }}</p>
        <div class="flex gap-2">
          <button class="min-h-[48px] flex-1 rounded-xl bg-[#1D6B57] font-bold text-white" data-testid="consent-accept" @click="acceptConsent">{{ __('موافق') }}</button>
          <button class="min-h-[48px] flex-1 rounded-xl border border-[#E2E5E0]" @click="showConsent = false">{{ __('مش دلوقتي') }}</button>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { call } from '@/lib/api'
import PageHeader from '@/components/PageHeader.vue'
import { __ } from '@/translate'

const props = defineProps<{ name: string }>()
const name = props.name
const weathers = ['صافي', 'حر شديد', 'مطر', 'رياح/تراب']
const form = reactive<any>({ log_date: '', weather: 'صافي', manpower: [], work_done: '', issues: '', internal_only: 0 })
const error = ref('')
const busy = ref(false)
const saved = ref(false)
const consentInfo = ref<any>(null)
const showConsent = ref(false)
const pending = ref<string | null>(null)
const worker = ref('')
const clockMsg = ref('')
const clockWarn = ref(false)

async function load() {
  try {
    const [log, c] = await Promise.all([
      call('construction_core.sitelog.get_daily_log', { project: name }),
      call('construction_core.sitelog.consent'),
    ])
    Object.assign(form, { work_done: '', issues: '', internal_only: 0 }, log)
    form.manpower = (log.manpower || []).map((m: any) => ({ trade: m.trade, crew: m.crew, supplier: m.supplier, headcount: m.headcount, hours: m.hours }))
    consentInfo.value = c
  } catch (e: any) {
    error.value = e.message
  }
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    const { log_date, weather, manpower, work_done, issues, internal_only } = form
    await call('construction_core.sitelog.save_daily_log', { project: name, data: { log_date, weather, manpower, work_done, issues, internal_only } }, true)
    saved.value = true
    setTimeout(() => (saved.value = false), 2000)
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function position(): Promise<GeolocationPosition | null> {
  if (!('geolocation' in navigator)) return Promise.resolve(null)
  return new Promise((resolve) =>
    navigator.geolocation.getCurrentPosition(resolve, () => resolve(null), { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }),
  )
}

async function doClock(event: string) {
  if (!consentInfo.value?.accepted) {
    pending.value = event
    showConsent.value = true
    return
  }
  busy.value = true
  clockMsg.value = ''
  try {
    const pos = await position() // read only now, at the moment of clocking
    const names = await call(
      'construction_core.sitelog.clock',
      {
        project: name,
        event,
        workers: [{ worker: worker.value.trim() }],
        latitude: pos?.coords.latitude,
        longitude: pos?.coords.longitude,
        accuracy_m: pos?.coords.accuracy,
        device_info: navigator.userAgent.slice(0, 140),
      },
      true,
    )
    clockWarn.value = !pos
    clockMsg.value = !pos
      ? __('اتسجل من غير مكان، هيستنى موافقة المهندس')
      : event === 'In' ? __('اتسجل الحضور ({0})', [names.length]) : __('اتسجل الانصراف ({0})', [names.length])
  } catch (e: any) {
    clockWarn.value = true
    clockMsg.value = e.message
  } finally {
    busy.value = false
  }
}

async function acceptConsent() {
  await call('construction_core.sitelog.accept_consent', { version: consentInfo.value.version }, true)
  consentInfo.value.accepted = true
  showConsent.value = false
  if (pending.value) await doClock(pending.value)
  pending.value = null
}

onMounted(load)
</script>
