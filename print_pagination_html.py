import os
import json
from playwright.sync_api import sync_playwright

def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def run():
    config = load_config()
    phone_no = config.get("phoneNo", "")
    verification_code = config.get("verificationCode", "")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("[主控台] 載入登入頁面...")
        page.goto("https://www.einvoice.nat.gov.tw/accounts/login/mw")
        
        # Pre-fill
        try:
            page.locator("input[name*='phone']").first.fill(phone_no)
            page.locator("input[type='password']").first.fill(verification_code)
            page.locator("input[placeholder*='圖形']").first.focus()
            print("[主控台] 欄位已預填。請在瀏覽器中輸入驗證碼並登入...")
        except Exception as e:
            print(f"[主控台] 預填失敗: {e}")
            
        # Wait for login
        logged_in = False
        for _ in range(120):
            if page.is_closed():
                break
            if "login" not in page.url and "accounts/login" not in page.url:
                logged_in = True
                break
            page.wait_for_timeout(1000)
            
        if not logged_in:
            print("[主控台] 未檢測到登入，終止。")
            return
            
        print("[主控台] 登入成功！跳轉至查詢頁面...")
        page.wait_for_timeout(2000)
        page.goto("https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search", wait_until="networkidle")
        page.wait_for_timeout(1000)
        
        # 點選查詢以顯示列表和分頁
        page.locator("button:has-text('查詢')").click()
        page.wait_for_selector("input[type='checkbox']")
        page.wait_for_timeout(1000)
        
        # 抓取並列印分頁列 HTML
        print("\n" + "="*70)
        print(" === PAGINATION BOX HTML === ")
        print("="*70)
        html = page.locator('.pagination_box').first.evaluate('el => el.outerHTML')
        print(html)
        print("="*70 + "\n")
        
        browser.close()

if __name__ == "__main__":
    run()
