/**
 * Chrome Extension Local Config E2E 测试
 *
 * 测试 Popup 在 LocalHotelConfig 模式下，直接通过 chrome.storage.local
 * 完成酒店配置的创建、编辑，不依赖后端 API。
 *
 * 与 mock-popup-backend 无关——测试直接操作 Service Worker 的 chrome.storage。
 */

import { test, expect } from '@playwright/test'
import { chromium, type BrowserContext } from 'playwright'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const extensionPath = path.resolve(__dirname, '../../dist')
const userDataDir = path.resolve(__dirname, '../../.test-chrome-profile-local-config')

/** 从 service worker URL 获取扩展 ID */
async function getExtensionId(context: BrowserContext): Promise<string> {
  const worker = await context.waitForEvent('serviceworker', { timeout: 10000 })
  return new URL(worker.url()).hostname
}

/** 在 Service Worker 中操作 chrome.storage.local */
function evalStorage(context: BrowserContext, script: string) {
  const worker = context.serviceWorkers()[0]
  if (!worker) throw new Error('No service worker')
  return worker.evaluate((code) => {
    return new Promise<void>((resolve, reject) => {
      try {
        // 直接执行传入的 JS 代码字符串
        const fn = new Function('chrome', 'resolve', 'reject', code)
        fn(chrome, resolve, reject)
      } catch (e) {
        reject(e)
      }
    })
  }, script)
}

