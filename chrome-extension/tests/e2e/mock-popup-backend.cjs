/**
 * Mock Popup Backend Server
 *
 * 模拟 FastAPI 后端，包含：
 * 1. /api/hotels — 酒店 CRUD
 * 2. /api/hotels/{id}/reply-settings — 回复设置读写
 * 3. /review/run + /review/stream/{run_id} — SSE 工作流（复用 mock-backend）
 */

const http = require('http')

const PORT = 8000

// ── 内存数据 ──────────────────────────────────────────────────────────────────

let hotels = [
  { hotel_id: 'hotel_001', hotel_name: '深圳万豪酒店', city: '深圳' },
  { hotel_id: 'hotel_002', hotel_name: '北京希尔顿', city: '北京' },
]
let settingsStore = {
  'hotel_001': { tone: '专业', style: '正式', rules: ['投诉必须先表达歉意', '24小时内回复'] },
  'hotel_002': { tone: '温暖', style: '亲切', rules: ['感谢好评'] },
}
let nextId = 3

// ── 工具 ──────────────────────────────────────────────────────────────────────

function parseUrl(url) {
  const [path, queryString] = url.split('?')
  return { path, query: Object.fromEntries(new URLSearchParams(queryString || '')) }
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try { resolve(JSON.parse(body)) } catch { resolve(null) }
    })
    req.on('error', reject)
  })
}

function json(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify(data))
}

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
}

// ── Review SSE（复用 mock-backend 逻辑）────────────────────────────────────

const SCENARIOS = {
  default: [
    { kind: 'workflow_started', category: 'system', display_name: '工作流开始', source: 'system' },
    { kind: 'state_updated', category: 'state', state: { reviews_content: 'mock review' } },
    { kind: 'node_started', category: 'progress', source: 'generation', display_name: '生成开始', node_name: 'generation' },
    { kind: 'token_delta', category: 'message', delta: '尊敬' },
    { kind: 'token_delta', category: 'message', delta: '的宾客' },
    { kind: 'token_delta', category: 'message', delta: '，' },
    { kind: 'token_delta', category: 'message', delta: '感谢' },
    { kind: 'token_delta', category: 'message', delta: '您的反馈' },
    { kind: 'token_delta', category: 'message', delta: '，我们会尽快改进' },
    { kind: 'node_completed', category: 'progress', source: 'generation', display_name: '生成完成', node_name: 'generation' },
    { kind: 'workflow_completed', category: 'system', display_name: '工作流完成', source: 'system', result: { reply_content: '尊敬的宾客，感谢您的反馈，我们会尽快改进' } },
  ],
  no_display_name: [
    { kind: 'workflow_started', category: 'system', source: 'system' },
    { kind: 'token_delta', category: 'message', delta: '尊敬' },
    { kind: 'token_delta', category: 'message', delta: '的宾客，感谢您的反馈' },
    { kind: 'workflow_completed', category: 'system', display_name: '工作流完成', source: 'system', result: { reply_content: '尊敬的宾客，感谢您的反馈' } },
  ],
  node_failed: [
    { kind: 'workflow_started', category: 'system', display_name: '工作流开始', source: 'system' },
    { kind: 'node_started', category: 'progress', source: 'generation', display_name: '生成开始', node_name: 'generation' },
    { kind: 'node_failed', category: 'progress', source: 'generation', node_name: 'generation', error: '模拟失败' },
    { kind: 'workflow_failed', category: 'system', display_name: '工作流失败', source: 'system', error: '模拟失败' },
  ],
}

let MOCK_EVENTS = SCENARIOS.default

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

// ── 服务器 ──────────────────────────────────────────────────────────────────

const server = http.createServer(async (req, res) => {
  const { path, query } = parseUrl(req.url)
  setCors(res)

  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    res.end()
    return
  }

  // ── POST /review/run ──
  if (req.method === 'POST' && path === '/review/run') {
    await readBody(req)
    return json(res, 200, {
      run_id: 'mock-run-001',
      thread_id: 'mock-thread-001',
      status: 'pending',
    })
  }

  // ── GET /review/stream/{run_id}?scenario=xxx ──
  if (req.method === 'GET' && path.startsWith('/review/stream/')) {
    const scenario = query.scenario || 'default'
    MOCK_EVENTS = SCENARIOS[scenario] || SCENARIOS.default
    eventIndex = 0
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    })
    let i = 0
    const interval = setInterval(() => {
      if (i < MOCK_EVENTS.length) {
        res.write(formatSSE(MOCK_EVENTS[i]))
        i++
      } else {
        clearInterval(interval)
        res.end()
      }
    }, 150)
    req.on('close', () => clearInterval(interval))
    return
  }

  // ── POST /api/hotels ──
  if (req.method === 'POST' && path === '/api/hotels') {
    const body = await readBody(req)
    if (!body?.name || !body?.city) {
      return json(res, 400, { detail: 'name 和 city 不能为空' })
    }
    const hotel = {
      hotel_id: `hotel_${String(nextId++).padStart(3, '0')}`,
      hotel_name: body.name,
      city: body.city,
    }
    hotels.push(hotel)
    settingsStore[hotel.hotel_id] = { tone: '', style: '', rules: [] }
    return json(res, 201, { hotel_id: hotel.hotel_id, hotel_name: hotel.hotel_name })
  }

  // ── GET /api/hotels ──
  if (req.method === 'GET' && path === '/api/hotels') {
    return json(res, 200, hotels)
  }

  // ── GET /api/hotels/{id}/reply-settings ──
  const settingsMatch = path.match(/^\/api\/hotels\/([^/]+)\/reply-settings$/)
  if (settingsMatch && req.method === 'GET') {
    const hotelId = settingsMatch[1]
    const s = settingsStore[hotelId]
    if (!s) return json(res, 404, { detail: '酒店不存在' })
    return json(res, 200, s)
  }

  // ── PUT /api/hotels/{id}/reply-settings ──
  if (settingsMatch && req.method === 'PUT') {
    const hotelId = settingsMatch[1]
    if (!settingsStore[hotelId]) return json(res, 404, { detail: '酒店不存在' })
    const body = await readBody(req)
    settingsStore[hotelId] = body
    return json(res, 200, body)
  }

  json(res, 404, { detail: 'Not found' })
})

server.listen(PORT, () => {
  console.log(`[MockPopupBackend] Running on http://localhost:${PORT}`)
})

module.exports = server
