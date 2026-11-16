<template>
  <span class="inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold" :style="style">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()
const MAP: Record<string, [string, string, string]> = {
  Done: ['خلصت', '#E3F0EB', '#14503F'],
  'In Progress': ['شغالة', '#FBEFDF', '#8A4A0C'],
  'On Hold': ['متوقفة', '#FDE8E6', '#B42318'],
  'Not Started': ['جاية', '#EEF0EC', '#4A5550'],
}
const entry = computed(() => MAP[props.status] || [props.status, '#EEF0EC', '#4A5550'])
const label = computed(() => entry.value[0])
const style = computed(() => ({ background: entry.value[1], color: entry.value[2] }))
</script>
