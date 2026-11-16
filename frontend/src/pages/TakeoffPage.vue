<template>
  <main class="mx-auto flex min-h-full max-w-5xl flex-col gap-3 px-4 pb-10">
    <PageHeader :title="__('قياس من الرسم')" back="/" />
    <p v-if="error" class="rounded-lg bg-[#FDE8E6] px-3 py-2 text-sm text-[#B42318]" role="alert" data-testid="error">{{ error }}</p>

    <section v-if="!file" class="flex flex-col gap-2 rounded-[14px] bg-white p-3.5">
      <input v-model="title" class="min-h-[44px] rounded-lg border border-[#E2E5E0] px-3 text-sm" :placeholder="__('اسم القياس (مثلاً مسقط الدور الأول)')" data-testid="takeoff-title" />
      <label class="flex min-h-[48px] cursor-pointer items-center justify-center rounded-lg bg-[#1D6B57] text-sm font-bold text-white">
        {{ __('افتح رسم (PDF أو صورة)') }}
        <input type="file" accept="application/pdf,image/*" class="hidden" data-testid="takeoff-file" @change="pick" />
      </label>
    </section>

    <template v-else>
      <div class="flex flex-wrap items-center gap-1.5" role="toolbar">
        <button v-for="m in modes" :key="m.key" class="min-h-[40px] rounded-lg border px-3 text-sm" :class="mode === m.key ? 'border-[#1D6B57] bg-[#1D6B57] text-white' : 'border-[#E2E5E0] bg-white'" :data-testid="`mode-${m.key}`" @click="start(m.key)">{{ m.label }}</button>
        <button v-if="current" class="min-h-[40px] rounded-lg bg-[#17201D] px-3 text-sm font-bold text-white" data-testid="finish" @click="finish">{{ __('خلص') }}</button>
        <label class="flex items-center gap-1 text-sm">
          {{ __('طول خط المعايرة (م)') }}
          <input v-model.number="calibrationM" type="number" min="0" step="0.01" inputmode="decimal" class="num w-20 rounded-lg border border-[#E2E5E0] px-2 py-1.5" data-testid="calibration-m" />
        </label>
        <span class="text-xs text-[#5B6661]">{{ scale ? __('المقياس: {0} بكسل/م', [scale.toFixed(2)]) : __('ارسم خط المعايرة الأول') }}</span>
      </div>

      <div class="max-h-[70vh] overflow-auto rounded-xl border border-[#E2E5E0] bg-white">
        <div class="relative" :style="{ width: `${w}px`, height: `${h}px` }">
          <img :src="background" :width="w" :height="h" class="block max-w-none" alt="" draggable="false" />
          <svg class="absolute inset-0" :width="w" :height="h" :viewBox="`0 0 ${w} ${h}`" data-testid="takeoff-canvas" @click="click">
            <line v-if="calibration.length === 2" :x1="calibration[0][0]" :y1="calibration[0][1]" :x2="calibration[1][0]" :y2="calibration[1][1]" stroke="#F5A524" stroke-width="3" />
            <circle v-for="(p, i) in calibration" :key="`c${i}`" :cx="p[0]" :cy="p[1]" r="4" fill="#F5A524" />
            <g v-for="(m, i) in shown" :key="i">
              <polygon v-if="m.kind === 'Area'" :points="pts(m.points)" fill="rgba(29,107,87,0.18)" stroke="#1D6B57" stroke-width="2" />
              <polyline v-else-if="m.kind === 'Length'" :points="pts(m.points)" fill="none" stroke="#E5484D" stroke-width="3" />
              <circle v-for="(p, j) in m.points" :key="j" :cx="p[0]" :cy="p[1]" r="4" :fill="m.kind === 'Count' ? '#4A62D8' : '#17201D'" />
            </g>
          </svg>
        </div>
      </div>

      <section class="flex flex-col gap-2 rounded-[14px] bg-white p-3.5">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-bold">{{ __('القياسات') }}</h2>
          <button class="min-h-[40px] rounded-lg bg-[#1D6B57] px-4 text-sm font-bold text-white disabled:opacity-50" :disabled="busy || !calibrationReady" data-testid="save-takeoff" @click="save">{{ __('حفظ') }}</button>
        </div>
        <p v-if="!measurements.length" class="text-sm text-[#5B6661]">{{ __('اختار طول أو مساحة أو عدد وارسم على الرسم.') }}</p>
        <div v-for="(m, i) in measurements" :key="i" class="flex flex-wrap items-center gap-2 border-b border-[#F0F1EE] py-1.5" data-testid="measurement">
          <input v-model="m.label" class="min-h-[36px] min-w-0 flex-1 rounded-lg border border-[#E2E5E0] px-2 text-sm" :placeholder="__('الاسم')" />
          <span class="num text-sm font-bold" dir="ltr" data-testid="measurement-value">{{ fmt(valueOf(m)) }} {{ unit(m.kind) }}</span>
          <template v-if="m.name && estimate">
            <select v-model="m.target" class="min-h-[36px] rounded-lg border border-[#E2E5E0] bg-white px-2 text-xs" data-testid="estimate-line">
              <option value="">{{ __('سطر جديد') }}</option>
              <option v-for="l in lines" :key="l.name" :value="l.name">{{ l.section }} — {{ l.description || l.item || l.assembly }}</option>
            </select>
            <button class="min-h-[36px] rounded-lg border border-[#1D6B57] px-3 text-xs font-bold text-[#1D6B57]" data-testid="push" @click="push(m)">{{ m.estimate_line ? __('اتضاف ✓') : __('أضف للتسعير') }}</button>
          </template>
          <button class="text-[#B42318]" :aria-label="__('امسح')" @click="measurements.splice(i, 1)">×</button>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call, uploadFile } from '@/lib/api'
