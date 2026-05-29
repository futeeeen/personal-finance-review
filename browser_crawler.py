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
    print(" === 財政部電子發票大平台 - 半自動網頁爬蟲系統 ===")
    print("="*70)
    
    if use_mock:
        print("[說明] 當前設定為 Mock 模擬模式。")
        print("       如果您希望透過真實網頁下載 CSV 檔案，請將 config.json 中的 useMock 改為 false。")
        print("       現在腳本仍會開啟瀏覽器供您體驗登入與操作。")
        print("-"*70)

    print("[提示] 正在初始化 Playwright 瀏覽器核心...")
    
    with sync_playwright() as p:
        # 啟動 headed 模式瀏覽器以供使用者手動操作與輸入驗證碼
        try:
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
            
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        
        print("[爬蟲] 正在載入新版財政部電子發票整合服務平台登入頁面...")
        # 直接進入新版消費者統一登入入口
        page.goto("https://www.einvoice.nat.gov.tw/accounts/login/mw")
        
        # 等待網頁載入
        page.wait_for_timeout(3000)
        
        # 嘗試自動填寫手機號碼與驗證碼 (密碼)
        # 由於財政部網頁可能包含 frame 或特定的 selector，我們嘗試使用多種常見的 selector
        print("[爬蟲] 嘗試為您自動填入登入欄位...")
        try:
            # 搜尋手機號碼輸入框
            phone_selectors = [
                "input[name*='phone']", "input[name*='mobile']", "input[id*='phone']", 
                "input[id*='mobile']", "input[placeholder*='手機']", "input[placeholder*='帳號']"
            ]
            phone_filled = False
            for sel in phone_selectors:
                if page.locator(sel).is_visible():
                    if phone_no and "09" in phone_no and phone_no != "0912345678":
                        page.locator(sel).fill(phone_no)
                        phone_filled = True
                        break
            
            # 搜尋驗證碼密碼輸入框
            pwd_selectors = [
                "input[type='password']", "input[name*='pwd']", "input[name*='encrypt']",
                "input[placeholder*='驗證碼']", "input[placeholder*='密碼']"
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
                print("[提示] 未偵測到預填資訊或使用預設範例，請在瀏覽器中手動點擊並輸入您的帳密。")
        except Exception as ex:
            # 即使填寫失敗也不影響使用者手動操作
            print(f"[提示] 欄位預填略過: {ex}")
            
        print("\n" + "*"*65)
        print(" >>> 請在打開的瀏覽器視窗中完成以下「手動操作」：")
        print("   1. 輸入圖形驗證碼，並點選『登入』。")
        print("   2. 登入後，點選選單『載具消費發票查詢』(消費發票彙整/查詢)。")
        print("   3. 選擇您想查詢的日期範圍（如：2026/01/01 至 2026/05/29）。")
        print("   4. 點擊『查詢』並點選『下載 CSV 檔案』(或匯出 CSV)。")
        print("   5. 下載成功後，將該 CSV 檔案移動或複製到專案根目錄的 `data/` 資料夾下。")
        print("      (不需重新命名！腳本會自動偵測 `data/` 目錄下的任何 CSV 檔案。)")
        print("*"*65 + "\n")
        
        # 暫停腳本，等待使用者手動下載並放置 CSV
        print("📢 腳本目前處於暫停狀態，等待您在網頁上操作下載...")
        input(">>> 當您下載好 CSV 檔案並放入 `data/` 資料夾後，請回到此處按下 [Enter] 鍵繼續...")
        
        print("\n[爬蟲] 收到確認指令！正在關閉瀏覽器視窗...")
        context.close()
        browser.close()
        
    print("[爬蟲] 瀏覽器已安全關閉。")
    print("[爬蟲] 正在啟動 Pandas 資料洗滌模組進行檔案處理與儀表板更新...")
    
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
