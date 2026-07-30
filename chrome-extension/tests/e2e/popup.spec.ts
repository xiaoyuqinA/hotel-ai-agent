/**
 * Chrome Extension E2E Popup 功能测试
 *
 * 测试 Popup 视图路由、酒店 CRUD、设置编辑、表单验证。
 *
 * Popup 访问路径：chrome-extension://<extensionId>/popup/index.html
 * 后端：mock-popup-backend.cjs（port 8000）
 */

import { test, expect } from '@playwright/test'
import { chromium, type BrowserContext } from 'playwright'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const extensionPath = path.resolve(__dirname, '../../dist')
const userDataDir = path.resolve(__dirname, '../../.test-chrome-profile-popup')

const MOCK_HOTEL = {
  hotel_id: 'hotel_001',
  hotel_name: '深圳万豪酒店',
  reply_settings: { tone: '专业', style: '正式', rules: ['投诉必须先表达歉意', '24小时内回复'] },
}

/** 从 service worker URL 获取扩展 ID */
async function getExtensionId(context: BrowserContext): Promise<string> {
  // 先检查已注册的 workers（service worker 可能已触发）
  let workers = context.serviceWorkers()
  if (workers.length > 0) {
    return new URL(workers[0].url()).hostname
  }
  // 再等待新 worker 注册
  const worker = await context.waitForEvent('serviceworker', { timeout: 10000 })
  return new URL(worker.url()).hostname
}

/** 创建 context 并设置 hotel storage */
async function createContextWithHotel() {
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`,
    ],
  })

  const extId = await getExtensionId(context)
  const popupUrl = `chrome-extension://${extId}/popup/index.html`

  // 打开 popup 页面触发 service worker
  const page = await context.newPage()
  await page.goto(popupUrl)
  await page.waitForLoadState('domcontentloaded')
  await page.waitForSelector('#app-content', { timeout: 5000 })

  // 在 service worker 中设置 storage
  let worker = context.serviceWorkers()[0]
  if (!worker) {
    worker = await context.waitForEvent('serviceworker', { timeout: 5000 })
  }
  await worker.evaluate((hotel) => {
    return new Promise<void>((resolve) => {
      chrome.storage.local.set({ current_hotel: hotel }, () => resolve())
    })
  }, MOCK_HOTEL)

  return { context, popupUrl }
}

// ── 测试 ──────────────────────────────────────────────────────────────────────

