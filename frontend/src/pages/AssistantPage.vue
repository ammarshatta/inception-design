<template>
  <main class="mx-auto flex h-full max-w-md flex-col">
    <PageHeader :title="__('المساعد')" :subtitle="__('بيعمل مسودات بس، والأسعار من محرك التسعير')" back="/" />
    <div ref="list" class="flex flex-1 flex-col gap-2 overflow-y-auto px-4 pb-4" data-testid="assistant-list">
      <p v-if="!msgs.length" class="text-sm text-[#5B6661]">{{ __('اسأل عن مشروع، أو اطلب مسودة أمر تغيير، مثلاً: عايز أغيّر سيراميك الريسبشن لباركيه.') }}</p>
      <div v-for="(m, i) in msgs" :key="i" class="max-w-[85%] whitespace-pre-line rounded-2xl px-3.5 py-2.5 text-sm" :class="m.role === 'user' ? 'self-start bg-[#1D6B57] text-white' : 'self-end bg-white'">
        {{ m.text }}
        <p v-for="w in m.warnings || []" :key="w" class="mt-1.5 rounded bg-[#FDE8E6] px-2 py-1 text-xs text-[#B42318]" data-testid="assistant-warning">{{ w }}</p>
        <a v-for="d in m.drafts || []" :key="d.name" :href="`/app/${d.doctype === 'Change Order' ? 'change-order' : 'estimate'}/${encodeURIComponent(d.name)}`" target="_blank" class="mt-1.5 block text-xs font-semibold text-[#1D6B57]">{{ __('افتح المسودة') }} {{ d.name }}</a>
      </div>
      <p v-if="busy" class="self-end text-xs text-[#5B6661]">{{ __('بيفكر…') }}</p>
    </div>
    <p v-if="error" class="px-4 text-sm text-[#B42318]" role="alert">{{ error }}</p>
    <form class="flex gap-2 border-t border-[#E2E5E0] bg-white p-3" @submit.prevent="send">
      <select v-model="project" class="w-28 rounded-lg border border-[#E2E5E0] bg-white px-1 text-xs" :disabled="!!conversation">
        <option value="">{{ __('من غير مشروع') }}</option>
        <option v-for="p in projects" :key="p.name" :value="p.name">{{ p.project_name }}</option>
      </select>
      <input v-model="text" class="min-h-[44px] min-w-0 flex-1 rounded-full border border-[#E2E5E0] px-3 text-sm" :placeholder="__('اكتب طلبك…')" data-testid="assistant-input" />
      <button class="h-11 w-11 shrink-0 rounded-full bg-[#1D6B57] text-white disabled:opacity-50" :disabled="busy || !text.trim()" :aria-label="__('إرسال')">➤</button>
    </form>
  </main>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { call } from '@/lib/api'
import PageHeader from '@/components/PageHeader.vue'

const msgs = ref<any[]>([])
const text = ref('')
const busy = ref(false)
const error = ref('')
const conversation = ref('')
const project = ref('')
const projects = ref<any[]>([])
const list = ref<HTMLElement | null>(null)

async function send() {
  const message = text.value.trim()
  if (!message) return
  msgs.value.push({ role: 'user', text: message })
  text.value = ''
  busy.value = true
  error.value = ''
  try {
    const res = await call('construction_core.ai.chat.send', { message, conversation: conversation.value || undefined, project: project.value || undefined }, true)
    conversation.value = res.conversation
    msgs.value.push({ role: 'assistant', text: res.reply, warnings: res.warnings, drafts: res.drafts })
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
    await nextTick()
    list.value?.scrollTo({ top: list.value.scrollHeight })
  }
}

onMounted(async () => {
  projects.value = await call('construction_core.api.portal.my_projects').catch(() => [])
})
</script>
