import { createResource } from 'frappe-ui'

export type Me = {
  user: string
  full_name: string
  roles: { admin: boolean; engineer: boolean; client: boolean }
  branding: {
    office_name: string
    logo: string
    primary_color: string
    secondary_color: string
    whatsapp_number: string
  }
  features: Record<string, boolean>
}

export const me = createResource({
  url: 'construction_core.api.portal.get_me',
  cache: 'me',
  onError(error: any) {
    // Logged out (or session expired): go to the login page and come back here.
    if (error?.exc_type === 'PermissionError' || error?.status === 403 || error?.status === 401) {
      window.location.href = '/login?redirect-to=' + encodeURIComponent(window.location.pathname)
    }
  },
})
