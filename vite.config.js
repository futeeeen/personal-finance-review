import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { spawn } from 'child_process'

// 自訂 Vite 伺服器中間件，提供後端 API 執行 Playwright 爬蟲
const crawlerApiPlugin = () => ({
  name: 'crawler-api-plugin',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const url = new URL(req.url, 'http://localhost')
      
      if (url.pathname === '/api/run-crawler') {
        const today = new Date()
        const yyyy = today.getFullYear()
        const mm = String(today.getMonth() + 1).padStart(2, '0')
        const dd = String(today.getDate()).padStart(2, '0')
        const defaultEnd = `${yyyy}/${mm}/${dd}`
        
        // 動態計算 9 個月前的第一天作為最早可查詢日期，避免硬編碼造成未來執行錯誤
        const startDateObj = new Date(today.getFullYear(), today.getMonth() - 8, 1)
        const startYyyy = startDateObj.getFullYear()
        const startMm = String(startDateObj.getMonth() + 1).padStart(2, '0')
        const defaultStart = `${startYyyy}/${startMm}/01`
        
        const start = url.searchParams.get('start') || defaultStart
        const end = url.searchParams.get('end') || defaultEnd
        
        res.writeHead(200, {
          'Content-Type': 'application/json; charset=utf-8',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive'
        })
        
        console.log(`[DevServer] 收到爬蟲請求，時間區間: ${start} ~ ${end}`)
        
        // 呼叫 python browser_crawler.py 並帶入參數
        const pyProcess = spawn('python', ['browser_crawler.py', '--start', start, '--end', end], {
          cwd: process.cwd(),
          shell: true
        })
        
        let stdoutData = ''
        let stderrData = ''
        
        pyProcess.stdout.on('data', (data) => {
          const str = data.toString()
          console.log(`[Crawler] ${str.trim()}`)
          stdoutData += str
        })
        
        pyProcess.stderr.on('data', (data) => {
          const str = data.toString()
          console.error(`[Crawler Error] ${str.trim()}`)
          stderrData += str
        })
        
        pyProcess.on('close', (code) => {
          console.log(`[DevServer] 爬蟲程式執行完畢，結束代碼: ${code}`)
          
          res.end(JSON.stringify({
            success: code === 0,
            code: code,
            stdout: stdoutData,
            stderr: stderrData
          }))
        })
        
      } else if (url.pathname === '/data/invoice_data.json') {
        const fs = require('fs')
        const path = require('path')
        const dbPath = path.join(process.cwd(), 'user_data', 'invoice_data.json')
        if (fs.existsSync(dbPath)) {
          res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
          })
          res.end(fs.readFileSync(dbPath))
        } else {
          res.writeHead(404, {
            'Content-Type': 'application/json'
          })
          res.end(JSON.stringify({ error: 'Database file not found' }))
        }
      } else {
        next()
      }
    })
  }
})

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), crawlerApiPlugin()],
})
