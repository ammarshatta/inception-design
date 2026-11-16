<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-28">
    <header class="flex flex-col gap-1 px-5 pb-2 pt-5">
      <h1 class="text-[22px] font-bold">{{ __('صور الموقع') }}</h1>
      <span class="text-[13px] text-[#5B6661]">{{ __('{0} صورة وفيديو', [count]) }}</span>
    </header>
    <div role="tablist" class="flex gap-2 overflow-x-auto px-4 pb-3 pt-2">
      <button
        v-for="c in chips"
        :key="c.value"
        role="tab"
        :aria-selected="stage === c.value"
        class="min-h-[40px] shrink-0 rounded-full border px-3.5 text-[13px] font-semibold"
        :class="stage === c.value ? 'border-[#1D6B57] bg-[#1D6B57] text-white' : 'border-[#E2E5E0] bg-white text-[#17201D]'"
        @click="select(c.value)"
      >{{ c.label }}</button>
    </div>
    <p v-if="error" class="px-5 text-sm text-[#B42318]">{{ error }}</p>
    <section v-for="g in groups" :key="g.update" class="flex flex-col gap-2 px-4 pb-4" data-testid="gallery-group">
      <div class="flex items-baseline justify-between">
        <h2 class="text-[15px] font-bold">{{ g.stage_name }}</h2>
        <span class="text-xs text-[#5B6661]">{{ shortDate(g.date) }} · {{ g.author }}</span>
      </div>
      <p v-if="g.text" class="text-[13px] text-[#3E4944]">{{ g.text }}</p>
      <div class="grid grid-cols-3 gap-1.5">
        <button v-for="m in g.media" :key="m.name" class="relative aspect-square overflow-hidden rounded-[10px] bg-[#DCE1DB]" @click="open(m)">
          <img v-if="m.kind === 'Photo'" :src="m.file" loading="lazy" class="h-full w-full object-cover" alt="" />
          <span v-else class="absolute right-1.5 top-1.5 rounded bg-[#17201DB3] px-1.5 text-[11px] font-semibold text-white">{{ __('فيديو') }}</span>
        </button>
      </div>
    </section>
    <div v-if="lightbox" class="fixed inset-0 z-50 flex items-center justify-center bg-black/90" role="dialog" aria-modal="true" data-testid="lightbox" @click.self="lightbox = null">
      <button class="absolute left-4 top-4 h-11 w-11 rounded-full bg-white/90 text-xl" aria-label="إغلاق" @click="lightbox = null">×</button>
      <img v-if="lightbox.kind === 'Photo'" :src="lightbox.file" class="max-h-full max-w-full object-contain" alt="" />
      <video v-else :src="lightbox.file" controls autoplay class="max-h-full max-w-full"></video>
    </div>
    <ClientNav :project="project" active="gallery" />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import { shortDate } from '@/lib/format'
import ClientNav from '@/components/ClientNav.vue'

const props = defineProps<{ project: string }>()
const project = props.project
const groups = ref<any[]>([])
const stages = ref<any[]>([])
const stage = ref('')
const error = ref('')
const lightbox = ref<any>(null)

const chips = computed(() => [{ value: '', label: 'كل المراحل' }, ...stages.value.map((s) => ({ value: s.name, label: s.stage_name }))])
const count = computed(() => groups.value.reduce((n, g) => n + g.media.length, 0))

async function load() {
  try {
    const res = await call('construction_core.api.portal.gallery', { project, stage: stage.value || undefined })
    groups.value = res.groups
    if (!stages.value.length) stages.value = res.stages
  } catch (e: any) {
    error.value = e.message
  }
}
function select(v: string) {
  stage.value = v
  load()
}
function open(m: any) {
  lightbox.value = m
}
onMounted(load)
</script>
