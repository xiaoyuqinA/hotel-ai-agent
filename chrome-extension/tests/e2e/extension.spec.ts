/**
 * Chrome Extension E2E 测试 — 扩展加载测试
 *
 * 通过 launchPersistentContext 加载扩展，
 * 验证 content-script 注入的浮标和面板交互。
 *
 * 注意：这些测试需要 headless: false（Chrome 扩展不支持 headless 模式）
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const extensionPath = path.resolve(__dirname, '../../dist')
const userDataDir = path.resolve(__dirname, '../../.test-chrome-profile')

const BASE_URL = 'http://localhost:3456'

test.describe('Chrome Extension 加载测试', () => {

  test('扩展加载后浮标应出现在页面上', async () => {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    try {
      const page = await context.newPage()
      await page.goto(BASE_URL)
      await page.waitForLoadState('domcontentloaded')

      // 等待 content script 注入浮标
      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })
    } finally {
      await context.close()
    }
  })

  test('点击浮标应打开面板', async () => {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    try {
      const page = await context.newPage()
      await page.goto(BASE_URL)
      await page.waitForLoadState('domcontentloaded')

      // 等待浮标出现
      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      // 点击浮标
      await fab.click()

      // 验证面板出现
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()

      // 验证面板标题
      const title = panel.locator('.ha-panel-title')
      await expect(title).toContainText('AI 回复助手')
    } finally {
      await context.close()
    }
  })

  test('面板应显示初始视图', async () => {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    try {
      const page = await context.newPage()
      await page.goto(BASE_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })
      await fab.click()

      // 面板应处于 idle 或 no-hotel 视图
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toHaveAttribute('data-view', /idle|no-hotel/)

      // 面板标题应可见
      const title = panel.locator('.ha-panel-title')
      await expect(title).toContainText('AI 回复助手')
    } finally {
      await context.close()
    }
  })

  test('点击关闭按钮应隐藏面板', async () => {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    try {
      const page = await context.newPage()
      await page.goto(BASE_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      // 打开面板
      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()

      // 点击关闭按钮
      const closeBtn = panel.locator('#ha-close-btn')
      await closeBtn.click()

      // 验证面板隐藏
      await expect(panel).toHaveClass(/hidden/)
    } finally {
      await context.close()
    }
  })

  test('面板关闭后浮标仍可见', async () => {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    try {
      const page = await context.newPage()
      await page.goto(BASE_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      // 打开面板
      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()

      // 关闭面板
      const closeBtn = panel.locator('#ha-close-btn')
      await closeBtn.click()
      await expect(panel).toHaveClass(/hidden/)

      // 浮标仍然可见
      await expect(fab).toBeVisible()
    } finally {
      await context.close()
    }
  })
})
