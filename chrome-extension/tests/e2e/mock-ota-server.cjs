/**
 * Mock OTA 静态文件服务器
 * 支持任意 Hostname（兼容 --host-resolver-rules）
 */

const http = require('http')
const fs = require('fs')
const path = require('path')

const PORT = 3456
const DIR = path.resolve(__dirname, 'fixtures/mock-ota')

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
}

const server = http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0]
  const filePath = path.join(DIR, urlPath === '/' ? 'index.html' : urlPath)

  if (!fs.existsSync(filePath)) {
    res.writeHead(404)
    res.end('Not found')
    return
  }

  const ext = path.extname(filePath)
  const contentType = MIME[ext] || 'application/octet-stream'

  res.writeHead(200, { 'Content-Type': contentType })
  fs.createReadStream(filePath).pipe(res)
})

server.listen(PORT, () => {
  console.log(`[MockOTA] Serving on http://localhost:${PORT}`)
})
