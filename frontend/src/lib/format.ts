export function pct(v: number | null | undefined): string {
  return `${Math.round(Number(v) || 0)}%`
}

export function relDate(value?: string | null): string {
  if (!value) return 'لسه مفيش تحديثات'
  const d = new Date(value.replace(' ', 'T'))
  const days = Math.floor((Date.now() - d.getTime()) / 86400000)
  if (days <= 0) return 'آخر تحديث: النهارده'
  if (days === 1) return 'آخر تحديث: امبارح'
  return `آخر تحديث: من ${days} أيام`
}

export function shortDate(value?: string | null): string {
  if (!value) return ''
  const d = new Date(value.replace(' ', 'T'))
  return d.toLocaleDateString('ar-EG-u-nu-latn', { day: 'numeric', month: 'long' })
}
