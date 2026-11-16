<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-28">
    <PageHeader :title="__('أوامر التغيير')" :back="isClient ? `/c/${encodeURIComponent(project)}` : `/projects/${encodeURIComponent(project)}`" />
    <p v-if="error" class="mx-4 rounded-lg bg-[#FDE8E6] px-3 py-2 text-sm text-[#B42318]" role="alert">{{ error }}</p>
    <form class="mx-4 mb-3 flex flex-col gap-2 rounded-2xl bg-white p-3.5" @submit.prevent="submit">
      <span class="text-sm font-bold">{{ isClient ? __('اطلب تعديل') : __('تعديل من الموقع') }}</span>
      <textarea v-model="description" rows="3" required :placeholder="__('اكتب التعديل المطلوب')" class="rounded-[10px] border border-[#C9CFC9] p-2 text-sm" data-testid="change-description"></textarea>
      <label class="flex min-h-[40px] cursor-pointer items-center justify-center rounded-[10px] border border-dashed border-[#AEB7B1] text-sm font-semibold text-[#1D6B57]">
        {{ __('+ صور ({0})', [photos.length]) }}
        <input type="file" accept="image/*" multiple class="hidden" @change="addPhotos" />
      </label>
      <button class="min-h-[44px] rounded-[10px] bg-[#1D6B57] text-sm font-bold text-white disabled:opacity-60" :disabled="busy || !description.trim()" data-testid="change-submit">{{ __('ابعت') }}</button>
      <p v-if="sent" class="text-sm text-[#14503F]">{{ __('وصل طلبك، والمهندس هيسعّره.') }}</p>
    </form>
    <article v-for="c in rows" :key="c.name" class="mx-4 mb-2 flex flex-col gap-1 rounded-xl bg-white px-3.5 py-3" data-testid="change-order">
      <div class="flex items-center justify-between gap-2">
        <span class="text-sm font-semibold">{{ c.title }}</span>
        <span class="shrink-0 rounded-full bg-[#EEF0EC] px-2 py-0.5 text-xs font-semibold">{{ STATUS[c.status] || c.status }}</span>
      </div>
      <span v-if="c.cost_difference" class="num text-sm font-bold">{{ (c.cost_difference > 0 ? '+ ' : '') + money(c.cost_difference) }} ج.م</span>
      <span v-if="c.schedule_impact_days" class="text-xs text-[#5B6661]">{{ __('تأثير على المدة: {0} يوم', [c.schedule_impact_days]) }}</span>
      <RouterLink v-if="c.status === 'Sent to Client' && c.signature_request && isClient" :to="`/sign/${encodeURIComponent(c.signature_request)}`" class="text-sm font-semibold text-[#1D6B57]">{{ __('راجع ووقّع') }}</RouterLink>
      <a v-if="c.signed_pdf" :href="c.signed_pdf" target="_blank" class="text-sm font-semibold text-[#1D6B57]">{{ __('النسخة الموقّعة PDF') }}</a>
    </article>
    <ClientNav v-if="isClient" :project="project" active="home" />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { me } from '@/data/me'
import { call, uploadFile } from '@/lib/api'
import { resizePhoto } from '@/lib/media'
import { money } from '@/lib/money'
import PageHeader from '@/components/PageHeader.vue'
import ClientNav from '@/components/ClientNav.vue'

const STATUS: Record<string, string> = {
  Draft: 'بيتسعّر',
  'Engineer Approved': 'اتسعّر',
  'Sent to Client': 'مستني توقيعك',
  Approved: 'اتوافق عليه',
  Rejected: 'اترفض',
  Cancelled: 'اتلغى',
}
const props = defineProps<{ project: string }>()
const project = props.project
const rows = ref<any[]>([])
const description = ref('')
const photos = ref<string[]>([])
const busy = ref(false)
const sent = ref(false)
const error = ref('')
const isClient = computed(() => !!me.data?.roles?.client && !me.data?.roles?.engineer && !me.data?.roles?.admin)

async function load() {
  rows.value = await call('construction_core.change_orders.project_change_orders', { project })
}
async function addPhotos(event: Event) {
  const input = event.target as HTMLInputElement
  busy.value = true
  try {
    for (const f of Array.from(input.files || [])) {
      const blob = await resizePhoto(f)
      const up = await uploadFile(blob, f.name.replace(/\.[^.]+$/, '') + '.jpg', '', '', () => {})
      photos.value.push(up.file_url)
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    input.value = ''
    busy.value = false
  }
}
async function submit() {
  busy.value = true
  error.value = ''
  try {
    await call('construction_core.change_orders.request_change', { project, description: description.value, photos: photos.value }, true)
    description.value = ''
    photos.value = []
    sent.value = true
    await load()
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
me.fetch()
onMounted(load)
</script>
