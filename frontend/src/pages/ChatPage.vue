<template>
  <main class="mx-auto flex h-full max-w-md flex-col" :class="isClient ? 'pb-[78px]' : ''">
    <header class="flex items-center gap-2.5 border-b border-[#E2E5E0] bg-white px-4 pb-2.5 pt-4">
      <RouterLink v-if="!isClient" :to="`/projects/${encodeURIComponent(project)}`" aria-label="رجوع" class="flex h-11 w-11 items-center justify-center rounded-full border border-[#E2E5E0]">‹</RouterLink>
      <div class="flex min-w-0 flex-col">
        <h1 class="text-[17px] font-bold">{{ __('شات المشروع') }}</h1>
        <span class="truncate text-xs text-[#5B6661]">{{ projectName }}</span>
      </div>
    </header>

    <section ref="list" class="flex flex-1 flex-col gap-2 overflow-y-auto px-3.5 py-2.5" data-testid="chat-list">
      <p v-if="error" class="text-sm text-[#B42318]" role="alert">{{ error }}</p>
      <div
        v-for="m in msgs"
        :key="m.name"
        class="flex max-w-[82%] flex-col gap-0.5"
        :class="m.mine ? 'self-end' : 'self-start'"
        data-testid="chat-message"
      >
        <span v-if="!m.mine" class="text-[11px] font-bold text-[#14503F]">{{ m.author }}</span>
        <div
          v-if="m.kind === 'Approval'"
          class="flex flex-col gap-2 rounded-[14px] border border-[#E9B872] bg-[#FFF8EE] p-3"
          data-testid="approval-card"
        >
          <span class="text-xs font-bold text-[#8A4A0C]">{{ __('طلب موافقة') }}</span>
          <span class="text-[15px] font-semibold">{{ m.approval_title }}</span>
          <span v-if="m.approval_detail" class="text-sm">{{ m.approval_detail }}</span>
          <span v-if="m.approval_amount" class="num text-sm font-bold">{{ money(m.approval_amount) }}</span>
          <div v-if="m.approval_status === 'Pending' && isClient" class="grid grid-cols-2 gap-2">
            <button class="min-h-[44px] rounded-[10px] bg-[#1D6B57] text-sm font-bold text-white" data-testid="approve" @click="answer(m, 'Approved')">{{ __('موافق') }}</button>
            <button class="min-h-[44px] rounded-[10px] border border-[#C9CFC9] bg-white text-sm font-semibold" @click="answer(m, 'Question')">{{ __('عندي سؤال') }}</button>
          </div>
          <span v-else-if="m.approval_status === 'Pending'" class="text-xs text-[#5B6661]">{{ __('مستني رد العميل') }}</span>
          <span v-else class="text-xs font-bold" :class="m.approval_status === 'Approved' ? 'text-[#14503F]' : 'text-[#8A4A0C]'" data-testid="approval-answer">
            {{ m.approval_status === 'Approved' ? __('اتوافق عليه') : __('العميل عنده سؤال') }} · {{ when(m.answered_on) }}
          </span>
        </div>
        <div v-else class="flex flex-col gap-1.5 rounded-[14px] border px-3 py-2" :class="m.mine ? 'border-[#1D6B57] bg-[#1D6B57] text-white' : 'border-[#E2E5E0] bg-white'">
          <a v-if="m.attachment" :href="m.attachment" target="_blank"><img :src="m.attachment" class="max-h-48 rounded-lg" alt="" /></a>
          <span v-if="m.text" class="whitespace-pre-wrap text-sm leading-relaxed">{{ m.text }}</span>
        </div>
        <span class="text-[10px] text-[#5B6661]" :class="m.mine ? 'self-end' : ''">{{ when(m.creation) }}</span>
      </div>
    </section>

    <form v-if="!isClient && showApproval" class="flex flex-col gap-2 border-t border-[#E2E5E0] bg-white p-3" @submit.prevent="sendApproval">
      <input v-model="approval.title" required :placeholder="__('عنوان طلب الموافقة')" class="min-h-[40px] rounded-[10px] border border-[#C9CFC9] px-3 text-sm" />
      <input v-model="approval.detail" :placeholder="__('التفاصيل')" class="min-h-[40px] rounded-[10px] border border-[#C9CFC9] px-3 text-sm" />
      <input v-model.number="approval.amount" type="number" inputmode="decimal" :placeholder="__('المبلغ (اختياري)')" class="min-h-[40px] rounded-[10px] border border-[#C9CFC9] px-3 text-sm" />
      <button class="min-h-[44px] rounded-[10px] bg-[#1D6B57] text-sm font-bold text-white">{{ __('ابعت طلب الموافقة') }}</button>
    </form>

    <form class="flex items-center gap-2 bg-[#F4F5F2] px-3 py-2" @submit.prevent="send">
      <label class="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full border border-[#E2E5E0] bg-white" :aria-label="__('إرفاق صورة')">
        📎
        <input type="file" accept="image/*" class="hidden" @change="attach" />
      </label>
      <button v-if="!isClient" type="button" class="h-11 shrink-0 rounded-full border border-[#E2E5E0] bg-white px-3 text-xs font-semibold" @click="showApproval = !showApproval">{{ __('موافقة') }}</button>
      <input v-model="text" :placeholder="__('اكتب رسالة…')" class="min-h-[44px] min-w-0 flex-1 rounded-full border border-[#C9CFC9] bg-white px-3.5 text-sm" data-testid="chat-input" />
      <button type="submit" class="h-11 w-11 shrink-0 rounded-full bg-[#1D6B57] text-white" :aria-label="__('إرسال')" data-testid="chat-send" :disabled="sending">➤</button>
    </form>
    <ClientNav v-if="isClient" :project="project" active="chat" />
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { me } from '@/data/me'
import { call, uploadFile } from '@/lib/api'
import { resizePhoto } from '@/lib/media'
import { money } from '@/lib/money'
import ClientNav from '@/components/ClientNav.vue'

