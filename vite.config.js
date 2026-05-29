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
        const start = url.searchParams.get('start') || '2026/01/01'
        const end = url.searchParams.get('end') || '2026/05/29'
        
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
