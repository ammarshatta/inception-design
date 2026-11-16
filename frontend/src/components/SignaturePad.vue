<template>
  <div class="flex flex-col gap-1.5">
    <canvas
      ref="canvas"
      class="h-[140px] w-full touch-none rounded-[10px] border border-dashed border-[#AEB7B1] bg-[#FAFBF9]"
      data-testid="signature-pad"
      @pointerdown="start"
      @pointermove="move"
      @pointerup="end"
      @pointerleave="end"
    ></canvas>
    <button type="button" class="self-start text-xs font-semibold text-[#1D6B57]" @click="clear">{{ __('امسح') }}</button>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

const emit = defineEmits<{ (e: 'change', dataUrl: string): void }>()
const canvas = ref<HTMLCanvasElement | null>(null)
let drawing = false
let drawn = false
let ctx: CanvasRenderingContext2D | null = null

function setup() {
  const c = canvas.value!
  const ratio = window.devicePixelRatio || 1
  c.width = c.clientWidth * ratio
  c.height = c.clientHeight * ratio
  ctx = c.getContext('2d')!
  ctx.scale(ratio, ratio)
  ctx.lineWidth = 2.2
  ctx.lineCap = 'round'
  ctx.strokeStyle = '#17201D'
}
function pos(e: PointerEvent) {
  const r = canvas.value!.getBoundingClientRect()
  return [e.clientX - r.left, e.clientY - r.top]
}
function start(e: PointerEvent) {
  drawing = true
  const [x, y] = pos(e)
  ctx!.beginPath()
  ctx!.moveTo(x, y)
}
function move(e: PointerEvent) {
  if (!drawing) return
  const [x, y] = pos(e)
  ctx!.lineTo(x, y)
  ctx!.stroke()
  drawn = true
}
function end() {
  if (!drawing) return
  drawing = false
  if (drawn) emit('change', canvas.value!.toDataURL('image/png'))
}
function clear() {
  const c = canvas.value!
  ctx!.clearRect(0, 0, c.width, c.height)
  drawn = false
  emit('change', '')
}
onMounted(setup)
</script>
