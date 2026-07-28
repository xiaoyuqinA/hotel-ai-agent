/**
 * Event Router
 *
 * 将后端 WorkflowEvent 转换为 UI 消息
 * 职责：
 * - 按 category 分发事件
 * - 事件转换（WorkflowEvent → UI Message）
 * - 发送消息到 Content Script
 */

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
    await chrome.tabs.sendMessage(tabId, message)
  } catch (error) {
    console.debug('[EventRouter] Message send failed:', error.message)
  }
}

/**
 * 系统事件处理器
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
      sendToContentScript(tabId, {
        type: UIMessageType.STATUS_UPDATE,
        payload: {
          status: 'running',
          message: '连接成功，正在生成回复',
        },
      })
      break

    case 'workflow_completed':
      sendToContentScript(tabId, {
        type: UIMessageType.WORKFLOW_COMPLETED,
        payload: {
          status: 'completed',
          result: event.payload?.result,
        },
      })
      break

    case 'workflow_cancelled':
      sendToContentScript(tabId, {
        type: UIMessageType.WORKFLOW_CANCELLED,
        payload: {},
      })
      sendToContentScript(tabId, {
        type: UIMessageType.STATUS_UPDATE,
        payload: {
          status: 'cancelled',
          message: '工作流已取消',
        },
      })
      break

    case 'workflow_failed':
      sendToContentScript(tabId, {
        type: UIMessageType.WORKFLOW_ERROR,
        payload: {
          error: event.payload?.error || '工作流执行失败',
        },
      })
      sendToContentScript(tabId, {
        type: UIMessageType.STATUS_UPDATE,
        payload: {
          status: 'error',
          message: '工作流执行失败',
        },
      })
      break
  }
}

/**
 * 进度事件处理器
 */
function handleProgressEvent(event, tabId) {
  let message = ''
  let statusType = 'progress'

  switch (event.kind) {
    case 'node_started': {
      const displayName = event.payload.display_name || event.source
      message = displayName === event.source
        ? `正在执行: ${event.source}`
        : displayName
      break
    }

    case 'node_completed':
      message = `${event.source} 完成`
      break

    case 'node_failed':
      message = `${event.source} 失败: ${event.payload.error}`
      statusType = 'error'
      break

    case 'custom_event':
      message = event.payload.event_type || '处理中'
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
        delta: event.payload.delta,
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
      state: event.payload.state,
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
        toolName: event.payload.tool_name,
        toolInput: event.payload.tool_input,
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
      if (event.kind === 'node_started') {
        return event.payload.display_name || event.source
      }
      if (event.kind === 'node_completed') {
        return `${event.source} 完成`
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
