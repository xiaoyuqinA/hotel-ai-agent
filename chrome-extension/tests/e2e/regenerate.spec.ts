/**
 * E2E 测试：选中文本 → 生成回复 → 重新生成
 *
 * 使用真实后端（非 mock），测试：
 * 1. 选中文本 → 打开 FAB → 点击生成回复 → 验证回复
 * 2. 点击重新生成 → 验证第二次回复生成
 * 3. 第二次回复内容与第一次不同（或至少流程正常）
 */

import { test, expect } from '@playwright/test'
import { chromium, type BrowserContext } from 'playwright'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const extensionPath = path.resolve(__dirname, '../../dist')
const BASE_DATA_DIR = path.resolve(__dirname, '../../.test-chrome-profile-regenerate')
const MOCK_OTA_URL = 'http://localhost:3456'

let testIdx = 0

async function getExtensionId(context: BrowserContext): Promise<string> {
  const existing = context.serviceWorkers()
  if (existing.length > 0) {
    return new URL(existing[0].url()).hostname
  }
  const worker = await context.waitForEvent('serviceworker', { timeout: 15000 })
  return new URL(worker.url()).hostname
}

async function createContext() {
  const fs = await import('fs')
  testIdx++
  const userDataDir = `${BASE_DATA_DIR}/test-${testIdx}`
  if (fs.existsSync(userDataDir)) {
    fs.rmSync(userDataDir, { recursive: true, force: true })
  }

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`,
    ],
  })
  const extId = await getExtensionId(context)
  return { context, extId }
}

/** 获取生成回复后面板中的回复内容 */
async function waitForReply(panel: any, page: any, timeoutMs = 60000): Promise<string> {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    await page.waitForTimeout(1000)

    const currentView = await panel.getAttribute('data-view')
    const box = page.locator('#ha-reply-box')
    const boxText = await box.textContent()

    if (currentView === 'completed' && boxText && boxText !== '等待回复...' && boxText.trim()) {
      return boxText
    }

    // 每 3 秒唤醒一次 Service Worker
    if (Math.floor((Date.now() - start) / 1000) % 3 === 0) {
      await page.evaluate(() => {
        return chrome.runtime.sendMessage({ type: 'PING' }).catch(() => null)
      }).catch(() => {})
    }
  }
  return ''
}

test.describe('重新生成 E2E', () => {
  test.beforeAll(async () => {
    const fs = await import('fs')
    if (fs.existsSync(BASE_DATA_DIR)) {
      fs.rmSync(BASE_DATA_DIR, { recursive: true, force: true })
    }
  })

  test.afterAll(async () => {
    const fs = await import('fs')
    if (fs.existsSync(BASE_DATA_DIR)) {
      fs.rmSync(BASE_DATA_DIR, { recursive: true, force: true })
    }
  })

  test('选中文本 → 生成回复 → 重新生成', { timeout: 180000 }, async () => {
    const { context } = await createContext()
    try {
      const page = await context.newPage()

      // ── Step 1: 打开 OTA 页面 ────────────────────────────────────────────────
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')
      await page.waitForSelector('.comment-content', { timeout: 5000 })

      // 监听 Service Worker Console 日志
      const worker = context.serviceWorkers()[0]
      if (worker) {
        worker.on('console', msg => {
          const text = msg.text()
          if (text.includes('[ServiceWorker]') || text.includes('[SSEManager]') || text.includes('[EventRouter]')) {
            console.log('[SW]', text)
          }
        })
      }

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })
      console.log('[Test] FAB visible')

      // ── Step 2: 选中评论文本 ────────────────────────────────────────────────
      await page.evaluate(() => {
        const el = document.querySelector('.comment-content') as HTMLElement
        if (!el) return
        const range = document.createRange()
        range.selectNodeContents(el)
        const sel = window.getSelection()
        sel!.removeAllRanges()
        sel!.addRange(range)
      })

      // ── Step 3: 打开 FAB 点击生成回复 ────────────────────────────────────────
      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible({ timeout: 5000 })
      await page.waitForTimeout(1500)
      console.log('[Test] Panel view:', await panel.getAttribute('data-view'))

      const generateBtn = panel.locator('#ha-generate-btn')
      await expect(generateBtn).toBeVisible({ timeout: 5000 })
      await generateBtn.click()

      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 10000 })
      console.log('[Test] Generate started')

      // ── Step 4: 等待第一次回复生成 ──────────────────────────────────────────
      const firstReply = await waitForReply(panel, page)
      console.log('[Test] First reply:', firstReply)
      expect(firstReply).toBeTruthy()
      expect(firstReply.length).toBeGreaterThan(0)

      // 确认编辑和复制按钮可见
      await expect(panel.locator('#ha-edit-btn')).toBeVisible()
      await expect(panel.locator('#ha-copy-btn')).toBeVisible()

      // ── Step 5: 点击重新生成按钮 ────────────────────────────────────────────
      const retryBtn = panel.locator('#ha-retry-btn')
      await expect(retryBtn).toBeVisible()
      await retryBtn.click()

      // panel 切换到 running
      console.log('[Test] Retry clicked')

      // Step 6: 验证第二次生成
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 15000 })
      console.log('[Test] Second generate started')

      const secondReply = await waitForReply(panel, page)
      console.log('[Test] Second reply:', secondReply)
      expect(secondReply).toBeTruthy()
      expect(secondReply.length).toBeGreaterThan(0)

      console.log('[Test] Regenerate flow completed successfully')

    } finally {
      await context.close()
    }
  })
})
