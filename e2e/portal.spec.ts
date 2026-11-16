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
  await page.goto('/login?redirect-to=/portal')
  await page.fill('#login_email', user)
  await page.fill('#login_password', password)
  await page.locator('form.form-login button[type="submit"]').first().click()
  await page.waitForURL(/\/portal/)
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar')
  const greeting = page.getByTestId('greeting')
  await expect(greeting).toContainText('أهلاً')
  if (fullName) await expect(greeting).toContainText(fullName)
})
