<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col pb-24">
    <PageHeader :title="__('المستندات')" :back="client ? `/c/${encodeURIComponent(name)}` : `/projects/${encodeURIComponent(name)}`" />
    <p v-if="error" class="mx-4 rounded-lg bg-[#FDE8E6] px-3 py-2 text-sm text-[#B42318]" role="alert" data-testid="error">{{ error }}</p>

    <div class="flex flex-col gap-2 px-4 pb-2">
      <input v-model="search" type="search" class="min-h-[44px] rounded-xl border border-[#E2E5E0] bg-white px-3 text-sm" :placeholder="__('دوّر بالاسم أو المجلد')" data-testid="doc-search" @input="debouncedLoad" />
      <div class="flex gap-1.5 overflow-x-auto pb-1">
        <button v-for="f in ['', ...folders]" :key="f" class="min-h-[36px] shrink-0 rounded-full border px-3 text-xs font-semibold" :class="folder === f ? 'border-[#1D6B57] bg-[#1D6B57] text-white' : 'border-[#E2E5E0] bg-white'" @click="folder = f; load()">{{ f || __('الكل') }}</button>
      </div>
    </div>

    <p v-if="loaded && !docs.length" class="px-5 text-sm text-[#5B6661]" data-testid="no-docs">{{ __('مفيش مستندات.') }}</p>
    <article v-for="d in docs" :key="d.name" class="mx-4 mb-2 flex flex-col gap-1.5 rounded-[14px] bg-white p-3.5" data-testid="document">
      <div class="flex items-center justify-between gap-2">
        <span class="text-sm font-bold">{{ d.title }}</span>
        <span class="shrink-0 rounded-full bg-[#E3F0EB] px-2 py-0.5 text-[11px] font-semibold text-[#1D6B57]">{{ d.folder }}</span>
      </div>
      <div class="flex items-center justify-between text-xs text-[#5B6661]">
        <span>{{ __('النسخة') }} <span class="num">{{ d.current_version }}</span><template v-if="!client && !d.client_visible"> · {{ __('داخلي') }}</template></span>
        <button class="font-semibold text-[#1D6B57]" data-testid="doc-open" @click="open(d.name)">{{ __('فتح') }}</button>
      </div>
      <template v-if="!client">
        <details class="text-xs">
          <summary class="cursor-pointer text-[#5B6661]">{{ __('النسخ القديمة ({0})', [Math.max(d.versions.length - 1, 0)]) }}</summary>
          <ul>
            <li v-for="v in d.versions.slice(1)" :key="v.version_no" class="flex justify-between py-1">
              <span>{{ __('نسخة') }} <span class="num">{{ v.version_no }}</span> {{ v.note }}</span>
              <button class="font-semibold text-[#1D6B57]" @click="open(d.name, v.version_no)">{{ __('فتح') }}</button>
            </li>
          </ul>
        </details>
        <label class="flex min-h-[40px] cursor-pointer items-center justify-center rounded-lg border border-dashed border-[#AEB7B1] text-xs font-semibold text-[#1D6B57]">
          {{ busy === d.name ? __('بيترفع…') : __('+ نسخة جديدة') }}
          <input type="file" class="hidden" data-testid="doc-new-version" @change="upload($event, d.name)" />
        </label>
      </template>
    </article>

    <section v-if="!client" class="mx-4 mt-2 flex flex-col gap-2 rounded-[14px] bg-white p-3.5" data-testid="new-document">
      <h2 class="text-sm font-bold">{{ __('مستند جديد') }}</h2>
      <input v-model="newTitle" class="min-h-[44px] rounded-lg border border-[#E2E5E0] px-3 text-sm" :placeholder="__('العنوان')" data-testid="doc-title" />
      <select v-model="newFolder" class="min-h-[44px] rounded-lg border border-[#E2E5E0] bg-white px-3 text-sm" data-testid="doc-folder">
        <option v-for="f in folders" :key="f" :value="f">{{ f }}</option>
      </select>
      <label class="flex items-center gap-2 text-sm"><input v-model="newVisible" type="checkbox" data-testid="doc-visible" /> {{ __('يظهر للعميل') }}</label>
      <label class="flex min-h-[44px] cursor-pointer items-center justify-center rounded-lg bg-[#1D6B57] text-sm font-bold text-white">
        {{ busy === 'new' ? __('بيترفع…') : __('اختار الملف وارفعه') }}
        <input type="file" class="hidden" data-testid="doc-file" @change="upload($event)" />
      </label>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { call, uploadFile } from '@/lib/api'
import { __ } from '@/translate'
import PageHeader from '@/components/PageHeader.vue'

const props = defineProps<{ name: string }>()
const name = props.name
const client = useRoute().path.startsWith('/c/')
const folders = ['عقود', 'رسومات', 'مواصفات', 'تصاريح', 'فواتير', 'أخرى']
const docs = ref<any[]>([])
const loaded = ref(false)
const error = ref('')
const search = ref('')
const folder = ref('')
const busy = ref('')
const newTitle = ref('')
const newFolder = ref('رسومات')
const newVisible = ref(false)
let timer: any = null

async function load() {
  try {
    docs.value = await call('construction_core.documents.project_documents', { project: name, search: search.value || undefined, folder: folder.value || undefined })
    loaded.value = true
  } catch (e: any) {
    error.value = e.message
  }
}
function debouncedLoad() {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
}

async function open(document: string, version?: number) {
  try {
    const url = await call('construction_core.documents.download_url', { document, version })
    window.open(url, '_blank')
  } catch (e: any) {
    error.value = e.message
  }
}

async function upload(ev: Event, document?: string) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!document && !newTitle.value.trim()) {
    error.value = __('اكتب العنوان الأول')
    return
  }
  error.value = ''
  busy.value = document || 'new'
  try {
    const up = await uploadFile(file, file.name, '', '', () => {})
    await call(
      'construction_core.documents.upload_version',
      document
        ? { project: name, file_url: up.file_url, document }
        : { project: name, file_url: up.file_url, title: newTitle.value, folder: newFolder.value, client_visible: newVisible.value ? 1 : 0 },
      true,
    )
    newTitle.value = ''
    await load()
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = ''
  }
}

onMounted(load)
</script>
