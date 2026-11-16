import { test, expect, request as pwRequest, type APIRequestContext } from '@playwright/test'
import path from 'path'
import fs from 'fs'

// Phase 13: Material Request → Purchase Order (office) → receipt on site with a photo (engineer
// portal) → Purchase Invoice (office) → the cost shows under the project and stage.
const adminPassword = process.env.E2E_ADMIN_PASSWORD || ''
const engUser = process.env.E2E_ENG_USER || ''
const engPassword = process.env.E2E_ENG_PASSWORD || ''
const project = process.env.E2E_ENG_PROJECT || ''
const photosDir = process.env.E2E_PHOTOS_DIR || ''
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'
const baseURL = process.env.E2E_BASE_URL || 'http://localhost:8000'

async function call(req: APIRequestContext, method: string, data: Record<string, any>) {
  const res = await req.post(`/api/method/${method}`, { data })
  const body = await res.json()
  expect(res.ok(), JSON.stringify(body).slice(0, 800)).toBeTruthy()
  return body.message
}

test.use({ viewport: { width: 360, height: 780 } })

test('Material Request → PO → Receipt with photo → Invoice', async ({ page }) => {
  test.skip(!adminPassword || !engUser || !project || !photosDir, 'Set E2E_ADMIN_PASSWORD, E2E_ENG_*, E2E_PHOTOS_DIR')
  fs.mkdirSync(shotsDir, { recursive: true })
  const admin = await pwRequest.newContext({ baseURL })
  expect((await admin.post('/api/method/login', { form: { usr: 'Administrator', pwd: adminPassword } })).ok()).toBeTruthy()

  const stages = await call(admin, 'frappe.client.get_list', {
    doctype: 'Project Stage', filters: { project }, fields: ['name', 'stage_name'], order_by: 'sort_order asc',
  })
  const stage = stages[0]
  const company = (await call(admin, 'frappe.client.get_value', { doctype: 'Project', filters: project, fieldname: 'company' })).company
  const itemCode = 'أسمنت e2e'
  await admin.post('/api/method/frappe.client.insert', {
    data: { doc: { doctype: 'Item', item_code: itemCode, item_name: itemCode, item_group: 'خامات', stock_uom: 'Nos', is_stock_item: 0 } },
  })
  await admin.post('/api/method/frappe.client.insert', {
    data: { doc: { doctype: 'Supplier', supplier_name: 'مورد e2e', supplier_group: 'موردين خامات' } },
  })
  const day = new Date(Date.now() + 5 * 864e5).toISOString().slice(0, 10)
  let mr = await call(admin, 'frappe.client.insert', {
    doc: {
      doctype: 'Material Request', material_request_type: 'Purchase', company, schedule_date: day,
      items: [{ item_code: itemCode, qty: 30, schedule_date: day, project, project_stage: stage.name }],
    },
  })
  mr = await call(admin, 'frappe.client.submit', { doc: mr })
  const poDraft = await call(admin, 'erpnext.stock.doctype.material_request.material_request.make_purchase_order', { source_name: mr.name })
  poDraft.supplier = 'مورد e2e'
  poDraft.items[0].rate = 80
  let po = await call(admin, 'frappe.client.insert', { doc: poDraft })
  po = await call(admin, 'frappe.client.submit', { doc: po })
  expect(po.items[0].project_stage).toBe(stage.name)

  // engineer on site
  expect((await page.request.post('/api/method/login', { form: { usr: engUser, pwd: engPassword } })).ok()).toBeTruthy()
  await page.goto(`/portal/projects/${encodeURIComponent(project)}`)
  await page.getByTestId('open-deliveries').click()
  const card = page.getByTestId('delivery').filter({ hasText: 'مورد e2e' })
  await expect(card).toBeVisible()
  const photo = fs.readdirSync(photosDir).find((f) => /\.jpe?g$/i.test(f))!
  await card.getByTestId('delivery-photo').setInputFiles(path.join(photosDir, photo))
  await expect(card.getByTestId('confirm-delivery')).toBeEnabled()
  await page.screenshot({ path: path.join(shotsDir, '70-delivery-360.png'), fullPage: true })
  await card.getByTestId('confirm-delivery').click()
  await expect(card.getByTestId('received')).toBeVisible()
  await page.screenshot({ path: path.join(shotsDir, '71-delivery-done-360.png'), fullPage: true })

  // office: invoice from the receipt
  const prs = await call(admin, 'frappe.client.get_list', {
    doctype: 'Purchase Receipt Item', parent: 'Purchase Receipt', filters: { purchase_order: po.name }, fields: ['parent'],
  })
  const prName = prs[0].parent
  await expect(card.getByTestId('received')).toContainText(prName)
  const prDoc = await call(admin, 'frappe.client.get', { doctype: 'Purchase Receipt', name: prName })
  expect(prDoc.docstatus).toBe(1)
  expect(prDoc.delivery_note_photo).toMatch(/^\/private\/files\//)
  const piDraft = await call(admin, 'erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice', { source_name: prName })
  let pi = await call(admin, 'frappe.client.insert', { doc: piDraft })
  pi = await call(admin, 'frappe.client.submit', { doc: pi })
  expect(pi.items[0].project_stage).toBe(stage.name)

  const report = await call(admin, 'frappe.desk.query_report.run', {
    report_name: 'Project Financial Summary', filters: { project },
  })
  const row = report.result.find((r: any) => r.label === stage.stage_name && r.amount >= 2400)
  expect(row, JSON.stringify(report.result).slice(0, 800)).toBeTruthy()
  await admin.dispose()
})
