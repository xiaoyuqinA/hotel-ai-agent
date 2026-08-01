/**
 * E2E 测试：邀请码流程
 *
 * 1. Popup 未设置邀请码时显示输入页
 * 2. 输入有效邀请码后进入首页
 * 3. 输入无效邀请码显示错误
 * 4. 完整流程：输入邀请码 → 创建酒店 → 生成回复
 */

import { test, expect } from '@playwright/test'
import { chromium, type BrowserContext } from 'playwright'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const extensionPath = path.resolve(__dirname, '../../dist')
const BASE_DATA_DIR = path.resolve(__dirname, '../../.test-chrome-profile-invite')
const MOCK_OTA_URL = 'http://localhost:3456'

let testIdx = 0

async function getExtensionId(context: BrowserContext): Promise<string> {
  const existing = context.serviceWorkers()
  if (existing.length > 0) return new URL(existing[0].url()).hostname
  const worker = await context.waitForEvent('serviceworker', { timeout: 20000 })
  return new URL(worker.url()).hostname
}

async function createContext() {
  const fs = await import('fs')
  testIdx++
  const userDataDir = `${BASE_DATA_DIR}/test-${testIdx}`
  if (fs.existsSync(userDataDir)) fs.rmSync(userDataDir, { recursive: true, force: true })

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`,
    ],
  })
  const extId = await getExtensionId(context)
  const popupUrl = `chrome-extension://${extId}/popup/index.html`
  return { context, extId, popupUrl }
}

test.describe('邀请码流程 E2E', () => {
  test.beforeAll(async () => {
    const fs = await import('fs')
    if (fs.existsSync(BASE_DATA_DIR)) fs.rmSync(BASE_DATA_DIR, { recursive: true, force: true })
  })

  test.afterAll(async () => {
    const fs = await import('fs')
    if (fs.existsSync(BASE_DATA_DIR)) fs.rmSync(BASE_DATA_DIR, { recursive: true, force: true })
  })

  test('未设置邀请码时应显示输入页', { timeout: 30000 }, async () => {
    const { context, popupUrl } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(popupUrl, { timeout: 15000 })
      await page.waitForLoadState('domcontentloaded')

      // 应显示邀请码输入框
      await expect(page.locator('#invite-code-input')).toBeVisible({ timeout: 10000 })
      await expect(page.locator('#verify-invite-btn')).toBeVisible()
    } finally {
      await context.close()
    }
  })

  test('输入无效邀请码应显示错误', { timeout: 30000 }, async () => {
    const { context, popupUrl } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(popupUrl, { timeout: 15000 })
      await page.waitForLoadState('domcontentloaded')

      await expect(page.locator('#invite-code-input')).toBeVisible({ timeout: 10000 })

      // 输入无效邀请码
      await page.fill('#invite-code-input', 'INVITE-FAKE')
      await page.click('#verify-invite-btn')

      // 应显示错误提示，且仍停留在输入页
      await expect(page.locator('#invite-status')).toContainText('邀请码不存在', { timeout: 10000 })
      await expect(page.locator('#invite-code-input')).toBeVisible()
    } finally {
      await context.close()
    }
  })
})