const POLL_MS = 3000

const props = defineProps<{ project: string }>()
const project = props.project
const msgs = ref<any[]>([])
const text = ref('')
const error = ref('')
const sending = ref(false)
const projectName = ref('')
const showApproval = ref(false)
const approval = reactive({ title: '', detail: '', amount: null as number | null })
const list = ref<HTMLElement | null>(null)
let timer: number | undefined

const isClient = computed(() => !!me.data?.roles?.client && !me.data?.roles?.engineer && !me.data?.roles?.admin)

function when(v?: string) {
  if (!v) return ''
  const d = new Date(v.replace(' ', 'T'))
  return d.toLocaleString('ar-EG-u-nu-latn', { hour: 'numeric', minute: '2-digit', day: 'numeric', month: 'short' })
}

async function scrollDown() {
  await nextTick()
  if (list.value) list.value.scrollTop = list.value.scrollHeight
}

async function loadAll() {
  msgs.value = await call('construction_core.api.portal.messages', { project, limit: 50 })
  scrollDown()
}

async function poll() {
  try {
    const last = msgs.value[msgs.value.length - 1]
    const fresh = await call('construction_core.api.portal.messages', { project, after: last?.creation })
    const known = new Set(msgs.value.map((m) => m.name))
    const added = fresh.filter((m: any) => !known.has(m.name))
    if (added.length) {
      msgs.value.push(...added)
      scrollDown()
    }
    // refresh answered approvals
    const pending = msgs.value.filter((m) => m.kind === 'Approval' && m.approval_status === 'Pending')
    if (pending.length) {
      const all = await call('construction_core.api.portal.messages', { project, limit: 50 })
      const byName = new Map(all.map((m: any) => [m.name, m]))
      msgs.value = msgs.value.map((m) => (byName.get(m.name) as any) || m)
    }
  } catch {
    /* keep polling */
  }
}

async function send(fileUrl?: string) {
  if (!text.value.trim() && !fileUrl) return
  sending.value = true
  try {
    const m = await call('construction_core.api.portal.send_message', { project, text: text.value, file_url: fileUrl }, true)
    text.value = ''
    if (!msgs.value.find((x) => x.name === m.name)) msgs.value.push(m)
    scrollDown()
  } catch (e: any) {
    error.value = e.message
  } finally {
    sending.value = false
  }
}

async function attach(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const blob = await resizePhoto(file)
    const up = await uploadFile(blob, file.name.replace(/\.[^.]+$/, '') + '.jpg', '', '', () => {})
    await send(up.file_url)
  } catch (e: any) {
    error.value = e.message
  }
}

async function sendApproval() {
  try {
    const m = await call('construction_core.api.portal.request_approval', { project, ...approval }, true)
    msgs.value.push(m)
    approval.title = ''
    approval.detail = ''
    approval.amount = null
    showApproval.value = false
    scrollDown()
  } catch (e: any) {
    error.value = e.message
  }
}

async function answer(m: any, value: string) {
  try {
    const updated = await call('construction_core.api.portal.answer_approval', { message: m.name, answer: value }, true)
    Object.assign(m, updated)
  } catch (e: any) {
    error.value = e.message
  }
}

me.fetch()
onMounted(async () => {
  try {
    projectName.value = (await call('construction_core.api.portal.project_detail', { project })).project_name
    await loadAll()
  } catch (e: any) {
    error.value = e.message
  }
  timer = window.setInterval(poll, POLL_MS)
})
onUnmounted(() => window.clearInterval(timer))
</script>
