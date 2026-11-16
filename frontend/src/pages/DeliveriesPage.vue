<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-10">
    <PageHeader :title="__('استلام خامات في الموقع')" :back="`/projects/${encodeURIComponent(name)}`" />
    <p v-if="error" class="px-5 text-sm text-[#B42318]" data-testid="error">{{ error }}</p>
    <p v-if="loaded && !orders.length" class="px-5 text-sm text-[#5B6661]" data-testid="no-deliveries">{{ __('مفيش توريدات مستنية استلام.') }}</p>
    <article v-for="o in orders" :key="o.name" class="mx-4 mb-3 flex flex-col gap-2 rounded-[14px] bg-white p-3.5" data-testid="delivery">
      <div class="flex items-center justify-between">
        <span class="text-base font-bold">{{ o.supplier }}</span>
        <span class="num text-xs text-[#5B6661]" dir="ltr">{{ o.name }}</span>
      </div>
      <span class="text-xs text-[#5B6661]">{{ __('مطلوب يوم') }} <span class="num">{{ o.schedule_date }}</span></span>
      <ul class="text-sm">
        <li v-for="(it, i) in o.items" :key="i" class="flex justify-between border-b border-[#F0F1EE] py-1">
          <span>{{ it.item_name }}</span>
          <span class="num" dir="ltr">{{ it.qty - it.received_qty }} {{ it.uom }}</span>
        </li>
      </ul>
      <template v-if="done[o.name]">
        <p class="text-sm font-semibold text-[#1D6B57]" data-testid="received">{{ __('اتسجل الاستلام ✓') }} <span class="num" dir="ltr">{{ done[o.name] }}</span></p>
      </template>
      <template v-else>
        <label class="flex min-h-[48px] cursor-pointer items-center justify-center rounded-xl border border-dashed border-[#1D6B57] text-sm font-semibold text-[#1D6B57]">
          {{ photos[o.name] ? __('اتصورت ✓ (غيّر الصورة)') : __('صوّر إذن التسليم') }}
          <input type="file" accept="image/*" capture="environment" class="hidden" data-testid="delivery-photo" @change="pick(o.name, $event)" />
        </label>
        <button class="min-h-[48px] rounded-xl bg-[#1D6B57] font-bold text-white disabled:opacity-50" :disabled="!photos[o.name] || busy === o.name" data-testid="confirm-delivery" @click="confirm(o.name)">
          {{ busy === o.name ? __('بيتسجل…') : __('تأكيد الاستلام') }}
        </button>
      </template>
    </article>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { call } from '@/lib/api'
import { resizePhoto } from '@/lib/media'
import PageHeader from '@/components/PageHeader.vue'

const props = defineProps<{ name: string }>()
const name = props.name
const orders = ref<any[]>([])
const loaded = ref(false)
const error = ref('')
const busy = ref('')
const photos = reactive<Record<string, string>>({})
const done = reactive<Record<string, string>>({})

async function load() {
  try {
    orders.value = await call('construction_core.procurement.open_deliveries', { project: name })
    loaded.value = true
  } catch (e: any) {
    error.value = e.message
  }
}

function toDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result as string)
    r.onerror = reject
    r.readAsDataURL(blob)
  })
}

async function pick(po: string, ev: Event) {
  const file = (ev.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    photos[po] = await toDataUrl(await resizePhoto(file)) // small JPEG, no EXIF
  } catch (e: any) {
    error.value = e.message
  }
}

async function confirm(po: string) {
  busy.value = po
  error.value = ''
  try {
    done[po] = await call('construction_core.procurement.confirm_delivery', { purchase_order: po, photo: photos[po] }, true)
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = ''
  }
}

onMounted(load)
</script>
