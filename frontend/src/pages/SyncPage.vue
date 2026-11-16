<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-10">
    <PageHeader :title="__('اللي مستني يتبعت')" back="/" />
    <p class="px-5 pb-2 text-xs text-[#5B6661]">{{ online ? __('النت شغال، بيتبعت بالترتيب.') : __('مفيش نت دلوقتي. كل حاجة محفوظة على الموبايل وهتتبعت لوحدها.') }}</p>
    <p v-if="!items.length" class="px-5 text-sm text-[#5B6661]" data-testid="sync-empty">{{ __('كل حاجة اتبعتت ✓') }}</p>
    <article v-for="i in items" :key="i.uuid" class="mx-4 mb-2 flex flex-col gap-1 rounded-[14px] bg-white p-3.5" data-testid="sync-item" :data-status="i.status">
      <div class="flex items-center justify-between gap-2">
        <span class="text-sm font-semibold">{{ i.label }}</span>
        <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="pill(i.status)">{{ LABEL[i.status] }}</span>
      </div>
      <span class="text-xs text-[#5B6661]">{{ new Date(i.created).toLocaleString('ar-EG-u-nu-latn') }}<template v-if="i.attempts"> · {{ __('محاولات: {0}', [i.attempts]) }}</template></span>
      <p v-if="i.error" class="text-xs text-[#B42318]">{{ i.error }}</p>
      <div v-if="i.status === 'failed' || (i.status === 'pending' && i.attempts)" class="flex gap-2">
        <button class="min-h-[40px] flex-1 rounded-lg bg-[#1D6B57] text-sm font-bold text-white" data-testid="sync-retry" @click="retry(i.uuid)">{{ __('جرّب تاني') }}</button>
        <button v-if="i.status === 'failed'" class="min-h-[40px] rounded-lg border border-[#E2E5E0] px-3 text-sm" @click="confirmDiscard(i.uuid)">{{ __('امسح') }}</button>
      </div>
    </article>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { discard, items, retry, run } from '@/lib/queue'
import { __ } from '@/translate'
import PageHeader from '@/components/PageHeader.vue'

const online = ref(navigator.onLine)
const LABEL: Record<string, string> = { pending: 'مستني', syncing: 'بيتبعت', failed: 'اترفض', done: 'اتبعت' }
function pill(s: string) {
  return s === 'failed' ? 'bg-[#FDE8E6] text-[#B42318]' : s === 'done' ? 'bg-[#E3F0EB] text-[#14503F]' : 'bg-[#FBEFDF] text-[#8A4A0C]'
}
function confirmDiscard(uuid: string) {
  if (window.confirm(__('متأكد؟ البند ده مش هيتبعت.'))) void discard(uuid)
}
onMounted(() => {
  window.addEventListener('online', () => (online.value = true))
  window.addEventListener('offline', () => (online.value = false))
  void run()
})
</script>
