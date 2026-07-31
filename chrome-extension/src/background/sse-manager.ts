/**
 * SSE Manager
 *
 * 管理多个 SSE 连接
 * 职责：
 * - EventSource 连接管理
 * - 断线重连（指数退避）
 * - lastSequence 断线恢复
 *
 * 连接状态：
 * - connecting
 * - connected
 * - reconnecting
 * - disconnected
 * - error
 */

import { getSessionManager, SessionStatus } from './session-manager.js'

// 重连配置
const RECONNECT_CONFIG = {
  maxRetry: 5,          // 最大重连次数
  baseDelay: 1000,       // 基础延迟（毫秒）
  maxDelay: 30000,       // 最大延迟（毫秒）
  backoffMultiplier: 2,   // 退避倍数
}

// 连接状态枚举
export const ConnectionStatus = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
}

class SSEManager {
  constructor() {
    // runId -> Connection
    this._connections = {}
  }

  /**
   * 创建 SSE 连接
   */
  connect(runId, options = {}) {
    const {
      apiUrl = 'http://localhost:8000',
      lastSequence = 0,
      onEvent,
      onError,
      onComplete,
      onStatusChange,
      retry = false,
      maxRetry = 0,
    } = options

    // 如果已存在连接，先关闭
    if (this._connections[runId]) {
      this.disconnect(runId)
    }

    const connection = {
      status: ConnectionStatus.CONNECTING,
      eventSource: null,
      apiUrl,
      lastSequence,
      retry,
      maxRetry,
      retryCount: 0,
      onEvent,
      onError,
      onComplete,
      onStatusChange,
      reconnectTimeout: null,
    }

    this._connections[runId] = connection

    this._doConnect(runId)

    return connection
  }

  /**
   * 执行连接
   */
  async _doConnect(runId) {
    const connection = this._connections[runId]
    if (!connection) return

    const sessionManager = getSessionManager()
    const session = sessionManager.getSession(runId)

    // 更新连接状态
    connection.status = connection.retryCount > 0
      ? ConnectionStatus.RECONNECTING
      : ConnectionStatus.CONNECTING

    this._notifyStatusChange(runId)

    // 构建 SSE URL
    const url = `${connection.apiUrl}/review/stream/${runId}?last_sequence=${connection.lastSequence}`
    console.log('[SSEManager] Connecting to:', url)

    // 创建 EventSource
    connection.eventSource = new EventSource(url)

    // 连接打开
    connection.eventSource.onopen = () => {
      console.log('[SSEManager] Connected:', runId)
      connection.status = ConnectionStatus.CONNECTED
      this._notifyStatusChange(runId)

      // 收到首条消息后再清零 retryCount，避免空流反复 onopen 造成死循环
      sessionManager.resetReconnectCount(runId)
    }

    // 接收消息
    connection.eventSource.onmessage = (event) => {
      try {
        const raw = event.data
        if (raw === ': heartbeat' || raw.startsWith(': heartbeat')) {
          console.debug('[SSEManager] Heartbeat received:', runId)
          return  // 心跳事件，不需要处理
        }
        const workflowEvent = JSON.parse(raw)
        console.debug('[SSEManager] Received event:', runId, workflowEvent.kind, 'sequence:', workflowEvent.sequence)

        // 成功收到事件后再清零重试计数
        connection.retryCount = 0

        // 更新 lastSequence
        if (workflowEvent.sequence) {
          connection.lastSequence = workflowEvent.sequence
          sessionManager.updateSequence(runId, workflowEvent.sequence)
        }

        // 回调
        if (connection.onEvent) {
          connection.onEvent(workflowEvent)
        }

        // 检查是否完成
        if (workflowEvent.kind === 'workflow_completed') {
          this._handleComplete(runId, workflowEvent)
        } else if (
          workflowEvent.kind === 'workflow_failed' ||
          workflowEvent.kind === 'workflow_cancelled'
        ) {
          this._handleError(runId, workflowEvent.error || workflowEvent.kind)
        }

      } catch (error) {
        console.error('[SSEManager] Failed to parse event:', error)
      }
    }

    // 错误处理
    connection.eventSource.onerror = (error) => {
      console.error('[SSEManager] SSE error:', runId, 'type:', error?.type, 'event:', JSON.stringify({type: error?.type, eventPhase: (error as any)?.eventPhase, timeStamp: (error as any)?.timeStamp}))

      // EventSource 内置超时（约 30 秒无数据）会触发 onerror。
      // 如果已经收到过事件（retryCount == 0），说明流是通的，忽略此 error
      // 只在连续 error 时才需要处理
      if (
        !this._connections[runId] ||
        connection.status === ConnectionStatus.DISCONNECTED
      ) {
        return
      }

      // 首次 error（已收到过事件）大概率是空闲超时，自动重连
      if (connection.retryCount < connection.maxRetry) {
        console.log('[SSEManager] SSE idle timeout, reconnecting:', runId)
        connection.status = ConnectionStatus.RECONNECTING
        this._notifyStatusChange(runId)
        if (connection.eventSource) {
          connection.eventSource.close()
          connection.eventSource = null
        }
        this._scheduleReconnect(runId)
        return
      }

      connection.status = ConnectionStatus.ERROR
      this._notifyStatusChange(runId)

      // 关闭连接
      if (connection.eventSource) {
        connection.eventSource.close()
        connection.eventSource = null
      }

      // 检查是否需要重连
      if (connection.retry && connection.retryCount < connection.maxRetry) {
        this._scheduleReconnect(runId)
      } else {
        // 不重试，直接回调 onError 通知 content script
        if (connection.onError) {
          connection.onError(new Error('SSE 连接失败'))
        }
        this.disconnect(runId)
      }
    }
  }

