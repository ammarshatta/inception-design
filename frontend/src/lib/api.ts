// Small fetch wrapper for Frappe whitelisted methods (/api/method/...).
declare global {
  interface Window {
    csrf_token?: string
  }
}

export class ApiError extends Error {
  status: number
  excType?: string
  constructor(message: string, status: number, excType?: string) {
    super(message)
    this.status = status
    this.excType = excType
  }
}

function csrfHeaders(): Record<string, string> {
  const token = window.csrf_token
  return token && token !== '{{ csrf_token }}' ? { 'X-Frappe-CSRF-Token': token } : {}
}

function errorMessage(data: any, fallback: string): string {
  try {
    if (data?._server_messages) {
      const msgs = JSON.parse(data._server_messages).map((m: string) => JSON.parse(m).message)
      if (msgs.length) return msgs.join('\n').replace(/<[^>]+>/g, '')
    }
  } catch {
    /* ignore */
  }
  return data?.exception?.split(':').slice(1).join(':').trim() || data?.message || fallback
}

export async function call<T = any>(method: string, args: Record<string, any> = {}, post = false): Promise<T> {
  const url = `/api/method/${method}`
  let res: Response
  if (post) {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...csrfHeaders() },
      body: JSON.stringify(args),
      credentials: 'same-origin',
    })
  } else {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(args)) if (v !== undefined && v !== null) qs.set(k, String(v))
    res = await fetch(`${url}?${qs}`, { headers: { Accept: 'application/json' }, credentials: 'same-origin' })
  }
  let data: any = null
  try {
    data = await res.json()
  } catch {
    /* non-JSON */
  }
  if (!res.ok) {
    if (res.status === 401 || res.status === 403) {
      if (data?.exc_type === 'PermissionError' && !document.cookie.includes('user_id=') ) {
        window.location.href = '/login?redirect-to=' + encodeURIComponent(window.location.pathname)
      }
    }
    throw new ApiError(errorMessage(data, `خطأ ${res.status}`), res.status, data?.exc_type)
  }
  return data?.message as T
}

export type UploadResult = { file_url: string; name: string }

/** Upload one private file with progress; attached to the given document. */
export function uploadFile(
  file: Blob,
  fileName: string,
  doctype: string,
  docname: string,
  onProgress: (fraction: number) => void,
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/method/upload_file', true)
    xhr.setRequestHeader('Accept', 'application/json')
    const token = csrfHeaders()['X-Frappe-CSRF-Token']
    if (token) xhr.setRequestHeader('X-Frappe-CSRF-Token', token)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total)
    }
    xhr.onload = () => {
      let data: any = null
      try {
        data = JSON.parse(xhr.responseText)
      } catch {
        /* ignore */
      }
      if (xhr.status >= 200 && xhr.status < 300 && data?.message?.file_url) {
        onProgress(1)
        resolve({ file_url: data.message.file_url, name: data.message.name })
      } else {
        reject(new ApiError(errorMessage(data, `فشل الرفع (${xhr.status})`), xhr.status))
      }
    }
    xhr.onerror = () => reject(new ApiError('مفيش اتصال', 0))
    const form = new FormData()
    form.append('file', file, fileName)
    form.append('is_private', '1')
    if (doctype) form.append('doctype', doctype)
    if (docname) form.append('docname', docname)
    xhr.send(form)
  })
}
