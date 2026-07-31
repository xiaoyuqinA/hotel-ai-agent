// @vitest-environment jsdom

/**
 * 消息流集成测试
 *
 * 覆盖：
 * - Service Worker → Content Script 消息流
 * - Store 状态更新 → UI 更新
 * - 完整 token 流 → 回复累积
 * - workflow_completed → 结果提取
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createStore } from '../../src/state/workflow-store'
import type { WorkflowStore, WorkflowEvent } from '../../src/state/workflow-store'

// Mock DOM 环境
const setupDOM = () => {
  document.body.innerHTML = `
    <div id="hotel-ai-panel" class="hotel-ai-panel hidden">
      <div class="ha-panel-body">
        <div class="ha-reply-box" id="ha-reply-box">等待回复...</div>
        <div class="ha-status-text" id="ha-status-text"></div>
      </div>
    </div>
    <div id="hotel-ai-fab" class="hotel-ai-fab">
      <span>✦</span>
    </div>
  `
}

// 模拟 content-script 的消息处理逻辑
const createMessageHandler = (store: WorkflowStore) => {
  const handleMessage = (message: { type: string; payload: any }) => {
    const { type, payload } = message

    switch (type) {
      case 'TOKEN_DELTA':
        store.handleEvent({
          kind: 'token_delta',
          delta: payload.delta,
          category: 'message',
        })
        updateReplyUI(store.getReply())
        break

      case 'WORKFLOW_COMPLETED':
        store.handleEvent({
          kind: 'workflow_completed',
          result: payload.result,
          category: 'system',
        })
        updateStatusUI('completed', '回复生成完成')
        updateReplyUI(store.getReply())
        break

      case 'WORKFLOW_ERROR':
        store.handleEvent({
          kind: 'workflow_failed',
          error: payload.error,
          category: 'system',
        })
        updateStatusUI('error', payload.error)
        break

      case 'STATUS_UPDATE':
        updateStatusUI(payload.status, payload.message)
        break
    }
  }

  return handleMessage
}

// UI 更新函数
const updateReplyUI = (content: string) => {
  const box = document.getElementById('ha-reply-box')
  if (box) box.textContent = content
}

const updateStatusUI = (status: string, message: string) => {
  const el = document.getElementById('ha-status-text')
  if (el) el.textContent = message
}

describe('消息流集成测试', () => {
  let store: WorkflowStore
  let handleMessage: ReturnType<typeof createMessageHandler>

  beforeEach(() => {
    setupDOM()
    store = createStore()
    store.reset()  // 确保每次测试前清空状态
    handleMessage = createMessageHandler(store)
  })

  describe('Token 流式输出', () => {
    it('单个 token 应更新回复框', () => {
      handleMessage({
        type: 'TOKEN_DELTA',
        payload: { delta: '感谢' },
      })

      expect(store.getReply()).toBe('感谢')
      expect(document.getElementById('ha-reply-box')?.textContent).toBe('感谢')
    })

    it('多个 token 应累积显示', () => {
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '感谢' } })
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '您的' } })
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '反馈' } })

      expect(store.getReply()).toBe('感谢您的反馈')
      expect(document.getElementById('ha-reply-box')?.textContent).toBe('感谢您的反馈')
    })

    it('token 流 + completion 应显示最终结果', () => {
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '{"reply_content":' } })
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: ' "纯文本"}' } })

      // completion 事件携带解析后的纯文本，store 应提取并保存
      handleMessage({
        type: 'WORKFLOW_COMPLETED',
        payload: { result: { reply_content: '纯文本' } },
      })

      expect(store.getReply()).toBe('纯文本')
      expect(document.getElementById('ha-reply-box')?.textContent).toBe('纯文本')
    })
  })

  describe('Workflow 完成', () => {
    it('completion 应更新状态为 completed', () => {
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '回复内容' } })
      handleMessage({
        type: 'WORKFLOW_COMPLETED',
        payload: { result: { reply_content: '回复内容' } },
      })

      expect(store.getStatus()).toBe('completed')
      expect(document.getElementById('ha-status-text')?.textContent).toBe('回复生成完成')
    })

    it('completion 无 result 时保持 token 累积内容', () => {
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '累积内容' } })
      handleMessage({
        type: 'WORKFLOW_COMPLETED',
        payload: {},
      })

      expect(store.getReply()).toBe('累积内容')
    })
  })

  describe('Workflow 错误', () => {
    it('error 应设置错误信息', () => {
      handleMessage({
        type: 'WORKFLOW_ERROR',
        payload: { error: 'API 超时' },
      })

      expect(store.getStatus()).toBe('failed')
      expect(store.getError()).toBe('API 超时')
      expect(document.getElementById('ha-status-text')?.textContent).toBe('API 超时')
    })
  })

  describe('状态更新', () => {
    it('status_update 应更新状态文本', () => {
      handleMessage({
        type: 'STATUS_UPDATE',
        payload: { status: 'progress', message: '分析评论中' },
      })

      expect(document.getElementById('ha-status-text')?.textContent).toBe('分析评论中')
    })
  })

  describe('完整流程模拟', () => {
    it('模拟生成回复完整流程', () => {
      // 1. Token 流
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '尊敬' } })
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '的宾客' } })
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '，' } })
      handleMessage({ type: 'TOKEN_DELTA', payload: { delta: '感谢您的反馈' } })

      expect(store.getReply()).toBe('尊敬的宾客，感谢您的反馈')
      expect(store.isRunning()).toBe(false) // 初始状态

      // 2. 完成
      handleMessage({
        type: 'WORKFLOW_COMPLETED',
        payload: { result: { reply_content: '尊敬的宾客，感谢您的反馈' } },
      })

      expect(store.getStatus()).toBe('completed')
      expect(store.getReply()).toBe('尊敬的宾客，感谢您的反馈')
      expect(document.getElementById('ha-reply-box')?.textContent).toBe('尊敬的宾客，感谢您的反馈')
    })
  })
})