import { test, expect } from '@playwright/test'

// Phase 12: consent first, then clock in at the site; the daily log saves once per day (P12-01, P12-02).
const engUser = process.env.E2E_ENG_USER || ''
const engPassword = process.env.E2E_ENG_PASSWORD || ''
const project = process.env.E2E_ENG_PROJECT || ''

test.use({ viewport: { width: 360, height: 780 }, geolocation: { latitude: 30.0084, longitude: 31.4301, accuracy: 10 }, permissions: ['geolocation'] })

test('engineer: consent, clock in inside the site, save the daily log', async ({ page }) => {
  test.skip(!engUser || !project, 'Set E2E_ENG_*')
  const res = await page.request.post('/api/method/login', { form: { usr: engUser, pwd: engPassword } })
  expect(res.ok()).toBeTruthy()

  await page.goto(`/portal/projects/${encodeURIComponent(project)}/daily`)
  await expect(page.getByTestId('clock-card')).toBeVisible()
  await page.getByTestId('worker').fill('عم سعيد')
  await page.getByTestId('clock-in').click()
  // nothing is recorded before consent
  await expect(page.getByTestId('consent')).toBeVisible()
  await page.getByTestId('consent-accept').click()
  await expect(page.getByTestId('clock-msg')).toContainText('اتسجل الحضور')

  const ev = await page.request.get('/api/method/frappe.client.get_list', {
    params: { doctype: 'Clock Event', fields: JSON.stringify(['inside_geofence', 'needs_approval']), filters: JSON.stringify({ project }) },
  })
  const rows = (await ev.json()).message
  expect(rows.length).toBe(1)
  expect(rows[0].inside_geofence).toBe(1)
  expect(rows[0].needs_approval).toBe(0)

  await page.getByTestId('add-manpower').click()
  await page.getByTestId('manpower-row').last().locator('input').first().fill('محارة')
  await page.getByTestId('work-done').fill('بطانة الريسبشن')
  await page.getByTestId('save-log').click()
  await expect(page.getByTestId('save-log')).toContainText('اتحفظ')

  await page.reload()
  await expect(page.getByTestId('work-done')).toHaveValue('بطانة الريسبشن')
})