test.describe('Popup 功能测试', () => {
  test.beforeAll(async () => {
    const fs = await import('fs')
    if (fs.existsSync(userDataDir)) fs.rmSync(userDataDir, { recursive: true, force: true })
  })

  test.afterAll(async () => {
    const fs = await import('fs')
    if (fs.existsSync(userDataDir)) fs.rmSync(userDataDir, { recursive: true, force: true })
  })

  test('首次打开应显示创建酒店表单', async () => {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    try {
      const extId = await getExtensionId(context)
      const page = await context.newPage()
      await page.goto(`chrome-extension://${extId}/popup/index.html`)
      await page.waitForLoadState('domcontentloaded')

      // 清空 current_hotel
      const worker = context.serviceWorkers()[0]
      if (worker) {
        await worker.evaluate(() => {
          return new Promise<void>((resolve) => {
            chrome.storage.local.remove('current_hotel', () => resolve())
          })
        })
      }

      // 刷新页面触发 render
      await page.reload()
      await page.waitForLoadState('domcontentloaded')

      // 应显示创建表单
      await expect(page.locator('#hotel-name-input')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#hotel-city-input')).toBeVisible()
      await expect(page.locator('#create-hotel-btn')).toBeVisible()
      await expect(page.locator('#create-hotel-btn')).toHaveText('创建酒店')
    } finally {
      await context.close()
    }
  })

  test('创建酒店成功应跳转到首页', async () => {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    try {
      const extId = await getExtensionId(context)
      const page = await context.newPage()
      await page.goto(`chrome-extension://${extId}/popup/index.html`)
      await page.waitForLoadState('domcontentloaded')

      // 清空 current_hotel
      const worker = context.serviceWorkers()[0]
      if (worker) {
        await worker.evaluate(() => {
          return new Promise<void>((resolve) => {
            chrome.storage.local.remove('current_hotel', () => resolve())
          })
        })
      }
      await page.reload()
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      // 填写表单
      await page.fill('#hotel-name-input', '测试新酒店')
      await page.fill('#hotel-city-input', '上海')

      // 监听 API 调用
      const postPromise = page.waitForResponse(resp =>
        resp.url().includes('/api/hotels') && resp.request().method() === 'POST'
      )

      // 点击创建
      await page.click('#create-hotel-btn')

      // 验证 POST 被调用
      const resp = await postPromise
      expect(resp.status()).toBe(201)

      // 验证跳转到首页
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#hotel-selector-btn')).toContainText('测试新酒店')
    } finally {
      await context.close()
    }
  })

  test('创建酒店失败应显示错误', async () => {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    try {
      const extId = await getExtensionId(context)
      const page = await context.newPage()
      await page.goto(`chrome-extension://${extId}/popup/index.html`)
      await page.waitForLoadState('domcontentloaded')

      // 清空 current_hotel
      const worker = context.serviceWorkers()[0]
      if (worker) {
        await worker.evaluate(() => {
          return new Promise<void>((resolve) => {
            chrome.storage.local.remove('current_hotel', () => resolve())
          })
        })
      }
      await page.reload()
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      // 拦截 POST /api/hotels 返回 500
      await page.route('**/api/hotels', (route, request) => {
        if (request.method() === 'POST') {
          return route.fulfill({ status: 500, body: 'Internal Server Error' })
        }
        return route.continue()
      })

      await page.fill('#hotel-name-input', '失败测试')
      await page.fill('#hotel-city-input', '测试')
      await page.click('#create-hotel-btn')

      // 验证错误提示
      await expect(page.locator('#create-status')).toContainText('创建失败', { timeout: 5000 })

      // 验证按钮恢复可用
      await expect(page.locator('#create-hotel-btn')).toBeEnabled()
      await expect(page.locator('#create-hotel-btn')).toHaveText('创建酒店')
    } finally {
      await context.close()
    }
  })

  test('首页展示配置预览', async () => {
    const { context, popupUrl } = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')

      // 验证酒店选择器
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#hotel-selector-btn')).toContainText(MOCK_HOTEL.hotel_name)

      // 等待配置加载完成
      await expect(page.locator('.config-value').first()).not.toHaveText('加载中...')

      // 验证配置预览
      await expect(page.locator('.config-value').first()).toContainText('专业')

      // 验证编辑按钮
      await expect(page.locator('#edit-settings-btn')).toBeVisible()
    } finally {
      await context.close()
    }
  })

  test('编辑设置 → 保存 → 返回首页', async () => {
    const { context, popupUrl } = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#edit-settings-btn')).toBeVisible({ timeout: 5000 })

      // 点击编辑
      await page.click('#edit-settings-btn')

      // 验证进入编辑视图
      await expect(page.locator('#back-btn')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#save-settings-btn')).toBeVisible()

      // 等待设置加载
      await page.waitForFunction(() => {
        const input = document.getElementById('edit-tone') as HTMLInputElement
        return input && input.value.length > 0
      }, { timeout: 5000 })

      // 修改 tone
      await page.fill('#edit-tone', '温暖亲切')
      await page.fill('#edit-style', '轻松自然')
      await page.fill('#edit-rules', '投诉先道歉\n三天内回复')

      // 监听 PUT
      const putPromise = page.waitForResponse(resp =>
        resp.url().includes('/api/hotels/hotel_001/reply-settings') && resp.request().method() === 'PUT'
      )

      // 保存
      await page.click('#save-settings-btn')

      const resp = await putPromise
      expect(resp.status()).toBe(200)

      // 验证返回首页
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 3000 })
      await expect(page.locator('#edit-settings-btn')).toBeVisible()
    } finally {
      await context.close()
    }
  })

  test('编辑设置空 tone 应显示验证错误', async () => {
    const { context, popupUrl } = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#edit-settings-btn')).toBeVisible({ timeout: 5000 })

      // 进入编辑
      await page.click('#edit-settings-btn')
      await expect(page.locator('#back-btn')).toBeVisible({ timeout: 5000 })

      // 等待设置加载
      await page.waitForFunction(() => {
        const input = document.getElementById('edit-tone') as HTMLInputElement
        return input && input.value.length > 0
      }, { timeout: 5000 })

      // 清空 tone
      await page.fill('#edit-tone', '')

      // 保存
      await page.click('#save-settings-btn')

      // 验证错误提示
      await expect(page.locator('#edit-status')).toContainText('回复语气不能为空', { timeout: 3000 })

      // 验证仍在编辑页面
      await expect(page.locator('#back-btn')).toBeVisible()
      await expect(page.locator('#save-settings-btn')).toBeVisible()
    } finally {
      await context.close()
    }
  })

  test('酒店选择弹窗切换酒店', async () => {
    const { context, popupUrl } = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#hotel-selector-btn')).toContainText('深圳万豪酒店', { timeout: 5000 })

      // 点击酒店选择器
      await page.click('#hotel-selector-btn')

      // 验证弹窗出现
      await expect(page.locator('#hotel-list-modal')).not.toHaveClass(/hidden/)
      // 酒店数量 >= 2（前面测试可能新增了酒店）
      const hotelCount = await page.locator('.modal-hotel-item').count()
      expect(hotelCount).toBeGreaterThanOrEqual(2)

      // 点击另一个酒店
      const secondHotel = page.locator('.modal-hotel-item').nth(1)
      await secondHotel.click()

      // 验证首页切换到新酒店
      await expect(page.locator('#hotel-selector-btn')).toContainText('北京希尔顿')
    } finally {
      await context.close()
    }
  })
})
