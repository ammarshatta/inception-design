import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

// Phase 16: offline update with 3 photos + a checklist tick; back online, interrupted by a
// reload mid-sync; everything arrives exactly once (P16-01, P16-03).
const engUser = process.env.E2E_ENG_USER || ''
const engPassword = process.env.E2E_ENG_PASSWORD || ''
const project = process.env.E2E_ENG_PROJECT || ''
const photosDir = process.env.E2E_PHOTOS_DIR || ''
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'

test.use({ viewport: { width: 360, height: 780 } })
test.setTimeout(240_000)

async function spaGo(page: any, path: string) {
  await page.evaluate((u: string) => {
    history.pushState({}, '', u)
    dispatchEvent(new PopStateEvent('popstate'))
  }, path)
}

test('offline: queued update, photos and tick arrive exactly once', async ({ page, context }) => {
  test.skip(!engUser || !project || !photosDir, 'Set E2E_ENG_* and E2E_PHOTOS_DIR')
  expect((await page.request.post('/api/method/login', { form: { usr: engUser, pwd: engPassword } })).ok()).toBeTruthy()
  const projectPath = `/portal/projects/${encodeURIComponent(project)}`

  // Online first: screens and their code are loaded and cached for offline use
  await page.goto('/portal/sync')
  await expect(page.getByTestId('sync-empty')).toBeVisible()
  await spaGo(page, projectPath)
  await page.getByTestId('stage-row').first().click()
  await expect(page.getByTestId('checklist-item').first()).toBeVisible()
  const stagePath = new URL(page.url()).pathname
  const stageName = decodeURIComponent(stagePath.split('/stages/')[1])
  await spaGo(page, projectPath)
  await page.getByTestId('new-update').click()
  await expect(page.getByTestId('stage-select')).toBeVisible()

  await context.setOffline(true)
  await page.getByTestId('stage-select').selectOption(stageName)
  const text = `تحديث بدون نت ${Date.now()}`
  await page.getByTestId('update-text').fill(text)
  const photos = fs.readdirSync(photosDir).filter((f) => /\.jpe?g$/i.test(f)).slice(0, 3).map((f) => path.join(photosDir, f))
  await page.getByTestId('file-input').setInputFiles(photos)
  await page.getByTestId('publish').click()
  await expect(page.getByTestId('queued')).toBeVisible({ timeout: 30000 })

  // tick one checklist item, still offline (the stage page comes from the saved copy)
  await spaGo(page, stagePath)
  await expect(page.getByTestId('offline-banner')).toBeVisible()
  const tick = page.locator('label').filter({ has: page.locator('[data-testid="checklist-item"]:not(:checked)') }).first()
  const rowLabel = (await tick.locator('span').first().innerText()).trim()
  await tick.locator('[data-testid="checklist-item"]').check()
  await spaGo(page, '/portal/sync')
  await expect(page.getByTestId('sync-item')).toHaveCount(5)
  await page.screenshot({ path: `${shotsDir}/90-sync-queue-offline-360.png`, fullPage: true })

  // back online, and the page is reloaded in the middle of the sync
  await context.setOffline(false)
  await page.waitForTimeout(400)
  await page.reload()
  await expect(page.getByTestId('sync-empty')).toBeVisible({ timeout: 90000 })

  const res = await page.request.get('/api/method/frappe.client.get_list', {
    params: { doctype: 'Stage Update', filters: JSON.stringify({ project, text }), fields: JSON.stringify(['name']) },
  })
  expect((await res.json()).message.length).toBe(1)
  const detail = (await (await page.request.get(`/api/method/construction_core.api.portal.stage_detail?stage=${encodeURIComponent(stageName)}`)).json()).message
  expect(detail.updates.find((x: any) => x.text === text).media.length).toBe(3)
  expect(detail.checklist.find((c: any) => c.label === rowLabel).done).toBe(1)
})
