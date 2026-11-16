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
