<template>
  <main class="mx-auto flex min-h-full max-w-3xl flex-col pb-24">
    <PageHeader :title="__('الرسم على الصورة')" back="/" />
    <p v-if="error" class="mx-4 rounded-lg bg-[#FDE8E6] px-3 py-2 text-sm text-[#B42318]" role="alert" data-testid="error">{{ error }}</p>

    <div class="flex flex-wrap items-center gap-1.5 px-4 pb-2" role="toolbar">
      <button v-for="t in tools" :key="t.key" class="min-h-[40px] rounded-lg border px-3 text-sm" :class="tool === t.key ? 'border-[#1D6B57] bg-[#1D6B57] text-white' : 'border-[#E2E5E0] bg-white'" :data-testid="`tool-${t.key}`" @click="tool = t.key">{{ t.label }}</button>
      <span class="mx-1 h-6 w-px bg-[#E2E5E0]"></span>
      <button v-for="c in colors" :key="c" class="h-8 w-8 rounded-full border-2" :style="{ background: c, borderColor: color === c ? '#17201D' : 'transparent' }" :aria-label="c" @click="color = c"></button>
      <button class="min-h-[40px] rounded-lg border border-[#E2E5E0] bg-white px-3 text-sm" :disabled="!shapes.length" data-testid="undo" @click="shapes.pop()">{{ __('تراجع') }}</button>
    </div>

    <div v-if="imgW" class="relative mx-4 select-none overflow-hidden rounded-xl bg-[#DCE1DB]" style="touch-action: none">
      <img :src="file" class="block w-full" alt="" draggable="false" />
      <svg
        class="absolute inset-0 h-full w-full"
        :viewBox="`0 0 ${imgW} ${imgH}`"
        data-testid="markup-canvas"
        @pointerdown="down"
        @pointermove="move"
        @pointerup="up"
        @pointerleave="up"
      >
        <defs>
          <marker v-for="c in colors" :id="`head-${c.slice(1)}`" :key="c" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" :fill="c" />
          </marker>
        </defs>
        <g v-for="(s, i) in all" :key="i" :stroke="s.color" :stroke-width="s.width" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <line v-if="s.type === 'arrow' && s.points.length > 1" :x1="s.points[0][0]" :y1="s.points[0][1]" :x2="s.points[1][0]" :y2="s.points[1][1]" :marker-end="`url(#head-${s.color.slice(1)})`" />
          <rect v-else-if="s.type === 'rect' && s.points.length > 1" v-bind="rectOf(s)" />
          <ellipse v-else-if="s.type === 'circle' && s.points.length > 1" v-bind="ellipseOf(s)" />
          <polyline v-else-if="s.type === 'free'" :points="s.points.map((p: number[]) => p.join(',')).join(' ')" />
          <text v-else-if="s.type === 'text'" :x="s.points[0][0]" :y="s.points[0][1]" :fill="s.color" stroke="none" :font-size="fontSize" direction="rtl" font-weight="700">{{ s.text }}</text>
        </g>
      </svg>
    </div>

    <div class="fixed inset-x-0 bottom-0 mx-auto flex max-w-3xl gap-2 bg-[#F4F5F2] px-4 pb-5 pt-3">
      <input v-model="title" class="min-h-[52px] min-w-0 flex-1 rounded-[14px] border border-[#E2E5E0] px-3 text-sm" :placeholder="__('عنوان (اختياري)')" />
      <button class="min-h-[52px] rounded-[14px] bg-[#1D6B57] px-6 text-base font-bold text-white disabled:opacity-50" :disabled="busy || !shapes.length" data-testid="save-markup" @click="save">
        {{ saved ? __('اتحفظ ✓') : __('حفظ') }}
      </button>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call } from '@/lib/api'
import { __ } from '@/translate'
import PageHeader from '@/components/PageHeader.vue'

type Shape = { type: string; color: string; width: number; points: number[][]; text?: string }

const route = useRoute()
const router = useRouter()
const file = String(route.query.file || '')
const markup = ref(String(route.query.markup || ''))
const tools = [
  { key: 'arrow', label: 'سهم' },
  { key: 'circle', label: 'دايرة' },
  { key: 'rect', label: 'مربع' },
  { key: 'free', label: 'قلم' },
  { key: 'text', label: 'كتابة' },
]
const colors = ['#E5484D', '#F5A524', '#1D6B57', '#FFFFFF']
const tool = ref('arrow')
const color = ref(colors[0])
const shapes = ref<Shape[]>([])
const drawing = ref<Shape | null>(null)
const imgW = ref(0)
const imgH = ref(0)
const title = ref('')
const error = ref('')
const busy = ref(false)
const saved = ref(false)
let image: HTMLImageElement | null = null