import { __ } from '@/translate'
import PageHeader from '@/components/PageHeader.vue'

type Pt = [number, number]
type M = { name?: string; label: string; kind: 'Length' | 'Area' | 'Count'; points: Pt[]; value?: number; estimate_line?: string; target?: string }

const props = defineProps<{ name?: string }>()
const route = useRoute()
const router = useRouter()
const takeoffName = ref(props.name || '')
const estimate = ref(String(route.query.estimate || ''))
const project = ref(String(route.query.project || ''))
const file = ref(String(route.query.file || ''))
const title = ref('')
const background = ref('')
const w = ref(0)
const h = ref(0)
const modes = [
  { key: 'calibrate', label: 'معايرة' },
  { key: 'Length', label: 'طول' },
  { key: 'Area', label: 'مساحة' },
  { key: 'Count', label: 'عدد' },
]
const mode = ref('calibrate')
const calibration = ref<Pt[]>([])
const calibrationM = ref<number | null>(null)
const measurements = ref<M[]>([])
const current = ref<M | null>(null)
const lines = ref<any[]>([])
const busy = ref(false)
const error = ref('')

const shown = computed(() => (current.value ? [...measurements.value, current.value] : measurements.value))
const scale = computed(() => {
  if (calibration.value.length !== 2 || !calibrationM.value) return 0
  const [[x1, y1], [x2, y2]] = calibration.value
  return Math.hypot(x2 - x1, y2 - y1) / calibrationM.value
})
const calibrationReady = computed(() => scale.value > 0)

// Same formulas as the server (construction_core/takeoff.py); the server value is the one kept.
function valueOf(m: M): number {
  if (m.value !== undefined && m.value !== null && m.name) return m.value
  if (!scale.value) return 0
  const p = m.points
  if (m.kind === 'Count') return p.length
  if (m.kind === 'Length') return p.slice(1).reduce((s, q, i) => s + Math.hypot(q[0] - p[i][0], q[1] - p[i][1]), 0) / scale.value
  let a = 0
  for (let i = 0; i < p.length; i++) {
    const [x1, y1] = p[i]
    const [x2, y2] = p[(i + 1) % p.length]
    a += x1 * y2 - x2 * y1
  }
  return Math.abs(a) / 2 / (scale.value * scale.value)
}
const fmt = (v: number) => (Math.round(v * 100) / 100).toFixed(2)
const unit = (k: string) => ({ Length: 'م', Area: 'م²', Count: 'عدد' })[k]
const pts = (p: Pt[]) => p.map((q) => q.join(',')).join(' ')

