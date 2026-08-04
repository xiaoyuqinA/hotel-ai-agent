/**
 * Event Router
 *
 * 将后端 WorkflowEvent 转换为 UI 消息
 * 职责：
 * - 按 category 分发事件
 * - 事件转换（WorkflowEvent → UI Message）
 * - 发送消息到 Content Script
 */

import { initI18n, t } from '../i18n/index.js';

// 初始化语言（异步，通常早于首个事件）
initI18n();

// UI 消息类型枚举（与 content-script 对齐）
export const UIMessageType = {
  WORKFLOW_STARTED: 'WORKFLOW_STARTED',
  WORKFLOW_COMPLETED: 'WORKFLOW_COMPLETED',
  WORKFLOW_ERROR: 'WORKFLOW_ERROR',
  WORKFLOW_CANCELLED: 'WORKFLOW_CANCELLED',
  STATUS_UPDATE: 'STATUS_UPDATE',
  TOKEN_DELTA: 'TOKEN_DELTA',
  STATE_UPDATE: 'STATE_UPDATE',
  TOOL_CALL: 'TOOL_CALL',
  WORKFLOW_EVENT: 'WORKFLOW_EVENT',  // 透传自定义事件
}

/**
 * 发送消息到 Content Script
 */
async function sendToContentScript(tabId, message) {
  try {
    console.debug('[EventRouter] Sending to tab', tabId, ':', message.type)
    await chrome.tabs.sendMessage(tabId, message)
    console.debug('[EventRouter] Sent OK to tab', tabId, ':', message.type)
  } catch (error) {
    console.debug('[EventRouter] Message send failed to tab', tabId, ':', message.type, error.message)
  }
}

/**
 * 系统事件处理器
 * display_name 统一从事件顶层字段读取
 */
function handleSystemEvent(event, tabId) {
  switch (event.kind) {
    case 'workflow_started':
      sendToContentScript(tabId, {
        type: UIMessageType.WORKFLOW_STARTED,
        payload: {
          runId: event.workflow_id,
          status: 'running',
        },
      })
      sendStatusUpdate(tabId, 'running', event.display_name)
      break

    case 'workflow_completed':
      sendToContentScript(tabId, {
        type: UIMessageType.WORKFLOW_COMPLETED,
        payload: {
          status: event.display_name || 'completed',
          result: event.result,
        },
      })
      sendStatusUpdate(tabId, 'completed', event.display_name)
      break

    case 'workflow_cancelled':
      sendToContentScript(tabId, {
        type: UIMessageType.WORKFLOW_CANCELLED,
        payload: {},
      })
      sendStatusUpdate(tabId, 'cancelled', event.display_name)
      break

    case 'workflow_failed':
      sendToContentScript(tabId, {
        type: UIMessageType.WORKFLOW_ERROR,
        payload: {
          error: event.error || t('widget.operation_failed'),
        },
      })
      sendStatusUpdate(tabId, 'error', event.display_name)
      break
  }
}

function sendStatusUpdate(tabId, status, message) {
  if (!message) return
  sendToContentScript(tabId, {
    type: UIMessageType.STATUS_UPDATE,
    payload: { status, message },
  })
}

/**
 * 进度事件处理器
 * display_name 统一从事件顶层字段读取
 */
function handleProgressEvent(event, tabId) {
  let message = ''
  let statusType = 'progress'

  switch (event.kind) {
    case 'node_started':
    case 'node_completed':
      message = event.display_name
      break

    case 'node_failed':
      message = event.display_name
      statusType = 'error'
      break

    case 'custom_event':
      message = event.event_type || t('widget.processing')
      break
  }

  if (message) {
    sendToContentScript(tabId, {
      type: UIMessageType.STATUS_UPDATE,
      payload: { status: statusType, message },
    })
  }
}

/**
 * 消息事件处理器（token 流）
 */
function handleMessageEvent(event, tabId) {
  if (event.kind === 'token_delta') {
    sendToContentScript(tabId, {
      type: UIMessageType.TOKEN_DELTA,
      payload: {
        delta: event.delta,
      },
    })
  }
}

/**
 * 状态事件处理器
 */
function handleStateEvent(event, tabId) {
  sendToContentScript(tabId, {
    type: UIMessageType.STATE_UPDATE,
    payload: {
      state: event.state,
    },
  })
}

/**
 * 工具调用事件处理器
 */
function handleToolEvent(event, tabId) {
  if (event.kind === 'tool_call') {
    sendToContentScript(tabId, {
      type: UIMessageType.TOOL_CALL,
      payload: {
        toolName: event.tool_name,
        toolInput: event.tool_input,
      },
    })
  }
}

/**
 * 自定义事件处理器
 */
function handleCustomEvent(event, tabId) {
  // 透传自定义事件
  sendToContentScript(tabId, {
    type: UIMessageType.WORKFLOW_EVENT,
    payload: event,
  })
}

// Category 到 Handler 的映射
const CATEGORY_HANDLERS = {
  system: handleSystemEvent,
  progress: handleProgressEvent,
  message: handleMessageEvent,
  state: handleStateEvent,
  tool: handleToolEvent,
  custom: handleCustomEvent,
}

class EventRouter {
  /**
   * 路由事件
   */
  route(event, tabId) {
    const handler = CATEGORY_HANDLERS[event.category]

    if (handler) {
      handler(event, tabId)
    } else {
      // 未知的 category，透传
      handleCustomEvent(event, tabId)
    }
  }

  /**
   * 获取状态消息
   */
  getStatusMessage(event) {
    if (event.category === 'progress') {
      if (event.kind === 'node_started' || event.kind === 'node_completed') {
        return event.display_name || ''
      }
    }
    return ''
  }
}

// 单例
let _instance = null

export function getEventRouter() {
  if (!_instance) {
    _instance = new EventRouter()
  }
  return _instance
}
