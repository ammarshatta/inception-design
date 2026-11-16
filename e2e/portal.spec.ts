import { test, expect } from '@playwright/test'

// Story P00-02. Needs a user on the local site:
//   E2E_USER / E2E_PASSWORD (and the user's full name in E2E_FULL_NAME)
const user = process.env.E2E_USER || ''
const password = process.env.E2E_PASSWORD || ''
const fullName = process.env.E2E_FULL_NAME || ''

test('logged out: /portal redirects to login, then back to /portal', async ({ page }) => {
  await page.goto('/portal')
  await expect(page).toHaveURL(/\/login/)
  expect(new URL(page.url()).searchParams.get('redirect-to')).toBe('/portal')
})

test('logged in: Arabic RTL greeting with the full name', async ({ page }) => {
  test.skip(!user || !password, 'Set E2E_USER and E2E_PASSWORD')
  // Log in through Frappe's login API (same session cookie as the login form)
  const res = await page.request.post('/api/method/login', { form: { usr: user, pwd: password } })
  expect(res.ok(), await res.text()).toBeTruthy()

  const portal = await page.goto('/portal')
  expect(portal?.status()).toBe(200)
  expect(new URL(page.url()).pathname).toMatch(/^\/portal\/?$/)
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar')
  const greeting = page.getByTestId('greeting')
  await expect(greeting).toContainText('أهلاً', { timeout: 15000 })
  if (fullName) await expect(greeting).toContainText(fullName)
})

// Story P02-04: a temporary password allows only the change-password page.
const tempUser = process.env.E2E_TEMP_USER || ''
const tempPassword = process.env.E2E_TEMP_PASSWORD || ''

test('temporary password: only the change-password page until changed', async ({ page }) => {
  test.skip(!tempUser || !tempPassword, 'Set E2E_TEMP_USER and E2E_TEMP_PASSWORD')
  const res = await page.request.post('/api/method/login', { form: { usr: tempUser, pwd: tempPassword } })
  expect(res.ok(), await res.text()).toBeTruthy()

  await page.goto('/portal')
  await expect(page).toHaveURL(/\/update-password/)
  const api = await page.request.get('/api/method/construction_core.api.portal.get_me')
  expect(api.status()).toBe(403)

  const newPassword = 'Nw-' + tempPassword + '-9x'
  // Frappe's page enables "Confirm" from keyup handlers, so type like a user would
  await page.locator('#old_password').pressSequentially(tempPassword)
  await page.locator('#new_password').pressSequentially(newPassword)
  await page.locator('#confirm_password').pressSequentially(newPassword)
  await expect(page.locator('#update')).toBeEnabled({ timeout: 10000 })
  await page.locator('#update').click()
  await page.waitForURL(/\/portal/, { timeout: 15000 })
  await expect(page.getByTestId('greeting')).toContainText('أهلاً', { timeout: 15000 })
})
