<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-28">
    <PageHeader :title="__('اختياراتي')" :back="`/c/${encodeURIComponent(project)}`" />
    <p v-if="error" class="mx-4 rounded-lg bg-[#FDE8E6] px-3 py-2 text-sm text-[#B42318]" role="alert">{{ error }}</p>
    <p v-if="loaded && !rows.length" class="px-5 text-sm text-[#5B6661]">{{ __('مفيش اختيارات مطلوبة دلوقتي.') }}</p>
    <section v-for="s in rows" :key="s.name" class="mx-4 mb-3 flex flex-col gap-2.5 rounded-2xl bg-white p-3.5" data-testid="selection">
      <div class="flex items-start justify-between gap-2">
        <div class="flex flex-col">
          <span class="text-base font-bold">{{ s.title }}</span>
          <span class="text-xs text-[#5B6661]">{{ s.qty }} {{ s.uom || '' }} · {{ __('المسموح {0} للوحدة', [money(s.allowance_per_unit)]) }}</span>
        </div>
        <span v-if="s.due_date && !locked(s)" class="shrink-0 rounded-full bg-[#FBEFDF] px-2 py-0.5 text-xs font-semibold text-[#8A4A0C]">{{ __('قبل {0}', [shortDate(s.due_date)]) }}</span>
        <span v-else-if="locked(s)" class="shrink-0 rounded-full bg-[#E3F0EB] px-2 py-0.5 text-xs font-semibold text-[#14503F]">{{ s.status === 'Awaiting Signature' ? __('مستني توقيعك') : __('اتعمد') }}</span>
      </div>
      <button
        v-for="o in s.options"
        :key="o.name"
        class="flex items-center gap-3 rounded-xl border-2 p-2 text-start"
        :class="s.chosen_option === o.name ? 'border-[#1D6B57] bg-[#F3FAF7]' : 'border-[#E2E5E0]'"
        :disabled="locked(s) || busy"
        data-testid="option"
        @click="choose(s, o)"
      >
        <img v-if="o.images[0]" :src="o.images[0]" class="h-16 w-16 shrink-0 rounded-lg object-cover" alt="" />
        <div v-else class="h-16 w-16 shrink-0 rounded-lg bg-[#DCE1DB]"></div>
        <div class="flex min-w-0 flex-1 flex-col">
          <span class="text-sm font-semibold">{{ o.option_name }}</span>
          <span class="text-xs text-[#5B6661]">{{ [o.brand, o.origin].filter(Boolean).join(' · ') }}</span>
          <span class="num text-xs">{{ __('{0} ج.م للوحدة', [money(o.unit_price)]) }}</span>
        </div>
        <span class="num shrink-0 text-xs font-bold" :class="o.difference > 0 ? 'text-[#8A4A0C]' : 'text-[#14503F]'" data-testid="option-difference">
          {{ o.difference > 0 ? '+ ' + money(o.difference) + ' ج.م' : __('ضمن الميزانية') }}
        </span>
      </button>
      <div v-if="s.status === 'Chosen'" class="flex flex-col gap-1.5">
        <span class="text-sm">{{ __('الفرق:') }} <b class="num">{{ s.price_difference > 0 ? '+ ' + money(s.price_difference) + ' ج.م' : __('ضمن الميزانية') }}</b></span>
        <button class="min-h-[48px] rounded-[12px] bg-[#1D6B57] font-bold text-white" :disabled="busy" data-testid="approve-selection" @click="approve(s)">
          {{ s.price_difference > 0 ? __('اعتمد ووقّع على الفرق') : __('اعتمد الاختيار') }}
        </button>
      </div>
      <RouterLink v-if="s.status === 'Awaiting Signature' && s.signature_request" :to="`/sign/${encodeURIComponent(s.signature_request)}`" class="text-sm font-semibold text-[#1D6B57]">{{ __('افتح صفحة التوقيع') }}</RouterLink>
    </section>
    <ClientNav :project="project" active="home" />
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '@/lib/api'
import { shortDate } from '@/lib/format'
import { money } from '@/lib/money'
import PageHeader from '@/components/PageHeader.vue'
import ClientNav from '@/components/ClientNav.vue'

const props = defineProps<{ project: string }>()
const project = props.project
const router = useRouter()
const rows = ref<any[]>([])
const loaded = ref(false)
const busy = ref(false)
const error = ref('')

const locked = (s: any) => ['Awaiting Signature', 'Approved', 'Locked'].includes(s.status)

async function load() {
  rows.value = await call('construction_core.selections.project_selections', { project })
  loaded.value = true
}
async function run(fn: () => Promise<void>) {
  busy.value = true
  error.value = ''
  try {
    await fn()
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
const choose = (s: any, o: any) => run(async () => {
  await call('construction_core.selections.choose', { selection: s.name, option: o.name }, true)
  await load()
})
const approve = (s: any) => run(async () => {
  const res = await call('construction_core.selections.approve', { selection: s.name }, true)
  if (res.signature_request) router.push(`/sign/${encodeURIComponent(res.signature_request)}`)
  else await load()
})
onMounted(() => run(load))
</script>
