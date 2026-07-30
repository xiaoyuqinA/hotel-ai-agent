/**
 * Chrome Extension E2E 功能测试
 *
 * 测试完整流程：
 * 1. 打开 OTA 页面（localhost:3456 + __HOTEL_AI_TEST_MODE 绕过域名检查）
 * 2. 预设酒店配置（通过 CDP 在 service worker 设置 chrome.storage.local）
 * 3. 点击生成回复
 * 4. 验证状态流转 idle → running → completed
 * 5. 验证 token 累积输出
 * 6. 验证最终回复内容
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const extensionPath = path.resolve(__dirname, '../../dist')
const userDataDir = path.resolve(__dirname, '../../.test-chrome-profile-functional')

// 直接使用 localhost（通过 __HOTEL_AI_TEST_MODE 绕过域名检查）
const MOCK_OTA_URL = 'http://localhost:3456/'

const MOCK_HOTEL = {
  hotel_id: 'hotel_test_001',
  hotel_name: '测试酒店',
  reply_settings: {
    tone: 'professional',
    language: 'zh-CN',
  },
}

test.describe('功能测试：生成回复全流程', () => {

  test.beforeAll(async () => {
    // 清理旧的 profile
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

  /** 辅助：创建加载扩展的 context 并预设酒店 + 测试模式 */
  async function createContextWithHotel() {
    const context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
      ],
    })

    // 打开一个临时页面触发 service worker 启动
    const setupPage = await context.newPage()
    await setupPage.goto(MOCK_OTA_URL)
    await setupPage.waitForLoadState('domcontentloaded')
    await setupPage.waitForSelector('#hotel-ai-fab', { timeout: 10000 })

    // 通过 CDP 在 service worker 中设置 chrome.storage.local
    const sw = context.serviceWorkers()[0]
    if (sw) {
      await sw.evaluate((hotel) => {
        return new Promise<void>((resolve) => {
          chrome.storage.local.set({
            current_hotel: hotel,
            __HOTEL_AI_TEST_MODE: true,
          }, () => resolve())
        })
      }, MOCK_HOTEL)
    } else {
      // 如果 service worker 还没出现，等一下再试
      const worker = await context.waitForEvent('serviceworker', { timeout: 5000 })
      await worker.evaluate((hotel) => {
        return new Promise<void>((resolve) => {
          chrome.storage.local.set({
            current_hotel: hotel,
            __HOTEL_AI_TEST_MODE: true,
          }, () => resolve())
        })
      }, MOCK_HOTEL)
    }

    await setupPage.close()
    return context
  }

  test('完整流程：选中评论 → 生成回复 → 状态流转 → token 输出', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      // 1. 等待浮标出现
      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      // 2. 选中评论文本
      const reviewText = page.locator('.comment-content').first()
      await reviewText.waitFor({ state: 'visible' })
      await reviewText.click()

      // 3. 点击浮标打开面板
      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()

      // 4. 验证面板处于 idle 视图，有评论内容
      await expect(panel).toHaveAttribute('data-view', 'idle')
      const reviewBox = page.locator('#ha-review-text')
      await expect(reviewBox).toContainText('房间卫生很差')

      // 5. 点击「生成回复」
      const generateBtn = page.locator('#ha-generate-btn')
      await expect(generateBtn).toBeVisible()
      await generateBtn.click()

      // 6. 验证状态流转 → running
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })

      // 7. 验证回复区域出现流式输出
      const replyBox = page.locator('#ha-reply-box')
      await expect(replyBox).toBeVisible()

      // 8. 等待 token 累积（回复框内容从空变为有内容）
      await expect(replyBox).not.toContainText('等待回复...', { timeout: 15000 })

      // 9. 验证状态流转 → completed
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 15000 })

      // 10. 验证最终回复内容
      await expect(replyBox).toContainText('尊敬的宾客')
      await expect(replyBox).toContainText('感谢您的反馈')

      // 11. 验证完成视图有操作按钮
      const editBtn = page.locator('#ha-edit-btn')
      await expect(editBtn).toBeVisible()
      const publishBtn = page.locator('#ha-publish-btn')
      await expect(publishBtn).toBeVisible()

    } finally {
      await context.close()
    }
  })

  test('状态流转：idle → running → completed 各阶段 UI 正确', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })
      await fab.click()

      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()

      // idle: 应有生成按钮
      await expect(panel).toHaveAttribute('data-view', 'idle')
      await expect(page.locator('#ha-generate-btn')).toBeVisible()

      // 点击生成
      await page.locator('#ha-generate-btn').click()

      // running: 应有状态条和流式回复区域
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })
      await expect(page.locator('#ha-status-text')).toBeVisible()
      await expect(page.locator('#ha-reply-box')).toBeVisible()

      // completed: 应有回复内容和操作按钮
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 15000 })
      await expect(page.locator('#ha-reply-box')).not.toContainText('等待回复...')

    } finally {
      await context.close()
    }
  })

  test('Token 流式输出：回复内容逐步累积', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })
      await fab.click()

      // 点击生成
      const generateBtn = page.locator('#ha-generate-btn')
      await expect(generateBtn).toBeVisible()
      await generateBtn.click()

      // 等待 running 状态
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })

      // 等待第一个 token 出现
      const replyBox = page.locator('#ha-reply-box')
      await expect(replyBox).toContainText('尊敬', { timeout: 15000 })

      // 验证内容持续增长（后续 token 陆续到达）
      await expect(replyBox).toContainText('感谢')
      await expect(replyBox).toContainText('反馈')

      // 最终完成
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 10000 })
      await expect(replyBox).toContainText('尊敬的宾客，感谢您的反馈，我们会尽快改进')

    } finally {
      await context.close()
    }
  })

  test('面板最小化再打开后状态保持', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })
      await fab.click()

      // 生成回复
      await page.locator('#ha-generate-btn').click()

      // 等待完成
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 15000 })

      // 最小化面板（不是关闭）
      await page.locator('#ha-minimize-btn').click()
      await expect(panel).toHaveClass(/hidden/)

      // 再次打开
      await fab.click()
      await expect(panel).toBeVisible()

      // 应该仍显示 completed 视图，回复内容保留
      await expect(panel).toHaveAttribute('data-view', 'completed')
      await expect(page.locator('#ha-reply-box')).toContainText('尊敬的宾客')

    } finally {
      await context.close()
    }
  })

  test('用户选中整条评论：triple-click 选中第二条 → 面板显示选中文本 + 按钮文案正确', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      // 1. 等待浮标出现
      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      // 2. triple-click 选中第二条评论的全文（创建 Selection）
      const secondReview = page.locator('.comment-content').nth(1)
      await secondReview.waitFor({ state: 'visible' })
      await secondReview.click({ clickCount: 3 })

      // 3. 点击浮标打开面板
      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()

      // 4. 验证面板显示的是第二条评论（getSelection 路径）
      await expect(panel).toHaveAttribute('data-view', 'idle')
      const reviewBox = page.locator('#ha-review-text')
      await expect(reviewBox).toContainText('服务很好')
      await expect(reviewBox).toContainText('房间干净整洁')

      // 5. 验证按钮文案 = "AI生成回复"（有评论时）
      const generateBtn = page.locator('#ha-generate-btn')
      await expect(generateBtn).toHaveText('AI生成回复')

    } finally {
      await context.close()
    }
  })

  test('用户选中部分文本：选中"房间卫生很差" → 面板只显示选中部分 + 按钮文案正确', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      // 1. 等待浮标出现
      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      // 2. 用 page.evaluate 手动创建 Selection，只选中"房间卫生很差"
      await page.evaluate(() => {
        const el = document.querySelector('.comment-content')
        if (!el) return
        const textNode = el.firstChild
        if (!textNode) return
        const range = document.createRange()
        range.setStart(textNode, 0)
        range.setEnd(textNode, 6) // "房间卫生很差" = 6 个字符
        const selection = window.getSelection()
        selection.removeAllRanges()
        selection.addRange(range)
      })

      // 3. 点击浮标打开面板
      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()

      // 4. 验证面板只显示选中的部分文本（getSelection 路径）
      await expect(panel).toHaveAttribute('data-view', 'idle')
      const reviewBox = page.locator('#ha-review-text')
      await expect(reviewBox).toContainText('房间卫生很差')
      // 不应包含完整评论的后半部分
      await expect(reviewBox).not.toContainText('床单有污渍')

      // 5. 验证按钮文案 = "AI生成回复"（有评论时）
      const generateBtn = page.locator('#ha-generate-btn')
      await expect(generateBtn).toHaveText('AI生成回复')

    } finally {
      await context.close()
    }
  })

  test('display_name 为空时不发送 STATUS_UPDATE → 状态栏保持默认文案', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      const reviewText = page.locator('.comment-content').first()
      await reviewText.waitFor({ state: 'visible' })
      await reviewText.click()
      await fab.click()

      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()
      await expect(panel).toHaveAttribute('data-view', 'idle')

      // 拦截 stream 请求，使用无 display_name 的事件序列
      await page.route('**/review/stream/**', async (route) => {
        const events = [
          { kind: 'workflow_started', category: 'system', source: 'system' },
          { kind: 'token_delta', category: 'message', delta: '尊敬' },
          { kind: 'token_delta', category: 'message', delta: '的宾客，感谢您的反馈' },
          { kind: 'workflow_completed', category: 'system', display_name: '工作流完成', source: 'system', result: { reply_content: '尊敬的宾客，感谢您的反馈' } },
        ]

        const body = events.map((evt, i) => {
          const data = JSON.stringify({
            id: `mock-${Date.now()}-${i}`,
            workflow_id: 'mock-run-001',
            sequence: i + 1,
            category: evt.category,
            kind: evt.kind,
            display_name: evt.display_name || null,
            source: evt.source || null,
            timestamp: Date.now(),
            ...evt,
          })
          return `data: ${data}\n\n`
        }).join('')

        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          body,
        })
      })

      // 点击生成
      await page.locator('#ha-generate-btn').click()

      // panel 转为 running 视图
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })

      // workflow_started 无 display_name → sendStatusUpdate 跳过
      // 状态栏不应包含"null"、"undefined"等异常文字
      const statusText = page.locator('#ha-status-text')
      await expect(statusText).not.toContainText('null')
      await expect(statusText).not.toContainText('undefined')

      // 等待完成
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 15000 })

    } finally {
      await context.close()
    }
  })

  test('node_failed 无 display_name 时不 fallback 到 source', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      const reviewText = page.locator('.comment-content').first()
      await reviewText.waitFor({ state: 'visible' })
      await reviewText.click()
      await fab.click()

      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()
      await expect(panel).toHaveAttribute('data-view', 'idle')

      // 先注册路由拦截，再点击生成
      const nodeFailedEvents = [
        { kind: 'workflow_started', category: 'system', display_name: '工作流开始', source: 'system' },
        { kind: 'node_started', category: 'progress', source: 'generation', display_name: '生成开始', node_name: 'generation' },
        { kind: 'node_failed', category: 'progress', source: 'generation', node_name: 'generation', error: '模拟失败' },
        { kind: 'workflow_failed', category: 'system', display_name: '工作流失败', source: 'system', error: '模拟失败' },
      ]

      const sseBody = nodeFailedEvents.map((evt, i) => {
        const data = JSON.stringify({
          id: `mock-${Date.now()}-${i}`,
          workflow_id: 'mock-run-001',
          sequence: i + 1,
          category: evt.category,
          kind: evt.kind,
          display_name: evt.display_name || null,
          source: evt.source || null,
          timestamp: Date.now(),
          ...evt,
        })
        return `data: ${data}\n\n`
      }).join('')

      await page.route('**/review/stream/**', async (route) => {
        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          body: sseBody,
        })
      })

      // 点击生成
      await page.locator('#ha-generate-btn').click()

      // 等待 running
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })

      // node_failed 无 display_name → 不应发送 STATUS_UPDATE
      const statusText = page.locator('#ha-status-text')
      await expect(statusText).not.toContainText('generation')

      // 最终转为 error 视图
      await expect(panel).toHaveAttribute('data-view', 'error', { timeout: 15000 })

    } finally {
      await context.close()
    }
  })

  test('有 display_name 时状态栏显示正确的状态文案', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      const reviewText = page.locator('.comment-content').first()
      await reviewText.waitFor({ state: 'visible' })
      await reviewText.click()
      await fab.click()

      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()
      await expect(panel).toHaveAttribute('data-view', 'idle')

      // 点击生成
      await page.locator('#ha-generate-btn').click()

      // 等待 running 视图
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })

      // 默认场景事件按序触发 STATUS_UPDATE:
      // 1. workflow_started (display_name: "工作流开始") → sendStatusUpdate('running', '工作流开始')
      // 2. node_started (display_name: "生成开始") → sendStatusUpdate('progress', '生成开始')
      // 最终状态栏被最后一次 STATUS_UPDATE 覆盖为 "生成开始"
      // 验证状态栏已被 STATUS_UPDATE 更新（不再是默认的"正在生成回复..."）
      const statusText = page.locator('#ha-status-text')
      await expect(statusText).not.toContainText('正在生成回复...', { timeout: 5000 })

      // 验证包含实际状态文案（无论是"工作流开始"还是"生成开始"都算正确）
      const text = await statusText.textContent()
      const isValidStatus = text.includes('工作流') || text.includes('生成')
      expect(isValidStatus).toBeTruthy()

      // 等待 completed
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 20000 })

    } finally {
      await context.close()
    }
  })

  test('重新生成：完成 → 点击重新生成 → 新回复流式输出', async () => {
    const context = await createContextWithHotel()

    try {
      const page = await context.newPage()
      await page.goto(MOCK_OTA_URL)
      await page.waitForLoadState('domcontentloaded')

      const fab = page.locator('#hotel-ai-fab')
      await expect(fab).toBeVisible({ timeout: 15000 })

      // 选中评论文本
      const reviewText = page.locator('.comment-content').first()
      await reviewText.waitFor({ state: 'visible' })
      await reviewText.click()

      // 打开面板
      await fab.click()
      const panel = page.locator('#hotel-ai-panel')
      await expect(panel).toBeVisible()
      await expect(panel).toHaveAttribute('data-view', 'idle')

      // 第一次生成：使用 mock-backend 默认场景
      await page.locator('#ha-generate-btn').click()
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })

      // 等待第一次完成
      const replyBox = page.locator('#ha-reply-box')
      await expect(replyBox).not.toContainText('等待回复...', { timeout: 15000 })
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 15000 })

      // 记录第一次回复内容
      const firstReply = await replyBox.textContent()
      expect(firstReply).toContain('尊敬的宾客')

      // 验证重新生成按钮可见
      const retryBtn = page.locator('#ha-retry-btn')
      await expect(retryBtn).toBeVisible()

      // 拦截第二次 SSE 请求，使用不同的 token 序列
      await page.route('**/review/stream/**', async (route) => {
        const events = [
          { kind: 'workflow_started', category: 'system', display_name: '工作流开始', source: 'system' },
          { kind: 'node_started', category: 'progress', source: 'generation', display_name: '生成开始', node_name: 'generation' },
          { kind: 'token_delta', category: 'message', delta: '第二次' },
          { kind: 'token_delta', category: 'message', delta: '生成的回复' },
          { kind: 'token_delta', category: 'message', delta: '，已更新' },
          { kind: 'node_completed', category: 'progress', source: 'generation', display_name: '生成完成', node_name: 'generation' },
          { kind: 'workflow_completed', category: 'system', display_name: '工作流完成', source: 'system', result: { reply_content: '第二次生成的回复，已更新' } },
        ]

        const body = events.map((evt, i) => {
          const data = JSON.stringify({
            id: `mock-retry-${Date.now()}-${i}`,
            workflow_id: 'mock-run-retry-001',
            sequence: i + 1,
            category: evt.category,
            kind: evt.kind,
            display_name: evt.display_name || null,
            source: evt.source || null,
            timestamp: Date.now(),
            ...evt,
          })
          return `data: ${data}\n\n`
        }).join('')

        await route.fulfill({
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          body,
        })
      })

      // 点击重新生成
      await retryBtn.click()

      // 验证面板回到 running 状态
      await expect(panel).toHaveAttribute('data-view', 'running', { timeout: 5000 })

      // 等待新回复流式输出
      await expect(replyBox).toContainText('第二次', { timeout: 15000 })

      // 等待第二次完成
      await expect(panel).toHaveAttribute('data-view', 'completed', { timeout: 15000 })

      // 验证最终回复内容是第二次生成的
      await expect(replyBox).toContainText('第二次生成的回复，已更新')

      // 验证完成视图有操作按钮
      await expect(page.locator('#ha-edit-btn')).toBeVisible()
      await expect(page.locator('#ha-publish-btn')).toBeVisible()
      await expect(retryBtn).toBeVisible()

    } finally {
      await context.close()
    }
  })
})
