export function money(v: number | null | undefined): string {
  return (Number(v) || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })
}
