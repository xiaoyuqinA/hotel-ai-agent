/**
 * E2E 测试：创建配置 → 选中文本 → 生成回复
 *
 * 流程：
 * 1. 打开 Popup 创建酒店
 * 2. 关闭 Popup，在**同一个标签页**导航到 Mock OTA 页面
 * 3. 选中文本 → 打开 FAB → 点击生成回复
 * 4. 验证 SSE 流式回复出现
 *
 * 关键：使用同一个标签页完成所有操作，避免 Content Script 上下文切换
 */

import { test, expect } from '@playwright/test'
import { chromium, type BrowserContext } from 'playwright'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const extensionPath = path.resolve(__dirname, '../../dist')
const BASE_DATA_DIR = path.resolve(__dirname, '../../.test-chrome-profile-full-flow-v2')
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
  const popupUrl = `chrome-extension://${extId}/popup/index.html`
  return { context, extId, popupUrl }
}

test.describe('完整流程 E2E', () => {
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

  test('创建配置 → 同一标签页导航到 OTA → 生成回复', { timeout: 120000 }, async () => {
    const { context, popupUrl } = await createContext()
    try {
      // ── Step 1: 在一个标签页打开 Popup 创建酒店 ──────────────────────────────
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      await page.fill('#hotel-name-input', '深圳湾万豪酒店')
      await page.fill('#hotel-city-input', '深圳')
      await page.click('#create-hotel-btn')

      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#hotel-selector-btn')).toContainText('深圳湾万豪酒店')
      console.log('[Test] Hotel created')

      // ── Step 2: 在同一个标签页导航到 OTA 页面 ────────────────────────────────
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')
      await page.waitForSelector('.comment-content', { timeout: 5000 })

      // 监听 Console 日志（Content Script 页面）
      const consoleLogs: string[] = []
      page.on('console', msg => {
        const text = msg.text()
        if (text.includes('[SSEManager]') || text.includes('[EventRouter]') || text.includes('[ServiceWorker]')) {
          consoleLogs.push(text)
          console.log('[PageConsole]', text)
        }
      })

      // 监听 Service Worker Console 日志
      const worker = context.serviceWorkers()[0]
      if (worker) {
        worker.on('console', msg => {
          const text = msg.text()
          consoleLogs.push('[SW] ' + text)
          console.log('[SWConsole]', text)
        })
      }

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })
      console.log('[Test] FAB visible on OTA page')

      // ── Step 3: 选中评论文本 ────────────────────────────────────────────────
      await page.evaluate(() => {
        const el = document.querySelector('.comment-content') as HTMLElement
        if (!el) return
        const range = document.createRange()
        range.selectNodeContents(el)
        const sel = window.getSelection()
        sel!.removeAllRanges()
        sel!.addRange(range)
      })

      // ── Step 4: 打开 FAB → 等待 panel 就绪 ────────────────────────────────
      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible({ timeout: 5000 })

      // 等待视图加载
      await page.waitForTimeout(1500)
      const view = await panel.getAttribute('data-view')
      console.log('[Test] Panel view:', view)

      // 酒店名称应显示
      const hotelBadge = panel.locator('.ha-hotel-badge')
      await expect(hotelBadge).toContainText('深圳湾万豪酒店', { timeout: 5000 })
      console.log('[Test] Hotel badge confirmed')

      // ── Step 5: 点击生成回复 ────────────────────────────────────────────────
      const generateBtn = panel.locator('#ha-generate-btn')
      await expect(generateBtn).toBeVisible({ timeout: 5000 })
      await generateBtn.click()

      // 等待 panel 切换到 running
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 10000 })
      console.log('[Test] Generate started')

      // ── Step 6: 等待 completed + 轮询检查回复框 ─────────────────────────────
      // 使用轮询方式等待回复内容出现，避免因 Service Worker 短暂休眠导致事件丢失
      let replyText = ''
      for (let i = 0; i < 60; i++) {
        await page.waitForTimeout(1000)

        const currentView = await panel.getAttribute('data-view')
        const box = page.locator('#ha-reply-box')
        const boxText = await box.textContent()

        if (currentView === 'completed' && boxText && boxText !== '等待回复...' && boxText.trim()) {
          replyText = boxText
          break
        }

        // 每 3 秒唤醒一次 Service Worker
        if (i % 3 === 0) {
          await page.evaluate(() => {
            return chrome.runtime.sendMessage({ type: 'PING' }).catch(() => null)
          }).catch(() => {})
        }
      }

      console.log('[Test] Reply:', replyText)
      console.log('[Test] Console logs from page:', JSON.stringify(consoleLogs, null, 2))

      // 即使没等到回复，也打印日志方便诊断
      if (!replyText) {
        console.log('[Test] WARNING: No reply generated. Console logs above may indicate the issue.')
      }

      expect(replyText).toBeTruthy()
      expect(replyText!.length).toBeGreaterThan(0)

      // 最终检查视图
      if (replyText) {
        await expect(panel).toHaveAttribute('data-view', /completed|running/, { timeout: 3000 })
      }

    } finally {
      await context.close()
    }
  })

  test('不创建配置 → 默认模式生成回复', async () => {
    const { context } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')
      await page.waitForSelector('.comment-content', { timeout: 5000 })

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      // 选中评论
      await page.evaluate(() => {
        const el = document.querySelector('.comment-content') as HTMLElement
        if (!el) return
        const range = document.createRange()
        range.selectNodeContents(el)
        const sel = window.getSelection()
        sel!.removeAllRanges()
        sel!.addRange(range)
      })

      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible({ timeout: 5000 })

      const hotelBadge = panel.locator('.ha-hotel-badge')
      await expect(hotelBadge).toContainText('默认回复模式')

      const generateBtn = panel.locator('#ha-generate-btn')
      await expect(generateBtn).toBeVisible({ timeout: 5000 })
      await generateBtn.click()

      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 30000 })

      const replyBox = panel.locator('#ha-reply-box')
      const replyText = await replyBox.textContent()
      console.log('[Test] Default reply:', replyText)
      expect(replyText).toBeTruthy()
      expect(replyText!.length).toBeGreaterThan(0)

    } finally {
      await context.close()
    }
  })
})
