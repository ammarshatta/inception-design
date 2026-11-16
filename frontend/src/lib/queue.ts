// Offline queue (phase 16): actions wait in IndexedDB and are sent in order, exactly once
// (each carries a UUID; the server's sync.apply ignores a UUID it has already done).
import { ref } from 'vue'
import { call, uploadFile, ApiError } from '@/lib/api'
import { idbAll, idbDelete, idbPut } from '@/lib/idb'

export type QueueItem = {
  uuid: string
  action: 'create_update' | 'attach_media' | 'tick' | 'save_daily_log' | 'clock'
  payload: Record<string, any>
  label: string
  created: string // phone time, sent as client_time
  status: 'pending' | 'syncing' | 'failed' | 'done'
  attempts: number
  next: number // epoch ms of the next try
  error?: string
  dependsOn?: string // uuid of an earlier item (a photo waits for its update)
  blob?: Blob
  fileName?: string
  fileUrl?: string // set once the photo is uploaded, so a retry does not upload again
  result?: any
  media?: boolean
}

export const pending = ref(0)
export const items = ref<QueueItem[]>([])
let running = false

export function newUuid(): string {
  return (crypto as any).randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function loadAll(): Promise<QueueItem[]> {
  return (await idbAll<QueueItem>('queue')).sort((a, b) => a.created.localeCompare(b.created))
}

async function refresh() {
  const all = await loadAll()
  // the UI gets copies without the photo data
  items.value = all.map((i) => ({ ...i, blob: undefined }))
  pending.value = all.filter((i) => i.status !== 'done').length
}

export async function enqueue(item: Omit<QueueItem, 'uuid' | 'created' | 'status' | 'attempts' | 'next'> & { uuid?: string }) {
  const full: QueueItem = { uuid: item.uuid || newUuid(), created: new Date().toISOString(), status: 'pending', attempts: 0, next: 0, ...item } as QueueItem
  await idbPut('queue', full)
  await refresh()
  try {
    const reg: any = await navigator.serviceWorker?.ready
    await reg?.sync?.register('cc-queue')
  } catch {
    /* Background Sync not available (iOS): the queue runs when the app is open */
  }
  void run()
  return full.uuid
}

export function wifiOnly(): boolean {
  try {
    return localStorage.getItem('cc-wifi-only') === '1'
  } catch {
    return false
  }
}
function onCellular(): boolean {
  const c: any = (navigator as any).connection
  return !!c && c.type === 'cellular'
}

async function sendOne(item: QueueItem, done: Map<string, QueueItem>) {
  const payload = { ...item.payload }
  if (item.dependsOn) {
    const dep = done.get(item.dependsOn)
    if (!dep) return 'wait'
    if (item.action === 'attach_media') payload.update = dep.result?.name || item.dependsOn
  }
  if (item.media) {
    if (wifiOnly() && onCellular()) return 'wait'
    if (!item.fileUrl) {
      const up = await uploadFile(item.blob!, item.fileName || 'photo.jpg', 'Stage Update', payload.update, () => {})
      item.fileUrl = up.file_url
      await idbPut('queue', item)
    }
    payload.file_url = item.fileUrl
  }
  const res = await call('construction_core.sync.apply', { uuid: item.uuid, action: item.action, payload, client_time: item.created }, true)
  return res
}

export async function run() {
  if (running || !navigator.onLine) return
  running = true
  try {
    for (;;) {
      await refresh()
      const all = await loadAll()
      const done = new Map(all.filter((i) => i.status === 'done').map((i) => [i.uuid, i]))
      const now = Date.now()
      const next = all.find((i) => (i.status === 'pending' || i.status === 'syncing') && i.next <= now && (!i.dependsOn || done.has(i.dependsOn)))
      if (!next) break
      next.status = 'syncing'
      await idbPut('queue', next)
      try {
        const res: any = await sendOne(next, done)
        if (res === 'wait') {
          next.status = 'pending'
          next.next = Date.now() + 30_000
        } else if (res.status === 'rejected') {
          next.status = 'failed'
          next.error = res.reason
        } else {
          next.status = 'done'
          next.result = res.result
          delete next.blob
        }
      } catch (e: any) {
        next.attempts += 1
        if (e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 408 && e.status !== 429) {
          next.status = 'failed' // the server refused it: show the reason, never drop it silently
          next.error = e.message
        } else {
          next.status = 'pending' // network or server trouble: try again later
          next.next = Date.now() + Math.min(2 ** next.attempts * 2000, 5 * 60_000)
          next.error = e.message
        }
      }
      await idbPut('queue', next)
    }
    // Done items are kept until every item that depends on them is done, then cleared.
    const all = (await idbAll<QueueItem>('queue'))
    const needed = new Set(all.filter((i) => i.status !== 'done' && i.dependsOn).map((i) => i.dependsOn))
    for (const i of all) if (i.status === 'done' && !needed.has(i.uuid)) await idbDelete('queue', i.uuid)
    await refresh()
  } finally {
    running = false
  }
}

export async function retry(uuid: string) {
  const item = (await loadAll()).find((i) => i.uuid === uuid)
  if (!item) return
  item.status = 'pending'
  item.next = 0
  item.error = undefined
  await idbPut('queue', item)
  await run()
}

export async function discard(uuid: string) {
  await idbDelete('queue', uuid)
  await refresh()
}

export function startQueue() {
  refresh().catch(() => {})
  window.addEventListener('online', () => void run())
  navigator.serviceWorker?.addEventListener('message', (e: MessageEvent) => {
    if (e.data?.type === 'cc-sync') void run()
  })
  setInterval(() => void run(), 20_000)
  void run()
}
