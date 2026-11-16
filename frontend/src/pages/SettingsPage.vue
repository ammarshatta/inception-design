<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col gap-3 px-4 pb-10">
    <PageHeader :title="__('الإعدادات')" back="/" />
    <p v-if="error" class="rounded-lg bg-[#FDE8E6] px-3 py-2 text-sm text-[#B42318]" role="alert">{{ error }}</p>

    <section class="flex flex-col gap-2 rounded-[14px] bg-white p-3.5">
      <h2 class="text-sm font-bold">{{ __('إشعارات الموبايل') }}</h2>
      <p v-if="!supported" class="text-xs text-[#5B6661]">{{ __('المتصفح ده مش بيدعم الإشعارات. على الآيفون لازم تضيف البوابة للشاشة الرئيسية الأول.') }}</p>
      <template v-else-if="s">
        <p v-if="!s.public_key" class="text-xs text-[#5B6661]">{{ __('المكتب لسه ماشغلش الإشعارات.') }}</p>
        <button v-else class="min-h-[44px] rounded-lg text-sm font-bold" :class="subscribed ? 'border border-[#E2E5E0]' : 'bg-[#1D6B57] text-white'" data-testid="push-toggle" @click="togglePush">
          {{ subscribed ? __('اقفل الإشعارات على الجهاز ده') : __('شغّل الإشعارات على الجهاز ده') }}
        </button>
        <fieldset class="flex flex-col gap-1.5">
          <legend class="mb-1 text-xs text-[#5B6661]">{{ __('ابعتلي إشعار عن:') }}</legend>
          <label v-for="c in s.categories" :key="c" class="flex min-h-[36px] items-center gap-2 text-sm">
            <input type="checkbox" :checked="!s.muted.includes(c)" :data-testid="`cat-${c}`" @change="toggleCat(c, ($event.target as HTMLInputElement).checked)" />
            {{ CAT[c] || c }}
          </label>
        </fieldset>
      </template>
    </section>

    <section class="flex flex-col gap-2 rounded-[14px] bg-white p-3.5">
      <h2 class="text-sm font-bold">{{ __('الصور') }}</h2>
      <label class="flex items-center gap-2 text-sm">
        <input v-model="wifi" type="checkbox" data-testid="wifi-only" @change="saveWifi" />
        {{ __('ارفع الصور على الواي فاي بس') }}
      </label>
      <p class="text-xs text-[#5B6661]">{{ __('الصور هتستنى في قائمة الانتظار لحد ما تتوصل بواي فاي.') }}</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import PageHeader from '@/components/PageHeader.vue'
import { __ } from '@/translate'

const CAT: Record<string, string> = {
  message: 'رسايل الشات',
  approval: 'طلبات الموافقة والتوقيع',
  selection: 'اختيارات الخامات',
  payment: 'الدفعات والتذكير',
  schedule: 'تغييرات المواعيد',
  update: 'تحديثات الموقع',
}
const s = ref<any>(null)
const error = ref('')
const subscribed = ref(false)
const supported = 'serviceWorker' in navigator && 'PushManager' in window
const wifi = ref(false)
try {
  wifi.value = localStorage.getItem('cc-wifi-only') === '1'
} catch {
  /* private mode */
}

function saveWifi() {
  try {
    localStorage.setItem('cc-wifi-only', wifi.value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

function keyBytes(b64: string) {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4)
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(raw, (c) => c.charCodeAt(0))
}

async function togglePush() {
  error.value = ''
  try {
    const reg = await navigator.serviceWorker.ready
    const existing = await reg.pushManager.getSubscription()
    if (existing) {
      await call('construction_core.push.unsubscribe', { endpoint: existing.endpoint }, true)
      await existing.unsubscribe()
      subscribed.value = false
      return
    }
    if ((await Notification.requestPermission()) !== 'granted') {
      error.value = __('الإذن مرفوض من المتصفح')
      return
    }
    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(s.value.public_key) })
    await call('construction_core.push.subscribe', { subscription: sub.toJSON(), device: navigator.userAgent.slice(0, 120) }, true)
    subscribed.value = true
  } catch (e: any) {
    error.value = e.message
  }
}

async function toggleCat(c: string, on: boolean) {
  const muted = new Set<string>(s.value.muted)
  if (on) muted.delete(c)
  else muted.add(c)
  try {
    s.value.muted = await call('construction_core.push.set_muted', { categories: [...muted] }, true)
  } catch (e: any) {
    error.value = e.message
  }
}

onMounted(async () => {
  try {
    s.value = await call('construction_core.push.settings')
    if (supported) {
      const reg = await navigator.serviceWorker.getRegistration('/portal/')
      subscribed.value = !!(await reg?.pushManager.getSubscription())
    }
  } catch (e: any) {
    error.value = e.message
  }
})
</script>