function start(key: string) {
  finish()
  current.value = null
  mode.value = key
  if (key === 'calibrate') calibration.value = []
  else current.value = { label: '', kind: key as M['kind'], points: [] }
}
function click(ev: MouseEvent) {
  const r = (ev.currentTarget as SVGSVGElement).getBoundingClientRect()
  const p: Pt = [Math.round(ev.clientX - r.left), Math.round(ev.clientY - r.top)]
  if (mode.value === 'calibrate') {
    if (calibration.value.length >= 2) calibration.value = []
    calibration.value.push(p)
  } else if (current.value) {
    current.value.points.push(p)
  }
}
function finish() {
  const m = current.value
  current.value = null
  if (!m) return
  const min = m.kind === 'Area' ? 3 : m.kind === 'Length' ? 2 : 1
  if (m.points.length >= min) measurements.value.push(m)
  if (mode.value !== 'calibrate') current.value = { label: '', kind: m.kind, points: [] }
}

async function renderPdf(url: string) {
  const pdfjs: any = await import('pdfjs-dist')
  pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.js', import.meta.url).toString()
  const pdf = await pdfjs.getDocument({ url, isEvalSupported: false, withCredentials: true }).promise
  const page = await pdf.getPage(1)
  const viewport = page.getViewport({ scale: 1 }) // 1 PDF point = 1 px, so points stay stable
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(viewport.width)
  canvas.height = Math.round(viewport.height)
  await page.render({ canvasContext: canvas.getContext('2d')!, viewport }).promise
  return { src: canvas.toDataURL('image/png'), w: canvas.width, h: canvas.height }
}
async function renderImage(url: string) {
  const img = new Image()
  img.src = url
  await img.decode()
  return { src: url, w: img.naturalWidth, h: img.naturalHeight }
}
async function openDrawing() {
  const r = /\.pdf($|\?)/i.test(file.value) ? await renderPdf(file.value) : await renderImage(file.value)
  background.value = r.src
  w.value = r.w
  h.value = r.h
}

async function pick(ev: Event) {
  const f = (ev.target as HTMLInputElement).files?.[0]
  if (!f) return
  try {
    const up = await uploadFile(f, f.name, '', '', () => {})
    file.value = up.file_url
    if (!title.value) title.value = f.name.replace(/\.[^.]+$/, '')
    await openDrawing()
  } catch (e: any) {
    error.value = e.message
  }
}

async function loadLines() {
  if (!estimate.value) return
  const est = await call('frappe.client.get', { doctype: 'Estimate', name: estimate.value })
  lines.value = est.lines
}

function apply(res: any) {
  takeoffName.value = res.name
  title.value = res.title
  file.value = res.drawing_file
  estimate.value = res.estimate || estimate.value
  calibration.value = res.calibration
  calibrationM.value = res.calibration_m
  measurements.value = res.measurements.map((m: any) => ({ ...m, target: '' }))
}

async function save() {
  finish()
  busy.value = true
  error.value = ''
  try {
    const res = await call(
      'construction_core.takeoff.save_takeoff',
      {
        data: {
          name: takeoffName.value || undefined,
          title: title.value || __('قياس'),
          estimate: estimate.value || undefined,
          project: project.value || undefined,
          drawing_file: file.value,
          calibration: calibration.value,
          calibration_m: calibrationM.value,
          measurements: measurements.value.map((m) => ({ name: m.name, label: m.label, kind: m.kind, points: m.points })),
        },
      },
      true,
    )
    apply(res)
    if (!props.name) router.replace({ path: `/takeoff/${encodeURIComponent(res.name)}` })
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function push(m: M) {
  error.value = ''
  try {
    const res = await call('construction_core.takeoff.push_to_estimate', { takeoff: takeoffName.value, measurement: m.name, estimate: estimate.value, line: m.target || undefined }, true)
    m.estimate_line = res.line
    await loadLines()
  } catch (e: any) {
    error.value = e.message
  }
}

onMounted(async () => {
  try {
    if (takeoffName.value) apply(await call('construction_core.takeoff.get_takeoff', { name: takeoffName.value }))
    if (file.value) await openDrawing()
    await loadLines()
  } catch (e: any) {
    error.value = e.message
  }
})
</script>
