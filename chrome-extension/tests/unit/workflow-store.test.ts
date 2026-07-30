/**
 * Workflow Store 单元测试
 *
 * 覆盖：
 * - 状态管理（startRun, reset, setError）
 * - Token 流式累积（token_delta）
 * - Workflow 完成事件（workflow_completed）
 * - 回复编辑（setReply）
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { createStore } from '../../src/state/workflow-store'
import type { WorkflowStore, WorkflowEvent } from '../../src/state/workflow-store'

describe('WorkflowStore', () => {
  let store: WorkflowStore

  beforeEach(() => {
    store = createStore()
  })

  describe('初始状态', () => {
    it('应返回正确的初始状态', () => {
      const state = store.getState()
      expect(state.status).toBe('idle')
      expect(state.replyContent).toBe('')
      expect(state.hotelId).toBeNull()
      expect(state.error).toBeNull()
      expect(state.runId).toBeNull()
      expect(state.events).toEqual([])
    })
  })

  describe('startRun', () => {
    it('应设置状态为 running', () => {
      store.startRun('run-001', 'hotel_001')

      expect(store.getStatus()).toBe('running')
      expect(store.getRunId()).toBe('run-001')
      expect(store.isRunning()).toBe(true)
    })

    it('应清空之前的 reply 内容', () => {
      store.setReply('旧回复')
      store.startRun('run-002')

      expect(store.getReply()).toBe('')
    })

    it('应清空之前的 error', () => {
      store.setError('旧错误')
      store.startRun('run-003')

      expect(store.getError()).toBeNull()
    })
  })

  describe('token_delta 事件', () => {
    it('应累积单个 token', () => {
      store.startRun('run-001')

      store.handleEvent({
        kind: 'token_delta',
        delta: '感谢',
      })

      expect(store.getReply()).toBe('感谢')
    })

    it('应累积多个 token', () => {
      store.startRun('run-001')

      store.handleEvent({ kind: 'token_delta', delta: '感谢' })
      store.handleEvent({ kind: 'token_delta', delta: '您的' })
      store.handleEvent({ kind: 'token_delta', delta: '反馈' })

      expect(store.getReply()).toBe('感谢您的反馈')
    })

    it('空 delta 不影响内容', () => {
      store.startRun('run-001')

      store.handleEvent({ kind: 'token_delta', delta: '开始' })
      store.handleEvent({ kind: 'token_delta', delta: '' })
      store.handleEvent({ kind: 'token_delta', delta: '结束' })

      expect(store.getReply()).toBe('开始结束')
    })

    it('应记录事件', () => {
      store.startRun('run-001')

      store.handleEvent({ kind: 'token_delta', delta: '测试' })

      expect(store.getState().events).toHaveLength(1)
      expect(store.getState().events[0].kind).toBe('token_delta')
    })
  })

  describe('workflow_completed 事件', () => {
    it('应从 result 提取 reply_content 并保存', () => {
      store.startRun('run-001')
      store.handleEvent({ kind: 'token_delta', delta: '{"reply_content":' })
      store.handleEvent({ kind: 'token_delta', delta: ' "纯文本回复"}' })

      store.handleEvent({
        kind: 'workflow_completed',
        result: { reply_content: '纯文本回复' },
      })

      expect(store.getReply()).toBe('纯文本回复')
      expect(store.getStatus()).toBe('completed')
    })

    it('无 result 时保持累积的 token 内容', () => {
      store.startRun('run-001')
      store.handleEvent({ kind: 'token_delta', delta: '累积内容' })

      store.handleEvent({
        kind: 'workflow_completed',
      })

      expect(store.getReply()).toBe('累积内容')
      expect(store.getStatus()).toBe('completed')
    })

    it('result 无 reply_content 时保持累积内容', () => {
      store.startRun('run-001')
      store.handleEvent({ kind: 'token_delta', delta: '已有内容' })

      store.handleEvent({
        kind: 'workflow_completed',
        result: { other_field: 'value' },
      })

      expect(store.getReply()).toBe('已有内容')
    })
  })

  describe('workflow_failed 事件', () => {
    it('应设置 error 信息', () => {
      store.startRun('run-001')

      store.handleEvent({
        kind: 'workflow_failed',
        error: 'API 超时',
      })

      expect(store.getStatus()).toBe('failed')
      expect(store.getError()).toBe('API 超时')
    })
  })

  describe('setReply', () => {
    it('应直接设置回复内容', () => {
      store.startRun('run-001')
      store.handleEvent({ kind: 'token_delta', delta: 'AI生成' })

      store.setReply('手动编辑')

      expect(store.getReply()).toBe('手动编辑')
    })
  })

  describe('reset', () => {
    it('应清空所有状态', () => {
      store.startRun('run-001', 'hotel_001')
      store.handleEvent({ kind: 'token_delta', delta: '回复' })

      store.reset()

      const state = store.getState()
      expect(state.status).toBe('idle')
      expect(state.replyContent).toBe('')
      expect(state.hotelId).toBeNull()
      expect(state.error).toBeNull()
      expect(state.runId).toBeNull()
      expect(state.events).toEqual([])
    })
  })

  describe('updateCallback', () => {
    it('状态变化时应触发回调', () => {
      const updates: any[] = []
      store.setUpdateCallback((state) => updates.push({ ...state }))

      store.startRun('run-001')
      store.handleEvent({ kind: 'token_delta', delta: '测试' })

      expect(updates).toHaveLength(2)
      expect(updates[0].status).toBe('running')
      expect(updates[1].replyContent).toBe('测试')
    })
  })
})