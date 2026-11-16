import { test, expect, type Page } from '@playwright/test'
import fs from 'fs'
import path from 'path'

// Phase 3: engineer posts an update with 10 photos on Slow 4G (stories P03-01, P03-02).
const engUser = process.env.E2E_ENG_USER || ''
const engPassword = process.env.E2E_ENG_PASSWORD || ''
const project = process.env.E2E_ENG_PROJECT || ''
const photosDir = process.env.E2E_PHOTOS_DIR || ''
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'

test.use({ viewport: { width: 360, height: 780 } })
test.setTimeout(300_000)

async function login(page: Page) {
  const res = await page.request.post('/api/method/login', { form: { usr: engUser, pwd: engPassword } })
  expect(res.ok(), await res.text()).toBeTruthy()
}

function hasExif(buf: Buffer): boolean {
  // An EXIF block starts with "Exif\0\0" inside an APP1 segment.
  return buf.includes(Buffer.from([0x45, 0x78, 0x69, 0x66, 0x00, 0x00]))
}

test('engineer: 10 large photos on Slow 4G, all small and without GPS', async ({ page, browser }) => {
  test.skip(!engUser || !project || !photosDir, 'Set E2E_ENG_* and E2E_PHOTOS_DIR')
  fs.mkdirSync(shotsDir, { recursive: true })
  await login(page)

  await page.goto('/portal')
  await expect(page.getByTestId('project-card').first()).toBeVisible()
  await page.screenshot({ path: path.join(shotsDir, '01-my-projects-360.png'), fullPage: true })

  await page.goto(`/portal/projects/${encodeURIComponent(project)}`)
  await expect(page.getByTestId('stage-row').first()).toBeVisible()
  await page.screenshot({ path: path.join(shotsDir, '02-project-360.png'), fullPage: true })

  await page.getByTestId('new-update').click()
  await expect(page.getByTestId('stage-select')).toBeVisible()

  // Slow 4G (Chrome DevTools preset)
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Network.enable')
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 562.5,
    downloadThroughput: (1.6 * 1024 * 1024) / 8 * 0.9,
    uploadThroughput: (750 * 1024) / 8 * 0.9,
  })

  const files = fs.readdirSync(photosDir).filter((f) => f.endsWith('.jpg')).map((f) => path.join(photosDir, f))
  expect(files.length).toBe(10)
  await page.getByTestId('update-text').fill('تجربة رفع 10 صور')
  await page.getByTestId('file-input').setInputFiles(files)
  await expect(page.getByTestId('upload-item')).toHaveCount(10)
  await page.screenshot({ path: path.join(shotsDir, '03-new-update-360.png'), fullPage: true })
  await page.getByTestId('publish').click()
  await expect(page.getByTestId('done')).toBeVisible({ timeout: 280_000 })
  await expect(page.locator('[data-testid="upload-item"][data-state="done"]')).toHaveCount(10)

  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 })

  await page.getByTestId('done').click()
  await expect(page.getByTestId('update-card').first()).toBeVisible()
  await page.screenshot({ path: path.join(shotsDir, '04-stage-360.png'), fullPage: true })

  // Check every stored photo through the API
  const stage = decodeURIComponent(new URL(page.url()).pathname.split('/').pop() || '')
  const res = await page.request.get(`/api/method/construction_core.api.portal.stage_detail?stage=${encodeURIComponent(stage)}`)
  const detail = (await res.json()).message
  const update = detail.updates.find((u: any) => u.text === 'تجربة رفع 10 صور')
  expect(update.media.length).toBe(10)
  for (const m of update.media) {
    expect(m.file.startsWith('/private/files/')).toBeTruthy()
    const file = await page.request.get(m.file)
    expect(file.status()).toBe(200)
    const body = await file.body()
    expect(body.length).toBeLessThan(500 * 1024)
    expect(hasExif(body), `EXIF found in ${m.file}`).toBeFalsy()
  }

  // A private file is not served to a logged-out browser
  const anon = await browser.newContext()
  const anonRes = await anon.request.get(update.media[0].file, { maxRedirects: 0 })
  const isImage = anonRes.status() === 200 && (anonRes.headers()['content-type'] || '').startsWith('image/')
  expect(isImage, `private file served to a guest (status ${anonRes.status()})`).toBeFalsy()
  await anon.close()
})

test('video over the limits shows an Arabic message', async ({ page }) => {
  test.skip(!engUser || !project, 'Set E2E_ENG_*')
  await login(page)
  await page.goto(`/portal/projects/${encodeURIComponent(project)}/update`)
  await expect(page.getByTestId('stage-select')).toBeVisible()
  // 51 MB of zeros with a video MIME type: rejected by size before any upload
  await page.getByTestId('file-input').setInputFiles({
    name: 'long.mp4',
    mimeType: 'video/mp4',
    buffer: Buffer.alloc(51 * 1024 * 1024),
  })
  await expect(page.getByRole('alert')).toContainText('50 ميجا')
  await expect(page.getByTestId('upload-item')).toHaveCount(0)
})
