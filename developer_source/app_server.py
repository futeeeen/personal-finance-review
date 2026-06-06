# -*- coding: utf-8 -*-
import os
import sys
import json
import webbrowser
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = 5173

# 取得靜態資源根目錄（支援 PyInstaller 解壓路徑與本地開發路徑）
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, 'dist')

def get_user_data_path(*paths):
    """
    獲取與執行檔/腳本同級之 user_data/ 下的絕對路徑。
    若是打包成 EXE，則以 EXE 所在同級資料夾為準；
    若是開發環境，則以專案根目錄為準。
    """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(base_dir) == "developer_source":
            base_dir = os.path.dirname(base_dir)
    return os.path.join(base_dir, "user_data", *paths)


class SPAAndApiHandler(SimpleHTTPRequestHandler):
    """
    自訂 HTTP 處理器，支援：
    1. SPA 單頁面路徑重寫（如果檔案不存在，均重定向至 index.html）
    2. /api/run-crawler 爬蟲啟動接口
    3. /api/crawler-status 爬蟲進度與狀態查詢接口
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
        elif clean_path == '/api/crawler-status':
            self.handle_crawler_status()
            return

        # 優先服務本地 Cwd 產出的真實發票資料庫，避免讀取打包在 exe 內的唯讀/舊資料
        if clean_path == '/data/invoice_data.json':
            local_db_path = get_user_data_path('invoice_data.json')
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
            else:
                # 若本地資料庫不存在，直接返回 404 JSON，讓前端識別為初次使用！
                self.send_response(404)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Database file not found", "code": "FIRST_TIME_USE"}).encode('utf-8'))
                return

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
        
        # 檢查是否已經有爬蟲在執行
        status_file = get_user_data_path("crawler_status.json")
        if os.path.exists(status_file):
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                    if status_data.get("status") in ("running", "waiting_captcha"):
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "message": "已有爬蟲正在運行中"}).encode('utf-8'))
                        return
            except Exception:
                pass

        # 在背景啟動爬蟲，以防阻塞 HTTP 伺服器
        def run_crawler_thread():
            try:
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
            except Exception as e:
                print(f"[本地伺服器] 背景爬蟲執行出錯: {e}")
                try:
                    status_file = get_user_data_path("crawler_status.json")
                    with open(status_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "status": "error",
                            "message": f"啟動或同步出錯: {str(e)}。請確認 Python 依賴環境是否完整！",
                            "step": "error",
                            "error": str(e),
                            "timestamp": time.time()
                        }, f, ensure_ascii=False, indent=2)
                except Exception as ex:
                    print(f"[本地伺服器] 寫入錯誤狀態檔失敗: {ex}")

        # 寫入初始狀態以防輪詢時讀到空或舊狀態
        try:
            status_file = get_user_data_path("crawler_status.json")
            os.makedirs(os.path.dirname(status_file), exist_ok=True)
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump({
                    "status": "running",
                    "message": "正在啟動同步任務，請稍候...",
                    "step": "init",
                    "error": None,
                    "timestamp": time.time()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[本地伺服器] 初始化狀態檔失敗: {e}")

        # 啟動背景線程
        threading.Thread(target=run_crawler_thread, daemon=True).start()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True, "message": "已在背景啟動同步"}).encode('utf-8'))

    def handle_crawler_status(self):
        status_file = get_user_data_path("crawler_status.json")
        status_data = {"status": "idle", "message": "準備就緒", "step": "idle", "error": None}
        
        if os.path.exists(status_file):
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
            except Exception as e:
                status_data = {"status": "error", "message": f"讀取狀態失敗: {e}", "step": "error", "error": str(e)}
                
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(status_data).encode('utf-8'))

def start_server():
    # 檢查 dist 目錄是否存在
    if not os.path.exists(DIST_DIR):
        print(f"[錯誤] 找不到前端靜態資料夾 '{DIST_DIR}'！")
        print("請先在終端機執行 `npm run build` 編譯前端代碼。")
        input("\n按下 [Enter] 鍵結束程式...")
        sys.exit(1)
        
    # 重置爬蟲狀態檔，避免先前異常退出殘留 running 狀態
    try:
        status_file = get_user_data_path("crawler_status.json")
        if os.path.exists(status_file):
            os.remove(status_file)
    except Exception:
        pass
        
    server = ThreadingHTTPServer(('127.0.0.1', PORT), SPAAndApiHandler)
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