/** 创建浏览器上下文 */
async function createContext() {
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

test.describe('Local Hotel Config E2E', () => {
  test.beforeAll(async () => {
    const fs = await import('fs')
    if (fs.existsSync(userDataDir)) {
      fs.rmSync(userDataDir, { recursive: true, force: true })
    }
  })

  test.afterAll(async () => {
    const fs = await import('fs')
    if (fs.existsSync(userDataDir)) {
      fs.rmSync(userDataDir, { recursive: true, force: true })
    }
  })

  // ── 创建酒店 ────────────────────────────────────────────────────────────────

  test('首次打开应显示创建酒店表单', async () => {
    const { context, popupUrl } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')

      // 应显示创建酒店表单
      await expect(page.locator('#hotel-name-input')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#hotel-city-input')).toBeVisible()
      await expect(page.locator('#create-hotel-btn')).toBeVisible()
    } finally {
      await context.close()
    }
  })

  test('填写表单创建酒店 -> 跳转到酒店首页', async () => {
    const { context, popupUrl } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      // 填写并提交
      await page.fill('#hotel-name-input', '深圳湾万豪酒店')
      await page.fill('#hotel-city-input', '深圳')
      await page.click('#create-hotel-btn')

      // 跳转到首页，显示酒店名称
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#hotel-selector-btn')).toContainText('深圳湾万豪酒店')

      // 配置预览区域可见
      await expect(page.locator('#settings-preview')).toBeVisible()

      // 验证 storage 中有数据
      const stored = await evalStorage(context, `
        chrome.storage.local.get('hotel_configs', (result) => {
          resolve(JSON.stringify(result.hotel_configs))
        })
      `)
      const configs = JSON.parse(stored as string)
      expect(configs).toHaveLength(1)
      expect(configs[0].name).toBe('深圳湾万豪酒店')
      expect(configs[0].city).toBe('深圳')
      expect(configs[0].reply_settings.tone).toBeTruthy()
      expect(configs[0].reply_settings.style).toBeTruthy()
    } finally {
      await context.close()
    }
  })

  test('验证默认回复设置被正确填充', async () => {
    const { context, popupUrl } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      await page.fill('#hotel-name-input', '测试酒店')
      await page.fill('#hotel-city-input', '上海')
      await page.click('#create-hotel-btn')

      // 等待首页显示
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })

      // 验证回复设置预览包含默认值
      const configValues = page.locator('.config-value')
      const tone = await configValues.nth(0).textContent()
      const style = await configValues.nth(1).textContent()

      // 默认值不为空
      expect(tone).toBeTruthy()
      expect(tone!.length).toBeGreaterThan(0)
      expect(style).toBeTruthy()
    } finally {
      await context.close()
    }
  })

  // ── 表单验证 ────────────────────────────────────────────────────────────────

  test('创建酒店 - 名称不填应显示错误', async () => {
    const { context, popupUrl } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      await page.fill('#hotel-city-input', '深圳')
      await page.click('#create-hotel-btn')

      await expect(page.locator('#create-status')).toContainText('请输入酒店名称')
    } finally {
      await context.close()
    }
  })

  test('创建酒店 - 城市不填应显示错误', async () => {
    const { context, popupUrl } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      await page.fill('#hotel-name-input', '测试酒店')
      await page.click('#create-hotel-btn')

      await expect(page.locator('#create-status')).toContainText('请输入所在城市')
    } finally {
      await context.close()
    }
  })

  // ── 编辑回复设置 ────────────────────────────────────────────────────────────

  test('编辑设置 -> 保存 -> 返回首页 -> 预览更新', async () => {
    const { context, popupUrl } = await createContext()
    try {
      // 先通过 storage 直接写入一个酒店（模拟已有配置）
      await evalStorage(context, `
        const hotels = [{
          id: 'hotel_e2e_001',
          name: 'E2E测试酒店',
          city: '广州',
          reply_settings: { tone: '默认语气', style: '默认风格', rules: ['规则1'] },
          created_at: Date.now(),
          updated_at: Date.now()
        }]
        chrome.storage.local.set({ hotel_configs: hotels, current_hotel: { hotel_id: 'hotel_e2e_001', hotel_name: 'E2E测试酒店' } }, () => resolve())
      `)

      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')

      // 应显示酒店首页
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#hotel-selector-btn')).toContainText('E2E测试酒店')

      // 进入编辑
      await page.click('#edit-settings-btn')
      await expect(page.locator('#back-btn')).toBeVisible({ timeout: 5000 })

      // 等待设置加载（input 有值）
      await page.waitForFunction(() => {
        const input = document.getElementById('edit-tone') as HTMLInputElement
        return input && input.value.length > 0
      }, { timeout: 5000 })

      // 修改设置
      await page.fill('#edit-tone', '温暖亲切')
      await page.fill('#edit-style', '轻松自然')
      await page.fill('#edit-rules', '投诉先道歉\n三天内回复')

      // 保存
      await page.click('#save-settings-btn')

      // 验证保存成功提示
      await expect(page.locator('#edit-status')).toContainText('✅')

      // 验证返回到首页
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })

      // 验证预览值已更新
      await page.waitForFunction(() => {
        const values = document.querySelectorAll('.config-value')
        return values.length >= 2 && values[0].textContent === '温暖亲切'
      }, { timeout: 3000 })

      const configValues = page.locator('.config-value')
      await expect(configValues.nth(0)).toHaveText('温暖亲切')
      await expect(configValues.nth(1)).toHaveText('轻松自然')

      // 验证 storage 已更新
      const stored = await evalStorage(context, `
        chrome.storage.local.get('hotel_configs', (result) => {
          resolve(JSON.stringify(result.hotel_configs))
        })
      `)
      const configs = JSON.parse(stored as string)
      expect(configs[0].reply_settings.tone).toBe('温暖亲切')
    } finally {
      await context.close()
    }
  })

  test('编辑设置 - tone 为空应显示验证错误', async () => {
    const { context, popupUrl } = await createContext()
    try {
      await evalStorage(context, `
        const hotels = [{
          id: 'hotel_e2e_002',
          name: '验证测试酒店',
          city: '北京',
          reply_settings: { tone: '默认', style: '默认', rules: [] },
          created_at: Date.now(),
          updated_at: Date.now()
        }]
        chrome.storage.local.set({ hotel_configs: hotels, current_hotel: { hotel_id: 'hotel_e2e_002', hotel_name: '验证测试酒店' } }, () => resolve())
      `)

      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })

      // 进入编辑
      await page.click('#edit-settings-btn')
      await expect(page.locator('#back-btn')).toBeVisible({ timeout: 5000 })

      // 等待加载完成
      await page.waitForFunction(() => {
        const input = document.getElementById('edit-tone') as HTMLInputElement
        return input && input.value.length > 0
      }, { timeout: 5000 })

      // 清空 tone
      await page.fill('#edit-tone', '')

      // 保存
      await page.click('#save-settings-btn')

      // 验证错误提示
      await expect(page.locator('#edit-status')).toContainText('回复语气不能为空')

      // 验证仍在编辑视图
      await expect(page.locator('#back-btn')).toBeVisible()
      await expect(page.locator('#save-settings-btn')).toBeVisible()
    } finally {
      await context.close()
    }
  })

  // ── 酒店切换 ────────────────────────────────────────────────────────────────

  test('创建第二个酒店后可通过选择器切换', async () => {
    const { context, popupUrl } = await createContext()
    try {
      // 预置两个酒店
      await evalStorage(context, `
        const hotels = [
          { id: 'hotel_switch_a', name: '酒店A', city: '深圳', reply_settings: { tone: '专业', style: '正式', rules: [] }, created_at: 1000, updated_at: 1000 },
          { id: 'hotel_switch_b', name: '酒店B', city: '北京', reply_settings: { tone: '温暖', style: '亲切', rules: [] }, created_at: 1001, updated_at: 1001 }
        ]
        chrome.storage.local.set({ hotel_configs: hotels, current_hotel: { hotel_id: 'hotel_switch_a', hotel_name: '酒店A' } }, () => resolve())
      `)

      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#hotel-selector-btn')).toContainText('酒店A', { timeout: 5000 })

      // 打开选择器弹窗
      await page.click('#hotel-selector-btn')
      await expect(page.locator('#hotel-list-modal')).not.toHaveClass(/hidden/)

      // 应列出两个酒店
      const items = page.locator('.modal-hotel-item')
      await expect(items).toHaveCount(2)

      // 切换酒店
      await items.nth(1).click()

      // 验证当前酒店变为酒店B
      await expect(page.locator('#hotel-selector-btn')).toContainText('酒店B', { timeout: 5000 })

      // 验证 current_hotel 已更新
      const current = await evalStorage(context, `
        chrome.storage.local.get('current_hotel', (result) => {
          resolve(JSON.stringify(result.current_hotel))
        })
      `)
      const parsed = JSON.parse(current as string)
      expect(parsed.hotel_id).toBe('hotel_switch_b')
    } finally {
      await context.close()
    }
  })

  // ── 创建新酒店按钮 ──────────────────────────────────────────────────────────

  test('选择弹窗中点击创建新酒店按钮应回到创建表单', async () => {
    const { context, popupUrl } = await createContext()
    try {
      await evalStorage(context, `
        const hotels = [{
          id: 'hotel_new_btn',
          name: '已有酒店',
          city: '上海',
          reply_settings: { tone: '默认', style: '默认', rules: [] },
          created_at: Date.now(),
          updated_at: Date.now()
        }]
        chrome.storage.local.set({ hotel_configs: hotels, current_hotel: { hotel_id: 'hotel_new_btn', hotel_name: '已有酒店' } }, () => resolve())
      `)

      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })

      // 打开选择器
      await page.click('#hotel-selector-btn')
      await expect(page.locator('#hotel-list-modal')).not.toHaveClass(/hidden/)

      // 点击创建新酒店
      await page.click('#modal-new-hotel-btn')

      // 回到创建表单
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })
      await expect(page.locator('#hotel-name-input')).toBeVisible()
      await expect(page.locator('#hotel-city-input')).toBeVisible()
    } finally {
      await context.close()
    }
  })

  // ── 多次创建和切换完整流程 ──────────────────────────────────────────────────

  test('完整流程：创建酒店 → 编辑设置 → 创建新酒店 → 切换', async () => {
    const { context, popupUrl } = await createContext()
    try {
      const page = await context.newPage()
      await page.goto(popupUrl)
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      // Step 1: 创建第一个酒店
      await page.fill('#hotel-name-input', '三亚艾迪逊酒店')
      await page.fill('#hotel-city-input', '三亚')
      await page.click('#create-hotel-btn')

      await expect(page.locator('#hotel-selector-btn')).toContainText('三亚艾迪逊酒店', { timeout: 5000 })

      // Step 2: 编辑设置
      await page.click('#edit-settings-btn')
      await expect(page.locator('#back-btn')).toBeVisible({ timeout: 5000 })

      await page.waitForFunction(() => {
        const input = document.getElementById('edit-tone') as HTMLInputElement
        return input && input.value.length > 0
      }, { timeout: 5000 })

      await page.fill('#edit-tone', '热情')
      await page.fill('#edit-style', '度假风格')
      await page.click('#save-settings-btn')

      // 等待返回首页
      await expect(page.locator('#hotel-selector-btn')).toBeVisible({ timeout: 5000 })

      // Step 3: 打开选择器 → 创建新酒店
      await page.click('#hotel-selector-btn')
      await expect(page.locator('#hotel-list-modal')).not.toHaveClass(/hidden/)
      await page.click('#modal-new-hotel-btn')

      await expect(page.locator('#create-hotel-btn')).toBeVisible({ timeout: 5000 })

      // Step 4: 创建第二个酒店
      await page.fill('#hotel-name-input', '广州四季酒店')
      await page.fill('#hotel-city-input', '广州')
      await page.click('#create-hotel-btn')

      await expect(page.locator('#hotel-selector-btn')).toContainText('广州四季酒店', { timeout: 5000 })

      // Step 5: 切换回第一个酒店
      await page.click('#hotel-selector-btn')
      await expect(page.locator('#hotel-list-modal')).not.toHaveClass(/hidden/)
      await page.locator('.modal-hotel-item').first().click()

      await expect(page.locator('#hotel-selector-btn')).toContainText('三亚艾迪逊酒店', { timeout: 5000 })

      // 确认配置预览显示之前保存的值
      await page.waitForFunction(() => {
        const values = document.querySelectorAll('.config-value')
        return values.length >= 2 && values[0].textContent === '热情'
      }, { timeout: 3000 })
    } finally {
      await context.close()
    }
  })
})
