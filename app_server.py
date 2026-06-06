# -*- coding: utf-8 -*-
import os
import sys
import json
import webbrowser
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 5173

# 取得靜態資源根目錄（支援 PyInstaller 解壓路徑與本地開發路徑）
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, 'dist')

class SPAAndApiHandler(SimpleHTTPRequestHandler):
    """
    自訂 HTTP 處理器，支援：
    1. SPA 單頁面路徑重寫（如果檔案不存在，均重定向至 index.html）
    2. /api/run-crawler 爬蟲接口
    """
    def __init__(self, *args, **kwargs):
        # 指定 SimpleHTTPRequestHandler 的靜態根目錄
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        clean_path = parsed_url.path

        # 處理 API 請求
        if clean_path == '/api/run-crawler':
            self.handle_crawler_api(parsed_url.query)
            return

        # 優先服務本地 Cwd 產出的真實發票資料庫，避免讀取打包在 exe 內的唯讀/舊資料
        if clean_path == '/data/invoice_data.json':
            local_db_path = os.path.join(os.getcwd(), 'user_data', 'invoice_data.json')
            if os.path.exists(local_db_path):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                try:
                    with open(local_db_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
                except Exception as e:
                    print(f"[本地伺服器] 讀取本地發票資料庫失敗，降級使用內建資料庫: {e}")

        # 支援 SPA 路由：若請求的靜態檔案不存在，自動返回 index.html
        filepath = os.path.join(DIST_DIR, clean_path.lstrip('/'))
        if not os.path.exists(filepath) or os.path.isdir(filepath):
            self.path = '/index.html'
            
        super().do_GET()

    def handle_crawler_api(self, query_str):
        params = urllib.parse.parse_qs(query_str)
        start_date = params.get('start', [''])[0]
        end_date = params.get('end', [''])[0]
        
        print(f"\n[本地伺服器] 收到同步爬蟲請求，區間: {start_date} ~ {end_date}")
        
        # 為了避免阻塞 HTTP 伺服器主線程，我們在背景啟動爬蟲
        response_data = {"success": False, "message": "啟動失敗"}
        
        try:
            # 引入並調用 browser_crawler 的自動化函數
            import browser_crawler
            import sys as py_sys
            
            # 暫時替換命令列參數以適配 browser_crawler.py
            old_argv = py_sys.argv
            py_sys.argv = ['browser_crawler.py']
            if start_date:
                py_sys.argv += ['--start', start_date]
            if end_date:
                py_sys.argv += ['--end', end_date]
                
            # 執行爬蟲與清洗流程
            browser_crawler.run_browser_automation()
            
            # 還原命令列參數
            py_sys.argv = old_argv
            
            response_data = {"success": True, "message": "同步與洗滌完成！"}
            self.send_response(200)
        except Exception as e:
            print(f"[本地伺服器] 爬蟲執行出錯: {e}")
            response_data = {"success": False, "error": str(e)}
            self.send_response(500)
            
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

def start_server():
    # 檢查 dist 目錄是否存在
    if not os.path.exists(DIST_DIR):
        print(f"[錯誤] 找不到前端靜態資料夾 '{DIST_DIR}'！")
        print("請先在終端機執行 `npm run build` 編譯前端代碼。")
        input("\n按下 [Enter] 鍵結束程式...")
        sys.exit(1)
        
    server = HTTPServer(('127.0.0.1', PORT), SPAAndApiHandler)
    url = f"http://localhost:{PORT}"
    
    print("=" * 70)
    print("   錢去哪了：發票財務儀表板本地服務已啟動！")
    print(f"   請在瀏覽器中瀏覽: {url}")
    print("   (關閉此主控台視窗即可關閉儀表板服務)")
    print("=" * 70)
    
    # 自動為使用者開啟瀏覽器
    threading.Thread(target=lambda: webbrowser.open(url)).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[本地伺服器] 服務已停止。")

if __name__ == '__main__':
    start_server()
