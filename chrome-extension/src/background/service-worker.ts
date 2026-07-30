/**
 * Background Service Worker
 *
 * Chrome Extension Agent Runtime Orchestrator
 *
 * 职责：
 * - 消息入口（接收 content script 消息）
 * - 协调 SessionManager、SSEManager、EventRouter
 * - Service Worker 生命周期管理
 *
 * 架构：
 * ┌──────────────────────────────────────────────────┐
 * │  Content Script                                   │
 * │  - DOM 读取/写入                                  │
 * │  - UI 渲染                                       │
 * └────────────────────┬─────────────────────────────┘
 *                       │ chrome.runtime.sendMessage
 * ┌────────────────────▼────────────────────────────┐
 * │  Service Worker (Orchestrator)                    │
 * │  ┌─────────────────────────────────────────────┐ │
 * │  │ SessionManager: 状态管理                      │ │
 * │  │ SSEManager: 网络连接管理                      │ │
 * │  │ EventRouter: 事件分发                         │ │
 * │  └─────────────────────────────────────────────┘ │
 * └────────────────────┬─────────────────────────────┘
 *                       │ HTTP + SSE
 * ┌────────────────────▼────────────────────────────┐
 * │  FastAPI Backend                                 │
 * │  - WorkflowRuntime                              │
 * │  - LangGraph                                    │
 * │  - PostgreSQL + Redis                          │
 * └─────────────────────────────────────────────────┘
 */

import { getSessionManager, SessionStatus } from './session-manager.js'
import { getSSEManager, ConnectionStatus } from './sse-manager.js'
import { getEventRouter } from './event-router.js'

// ── 配置 ─────────────────────────────────────────────────────────────────────

/** 后端 API 地址（统一配置，由开发者维护） */
const DEFAULT_API_URL = 'http://localhost:8000'

// Service Worker 启动延迟重连的配置
const RECONNECT_DELAY_BASE = 500  // 基础延迟（毫秒）
const RECONNECT_DELAY_STEP = 200  // 递增步长（毫秒）

// ── 状态 ─────────────────────────────────────────────────────────────────────

let activeTabId = null

// ── 初始化 ─────────────────────────────────────────────────────────────────

/**
 * Service Worker 启动
 */
async function onServiceWorkerStart() {
  console.log('[ServiceWorker] Starting...')

  // 初始化 SessionManager（从 storage 恢复）
  const sessionManager = getSessionManager()
  await sessionManager.init()

  // 清理过期 Session
  await sessionManager.cleanup()

  // 恢复 Running 状态的 Session（延迟重连避免瞬间压力）
  const runningSessions = sessionManager.getRunningSessions()
  console.log('[ServiceWorker] Found running sessions:', runningSessions.length)

  for (let i = 0; i < runningSessions.length; i++) {
    const session = runningSessions[i]
    // 延迟重连
    setTimeout(() => {
      reconnectSession(session)
    }, i * RECONNECT_DELAY_STEP)
  }

  console.log('[ServiceWorker] Started')
}

/**
 * 重连 Session
 */
async function reconnectSession(session) {
  const sseManager = getSSEManager()
  const eventRouter = getEventRouter()

  console.log('[ServiceWorker] Reconnecting session:', session.runId)

  sseManager.connect(session.runId, {
    lastSequence: session.lastSequence,
    retry: false,
    maxRetry: 0,
    onEvent: (event) => {
      eventRouter.route(event, session.tabId)
    },
    onError: (error) => {
      eventRouter.route({
        category: 'system',
        kind: 'workflow_failed',
        payload: { error: error.message },
      }, session.tabId)
    },
    onComplete: (event) => {
      eventRouter.route(event, session.tabId)
    },
    onStatusChange: (status) => {
      console.log('[ServiceWorker] Connection status:', session.runId, status)
    },
  })
}

// ── 消息处理 ─────────────────────────────────────────────────────────────────

/**
 * 监听 content script 消息
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // 保存当前 tab
  if (sender.tab?.id) {
    activeTabId = sender.tab.id
  }

  handleMessage(message, sender)
    .then(sendResponse)
    .catch((error) => {
      console.error('[ServiceWorker] Message handler error:', error)
      sendResponse({ error: error.message })
    })

  return true // 异步响应
})

/**
 * 处理消息
 */
async function handleMessage(message, sender) {
  const { type, payload } = message

  switch (type) {
    case 'PING':
      return { pong: true }

    case 'GET_CURRENT_HOTEL':
      return await handleGetCurrentHotel()

    case 'GET_HOTEL_CONFIG':
      return await handleGetHotelConfig(payload?.hotel_id)

    case 'GENERATE_REPLY':
      return await handleGenerateReply(payload, sender.tab?.id)

    case 'GET_STATUS':
      return await handleGetStatus()

    case 'CANCEL':
      return await handleCancel()

    case 'GET_SESSIONS':
      return await handleGetSessions()

	    case 'GET_API_URL':
	      return { apiUrl: DEFAULT_API_URL }


    default:
      throw new Error(`Unknown message type: ${type}`)
  }
}

// ── 核心业务 ─────────────────────────────────────────────────────────────────

/**
 * 生成回复
 */
