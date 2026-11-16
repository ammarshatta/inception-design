// Read-only offline copies of the engineer's main screens (phase 16, P16-02).
import { ref } from 'vue'
import { call, ApiError } from '@/lib/api'
import { idbGet, idbPut } from '@/lib/idb'

/** When the screen shows a saved copy: the time it was saved (ISO), else ''. */
export const servedFromCache = ref('')

function isNetworkError(e: any) {
  return !(e instanceof ApiError) || e.status === 0
}

/** GET a whitelisted method; on success keep a copy, offline return the copy. */
export async function cachedCall<T = any>(method: string, args: Record<string, any> = {}): Promise<T> {
  const key = `${method}?${JSON.stringify(args)}`
  try {
    const data = await call<T>(method, args)
    servedFromCache.value = ''
    idbPut('cache', { data, at: new Date().toISOString() }, key).catch(() => {})
    return data
  } catch (e: any) {
    if (!isNetworkError(e)) throw e
    const hit = await idbGet<{ data: T; at: string }>('cache', key).catch(() => undefined)
    if (!hit) throw e
    servedFromCache.value = hit.at
    return hit.data
  }
}