  /**
   * 计划重连（指数退避）
   */
  _scheduleReconnect(runId) {
    const connection = this._connections[runId]
    if (!connection) return

    const sessionManager = getSessionManager()
    connection.retryCount += 1
    sessionManager.incrementReconnectCount(runId)

    // 计算延迟（指数退避）
    const delay = Math.min(
      RECONNECT_CONFIG.baseDelay * Math.pow(RECONNECT_CONFIG.backoffMultiplier, connection.retryCount - 1),
      RECONNECT_CONFIG.maxDelay
    )

    console.log(`[SSEManager] Reconnecting in ${delay}ms (attempt ${connection.retryCount})`)

    connection.status = ConnectionStatus.RECONNECTING
    this._notifyStatusChange(runId)

    connection.reconnectTimeout = setTimeout(() => {
      this._doConnect(runId)
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect(runId) {
    const connection = this._connections[runId]
    if (!connection) return

    // 清除重连定时器
    if (connection.reconnectTimeout) {
      clearTimeout(connection.reconnectTimeout)
      connection.reconnectTimeout = null
    }

    // 关闭 EventSource
    if (connection.eventSource) {
      connection.eventSource.close()
      connection.eventSource = null
    }

    connection.status = ConnectionStatus.DISCONNECTED
    this._notifyStatusChange(runId)

    console.log('[SSEManager] Disconnected:', runId)
  }

  /**
   * 重连（使用当前 lastSequence）
   */
  reconnect(runId) {
    const connection = this._connections[runId]
    if (!connection) {
      console.warn('[SSEManager] Cannot reconnect: no connection found')
      return
    }

    // 禁用自动重连（手动重连只尝试一次）
    const originalRetry = connection.retry
    connection.retry = false

    // 使用当前 lastSequence 重连
    this._doConnect(runId)

    // 恢复设置
    connection.retry = originalRetry
  }

  /**
   * 处理完成
   */
  _handleComplete(runId, event) {
    const connection = this._connections[runId]
    if (!connection) return

    const sessionManager = getSessionManager()

    // 标记 Session 完成
    sessionManager.markCompleted(runId, event.result)

    // 关闭连接
    this.disconnect(runId)

    // 回调
    if (connection.onComplete) {
      connection.onComplete(event)
    }

    console.log('[SSEManager] Complete:', runId)
  }

  /**
   * 处理错误
   */
  _handleError(runId, errorMessage) {
    const connection = this._connections[runId]
    if (!connection) return

    const sessionManager = getSessionManager()

    // 标记 Session 失败
    sessionManager.markFailed(runId, errorMessage)

    // 关闭连接
    this.disconnect(runId)

    // 回调
    if (connection.onError) {
      connection.onError(new Error(errorMessage))
    }

    console.log('[SSEManager] Error:', runId, errorMessage)
  }

  /**
   * 通知状态变化
   */
  _notifyStatusChange(runId) {
    const connection = this._connections[runId]
    if (connection?.onStatusChange) {
      connection.onStatusChange(connection.status)
    }
  }

  /**
   * 获取连接状态
   */
  getStatus(runId) {
    const connection = this._connections[runId]
    return connection?.status || null
  }

  /**
   * 检查是否已连接
   */
  isConnected(runId) {
    return this.getStatus(runId) === ConnectionStatus.CONNECTED
  }

  /**
   * 获取连接信息
   */
  getConnection(runId) {
    return this._connections[runId] || null
  }

  /**
   * 关闭所有连接
   */
  disconnectAll() {
    for (const runId of Object.keys(this._connections)) {
      this.disconnect(runId)
    }
  }

  /**
   * 获取所有连接
   */
  getAllConnections() {
    return Object.entries(this._connections).map(([runId, conn]) => ({
      runId,
      status: conn.status,
      lastSequence: conn.lastSequence,
      retryCount: conn.retryCount,
    }))
  }
}

// 单例
let _instance = null

export function getSSEManager() {
  if (!_instance) {
    _instance = new SSEManager()
  }
  return _instance
}
