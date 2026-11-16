import { test, expect } from '@playwright/test'

// Phase 14: open a PDF plan, calibrate a 5 m wall, measure a 4 × 5 m room, push it to an estimate line.
const adminPassword = process.env.E2E_ADMIN_PASSWORD || ''
const planPdf = process.env.E2E_PLAN_PDF || ''
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'

test.use({ viewport: { width: 1280, height: 900 } })

test('takeoff: calibrate, measure an area, push to an estimate line', async ({ page }) => {
  test.skip(!adminPassword || !planPdf, 'Set E2E_ADMIN_PASSWORD and E2E_PLAN_PDF')
  const req = page.request
  expect((await req.post('/api/method/login', { form: { usr: 'Administrator', pwd: adminPassword } })).ok()).toBeTruthy()
  const customer = (await (await req.post('/api/method/frappe.client.insert', {
    data: { doc: { doctype: 'Customer', customer_name: `عميل القياس ${Date.now()}`, customer_type: 'Individual' } },
  })).json()).message.name
  const est = (await (await req.post('/api/method/frappe.client.insert', {
    data: {
      doc: {
        doctype: 'Estimate', title: 'تسعير من الرسم', customer, estimate_date: new Date().toISOString().slice(0, 10),
        lines: [{ section: 'أرضيات', line_type: 'Other', description: 'سيراميك الريسبشن', qty: 1, unit_cost: 300 }],
      },
    },
  })).json()).message
  const lineName = est.lines[0].name

  await page.goto(`/portal/takeoff?estimate=${encodeURIComponent(est.name)}`)
  await page.getByTestId('takeoff-title').fill('مسقط الشقة')
  await page.getByTestId('takeoff-file').setInputFiles(planPdf)
  const canvas = page.getByTestId('takeoff-canvas')
  await expect(canvas).toBeVisible({ timeout: 20000 })
  await expect(canvas).toHaveAttribute('width', '800')
  const at = async (x: number, y: number) => canvas.click({ position: { x, y } })

  await page.getByTestId('mode-calibrate').click()
  await at(100, 500)
  await at(350, 500)
  await page.getByTestId('calibration-m').fill('5')
  await page.getByTestId('mode-Area').click()
  for (const [x, y] of [[100, 100], [300, 100], [300, 350], [100, 350]]) await at(x, y)
  await page.getByTestId('finish').click()
  await expect(page.getByTestId('measurement-value').first()).toContainText('20.00')
  await page.getByTestId('save-takeoff').click()
  await expect(page).toHaveURL(/\/portal\/takeoff\/TKO-/)
  await expect(page.getByTestId('measurement-value').first()).toContainText('20.00')
  await page.screenshot({ path: `${shotsDir}/80-takeoff.png` })

  await page.getByTestId('estimate-line').first().selectOption(lineName)
  await page.getByTestId('push').first().click()
  await expect(page.getByTestId('push').first()).toContainText('اتضاف')
  const after = (await (await req.get(`/api/method/frappe.client.get?doctype=Estimate&name=${encodeURIComponent(est.name)}`)).json()).message
  expect(after.lines.find((l: any) => l.name === lineName).qty).toBe(20)
})
