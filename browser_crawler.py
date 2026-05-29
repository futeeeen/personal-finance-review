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
        
        # 2. 自動重定向跳轉至新版發票查詢頁面
        # 新版電子發票平台發票查詢與捐贈路徑為 btc502w/search
        print("[爬蟲] 正在直接導航至『發票查詢及捐贈』頁面...")
        try:
            page.goto("https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search", timeout=20000)
            print(f"[爬蟲] 導航成功，當前頁面: {page.url}")
        except Exception as e:
            print(f"[提示] 直接導航失敗，請在瀏覽器中手動點選『發票查詢及捐贈』選單: {e}")
            try:
                page.locator("text=發票查詢及捐贈").first.click()
            except Exception:
                pass
            
        # 3. 自動設定日期範圍並點選查詢
        print("[爬蟲] 正在設定查詢條件...")
        query_success = False
        try:
            # 等待查詢表單動態渲染完成 (最長等待 10 秒)
            print("[爬蟲] 正在等待查詢表單渲染完成...")
            page.wait_for_selector("input", timeout=10000)
            page.wait_for_timeout(1500) # 給予額外穩定時間

            # 移除所有輸入框的 readonly 屬性，確保 Playwright 能 programmatic 直接填入日期！
            page.evaluate("() => { document.querySelectorAll('input').forEach(el => el.removeAttribute('readonly')); }")
            page.wait_for_timeout(500)

            # 自適應多重日期輸入框定位器：獲取頁面所有輸入框並進行屬性分析
            inputs = page.locator("input")
            date_inputs = []
            for i in range(inputs.count()):
                input_el = inputs.nth(i)
                placeholder = str(input_el.get_attribute("placeholder") or "").lower()
                name = str(input_el.get_attribute("name") or "").lower()
                id_attr = str(input_el.get_attribute("id") or "").lower()
                class_attr = str(input_el.get_attribute("class") or "").lower()
                
                # 若包含日期關鍵字，納入處理
                if any(kw in placeholder or kw in name or kw in id_attr or kw in class_attr 
                       for kw in ['date', 'range', '日期', '起迄', '開始', '結束', '選擇', '起', '迄']):
                    page.evaluate("el => el.removeAttribute('readonly')", input_el.element_handle())
                    date_inputs.append(input_el)

            start_date_str = "2026/01/01"
            end_date_str = "2026/05/29"
            
            # 情況 A：單一日期範圍輸入框 (如：2026/01/01 ~ 2026/05/29)
            if len(date_inputs) == 1:
                date_input = date_inputs[0]
                date_input.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                date_range_str = f"{start_date_str} ~ {end_date_str}"
                date_input.fill(date_range_str)
                print(f"[爬蟲] [OK] 已自動填入單一日期起迄欄位: {date_range_str}")
                page.wait_for_timeout(500)
                
                # 點擊頁面標題關閉彈出的月曆面板
                try:
                    page.locator("text=發票查詢及捐贈").first.click()
                    page.wait_for_timeout(500)
                except Exception:
                    pass
            # 情況 B：兩個獨立的起、迄輸入框 (如：[開始日期] [結束日期])
            elif len(date_inputs) >= 2:
                # 填入開始日期
                date_inputs[0].click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                date_inputs[0].fill(start_date_str)
                print(f"[爬蟲] [OK] 已自動填入開始日期欄位: {start_date_str}")
                page.wait_for_timeout(500)
                
                # 填入結束日期
                date_inputs[1].click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                date_inputs[1].fill(end_date_str)
                print(f"[爬蟲] [OK] 已自動填入結束日期欄位: {end_date_str}")
                page.wait_for_timeout(500)
                
                try:
                    page.locator("text=發票查詢及捐贈").first.click()
                    page.wait_for_timeout(500)
                except Exception:
                    pass
            else:
                print("[提示] 未能自動定位日期輸入框，將採用網頁預設值（當月）。")
                
            # 尋找並點擊查詢按鈕
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
                query_success = True
            else:
                print("[提示] 未能自動定位『查詢』按鈕，請手動在瀏覽器中點選『查詢』。")
                page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[提示] 自動設定查詢條件略過，請手動在瀏覽器設定日期並點擊『查詢』: {e}")
            
        # 4. 等待明細發票列表與勾選框載入 (解決新版平台 /detail 頁面跳轉問題)
        print("[爬蟲] 正在等待查詢發票結果列表載入...")
        try:
            # 最長等待 15 秒，直到畫面上渲染出勾選方塊 (這代表查詢成功且發票清單已加載)
            page.wait_for_selector("input[type='checkbox']", timeout=15000)
            page.wait_for_timeout(1500) # 給予 1.5 秒讓表格穩定
            print(f"[爬蟲] [OK] 發票清單加載成功，當前網址: {page.url}")
        except Exception as e:
            print(f"[提示] 等待發票明細表載入超時，將嘗試直接尋找方塊: {e}")

        # 5. 自動勾選所有發票項目 (核心發現：大平台規定必須「勾選」發票才能啟用下載按鈕！)
        print("[爬蟲] 正在自動勾選所有發票項目以啟用下載按鈕...")
        try:
            checkboxes = page.locator("input[type='checkbox']")
            box_count = checkboxes.count()
            print(f"[爬蟲] 偵測到 {box_count} 個勾選方塊。")
            
            if box_count > 0:
                # 優先點擊第一個勾選框 (大平台通常第一個是 Table Header 中的「全選」按鈕)
                first_box = checkboxes.first
                if not first_box.is_checked():
                    first_box.check()
                    print("[爬蟲] [OK] 已自動點擊『全選』勾選框。")
                    page.wait_for_timeout(1000)
                
                # 安全保險：二次檢查，若仍有未勾選的個別項目，手動將其全部勾選
                for i in range(box_count):
                    box = checkboxes.nth(i)
                    if not box.is_checked():
                        box.check()
                print("[爬蟲] [OK] 所有發票項目已確保皆已勾選。")
            else:
                print("[提示] 找不到任何勾選框，可能該區間內沒有發票數據。")
        except Exception as e:
            print(f"[提示] 自動勾選發票略過，請手動在瀏覽器中點選「全選」勾選框: {e}")

        # 6. 自動攔截並下載發票 CSV 檔案 (等待按鈕啟用，避免 disabled 點擊超時)
        print("[爬蟲] 正在尋找 CSV 下載按鈕...")
        download_success = False
        try:
            download_selectors = [
                "text=下載明細CSV", "text=下載明細", "text=下載", "text=匯出",
                "button:has-text('下載')", "button:has-text('匯出')", 
                "input[value*='下載']", "input[value*='匯出']", 
                "a:has-text('下載')", "a:has-text('匯出')", 
                "button[id*='download']", "a[id*='download']", "button[title*='下載']"
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
                # 輪詢等待下載按鈕變成啟用狀態 (not disabled)，最長等待 20 秒
                print("[爬蟲] 偵測到下載按鈕。正在等待按鈕啟用...")
                btn_enabled = False
                for _ in range(20):
                    if not download_btn.is_disabled():
                        btn_enabled = True
                        break
                    page.wait_for_timeout(1000)
                
                if btn_enabled:
                    print("[爬蟲] [OK] 下載按鈕已啟用！啟動自動下載攔截器...")
                    with page.expect_download(timeout=25000) as download_info:
                        download_btn.click()
                    download = download_info.value
                    
                    # 自動存檔至 data/invoices.csv
                    target_path = os.path.join("data", "invoices.csv")
                    download.save_as(target_path)
                    print(f"[成功] [OK] 發票明細 CSV 檔案已自動下載並儲存至: {target_path}")
                    download_success = True
                    page.wait_for_timeout(2000)
                else:
                    print("[提示] 下載按鈕仍為禁用狀態，請您在瀏覽器中手動點擊『下載CSV檔』。")
            else:
                print("[提示] 找不到自動下載按鈕，請在瀏覽器中手動點擊『下載CSV檔』...")
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
