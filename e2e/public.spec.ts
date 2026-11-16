import { test, expect } from '@playwright/test'

// Phase 5: visitor flow from home to a Lead, and the rate limit (P05-01..P05-03, P05-05).
const adminPassword = process.env.E2E_ADMIN_PASSWORD || ''
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'

test('visitor: home → designs → filter → design → request → Lead', async ({ page, browser }) => {
  test.skip(!adminPassword, 'Set E2E_ADMIN_PASSWORD (to check the Lead)')
  await page.setViewportSize({ width: 360, height: 780 })
  await page.goto('/')
  await expect(page.getByTestId('cta')).toBeVisible()
  await page.screenshot({ path: `${shotsDir}/30-public-home-360.png`, fullPage: true })

  await page.getByTestId('cta').click()
  await expect(page).toHaveURL(/\/designs/)
  await page.getByTestId('filter-style').selectOption('مودرن')
  await page.getByTestId('apply-filters').click()
  await expect(page).toHaveURL(/style=/)
  await expect(page.getByTestId('design-card').first()).toBeVisible()
  await page.screenshot({ path: `${shotsDir}/31-public-designs-360.png`, fullPage: true })

  await page.getByTestId('design-card').first().click()
  await expect(page.getByTestId('design-page')).toBeVisible()
  await expect(page.getByTestId('floor-plan')).toBeVisible()
  await expect(page.getByTestId('design-stages').locator('li')).toHaveCount(6)
  await expect(page.getByTestId('cost-range')).toContainText('التكلفة التقديرية')
  await page.screenshot({ path: `${shotsDir}/32-public-design-360.png`, fullPage: true })

  const mobile = '0101' + String(Date.now()).slice(-7)
  await page.fill('input[name=full_name]', 'زائر من Playwright')
  await page.fill('input[name=mobile]', mobile)
  await page.selectOption('select[name=governorate]', 'الجيزة')
  await page.fill('input[name=apartment_area_m2]', '140')
  await page.check('input[name=consent]')
  await page.getByTestId('request-submit').click()
  await expect(page.locator('#request-msg')).toContainText('وصلنا طلبك')

  const admin = await browser.newContext()
  const login = await admin.request.post('/api/method/login', { form: { usr: 'Administrator', pwd: adminPassword } })
  expect(login.ok()).toBeTruthy()
  const res = await admin.request.get(
    `/api/resource/Lead?filters=${encodeURIComponent(JSON.stringify([['mobile_no', '=', mobile]]))}&fields=${encodeURIComponent('["name","design_template","governorate"]')}`,
  )
  const leads = (await res.json()).data
  expect(leads.length).toBe(1)
  expect(leads[0].governorate).toBe('الجيزة')
  expect(leads[0].design_template).toBeTruthy()
  await admin.close()
})

test('privacy and data-deletion pages are in Arabic', async ({ page }) => {
  await page.goto('/privacy')
  await expect(page.getByTestId('privacy')).toContainText('سياسة الخصوصية')
  await page.goto('/data-deletion')
  await expect(page.getByTestId('data-deletion')).toContainText('حذف')
})

test('private or missing project and unknown design return 404', async ({ page }) => {
  for (const url of ['/projects/no-such-project', '/designs/no-such-design', '/p/PROJ-9999?t=nope']) {
    const res = await page.goto(url)
    expect(res?.status(), url).toBe(404)
  }
})

test('the 6th request from one IP within an hour is rejected', async ({ playwright, baseURL }) => {
  const ctx = await playwright.request.newContext({ baseURL })
  const statuses: number[] = []
  for (let i = 0; i < 6; i++) {
    const r = await ctx.post('/api/method/construction_core.api.public.request_design', {
      form: { full_name: `حد ${i}`, mobile: '0122' + String(1000000 + i), governorate: 'القاهرة', consent: '1' },
    })
    statuses.push(r.status())
  }
  // The first test already sent one request from this IP, so the limit can hit at 5 or 6.
  expect(statuses.slice(0, 4).every((s) => s === 200), JSON.stringify(statuses)).toBeTruthy()
  expect(statuses[5], JSON.stringify(statuses)).toBe(429)
  await ctx.dispose()
})