const all = computed(() => (drawing.value ? [...shapes.value, drawing.value] : shapes.value))
const width = computed(() => Math.max(3, Math.round(imgW.value / 250)))
const fontSize = computed(() => Math.max(18, Math.round(imgW.value / 22)))

function rectOf(s: Shape) {
  const [[x1, y1], [x2, y2]] = s.points
  return { x: Math.min(x1, x2), y: Math.min(y1, y2), width: Math.abs(x2 - x1), height: Math.abs(y2 - y1) }
}
function ellipseOf(s: Shape) {
  const [[x1, y1], [x2, y2]] = s.points
  return { cx: (x1 + x2) / 2, cy: (y1 + y2) / 2, rx: Math.abs(x2 - x1) / 2, ry: Math.abs(y2 - y1) / 2 }
}

function point(ev: PointerEvent): number[] {
  const svg = ev.currentTarget as SVGSVGElement
  const r = svg.getBoundingClientRect()
  return [Math.round(((ev.clientX - r.left) / r.width) * imgW.value), Math.round(((ev.clientY - r.top) / r.height) * imgH.value)]
}

function down(ev: PointerEvent) {
  const p = point(ev)
  saved.value = false
  if (tool.value === 'text') {
    const text = window.prompt(__('اكتب الملاحظة'))
    if (text) shapes.value.push({ type: 'text', color: color.value, width: width.value, points: [p], text })
    return
  }
  ;(ev.currentTarget as Element).setPointerCapture?.(ev.pointerId)
  drawing.value = { type: tool.value, color: color.value, width: width.value, points: tool.value === 'free' ? [p] : [p, p] }
}
function move(ev: PointerEvent) {
  if (!drawing.value) return
  const p = point(ev)
  if (drawing.value.type === 'free') drawing.value.points.push(p)
  else drawing.value.points[1] = p
}
function up() {
  if (!drawing.value) return
  const s = drawing.value
  drawing.value = null
  const [a, b] = [s.points[0], s.points[s.points.length - 1]]
  if (s.type === 'free' ? s.points.length > 2 : Math.hypot(b[0] - a[0], b[1] - a[1]) > 4) shapes.value.push(s)
}

/** Flatten the photo and the shapes into one PNG (the original file is never touched). */
function render(): string {
  const canvas = document.createElement('canvas')
  canvas.width = imgW.value
  canvas.height = imgH.value
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(image!, 0, 0)
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  for (const s of shapes.value) {
    ctx.strokeStyle = s.color
    ctx.fillStyle = s.color
    ctx.lineWidth = s.width
    ctx.beginPath()
    if (s.type === 'arrow') {
      const [[x1, y1], [x2, y2]] = s.points
      ctx.moveTo(x1, y1)
      ctx.lineTo(x2, y2)
      ctx.stroke()
      const ang = Math.atan2(y2 - y1, x2 - x1)
      const h = s.width * 4
      ctx.beginPath()
      ctx.moveTo(x2, y2)
      ctx.lineTo(x2 - h * Math.cos(ang - 0.5), y2 - h * Math.sin(ang - 0.5))
      ctx.lineTo(x2 - h * Math.cos(ang + 0.5), y2 - h * Math.sin(ang + 0.5))
      ctx.closePath()
      ctx.fill()
    } else if (s.type === 'rect') {
      const r = rectOf(s)
      ctx.strokeRect(r.x, r.y, r.width, r.height)
    } else if (s.type === 'circle') {
      const e = ellipseOf(s)
      ctx.ellipse(e.cx, e.cy, e.rx, e.ry, 0, 0, Math.PI * 2)
      ctx.stroke()
    } else if (s.type === 'free') {
      s.points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)))
      ctx.stroke()
    } else if (s.type === 'text') {
      ctx.direction = 'rtl'
      ctx.font = `700 ${fontSize.value}px "IBM Plex Sans Arabic", Tahoma, sans-serif`
      ctx.fillText(s.text || '', s.points[0][0], s.points[0][1])
    }
  }
  return canvas.toDataURL('image/png')
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    const res = await call(
      'construction_core.documents.save_markup',
      { base_file: file, overlay_json: JSON.stringify(shapes.value), rendered_png: render(), markup: markup.value || undefined, title: title.value },
      true,
    )
    markup.value = res.markup
    router.replace({ query: { file, markup: res.markup } })
    saved.value = true
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  if (!file) {
    error.value = __('مفيش صورة')
    return
  }
  try {
    if (markup.value) {
      const m = await call('construction_core.documents.get_markup', { markup: markup.value })
      shapes.value = m.overlay
      title.value = m.title || ''
    }
    image = new Image()
    image.src = file
    await image.decode()
    imgW.value = image.naturalWidth
    imgH.value = image.naturalHeight
  } catch (e: any) {
    error.value = e.message || __('الصورة مش بتفتح')
  }
})
</script>
