import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { spawn } from 'child_process'
import fs from 'fs'
import path from 'path'

// 自訂 Vite 伺服器中間件，提供後端 API 執行 Playwright 爬蟲與狀態查詢
const crawlerApiPlugin = () => ({
  name: 'crawler-api-plugin',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const url = new URL(req.url, 'http://localhost')
      let baseDir = process.cwd();
      if (path.basename(baseDir) === 'developer_source') {
        baseDir = path.dirname(baseDir);
      }
      const statusPath = path.join(baseDir, 'user_data', 'crawler_status.json')
      
      if (url.pathname === '/api/run-crawler') {
        const today = new Date()
        const yyyy = today.getFullYear()
        const mm = String(today.getMonth() + 1).padStart(2, '0')
        const dd = String(today.getDate()).padStart(2, '0')
        const defaultEnd = `${yyyy}/${mm}/${dd}`
        
        // 動態計算 7 個月前的第一天作為最早可查詢日期，避免大平台拒絕超時下載
        const startDateObj = new Date(today.getFullYear(), today.getMonth() - 7, 1)
        const startYyyy = startDateObj.getFullYear()
        const startMm = String(startDateObj.getMonth() + 1).padStart(2, '0')
        const defaultStart = `${startYyyy}/${startMm}/01`
        
        const start = url.searchParams.get('start') || defaultStart
        const end = url.searchParams.get('end') || defaultEnd
        
        console.log(`[DevServer] 收到爬蟲請求，時間區間: ${start} ~ ${end}`)

        // 檢查是否已經有爬蟲在執行
        if (fs.existsSync(statusPath)) {
          try {
            const statusData = JSON.parse(fs.readFileSync(statusPath, 'utf8'))
            if (statusData.status === 'running' || statusData.status === 'waiting_captcha') {
              res.writeHead(400, {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
              })
              res.end(JSON.stringify({ success: false, message: '已有爬蟲正在運行中' }))
              return
            }
          } catch (e) {
            // 解析出錯忽略，當作無狀態處理
          }
        }

        // 寫入初始狀態以防前端輪詢空窗
        const initialStatus = {
          status: 'running',
          message: '正在啟動同步任務，請稍候...',
          step: 'init',
          error: null,
          timestamp: Date.now() / 1000
        }
        fs.mkdirSync(path.dirname(statusPath), { recursive: true })
        fs.writeFileSync(statusPath, JSON.stringify(initialStatus, null, 2), 'utf8')
        
        // 呼叫 python browser_crawler.py 並帶入參數，在背景啟動
        const pyProcess = spawn('python', ['browser_crawler.py', '--start', start, '--end', end], {
          cwd: process.cwd(),
          shell: true
        })
        
        pyProcess.stdout.on('data', (data) => {
          console.log(`[Crawler] ${data.toString().trim()}`)
        })
        
        pyProcess.stderr.on('data', (data) => {
          console.error(`[Crawler Error] ${data.toString().trim()}`)
        })
        
        pyProcess.on('error', (err) => {
          console.error(`[DevServer] 無法啟動 Python 爬蟲: ${err.message}`)
          writeErrorStatus(`無法啟動 Python 爬蟲: ${err.message}。請確認 Python 是否已安裝並加入 PATH！`, err.message)
        })
        
        pyProcess.on('close', (code) => {
          console.log(`[DevServer] 背景爬蟲程式執行完畢，結束代碼: ${code}`)
          if (code !== 0) {
            // 如果異常退出，且狀態仍為 running，則寫入錯誤狀態
            if (fs.existsSync(statusPath)) {
              try {
                const statusData = JSON.parse(fs.readFileSync(statusPath, 'utf8'))
                if (statusData.status === 'running' || statusData.status === 'waiting_captcha') {
                  writeErrorStatus(`同步異常退出 (錯誤代碼: ${code})，請確認您是否在正確的 Python 環境下執行。`, `Exit code ${code}`)
                }
              } catch (e) {}
            }
          }
        })
        
        function writeErrorStatus(msg, errDetail) {
          try {
            const errorStatus = {
              status: 'error',
              message: msg,
              step: 'error',
              error: errDetail,
              timestamp: Date.now() / 1000
            }
            fs.writeFileSync(statusPath, JSON.stringify(errorStatus, null, 2), 'utf8')
          } catch (e) {
            console.error('[DevServer] 寫入錯誤狀態失敗:', e)
          }
        }

        // 立即向前端回傳啟動成功響應
        res.writeHead(200, {
          'Content-Type': 'application/json; charset=utf-8',
          'Access-Control-Allow-Origin': '*'
        })
        res.end(JSON.stringify({ success: true, message: '已在背景啟動同步' }))
        
      } else if (url.pathname === '/api/crawler-status') {
        res.writeHead(200, {
          'Content-Type': 'application/json; charset=utf-8',
          'Access-Control-Allow-Origin': '*'
        })
        if (fs.existsSync(statusPath)) {
          res.end(fs.readFileSync(statusPath))
        } else {
          res.end(JSON.stringify({ status: 'idle', message: '準備就緒', step: 'idle', error: null }))
        }
        
      } else if (url.pathname === '/api/custom-rules') {
        let baseDir = process.cwd();
        if (path.basename(baseDir) === 'developer_source') {
          baseDir = path.dirname(baseDir);
        }
        const configPath = path.join(baseDir, 'user_data', 'config.json')

        if (req.method === 'GET') {
          res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
          })
          let rules = { item_keywords: {}, seller_keywords: {} }
          if (fs.existsSync(configPath)) {
            try {
              const config = JSON.parse(fs.readFileSync(configPath, 'utf8'))
              rules = config.custom_rules || rules
            } catch (e) {}
          }
          res.end(JSON.stringify(rules))
        } else if (req.method === 'POST') {
          let body = ''
          req.on('data', chunk => { body += chunk.toString() })
          req.on('end', () => {
            try {
              const newRules = JSON.parse(body)
              let config = {}
              if (fs.existsSync(configPath)) {
                config = JSON.parse(fs.readFileSync(configPath, 'utf8'))
              }
              config.custom_rules = newRules
              fs.mkdirSync(path.dirname(configPath), { recursive: true })
              fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf8')
              
              res.writeHead(200, {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
              })
              res.end(JSON.stringify({ success: true }))
            } catch (e) {
              res.writeHead(500, {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
              })
              res.end(JSON.stringify({ success: false, error: e.message }))
            }
          })
        }
      } else if (url.pathname === '/api/run-cleaner' && req.method === 'POST') {
        let baseDir = process.cwd();
        if (path.basename(baseDir) === 'developer_source') {
          baseDir = path.dirname(baseDir);
        }
        
        console.log('[DevServer] 收到手動資料清洗請求...')
        
        const pyProcess = spawn('python', ['data_cleaner.py'], {
          cwd: path.join(baseDir, 'developer_source'),
          shell: true
        })
        
        pyProcess.on('close', (code) => {
          console.log(`[DevServer] 手動資料清洗執行完畢，結束代碼: ${code}`)
          res.writeHead(code === 0 ? 200 : 500, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
          })
          res.end(JSON.stringify({ success: code === 0 }))
        })
      } else if (url.pathname === '/data/invoice_data.json') {
        let baseDir = process.cwd();
        if (path.basename(baseDir) === 'developer_source') {
          baseDir = path.dirname(baseDir);
        }
        const dbPath = path.join(baseDir, 'user_data', 'invoice_data.json')
        if (fs.existsSync(dbPath)) {
          res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
          })
          res.end(fs.readFileSync(dbPath))
        } else {
          res.writeHead(404, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          })
          res.end(JSON.stringify({ error: 'Database file not found', code: 'FIRST_TIME_USE' }))
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
