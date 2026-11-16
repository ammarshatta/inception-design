// Minimal __() for the portal: Frappe's translation helper with {0} placeholders.
// Real translations are loaded later from Frappe's translation API.
export function __(text: string, args: (string | number)[] = []): string {
  return text.replace(/\{(\d+)\}/g, (_match, i) => String(args[Number(i)] ?? ''))
}

declare module 'vue' {
  interface ComponentCustomProperties {
    __: typeof __
  }
}