async function handleGenerateReply(payload, tabId) {
  const { review, threadId, hotel_context } = payload
  const targetTabId = tabId || activeTabId

  if (!targetTabId) {
    throw new Error('No active tab')
  }

  const sessionManager = getSessionManager()
  const sseManager = getSSEManager()
  const eventRouter = getEventRouter()
  const apiUrl = await getApiUrl()

  try {
    // 1. 创建 workflow run（直接用 fetch，不用 client）
    const body = JSON.stringify({ reviews_content: review, hotel_context })
    console.log('[ServiceWorker] POST /review/run request body:', body)
    const response = await fetch(`${apiUrl}/review/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })

    if (!response.ok) {
      const errBody = await response.text().catch(() => '')
      console.error('[ServiceWorker] POST /review/run failed:', response.status, errBody)
      throw new Error(`Failed to create run: ${response.statusText}`)
    }

    const result = await response.json()
    console.log('[ServiceWorker] POST /review/run response:', JSON.stringify(result))
    const { run_id, thread_id } = result
    console.log('[ServiceWorker] Workflow run created:', run_id, 'targetTabId:', targetTabId)

    // 2. 创建 Session
    await sessionManager.createSession(run_id, targetTabId)
    await sessionManager.updateStatus(run_id, SessionStatus.RUNNING)

    // 3. 连接 SSE
    sseManager.connect(run_id, {
      apiUrl,
      lastSequence: 0,
      retry: false,
      maxRetry: 0,
      onEvent: (event) => {
        eventRouter.route(event, targetTabId)
      },
      onError: (error) => {
        sessionManager.markFailed(run_id, error.message)
        eventRouter.route({
          category: 'system',
          kind: 'workflow_failed',
          payload: { error: error.message },
        }, targetTabId)
      },
      onComplete: (event) => {
        // 由 SSE Manager 处理
      },
      onStatusChange: (status) => {
        console.log('[ServiceWorker] Connection status:', run_id, status)
      },
    })

    return { run_id, thread_id, status: 'running' }

  } catch (error) {
    console.error('[ServiceWorker] Failed to create workflow:', error)

    if (error.response) {
      const data = await error.response.json()
      throw new Error(data.detail || error.message)
    }
    throw error
  }
}

/**
 * 获取当前酒店（从 chrome.storage.local 读取，由 Service Worker 代理）
 */
async function handleGetCurrentHotel() {
  try {
    const result = await chrome.storage.local.get('current_hotel')
    return { current_hotel: result['current_hotel'] || null }
  } catch (error) {
    return { error: error.message, current_hotel: null }
  }
}

/**
 * 获取酒店完整配置
 */
async function handleGetHotelConfig(hotelId) {
  if (!hotelId) return { hotel_config: null }
  try {
    const result = await chrome.storage.local.get('hotel_configs')
    const configs = result['hotel_configs'] || []
    const hotel = configs.find(h => h.id === hotelId)
    return { hotel_config: hotel || null }
  } catch (error) {
    return { error: error.message, hotel_config: null }
  }
}

/**
 * 获取状态
 */
async function handleGetStatus() {
  const sessionManager = getSessionManager()
  const runningSessions = sessionManager.getRunningSessions()

  if (runningSessions.length === 0) {
    return { status: 'idle', sessions: [] }
  }

  // 返回第一个 running session 的状态
  const session = runningSessions[0]
  return {
    status: session.status,
    runId: session.runId,
    lastSequence: session.lastSequence,
    reconnectCount: session.reconnectCount,
  }
}

/**
 * 获取所有 Session
 */
async function handleGetSessions() {
  const sessionManager = getSessionManager()
  return {
    sessions: sessionManager.listSessions(),
    runningCount: sessionManager.getRunningSessions().length,
  }
}

/**
 * 取消工作流
 */
async function handleCancel() {
  const sessionManager = getSessionManager()
  const sseManager = getSSEManager()
  const apiUrl = await getApiUrl()

  // 获取当前 running session
  const runningSessions = sessionManager.getRunningSessions()

  for (const session of runningSessions) {
    // 1. 关闭 SSE 连接
    sseManager.disconnect(session.runId)

    // 2. 调用后端取消（可选）
    try {
      await fetch(`${apiUrl}/review/run/${session.runId}/cancel`, {
        method: 'POST',
      })
    } catch (e) {
      console.warn('[ServiceWorker] Cancel backend call failed:', e)
    }

    // 3. 标记 Session 取消
    await sessionManager.closeSession(session.runId)

    // 4. 通知 UI
    await sendToContentScript(session.tabId, {
      type: 'WORKFLOW_CANCELLED',
      payload: {},
    })
  }

  return { success: true }
}

/**
 * 设置 API URL
 */
// ── 辅助函数 ─────────────────────────────────────────────────────────────────

/**
 * 获取 API URL（统一配置，无需用户设置）
 */
async function getApiUrl() {
  return DEFAULT_API_URL
}

/**
 * 发送消息到 content script
 */
async function sendToContentScript(tabId, message) {
  try {
    await chrome.tabs.sendMessage(tabId, message)
  } catch (error) {
    console.debug('[ServiceWorker] Message send failed:', error.message)
  }
}

// ── Service Worker 生命周期 ─────────────────────────────────────────────────

/**
 * Service Worker 激活
 */
chrome.runtime.onInstalled.addListener(() => {
  console.log('[ServiceWorker] Installed')
})

/**
 * Service Worker 启动
 */
chrome.runtime.onStartup.addListener(async () => {
  console.log('[ServiceWorker] Startup')
  await onServiceWorkerStart()
})

// 首次加载时也执行
onServiceWorkerStart()

console.log('[ServiceWorker] Initialized')
