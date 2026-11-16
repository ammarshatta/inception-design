import { test, expect } from '@playwright/test'

// Phase 8: the client signs on the phone with a code; the project is created (P08-01..P08-04).
const client = { user: process.env.E2E_SIGN_CLIENT || '', pwd: process.env.E2E_SIGN_CLIENT_PASSWORD || '' }
const request = process.env.E2E_SIGN_REQUEST || ''
const adminPassword = process.env.E2E_ADMIN_PASSWORD || ''
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'

test.use({ viewport: { width: 360, height: 780 } })

test('client signs with a code and the project is created', async ({ page, browser }) => {
  test.skip(!client.user || !request || !adminPassword, 'Set E2E_SIGN_* and E2E_ADMIN_PASSWORD')
  expect((await page.request.post('/api/method/login', { form: { usr: client.user, pwd: client.pwd } })).ok()).toBeTruthy()

  await page.goto('/portal')
  await expect(page.getByTestId('sign-item').first()).toBeVisible()
  await page.getByTestId('sign-item').first().click()
  await expect(page.getByTestId('request-otp')).toBeVisible()
  await page.screenshot({ path: `${shotsDir}/50-sign-request-360.png`, fullPage: true })
  await page.getByTestId('request-otp').click()
  await expect(page.getByTestId('otp-input')).toBeVisible()

  // Read the code the way a test mail outbox would (test sites only)
  const admin = await browser.newContext()
  expect((await admin.request.post('/api/method/login', { form: { usr: 'Administrator', pwd: adminPassword } })).ok()).toBeTruthy()
  const otp = (await (await admin.request.get(`/api/method/construction_core.tests.e2e_setup.peek_otp?request=${request}`)).json()).message
  expect(otp).toMatch(/^\d{6}$/)
  await admin.close()

  await page.getByTestId('otp-input').fill(otp)
  const pad = page.getByTestId('signature-pad')
  const box = (await pad.boundingBox())!
  await page.mouse.move(box.x + 30, box.y + 90)
  await page.mouse.down()
  for (const [dx, dy] of [[60, 40], [110, 100], [160, 50], [220, 95], [270, 60]]) {
    await page.mouse.move(box.x + dx, box.y + dy, { steps: 6 })
  }
  await page.mouse.up()
  await page.screenshot({ path: `${shotsDir}/51-sign-drawn-360.png`, fullPage: true })
  await page.getByTestId('sign').click()
  await expect(page.getByTestId('signed-banner')).toBeVisible({ timeout: 30000 })
  await expect(page.getByTestId('open-project')).toBeVisible()
  await page.getByTestId('open-project').click()
  await expect(page.getByTestId('client-progress')).toBeVisible()
  await page.screenshot({ path: `${shotsDir}/52-project-after-signing-360.png`, fullPage: true })
})
