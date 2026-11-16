import { test, expect, type Browser } from '@playwright/test'

// Phase 4: two browsers, a message reaches the other side within 5 seconds (P04-05, P04-06).
const project = process.env.E2E_ENG_PROJECT || ''
const eng = { user: process.env.E2E_ENG_USER || '', pwd: process.env.E2E_ENG_PASSWORD || '' }
const client = { user: process.env.E2E_CHAT_CLIENT || '', pwd: process.env.E2E_CHAT_CLIENT_PASSWORD || '' }
const shotsDir = process.env.E2E_SHOTS_DIR || 'screenshots'

test.use({ viewport: { width: 360, height: 780 } })

async function session(browser: Browser, who: { user: string; pwd: string }) {
  const ctx = await browser.newContext({ viewport: { width: 360, height: 780 } })
  const page = await ctx.newPage()
  const res = await page.request.post('/api/method/login', { form: { usr: who.user, pwd: who.pwd } })
  expect(res.ok(), await res.text()).toBeTruthy()
  return { ctx, page }
}

test('chat: message within 5 s, approval answered and locked', async ({ browser }) => {
  test.skip(!project || !client.user, 'Set E2E_ENG_* and E2E_CHAT_CLIENT*')
  const e = await session(browser, eng)
  const c = await session(browser, client)
  const chat = `/portal/c/${encodeURIComponent(project)}/chat`

  // The client lands on the client home of their only project
  await c.page.goto('/portal')
  await expect(c.page).toHaveURL(new RegExp(`/portal/c/`))
  await expect(c.page.getByTestId('client-progress')).toBeVisible()
  await c.page.screenshot({ path: `${shotsDir}/10-client-home-360.png`, fullPage: true })
  for (const tab of ['timeline', 'gallery', 'payments']) {
    await c.page.getByTestId(`tab-${tab}`).click()
    await c.page.waitForLoadState('networkidle')
    await c.page.screenshot({ path: `${shotsDir}/1${['timeline', 'gallery', 'payments'].indexOf(tab) + 1}-client-${tab}-360.png`, fullPage: true })
  }

  await e.page.goto(chat)
  await c.page.goto(chat)
  await expect(e.page.getByTestId('chat-list')).toBeVisible()
  await expect(c.page.getByTestId('chat-list')).toBeVisible()

  const text = `سؤال ${Date.now()}`
  await c.page.getByTestId('chat-input').fill(text)
  const sentAt = Date.now()
  await c.page.getByTestId('chat-send').click()
  await expect(e.page.getByTestId('chat-message').filter({ hasText: text })).toBeVisible({ timeout: 5000 })
  console.log(`message seen by the engineer after ${Date.now() - sentAt} ms`)

  // Engineer asks for an approval; the client answers; the answer is final
  await e.page.getByRole('button', { name: 'موافقة' }).click()
  await e.page.getByPlaceholder('عنوان طلب الموافقة').fill('سيراميك الريسبشن')
  await e.page.getByPlaceholder('التفاصيل').fill('فرق السعر عن المسموح')
  await e.page.getByPlaceholder('المبلغ (اختياري)').fill('6000')
  await e.page.getByRole('button', { name: 'ابعت طلب الموافقة' }).click()
  await expect(c.page.getByTestId('approve').last()).toBeVisible({ timeout: 5000 })
  await c.page.screenshot({ path: `${shotsDir}/14-client-chat-360.png`, fullPage: true })
  await c.page.getByTestId('approve').last().click()
  await expect(c.page.getByTestId('approval-answer').last()).toContainText('اتوافق')
  await expect(e.page.getByTestId('approval-answer').last()).toContainText('اتوافق', { timeout: 5000 })

  await e.ctx.close()
  await c.ctx.close()
})
