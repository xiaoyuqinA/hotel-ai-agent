/**
 * OTA Adapter 单元测试
 *
 * 覆盖：
 * - CtripAdapter.matches() URL 匹配
 * - CtripAdapter.getReview() 评论提取
 * - CtripAdapter.fillReply() 回复填充
 * - detectAdapter() 适配器检测
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { CtripAdapter } from '../../src/content-script/adapters/ctrip'

// Mock location
const mockLocation = (hostname: string) => {
  vi.stubGlobal('location', { hostname })
}

// Mock chrome.storage.local（matches() 现在读取 __HOTEL_AI_TEST_MODE）
vi.stubGlobal('chrome', {
  storage: {
    local: {
      get: vi.fn().mockResolvedValue({}),
    },
  },
})

// Helper: 创建带 innerText 的元素（jsdom 不完整支持 innerText）
const createElementWithText = (tag: string, className: string, text: string) => {
  const el = document.createElement(tag)
  el.className = className
  // innerText 需要 layout，jsdom 不支持，用 textContent 模拟
  Object.defineProperty(el, 'innerText', { value: text, writable: true })
  return el
}

describe('CtripAdapter', () => {
  let adapter: CtripAdapter

  beforeEach(() => {
    adapter = new CtripAdapter()
    document.body.innerHTML = ''
  })

  describe('matches', () => {
    it('应匹配 ctrip.com 域名', async () => {
      mockLocation('hotels.ctrip.com')
      expect(await adapter.matches()).toBe(true)
    })

    it('应匹配 YOU.ctrip.com', async () => {
      mockLocation('YOU.ctrip.com')
      expect(await adapter.matches()).toBe(true)
    })

    it('不应匹配非 ctrip 域名', async () => {
      mockLocation('www.booking.com')
      expect(await adapter.matches()).toBe(false)
    })

    it('不应匹配空 hostname', async () => {
      mockLocation('')
      expect(await adapter.matches()).toBe(false)
    })
  })

  describe('getReview', () => {
    it('应从 .comment-content 提取评论', async () => {
      mockLocation('hotels.ctrip.com')
      const el = createElementWithText('div', 'comment-content', '房间很干净，服务很好')
      document.body.appendChild(el)

      const result = await adapter.getReview()

      expect(result).not.toBeNull()
      expect(result?.content).toBe('房间很干净，服务很好')
      expect(result?.platform).toBe('ctrip')
    })

    it('应从 .review-content 提取评论', async () => {
      mockLocation('hotels.ctrip.com')
      const el = createElementWithText('div', 'review-content', '位置很方便')
      document.body.appendChild(el)

      const result = await adapter.getReview()

      expect(result).not.toBeNull()
      expect(result?.content).toBe('位置很方便')
    })

    it('无评论时返回 null', async () => {
      mockLocation('hotels.ctrip.com')
      document.body.innerHTML = `<div>空页面</div>`

      const result = await adapter.getReview()

      expect(result).toBeNull()
    })

    it('应提取评分', async () => {
      mockLocation('hotels.ctrip.com')
      // 使用完整 DOM 结构，确保 closest() 能找到 review-card
      document.body.innerHTML = `
        <div class="review-card">
          <div class="comment-content">很好</div>
          <div class="rating">4.5</div>
        </div>
      `
      // 补充 innerText（jsdom 不支持）
      const contentEl = document.querySelector('.comment-content')!
      const ratingEl = document.querySelector('.rating')!
      Object.defineProperty(contentEl, 'innerText', { value: '很好', writable: true })
      Object.defineProperty(ratingEl, 'innerText', { value: '4.5', writable: true })

      const result = await adapter.getReview()

      expect(result?.rating).toBe(4.5)
    })

    it('应提取 reviewId', async () => {
      mockLocation('hotels.ctrip.com')
      const container = document.createElement('div')
      container.setAttribute('data-review-id', '12345')
      const el = createElementWithText('div', 'comment-content', '好评')
      container.appendChild(el)
      document.body.appendChild(container)

      const result = await adapter.getReview()

      expect(result?.reviewId).toBe('12345')
    })
  })

  describe('fillReply', () => {
    it('应填充回复到 textarea', async () => {
      mockLocation('hotels.ctrip.com')
      document.body.innerHTML = `
        <textarea class="reply-textarea"></textarea>
      `

      const result = await adapter.fillReply('感谢您的反馈')

      expect(result).toBe(true)
      const textarea = document.querySelector('textarea') as HTMLTextAreaElement
      expect(textarea.value).toBe('感谢您的反馈')
    })

    it('无 textarea 时返回 false', async () => {
      mockLocation('hotels.ctrip.com')
      document.body.innerHTML = `<div>无输入框</div>`

      const result = await adapter.fillReply('测试')

      expect(result).toBe(false)
    })

    it('应触发 input 和 change 事件', async () => {
      mockLocation('hotels.ctrip.com')
      document.body.innerHTML = `
        <textarea class="reply-textarea"></textarea>
      `

      const textarea = document.querySelector('textarea')!
      const inputSpy = vi.fn()
      const changeSpy = vi.fn()
      textarea.addEventListener('input', inputSpy)
      textarea.addEventListener('change', changeSpy)

      await adapter.fillReply('触发事件')

      expect(inputSpy).toHaveBeenCalled()
      expect(changeSpy).toHaveBeenCalled()
    })
  })

  describe('publish', () => {
    it('应抛出错误（MVP 阶段手动确认）', async () => {
      await expect(adapter.publish()).rejects.toThrow('manual confirm required')
    })
  })
})
