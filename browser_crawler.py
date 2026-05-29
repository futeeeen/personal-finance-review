import os
import json
import time
from playwright.sync_api import sync_playwright

def load_config():
    """載入設定檔"""
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def run_browser_automation():
    config = load_config()
    phone_no = config.get("phoneNo", "")
    verification_code = config.get("verificationCode", "")
    use_mock = config.get("useMock", True)
    
    # 確保資料夾存在
    os.makedirs("data", exist_ok=True)
    
    print("\n" + "="*70)
    print(" === 財政部電子發票大平台 - 全自動接手下載爬蟲系統 ===")
    print("="*70)
    
    if use_mock:
        print("[說明] 當前設定為 Mock 模擬模式。")
        print("       如果您希望進行真實網頁全自動下載，請將 config.json 中的 useMock 改為 false。")
        print("       現在腳本仍會開啟新版登入頁面供您體驗。")
        print("-"*70)

    print("[提示] 正在初始化 Playwright 瀏覽器核心...")
    
    with sync_playwright() as p:
        try:
            # 啟動 headed 模式瀏覽器以供使用者手動操作與輸入驗證碼
            browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        except Exception as e:
            print(f"\n[錯誤] 無法啟動 Chromium 瀏覽器: {e}")
            print("建議執行以下命令安裝 Playwright 瀏覽器相依組件:")
            print("  playwright install chromium")
            print("\n您可以改採「完全手動」方案：")
            print("1. 手動使用您平常的瀏覽器開啟財政部電子發票整合服務平台並登入。")
            print("2. 查詢您需要的時間區間並下載 CSV 發票明細檔。")
            print("3. 直接將下載的 CSV 檔案放入專案的 `data` 目錄下。")
            print("4. 執行 `python data_cleaner.py` 即可自動完成資料洗滌與更新儀表板！")
            return
            
        # 強制指定一個標準的大螢幕桌面解析度 (1440x900)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        print("[爬蟲] 正在載入新版財政部電子發票整合服務平台登入頁面...")
        # 直接進入新版消費者統一登入入口
        page.goto("https://www.einvoice.nat.gov.tw/accounts/login/mw")
        
        page.wait_for_timeout(3000)
        
        # 嘗試自動填寫手機號碼與驗證碼
        print("[爬蟲] 嘗試為您自動填入登入欄位...")
        try:
            phone_selectors = [
                "input[name*='phone']", "input[name*='mobile']", "input[id*='phone']", 
                "input[id*='mobile']", "input[placeholder*='手機']", "input[placeholder*='帳號']",
                "input[id*='username']", "input[name*='username']"
            ]
            phone_filled = False
            for sel in phone_selectors:
                if page.locator(sel).is_visible():
                    if phone_no and "09" in phone_no and phone_no != "0912345678":
                        page.locator(sel).fill(phone_no)
                        phone_filled = True
                        break
            
            pwd_selectors = [
                "input[type='password']", "input[name*='pwd']", "input[name*='encrypt']",
                "input[placeholder*='驗證碼']", "input[placeholder*='密碼']", "input[id*='password']"
            ]
            pwd_filled = False
            for sel in pwd_selectors:
                if page.locator(sel).is_visible():
                    if verification_code and verification_code != "TEST_PASSWORD" and verification_code != "YOUR_CARRIER_PASSWORD":
                        page.locator(sel).fill(verification_code)
                        pwd_filled = True
                        break
            
            if phone_filled and pwd_filled:
                print("[成功] 已成功自動填入您的手機號碼與密碼！")
            else:
                print("[提示] 未偵測到預填資訊或使用預設範例，請在瀏覽器中手動填入您的帳號與密碼。")
        except Exception as ex:
            print(f"[提示] 欄位預填略過: {ex}")
            
        print("\n" + "*"*65)
        print(" >>> 請在瀏覽器視窗中完成以下動作：")
        print("     1. 手動輸入「圖形驗證碼」。")
        print("     2. 點選「登入」按鈕。")
        print(" 📢 [提示] 登入成功後，機器人將「自動接手」進行網頁導航、日期輸入與下載！")
        print("*"*65 + "\n")
        
        # 1. 偵測登入成功 (等待 URL 重定向)
        print("[爬蟲] 正在偵測登入狀態，請輸入圖形驗證碼並手動點擊「登入」...")
        logged_in = False
        for _ in range(300): # 最多等待 5 分鐘
            if page.is_closed():
                break
            current_url = page.url
            if "login" not in current_url and "accounts/login" not in current_url:
                logged_in = True
                break
            page.wait_for_timeout(1000)
            
        if not logged_in or page.is_closed():
            print("[爬蟲] 未偵測到登入，或瀏覽器已關閉。腳本退出。")
            return

        print("[爬蟲] 偵測到登入成功！機器人正在接管瀏覽器...")
        page.wait_for_timeout(3000) # 等待登入後首頁載入完成
        
        # 2. 自動重定向跳轉至新版發票查詢頁面 (直接網頁跳轉，最快速且 100% 穩健！)
        # 新版電子發票平台發票查詢與捐贈路徑為 btc502w/search
        print("[爬蟲] 正在直接導航至『發票查詢及捐贈』頁面...")
        try:
            page.goto("https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search", timeout=20000)
            page.wait_for_timeout(3000) # 等待頁面載入
            print(f"[爬蟲] 導航成功，當前頁面: {page.url}")
        except Exception as e:
            print(f"[提示] 直接導航失敗，請在瀏覽器中手動點選『發票查詢及捐贈』選單: {e}")
            try:
                page.locator("text=發票查詢及捐贈").first.click()
            except Exception:
                pass
            
        page.wait_for_timeout(2000) # 等待查詢頁面穩定
        
        # 3. 自動設定日期範圍並點選查詢
        print("[爬蟲] 正在設定查詢條件...")
        query_success = False
        try:
            # 移除所有輸入框的 readonly 屬性，確保 Playwright 能 programmatic 直接填入日期！
            page.evaluate("() => { document.querySelectorAll('input').forEach(el => el.removeAttribute('readonly')); }")
            page.wait_for_timeout(500)

            # 搜尋日期起迄輸入框
            date_selectors = [
                "input[placeholder*='日期']", "input[placeholder*='起迄']", 
                "input[class*='date']", "input[class*='range']",
                "input[id*='date']", "input[name*='date']", "input[placeholder*='選擇']"
            ]
            
            date_input = None
            for sel in date_selectors:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    date_input = loc.first
                    break
                    
            if date_input:
                date_input.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                # 填入發票查詢的 6 個月時間區間 (西元格式，元件會自動對齊)
                date_range_str = "2026/01/01 ~ 2026/05/29"
                date_input.fill(date_range_str)
                print(f"[爬蟲] [OK] 已自動填入發票日期起迄: {date_range_str}")
                page.wait_for_timeout(500)
                
                # 點擊頁面標題以關閉可能彈出的日期選擇下拉選單
                try:
                    page.locator("text=發票查詢及捐贈").first.click()
                    page.wait_for_timeout(500)
                except Exception:
                    pass
            else:
                print("[提示] 未能自動定位日期輸入框，將使用網頁預設值（當月）。")
                
            # 尋找並點擊查詢按鈕 (以獨立選擇器尋找，防止 Playwright 語法崩潰)
            query_btn_selectors = [
                "button:has-text('查詢')", "input[type='button'][value='查詢']", 
                "input[type='submit'][value='查詢']", "button[id*='query']", 
                "button[id*='search']", "text=查詢"
            ]
            
            query_btn = None
            for sel in query_btn_selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        query_btn = loc.first
                        break
                except Exception:
                    continue
                    
            if query_btn:
                query_btn.click()
                print("[爬蟲] [OK] 已自動點擊『查詢』按鈕，正在等待發票列表載入...")
                page.wait_for_timeout(6000) # 給予 6 秒完整載入發票清單與表單
                query_success = True
            else:
                print("[提示] 未能自動定位『查詢』按鈕，請手動在瀏覽器中點選藍色『查詢』按鈕。")
                page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[提示] 自動設定查詢條件略過，請手動在瀏覽器設定日期並點擊『查詢』: {e}")
            
        # 4. 自動攔截並下載發票 CSV 檔案
        print("[爬蟲] 正在尋找 CSV 下載按鈕...")
        download_success = False
        try:
            # 獨立的選擇器列表，避免 comma-separated 混合選擇器的解析錯誤
            download_selectors = [
                "text=下載明細CSV", "text=下載明細", "text=下載", "text=匯出",
                "button:has-text('下載')", "button:has-text('匯出')", 
                "input[value*='下載']", "input[value*='匯出']", 
                "a:has-text('下載')", "a:has-text('匯出')", 
                "button[id*='download']", "a[id*='download']"
            ]
            
            download_btn = None
            for sel in download_selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        download_btn = loc.first
                        break
                except Exception:
                    continue
            
            if download_btn:
                print(f"[爬蟲] 偵測到下載按鈕！啟動自動下載攔截器...")
                with page.expect_download(timeout=20000) as download_info:
                    download_btn.click()
                download = download_info.value
                
                # 自動存檔至 data/invoices.csv
                target_path = os.path.join("data", "invoices.csv")
                download.save_as(target_path)
                print(f"[成功] [OK] 發票明細 CSV 檔案已自動下載並儲存至: {target_path}")
                download_success = True
                page.wait_for_timeout(2000)
            else:
                print("[提示] 找不到自動下載按鈕，請在瀏覽器中手動點擊『下載明細 CSV』或『匯出 CSV』...")
        except Exception as e:
            print(f"[提示] 自動下載失敗，請手動在瀏覽器下載 CSV，並放入專案的 `data/` 目錄中: {e}")
            
        if not download_success:
            print("\n" + "="*70)
            print(" 👉 機器人自動化下載受阻，請手動在瀏覽器完成下載動作：")
            print("   1. 請手動在瀏覽器下載您的發票 CSV 明細檔。")
            print("   2. 將下載的 CSV 檔案移至專案目錄的 `data/` 資料夾下。")
            print("="*70 + "\n")
            input(">>> 當您「手動下載好 CSV」並放入 `data/` 資料夾後，請回到此處按下 [Enter] 鍵繼續...")
            
        print("\n[爬蟲] 流程完成！正在關閉瀏覽器...")
        context.close()
        browser.close()
        
    print("[爬蟲] 瀏覽器已安全關閉。")
    print("[爬蟲] 正在啟動 Pandas 資料洗滌模組進行處理與更新...")
    
    # 呼叫資料清洗模組
    import data_cleaner
    success = data_cleaner.clean_and_process_invoices()
    if success:
        print("\n" + "="*70)
        print(" *** 恭喜！發票資料清洗成功，財務分析儀表板已更新！ ***")
        print("    現在您可以開啟 React 網頁 (npm run dev) 檢視您最新的發票財務看板。")
        print("="*70 + "\n")
    else:
        print("\n[警告] 資料清洗未能順利完成，請檢查 `data/` 目錄下是否確實放有發票 CSV 檔案。")

if __name__ == "__main__":
    run_browser_automation()
