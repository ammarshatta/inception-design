import { test, expect } from '@playwright/test'

// Phase 10: the client asks for a change from the portal; a Draft change order exists.
// (Pricing, the admin's send and the signature are covered by unit tests and sign.spec.ts.)
const project = process.env.E2E_ENG_PROJECT || ''
const client = { user: process.env.E2E_CHAT_CLIENT || '', pwd: process.env.E2E_CHAT_CLIENT_PASSWORD || '' }
const adminPassword = process.env.E2E_ADMIN_PASSWORD || ''
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'

test.use({ viewport: { width: 360, height: 780 } })

test('client requests a change from the portal', async ({ page, browser }) => {
  test.skip(!project || !client.user || !adminPassword, 'Set E2E_ENG_PROJECT, E2E_CHAT_CLIENT* and E2E_ADMIN_PASSWORD')
  expect((await page.request.post('/api/method/login', { form: { usr: client.user, pwd: client.pwd } })).ok()).toBeTruthy()
  await page.goto(`/portal/c/${encodeURIComponent(project)}/changes`)
  const text = `نقل مكان الحوض ${Date.now()}`
  await page.getByTestId('change-description').fill(text)
  await page.getByTestId('change-submit').click()
  await expect(page.getByTestId('change-order').first()).toBeVisible()
  await page.screenshot({ path: `${shotsDir}/60-client-changes-360.png`, fullPage: true })

  const admin = await browser.newContext()
  expect((await admin.request.post('/api/method/login', { form: { usr: 'Administrator', pwd: adminPassword } })).ok()).toBeTruthy()
  const res = await admin.request.get(
    `/api/resource/Change Order?filters=${encodeURIComponent(JSON.stringify([['description', '=', text]]))}&fields=${encodeURIComponent('["name","status","source"]')}`,
  )
  const rows = (await res.json()).data
  expect(rows.length).toBe(1)
  expect(rows[0].status).toBe('Draft')
  expect(rows[0].source).toBe('Client Request')
  await admin.close()
})
