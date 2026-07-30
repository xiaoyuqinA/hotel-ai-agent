/**
 * Mock Backend Server
 *
 * 模拟 FastAPI 后端的 SSE 工作流端点，用于 E2E 测试。
 *
 * POST /review/run  → 返回 run_id
 * GET  /review/stream/{run_id} → 返回 SSE 事件流
 */

const http = require('http')

const PORT = 8000

// 默认事件序列（完整的成功流程）
const MOCK_EVENTS_DEFAULT = [
  {
    kind: 'workflow_started',
    category: 'system',
    display_name: '工作流开始',
    source: 'system',
  },
  {
    kind: 'state_updated',
    category: 'state',
    state: { reviews_content: 'mock review' },
  },
  {
    kind: 'node_started',
    category: 'progress',
    source: 'generation',
    display_name: '生成开始',
    node_name: 'generation',
  },
  {
    kind: 'token_delta',
    category: 'message',
    delta: '尊敬',
  },
  {
    kind: 'token_delta',
    category: 'message',
    delta: '的宾客',
  },
  {
    kind: 'token_delta',
    category: 'message',
    delta: '，',
  },
  {
    kind: 'token_delta',
    category: 'message',
    delta: '感谢',
  },
  {
    kind: 'token_delta',
    category: 'message',
    delta: '您的反馈',
  },
  {
    kind: 'token_delta',
    category: 'message',
    delta: '，我们会尽快改进',
  },
  {
    kind: 'node_completed',
    category: 'progress',
    source: 'generation',
    display_name: '生成完成',
    node_name: 'generation',
  },
  {
    kind: 'workflow_completed',
    category: 'system',
    display_name: '工作流完成',
    source: 'system',
    result: { reply_content: '尊敬的宾客，感谢您的反馈，我们会尽快改进' },
  },
]

// 无 display_name 的事件序列（验证空 display_name 不发送 STATUS_UPDATE）
const MOCK_EVENTS_NO_DISPLAY_NAME = [
  {
    kind: 'workflow_started',
    category: 'system',
    source: 'system',
  },
  {
    kind: 'token_delta',
    category: 'message',
    delta: '尊敬',
  },
  {
    kind: 'token_delta',
    category: 'message',
    delta: '的宾客，感谢您的反馈',
  },
  {
    kind: 'workflow_completed',
    category: 'system',
    display_name: '工作流完成',
    source: 'system',
    result: { reply_content: '尊敬的宾客，感谢您的反馈' },
  },
]

// node_failed 无 display_name 的事件序列（验证不 fallback 到 source）
const MOCK_EVENTS_NODE_FAILED = [
  {
    kind: 'workflow_started',
    category: 'system',
    display_name: '工作流开始',
    source: 'system',
  },
  {
    kind: 'node_started',
    category: 'progress',
    source: 'generation',
    display_name: '生成开始',
    node_name: 'generation',
  },
  {
    kind: 'node_failed',
    category: 'progress',
    source: 'generation',
    node_name: 'generation',
    error: '模拟失败',
  },
  {
    kind: 'workflow_failed',
    category: 'system',
    display_name: '工作流失败',
    source: 'system',
    error: '模拟失败',
  },
]

// 支持通过 query parameter 选择事件序列
const SCENARIOS = {
  default: MOCK_EVENTS_DEFAULT,
  no_display_name: MOCK_EVENTS_NO_DISPLAY_NAME,
  node_failed: MOCK_EVENTS_NODE_FAILED,
}

let eventIndex = 0

function formatSSE(event) {
  const id = `mock-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const data = JSON.stringify({
    id,
    workflow_id: 'mock-run-001',
    sequence: ++eventIndex,
    category: event.category,
    kind: event.kind,
    display_name: event.display_name || null,
    source: event.source || null,
    timestamp: Date.now(),
    ...event,
  })
  return `data: ${data}\n\n`
}

const server = http.createServer((req, res) => {
  console.log(`[MockBackend] ${req.method} ${req.url}`)

  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    res.end()
    return
  }

  // POST /review/run
  if (req.method === 'POST' && req.url === '/review/run') {
    let body = ''
    req.on('data', (chunk) => { body += chunk })
    req.on('end', () => {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({
        run_id: 'mock-run-001',
        thread_id: 'mock-thread-001',
        status: 'pending',
      }))
    })
    return
  }

  // GET /review/stream/{run_id}?scenario=xxx
  if (req.method === 'GET' && req.url.startsWith('/review/stream/')) {
    const url = new URL(req.url, `http://localhost:${PORT}`)
    const scenario = url.searchParams.get('scenario') || 'default'
    const events = SCENARIOS[scenario] || MOCK_EVENTS_DEFAULT

    eventIndex = 0
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    })

    // 逐步发送事件，模拟真实 SSE 流
    let i = 0
    const interval = setInterval(() => {
      if (i < events.length) {
        res.write(formatSSE(events[i]))
        i++
      } else {
        clearInterval(interval)
        res.end()
      }
    }, 150)

    req.on('close', () => {
      clearInterval(interval)
    })
    return
  }

  res.writeHead(404)
  res.end('Not found')
})

server.listen(PORT, () => {
  console.log(`[MockBackend] Running on http://localhost:${PORT}`)
})