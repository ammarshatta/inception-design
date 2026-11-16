<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col">
    <PageHeader :title="__('تحديث جديد')" :subtitle="project?.project_name" :back="`/projects/${encodeURIComponent(name)}`" />
    <p v-if="error" class="mx-4 rounded-lg bg-[#FDE8E6] px-3 py-2 text-sm text-[#B42318]" role="alert">{{ error }}</p>

    <form v-if="project" class="flex flex-col gap-3 px-4 pb-32" @submit.prevent="submit">
      <label class="flex flex-col gap-1.5">
        <span class="text-[13px] font-semibold">{{ __('المرحلة') }}</span>
        <select v-model="stage" data-testid="stage-select" class="min-h-[48px] rounded-xl border border-[#C9CFC9] bg-white px-3 text-[15px]" :disabled="!!updateName">
          <option v-for="s in project.stages" :key="s.name" :value="s.name">{{ s.stage_name }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-1.5">
        <span class="text-[13px] font-semibold">{{ __('إيه اللي اتعمل النهارده؟') }}</span>
        <textarea v-model="text" rows="3" data-testid="update-text" class="resize-none rounded-xl border border-[#C9CFC9] bg-white px-3 py-2.5 text-[15px]" :disabled="!!updateName"></textarea>
      </label>

      <div v-if="isManual" class="flex flex-col gap-1.5 rounded-[14px] bg-white p-3">
        <div class="flex items-center justify-between">
          <label for="prog" class="text-[13px] font-semibold">{{ __('نسبة المرحلة بعد التحديث') }}</label>
          <span class="num text-base font-bold">{{ progressAfter }}%</span>
        </div>
        <input id="prog" v-model.number="progressAfter" type="range" min="0" max="100" class="w-full accent-[#1D6B57]" :disabled="!!updateName" />
      </div>

      <section class="flex flex-col gap-2 rounded-[14px] bg-white p-3">
        <div class="flex items-center justify-between">
          <span class="text-[13px] font-semibold">{{ __('الصور ({0})', [items.length]) }}</span>
          <span class="text-xs text-[#5B6661]">{{ __('بتتصغّر قبل الرفع ومن غير موقع') }}</span>
        </div>
        <div v-if="items.length" class="grid grid-cols-4 gap-1.5">
          <div v-for="it in items" :key="it.id" class="flex flex-col gap-1" data-testid="upload-item" :data-state="it.state">
            <div class="relative aspect-square overflow-hidden rounded-lg bg-[#DCE1DB]" :class="it.state === 'failed' ? 'ring-2 ring-[#B42318]' : ''">
              <img v-if="it.preview" :src="it.preview" class="h-full w-full object-cover" alt="" />
              <span v-else class="absolute inset-0 flex items-center justify-center text-xs">{{ __('فيديو') }}</span>
              <button
                v-if="it.state === 'done' && it.kind === 'Photo'"
                type="button"
                class="absolute right-1 top-1 rounded px-1 text-[10px] font-bold"
                :class="it.publishable ? 'bg-[#1D6B57] text-white' : 'bg-white/90 text-[#17201D]'"
                :aria-pressed="it.publishable"
                @click="togglePublish(it)"
              >{{ __('مناسبة للنشر') }}</button>
            </div>
            <div class="h-1 overflow-hidden rounded bg-[#E9ECE7]"><div class="h-1" :style="{ width: it.progress * 100 + '%', background: it.state === 'failed' ? '#B42318' : '#1D6B57' }"></div></div>
            <button v-if="it.state === 'failed'" type="button" class="text-[11px] font-semibold text-[#B42318]" @click="retry(it)">{{ __('فشلت · أعد') }}</button>
            <span v-else class="text-[11px] text-[#5B6661]">{{ stateLabel(it) }}</span>
          </div>
        </div>
        <label class="flex min-h-[44px] cursor-pointer items-center justify-center rounded-[10px] border border-dashed border-[#AEB7B1] bg-[#FAFBF9] text-sm font-semibold text-[#1D6B57]">
          {{ __('+ صور أو فيديو (دقيقة / 50MB)') }}
          <input type="file" multiple accept="image/*,video/*" class="hidden" data-testid="file-input" @change="pick" />
        </label>
      </section>

      <label class="flex min-h-[44px] items-center justify-between rounded-[14px] bg-white p-3">
        <span class="flex flex-col"><span class="text-sm font-semibold">{{ __('داخلي فقط') }}</span><span class="text-xs text-[#5B6661]">{{ __('العميل مش هيشوف التحديث ده') }}</span></span>
        <input v-model="internalOnly" type="checkbox" class="h-[22px] w-[22px] accent-[#1D6B57]" data-testid="internal-only" :disabled="!!updateName" />
      </label>

      <div class="fixed inset-x-0 bottom-0 mx-auto max-w-md bg-[#F4F5F2] px-4 pb-5 pt-3">
        <button
          v-if="!finished"
          type="submit"
          data-testid="publish"
          class="min-h-[52px] w-full rounded-[14px] bg-[#1D6B57] text-base font-bold text-white disabled:opacity-60"
          :disabled="busy || (!text && !items.length)"
        >{{ busy ? __('جاري الرفع…') : __('انشر التحديث') }}</button>
        <RouterLink
          v-else
          :to="`/stages/${encodeURIComponent(stage)}`"
          data-testid="done"
          class="flex min-h-[52px] items-center justify-center rounded-[14px] bg-[#1D6B57] text-base font-bold text-white"
        >{{ __('اتنشر ✓ افتح المرحلة') }}</RouterLink>
      </div>
    </form>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { call, uploadFile } from '@/lib/api'
import { checkVideo, resizePhoto } from '@/lib/media'
import PageHeader from '@/components/PageHeader.vue'

type Item = {
  id: number
  file: File
  kind: 'Photo' | 'Video'
  preview: string
  state: 'queued' | 'preparing' | 'uploading' | 'done' | 'failed'
  progress: number
  attempts: number
  rowName?: string
  publishable: boolean
}

const props = defineProps<{ name: string }>()
const name = props.name
const project = ref<any>(null)
const stage = ref('')
const text = ref('')
const progressAfter = ref(0)
const internalOnly = ref(false)
const items = ref<Item[]>([])
const updateName = ref('')
const busy = ref(false)
const finished = ref(false)
const error = ref('')
let nextId = 1

const isManual = computed(() => project.value?.stages.find((s: any) => s.name === stage.value)?.progress_mode === 'Manual')

onMounted(async () => {
  try {
    project.value = await call('construction_core.api.portal.project_detail', { project: name })
    const current = project.value.stages.find((s: any) => s.status === 'In Progress') || project.value.stages.find((s: any) => s.status !== 'Done')
    stage.value = (current || project.value.stages[0])?.name || ''
  } catch (e: any) {
    error.value = e.message
  }
})

async function pick(event: Event) {
  const input = event.target as HTMLInputElement
  error.value = ''
  for (const file of Array.from(input.files || [])) {
    const kind = file.type.startsWith('video/') ? 'Video' : 'Photo'
    if (kind === 'Video') {
      const problem = await checkVideo(file)
      if (problem) {
        error.value = problem
        continue
      }
    }
    items.value.push({
      id: nextId++,
      file,
      kind,
      preview: kind === 'Photo' ? URL.createObjectURL(file) : '',
      state: 'queued',
      progress: 0,
      attempts: 0,
      publishable: false,
    })
  }
  input.value = ''
  if (updateName.value) await uploadAll()
}

function stateLabel(it: Item) {
  return { queued: 'مستني', preparing: 'بيتجهز', uploading: `${Math.round(it.progress * 100)}%`, done: 'اترفعت', failed: '' }[it.state]
}

async function uploadOne(it: Item) {
  it.state = 'preparing'
  it.progress = 0
  const blob = it.kind === 'Photo' ? await resizePhoto(it.file) : it.file
  const fileName = it.kind === 'Photo' ? it.file.name.replace(/\.[^.]+$/, '') + '.jpg' : it.file.name
  for (;;) {
    it.attempts++
    it.state = 'uploading'
    try {
      const up = await uploadFile(blob, fileName, 'Stage Update', updateName.value, (f) => (it.progress = f))
      const res = await call('construction_core.api.portal.attach_media', { update: updateName.value, file_url: up.file_url, kind: it.kind }, true)
      it.rowName = res.row
      it.state = 'done'
      return
    } catch (e) {
      if (it.attempts >= 3) {
        it.state = 'failed'
        return
      }
      await new Promise((r) => setTimeout(r, 1000 * it.attempts))
    }
  }
}

async function uploadAll() {
  busy.value = true
  for (const it of items.value) {
    if (it.state === 'queued') await uploadOne(it)
  }
  busy.value = false
  finished.value = items.value.every((it) => it.state === 'done')
}

async function retry(it: Item) {
  it.attempts = 0
  it.state = 'queued'
  await uploadAll()
}

async function submit() {
  error.value = ''
  busy.value = true
  try {
    if (!updateName.value) {
      updateName.value = await call(
        'construction_core.api.portal.create_stage_update',
        {
          project: name,
          stage: stage.value,
          text: text.value,
          progress_after: isManual.value ? progressAfter.value : null,
          internal_only: internalOnly.value ? 1 : 0,
        },
        true,
      )
    }
    await uploadAll()
  } catch (e: any) {
    error.value = e.message
    busy.value = false
  }
}

async function togglePublish(it: Item) {
  try {
    const res = await call(
      'construction_core.api.portal.set_media_publishable',
      { update: updateName.value, row_name: it.rowName, value: it.publishable ? 0 : 1 },
      true,
    )
    it.publishable = !!res.publishable
  } catch (e: any) {
    error.value = e.message
  }
}
</script>
