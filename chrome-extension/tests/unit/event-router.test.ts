/**
 * Event Router 单元测试
 *
 * 覆盖：
 * - 事件路由（按 category 分发）
 * - 消息转换（WorkflowEvent → UI Message）
 * - Chrome API mock
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getEventRouter, UIMessageType } from '../../src/background/event-router'
import { setCurrentLang } from '../../src/i18n/index'

// Mock chrome API
const mockSendMessage = vi.fn()
vi.stubGlobal('chrome', {
  tabs: {
    sendMessage: mockSendMessage,
  },
})

describe('EventRouter', () => {
  let router: ReturnType<typeof getEventRouter>

  beforeEach(() => {
    // 固定当前语言为中文，保证状态文案本地化后仍是中文
    setCurrentLang('zh')
    vi.clearAllMocks()
    router = getEventRouter()
  })

  describe('system 事件', () => {
    it('workflow_started 应发送 WORKFLOW_STARTED + STATUS_UPDATE', () => {
      const event = {
        kind: 'workflow_started',
        category: 'system',
        display_name: '工作流开始',
        workflow_id: 'run-001',
        source: 'system',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledTimes(2)
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_STARTED,
        payload: { runId: 'run-001', status: 'running' },
      })
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.STATUS_UPDATE,
        payload: { status: 'running', message: '工作流开始' },
      })
    })

    it('workflow_started 无 display_name 时不发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'workflow_started',
        category: 'system',
        display_name: null,
        workflow_id: 'run-001',
        source: 'system',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledTimes(1)
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_STARTED,
        payload: { runId: 'run-001', status: 'running' },
      })
    })

    it('workflow_completed 应发送 WORKFLOW_COMPLETED + STATUS_UPDATE', () => {
      const event = {
        kind: 'workflow_completed',
        category: 'system',
        display_name: '工作流完成',
        workflow_id: 'run-001',
        source: 'system',
        result: { reply_content: '回复内容' },
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_COMPLETED,
        payload: { status: '工作流完成', result: { reply_content: '回复内容' } },
      })
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.STATUS_UPDATE,
        payload: { status: 'completed', message: '工作流完成' },
      })
    })

    it('workflow_completed 无 display_name 时不发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'workflow_completed',
        category: 'system',
        display_name: null,
        workflow_id: 'run-001',
        source: 'system',
        result: { reply_content: '回复内容' },
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledTimes(1)
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_COMPLETED,
        payload: { status: 'completed', result: { reply_content: '回复内容' } },
      })
    })

    it('workflow_failed 应发送 WORKFLOW_ERROR + STATUS_UPDATE', () => {
      const event = {
        kind: 'workflow_failed',
        category: 'system',
        display_name: '工作流失败',
        workflow_id: 'run-001',
        source: 'system',
        error: 'API 超时',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledTimes(2)
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_ERROR,
        payload: { error: 'API 超时' },
      })
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.STATUS_UPDATE,
        payload: { status: 'error', message: '工作流失败' },
      })
    })

    it('workflow_failed 无 display_name 时不发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'workflow_failed',
        category: 'system',
        display_name: null,
        workflow_id: 'run-001',
        source: 'system',
        error: 'API 超时',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledTimes(1)
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_ERROR,
        payload: { error: 'API 超时' },
      })
    })

    it('workflow_cancelled 有 display_name 时发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'workflow_cancelled',
        category: 'system',
        display_name: '工作流取消',
        workflow_id: 'run-001',
        source: 'system',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledTimes(2)
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_CANCELLED,
        payload: {},
      })
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.STATUS_UPDATE,
        payload: { status: 'cancelled', message: '工作流取消' },
      })
    })

    it('workflow_cancelled 无 display_name 时不发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'workflow_cancelled',
        category: 'system',
        display_name: null,
        workflow_id: 'run-001',
        source: 'system',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledTimes(1)
      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_CANCELLED,
        payload: {},
      })
    })
  })

  describe('message 事件', () => {
    it('token_delta 应发送 TOKEN_DELTA', () => {
      const event = {
        kind: 'token_delta',
        category: 'message',
        workflow_id: 'run-001',
        delta: '感谢',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.TOKEN_DELTA,
        payload: { delta: '感谢' },
      })
    })
  })

  describe('progress 事件', () => {
    it('node_started 有 display_name 时发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'node_started',
        category: 'progress',
        display_name: '分析开始',
        workflow_id: 'run-001',
        source: 'analysis',
        node_name: 'analysis',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.STATUS_UPDATE,
        payload: { status: 'progress', message: '分析开始' },
      })
    })

    it('node_started 无 display_name 时不发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'node_started',
        category: 'progress',
        display_name: null,
        workflow_id: 'run-001',
        source: 'analysis',
        node_name: 'analysis',
      }

      router.route(event, 1)

      expect(mockSendMessage).not.toHaveBeenCalled()
    })

    it('node_completed 有 display_name 时发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'node_completed',
        category: 'progress',
        display_name: '分析完成',
        workflow_id: 'run-001',
        source: 'analysis',
        node_name: 'analysis',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.STATUS_UPDATE,
        payload: { status: 'progress', message: '分析完成' },
      })
    })

    it('node_completed 无 display_name 时不发送 STATUS_UPDATE', () => {
      const event = {
        kind: 'node_completed',
        category: 'progress',
        display_name: null,
        workflow_id: 'run-001',
        source: 'analysis',
        node_name: 'analysis',
      }

      router.route(event, 1)

      expect(mockSendMessage).not.toHaveBeenCalled()
    })

    it('node_failed 有 display_name 时发送 STATUS_UPDATE（error 类型）', () => {
      const event = {
        kind: 'node_failed',
        category: 'progress',
        display_name: '分析失败',
        workflow_id: 'run-001',
        source: 'analysis',
        node_name: 'analysis',
        error: '出错',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.STATUS_UPDATE,
        payload: { status: 'error', message: '分析失败' },
      })
    })

    it('node_failed 无 display_name 时不发送 STATUS_UPDATE（不 fallback 到 source）', () => {
      const event = {
        kind: 'node_failed',
        category: 'progress',
        display_name: null,
        workflow_id: 'run-001',
        source: 'analysis',
        node_name: 'analysis',
        error: '出错',
      }

      router.route(event, 1)

      // 即使用 source 有值，也不应 fallback 到 source
      expect(mockSendMessage).not.toHaveBeenCalled()
    })
  })

  describe('未知 category', () => {
    it('未知 category 应透传为 WORKFLOW_EVENT', () => {
      const event = {
        kind: 'unknown_event',
        category: 'unknown',
        workflow_id: 'run-001',
        event_type: 'custom_action',
      }

      router.route(event, 1)

      expect(mockSendMessage).toHaveBeenCalledWith(1, {
        type: UIMessageType.WORKFLOW_EVENT,
        payload: event,
      })
    })
  })

  describe('getStatusMessage', () => {
    it('node_started 返回 display_name', () => {
      const event = {
        kind: 'node_started',
        category: 'progress',
        source: 'analysis',
        display_name: '分析开始',
        node_name: 'analysis',
      }

      expect(router.getStatusMessage(event)).toBe('分析开始')
    })

    it('node_completed 返回 display_name', () => {
      const event = {
        kind: 'node_completed',
        category: 'progress',
        source: 'generation',
        display_name: '生成完成',
        node_name: 'generation',
      }

      expect(router.getStatusMessage(event)).toBe('生成完成')
    })

    it('非 progress 事件返回空字符串', () => {
      const event = {
        kind: 'token_delta',
        category: 'message',
        delta: 'test',
      }

      expect(router.getStatusMessage(event)).toBe('')
    })
  })
})