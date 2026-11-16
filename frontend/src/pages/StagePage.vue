<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col">
    <PageHeader
      :title="data?.stage_name || '…'"
      :subtitle="data?.project_name"
      :back="data ? `/projects/${encodeURIComponent(data.project)}` : '/'"
    />
    <p v-if="error" class="px-5 text-sm text-[#B42318]">{{ error }}</p>
    <section v-if="data" class="flex flex-col gap-3 px-4 pb-10">
      <div class="flex flex-col gap-2 rounded-[14px] bg-white p-3.5">
        <div class="flex items-center justify-between">
          <StatusPill :status="data.status" />
          <span class="num text-lg font-bold" data-testid="stage-progress">{{ pct(data.progress) }}</span>
        </div>
        <ProgressBar :value="data.progress" />
      </div>

      <div v-if="data.checklist.length" class="rounded-[14px] bg-white px-3.5 py-2">
        <h2 class="py-1 text-sm font-bold">{{ __('بنود المراجعة') }}</h2>
        <label
          v-for="item in data.checklist"
          :key="item.name"
          class="flex min-h-[44px] items-center justify-between gap-3 border-t border-[#EEF0EC] py-1"
        >
          <span class="text-sm">{{ item.label }}</span>
          <input
            type="checkbox"
            class="h-[22px] w-[22px] accent-[#1D6B57]"
            data-testid="checklist-item"
            :checked="!!item.done"
            :disabled="!data.can_post || busy === item.name"
            @change="toggle(item, ($event.target as HTMLInputElement).checked)"
          />
        </label>
      </div>

      <h2 class="px-1 text-sm font-bold">{{ __('آخر التحديثات') }}</h2>
      <p v-if="!data.updates.length" class="px-1 text-sm text-[#5B6661]">{{ __('مفيش تحديثات لسه.') }}</p>
      <article v-for="u in data.updates" :key="u.name" class="flex flex-col gap-2 rounded-[14px] bg-white p-3.5" data-testid="update-card">
        <div class="flex justify-between text-xs text-[#5B6661]">
          <span>{{ u.author }}</span>
          <span>{{ shortDate(u.creation) }}</span>
        </div>
        <span v-if="u.internal_only" class="self-start rounded-full bg-[#FBEFDF] px-2 text-xs font-semibold text-[#8A4A0C]">{{ __('داخلي فقط') }}</span>
        <p v-if="u.text" class="text-sm">{{ u.text }}</p>
        <div v-if="u.media.length" class="grid grid-cols-3 gap-1.5">
          <a v-for="m in u.media" :key="m.name" :href="m.file" target="_blank" class="relative block aspect-square overflow-hidden rounded-lg bg-[#DCE1DB]">
            <img v-if="m.kind === 'Photo'" :src="m.file" loading="lazy" class="h-full w-full object-cover" alt="" />
            <span v-else class="absolute inset-0 flex items-center justify-center text-xs font-semibold">{{ __('فيديو') }}</span>
            <span v-if="m.publishable" class="absolute right-1 top-1 rounded bg-[#1D6B57] px-1 text-[10px] font-bold text-white">{{ __('للنشر') }}</span>
            <RouterLink
              v-if="m.kind === 'Photo'"
              :to="{ path: '/markup', query: { file: m.file } }"
              class="absolute bottom-1 left-1 rounded bg-white/90 px-1.5 text-[11px] font-bold text-[#17201D]"
              data-testid="markup-photo"
              @click.stop
            >{{ __('ارسم') }}</RouterLink>
          </a>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import { cachedCall } from '@/lib/offline'
import { enqueue } from '@/lib/queue'
import { __ } from '@/translate'
import { pct, shortDate } from '@/lib/format'
import PageHeader from '@/components/PageHeader.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import StatusPill from '@/components/StatusPill.vue'

const props = defineProps<{ name: string }>()
const data = ref<any>(null)
const error = ref('')
const busy = ref('')

async function load() {
  try {
    data.value = await cachedCall('construction_core.api.portal.stage_detail', { stage: props.name })
  } catch (e: any) {
    error.value = e.message
  }
}

async function toggle(item: any, done: boolean) {
  busy.value = item.name
  if (!navigator.onLine) {
    // offline: tick now on the screen, send later (the server keeps a newer change made there)
    await enqueue({ action: 'tick', payload: { stage: props.name, row: item.name, done: done ? 1 : 0 }, label: `${__('بند')}: ${item.label}` })
    item.done = done ? 1 : 0
    busy.value = ''
    return
  }
  try {
    const res = await call(
      'construction_core.api.portal.toggle_checklist_item',
      { stage: props.name, row_name: item.name, done: done ? 1 : 0 },
      true,
    )
    item.done = done ? 1 : 0
    data.value.progress = res.progress
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = ''
  }
}

onMounted(load)
</script>
