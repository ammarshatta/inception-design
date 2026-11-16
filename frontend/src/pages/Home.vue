<template>
  <main class="mx-auto flex min-h-full max-w-md flex-col">
    <p v-if="me.loading" class="p-5 text-base text-[#5B6661]">{{ __('جاري التحميل…') }}</p>
    <template v-else-if="me.data">
      <header class="flex flex-col gap-0.5 px-5 pb-2 pt-5">
        <span v-if="me.data.branding.office_name" class="text-sm text-[#5B6661]">{{ me.data.branding.office_name }}</span>
        <h1 data-testid="greeting" class="text-2xl font-bold">{{ __('أهلاً، {0}', [me.data.full_name]) }}</h1>
        <div class="mt-1 flex items-center gap-2">
          <SyncBadge />
          <RouterLink to="/settings" class="text-xs font-semibold text-[#1D6B57]" data-testid="open-settings">{{ __('الإعدادات والإشعارات') }}</RouterLink>
          <RouterLink v-if="me.data.features?.enable_ai_assistant && (me.data.roles.engineer || me.data.roles.admin)" to="/assistant" class="text-xs font-semibold text-[#1D6B57]" data-testid="open-assistant">{{ __('المساعد') }}</RouterLink>
        </div>
      </header>

      <RouterLink v-if="me.data.roles.foreman" to="/foreman" class="mx-4 mt-2 flex min-h-[48px] items-center justify-center rounded-[14px] bg-[#17201D] font-bold text-white" data-testid="open-foreman">{{ __('شغلي النهارده') }}</RouterLink>

      <section v-if="signatures.length" class="flex flex-col gap-2 px-4 pt-2" data-testid="sign-list">
        <h2 class="px-1 text-sm font-semibold text-[#5B6661]">{{ __('مستندات للتوقيع') }}</h2>
        <RouterLink
          v-for="s in signatures"
          :key="s.name"
          :to="`/sign/${encodeURIComponent(s.name)}`"
          class="flex items-center justify-between rounded-[14px] p-3.5 text-[#17201D]"
          :class="['Sent', 'Viewed'].includes(s.status) ? 'bg-[#FBEFDF]' : 'bg-white'"
          data-testid="sign-item"
        >
          <span class="text-sm font-semibold">{{ s.title }}</span>
          <span class="text-xs">{{ ['Sent', 'Viewed'].includes(s.status) ? __('وقّع') : s.status === 'Signed' ? __('اتوقّع') : s.status }}</span>
        </RouterLink>
      </section>

      <section v-if="dash" class="mx-4 mt-2 flex flex-col gap-2 rounded-[14px] bg-white p-3.5" data-testid="engineer-dashboard">
        <h2 class="text-sm font-bold">{{ __('أولوياتي النهارده') }}</h2>
        <div class="grid grid-cols-3 gap-2 text-center">
          <div class="flex flex-col rounded-lg bg-[#F4F5F2] p-2"><span class="num text-lg font-bold">{{ dash.tasks_today.length }}</span><span class="text-[11px] text-[#5B6661]">{{ __('مهام النهارده') }}</span></div>
          <div class="flex flex-col rounded-lg bg-[#F4F5F2] p-2"><span class="num text-lg font-bold" :class="dash.overdue_selections.length ? 'text-[#B42318]' : ''">{{ dash.overdue_selections.length }}</span><span class="text-[11px] text-[#5B6661]">{{ __('اختيارات متأخرة') }}</span></div>
          <div class="flex flex-col rounded-lg bg-[#F4F5F2] p-2"><span class="num text-lg font-bold">{{ dash.pending_approvals.length + dash.client_requests.length }}</span><span class="text-[11px] text-[#5B6661]">{{ __('مستني رد') }}</span></div>
        </div>
        <ul class="text-sm">
          <li v-for="t in dash.tasks_today" :key="t.name" class="border-t border-[#EEF0EC] py-1.5">{{ t.subject }} <span class="text-xs text-[#5B6661]">· {{ t.project_name }}</span></li>
          <li v-for="s in dash.overdue_selections" :key="s.name" class="border-t border-[#EEF0EC] py-1.5 text-[#B42318]">{{ __('اختيار متأخر') }}: {{ s.title }} <span class="text-xs">· {{ s.project_name }}</span></li>
          <li v-for="a in dash.pending_approvals" :key="a.name" class="border-t border-[#EEF0EC] py-1.5">{{ __('موافقة') }}: {{ a.approval_title }} <span class="text-xs text-[#5B6661]">· {{ a.project_name }}</span></li>
          <li v-for="c in dash.client_requests" :key="c.name" class="border-t border-[#EEF0EC] py-1.5">{{ __('طلب تعديل') }}: {{ c.title }} <span class="text-xs text-[#5B6661]">· {{ c.project_name }}</span></li>
        </ul>
      </section>

      <section v-if="projects.length || !loadingProjects" class="flex flex-col gap-2.5 px-4 pb-24 pt-2">
        <h2 class="px-1 text-sm font-semibold text-[#5B6661]">{{ __('مشاريعي') }}</h2>
        <p v-if="!projects.length" class="px-1 text-sm text-[#5B6661]">{{ __('مفيش مشاريع متضافة ليك لسه.') }}</p>
        <RouterLink
          v-for="p in projects"
          :key="p.name"
          :to="projectLink(p.name)"
          data-testid="project-card"
          class="flex flex-col gap-2 rounded-[14px] bg-white p-3.5 text-[#17201D]"
        >
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-base font-bold">{{ p.project_name }}</span>
            <span class="num text-lg font-bold">{{ pct(p.weighted_progress) }}</span>
          </div>
          <ProgressBar :value="p.weighted_progress" />
          <div class="flex justify-between text-xs text-[#5B6661]">
            <span>{{ p.current_stage || '—' }}</span>
            <span>{{ relDate(p.last_update_on) }}</span>
          </div>
        </RouterLink>
      </section>
      <p v-if="error" class="px-5 text-sm text-[#B42318]">{{ error }}</p>
    </template>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { me } from '@/data/me'
import { call } from '@/lib/api'
import { cachedCall } from '@/lib/offline'
import SyncBadge from '@/components/SyncBadge.vue'
import { pct, relDate } from '@/lib/format'
import ProgressBar from '@/components/ProgressBar.vue'

const router = useRouter()
const projects = ref<any[]>([])
const signatures = ref<any[]>([])
const dash = ref<any>(null)

function isClientOnly() {
  const r = me.data?.roles
  return !!r?.client && !r?.engineer && !r?.admin
}
function isSigner() {
  const r = me.data?.roles
  return isClientOnly() || (!!r?.subcontractor && !r?.engineer && !r?.admin)
}
function projectLink(name: string) {
  return isClientOnly() ? `/c/${encodeURIComponent(name)}` : `/projects/${encodeURIComponent(name)}`
}
const loadingProjects = ref(true)
const error = ref('')

me.fetch()
onMounted(async () => {
  try {
    projects.value = await cachedCall('construction_core.api.portal.my_projects')
    await me.promise?.catch(() => {})
    if (!me.data) await me.fetch()
    if (me.data?.roles?.engineer) {
      dash.value = await cachedCall('construction_core.analytics.engineer_dashboard').catch(() => null)
    }
    if (isSigner()) {
      signatures.value = await call('construction_core.esign.my_signature_requests')
      const pending = signatures.value.some((s) => ['Sent', 'Viewed'].includes(s.status))
      if (isClientOnly() && !pending && projects.value.length === 1) router.replace(projectLink(projects.value[0].name))
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loadingProjects.value = false
  }
})
</script>
