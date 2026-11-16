import { test, expect, type APIRequestContext } from '@playwright/test'

// Phase 7: Lead → Opportunity → Estimate → Quotation, end to end through the server API,
// then the Kanban and the Quotation are opened in the desk.
const adminPassword = process.env.E2E_ADMIN_PASSWORD || ''
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'

async function call(req: APIRequestContext, method: string, data: Record<string, any>) {
  const res = await req.post(`/api/method/${method}`, { data })
  const body = await res.json()
  expect(res.ok(), JSON.stringify(body).slice(0, 500)).toBeTruthy()
  return body.message
}

test('Lead → Opportunity → Estimate → Quotation', async ({ page }) => {
  test.skip(!adminPassword, 'Set E2E_ADMIN_PASSWORD')
  const req = page.request
  expect((await req.post('/api/method/login', { form: { usr: 'Administrator', pwd: adminPassword } })).ok()).toBeTruthy()

  const lead = await call(req, 'frappe.client.insert', {
    doc: { doctype: 'Lead', lead_name: 'عميل المبيعات', first_name: 'عميل', mobile_no: '01099990000', governorate: 'القاهرة' },
  })
  const oppDraft = await call(req, 'erpnext.crm.doctype.lead.lead.make_opportunity', { source_name: lead.name })
  const opp = await call(req, 'frappe.client.insert', { doc: oppDraft })
  expect(opp.pipeline_stage).toBe('جديد')

  const est = await call(req, 'frappe.client.insert', {
    doc: {
      doctype: 'Estimate',
      title: 'تسعير شقة 150 م²',
      lead: lead.name,
      opportunity: opp.name,
      overhead_pct: 10,
      profit_pct: 15,
      lines: [
        { section: 'تأسيس', line_type: 'Other', description: 'تأسيس سباكة وكهرباء', qty: 1, unit_cost: 60000 },
        { section: 'تشطيب', line_type: 'Other', description: 'محارة ودهانات', qty: 150, unit_cost: 400 },
      ],
    },
  })
  expect(Number(est.grand_total)).toBeCloseTo((60000 + 60000) * 1.1 * 1.15, 2)
  const submitted = await call(req, 'frappe.client.submit', { doc: est })
  expect(submitted.status).toBe('Approved')

  const quotation = await call(req, 'construction_core.sales.make_quotation', { estimate: est.name })
  const q = await call(req, 'frappe.client.get', { doctype: 'Quotation', name: quotation })
  expect(q.items.length).toBe(2)
  expect(q.estimate).toBe(est.name)

  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto(`/app/opportunity/view/kanban/${encodeURIComponent('مسار المبيعات')}`)
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `${shotsDir}/40-sales-kanban.png` })
  await page.goto(`/app/quotation/${encodeURIComponent(quotation)}`)
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `${shotsDir}/41-quotation.png` })
})
