import os
import json
import time
import sys
from playwright.sync_api import sync_playwright

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


def update_crawler_status(status, message, step=None, error=None):
    """更新並寫入爬蟲狀態與進度到 user_data/crawler_status.json"""
    status_path = get_user_data_path("crawler_status.json")
    status_data = {
        "status": status,
        "message": message,
        "step": step or status,
        "error": error,
        "timestamp": time.time()
    }
    # 確保資料夾存在
    os.makedirs(os.path.dirname(status_path), exist_ok=True)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)

def init_user_data_directory():
    """初始化並建立分離的資料夾與預設設定檔"""
    os.makedirs(get_user_data_path("invoices"), exist_ok=True)
    config_path = get_user_data_path("config.json")
    if not os.path.exists(config_path):
        default_config = {
            "phoneNo": "",
            "verificationCode": ""
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        print("\n" + "="*75)
        print(" [系統初始化] 已為您在 user_data/ 下建立預設的 config.json 設定檔。")
        print("             (您可以在 user_data/config.json 填入載具帳密以啟用自動登入，或直接在瀏覽器手動輸入)")
        print("="*75 + "\n")

def load_config():
    """載入設定檔"""
    init_user_data_directory()
    config_path = get_user_data_path("config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def run_browser_automation():
    import sys
    from datetime import datetime, timedelta
    
    # 預設起迄日期：大平台支援回溯約 9 個月（包含當月），我們動態計算其最早月份的第一天，確保代碼具備未來相容性！
    end_date = datetime.now()
    end_date_str = end_date.strftime("%Y/%m/%d")
    
    # 往回推 7 個月，並將日期設為該月第一天
    # 例如當前為 2026/06，回推 7 個月即為 2025/11/01
    y = end_date.year
    m = end_date.month - 7
    while m <= 0:
        m += 12
        y -= 1
    start_date = datetime(y, m, 1)
    start_date_str = start_date.strftime("%Y/%m/%d")
    
    # 支援以命令列參數傳入 --start YYYY/MM/DD --end YYYY/MM/DD
    for i in range(len(sys.argv)):
        if sys.argv[i] == '--start' and i + 1 < len(sys.argv):
            start_date_str = sys.argv[i+1].replace('-', '/')
        elif sys.argv[i] == '--end' and i + 1 < len(sys.argv):
            end_date_str = sys.argv[i+1].replace('-', '/')
            
    config = load_config()
    phone_no = config.get("phoneNo", "")
    verification_code = config.get("verificationCode", "")
    
    # 確保資料夾存在
    os.makedirs(get_user_data_path("invoices"), exist_ok=True)
    
    print("\n" + "="*70)
    print(" === 財政部電子發票大平台 - 全自動接手下載爬蟲系統 ===")
    print("="*70)
    
    print("[提示] 正在初始化 Playwright 瀏覽器核心...")
    update_crawler_status("running", "正在初始化 Playwright 瀏覽器核心...", "init")
    
    with sync_playwright() as p:
        try:
            # 優先嘗試啟動本地 Google Chrome，再嘗試 Microsoft Edge，最後降級至 Playwright 預設 Chromium
            # 這能保證即使未執行 "playwright install chromium"，也能直接藉由使用者本地的瀏覽器開啟！
            try:
                browser = p.chromium.launch(headless=False, channel="chrome", args=["--start-maximized"])
                print("[爬蟲] 成功載入本地 Google Chrome 瀏覽器")
                update_crawler_status("running", "成功載入本地 Google Chrome，準備載入登入頁面...", "browser_started")
            except Exception:
                try:
                    browser = p.chromium.launch(headless=False, channel="msedge", args=["--start-maximized"])
                    print("[爬蟲] 成功載入本地 Microsoft Edge 瀏覽器")
                    update_crawler_status("running", "成功載入本地 Microsoft Edge，準備載入登入頁面...", "browser_started")
                except Exception:
                    browser = p.chromium.launch(headless=False, args=["--start-maximized"])
                    print("[爬蟲] 成功載入 Playwright 預設 Chromium 瀏覽器")
                    update_crawler_status("running", "成功載入 Playwright 預設 Chromium，準備載入登入頁面...", "browser_started")
        except Exception as e:
            print(f"\n[錯誤] 無法啟動任何相容的 Chromium 瀏覽器核心: {e}")
            update_crawler_status("error", f"無法啟動瀏覽器核心: {str(e)}", "error", str(e))
            print("建議執行以下命令安裝 Playwright 瀏覽器相依組件或安裝 Google Chrome/Edge:")
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
        
        # 註冊主控台日誌接聽器，以 safe ascii 備用方式印出，防範任何 non-BMP emoji 導致 CP950 崩潰！
        page.on("console", lambda msg: print(f"[瀏覽器主控台] {msg.text.encode('ascii', 'backslashreplace').decode()}"))
        
        print("[爬蟲] 正在載入新版財政部電子發票整合服務平台登入頁面...")
        update_crawler_status("running", "正在載入財政部電子發票登入頁面...", "loading_login")
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
                    if phone_no and phone_no.strip() and phone_no != "請輸入您的手機號碼 (10碼)" and phone_no != "0912345678":
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
                    if verification_code and verification_code.strip() and verification_code != "請輸入您的載具密碼 (首字通常為/)" and verification_code != "TEST_PASSWORD" and verification_code != "YOUR_CARRIER_PASSWORD":
                        page.locator(sel).fill(verification_code)
                        pwd_filled = True
                        break
            
            if phone_filled and pwd_filled:
                print("[成功] 已成功自動填入您的手機號碼與密碼！")
            else:
                print("[提示] 未偵測到預填資訊或使用預設範例，請在瀏覽器中手動填入您的帳號與密碼。")
                
            # 全自動聚焦並點選圖形驗證碼輸入框，方便使用者直接用鍵盤輸入！
            captcha_selectors = [
                "input[placeholder*='圖形']", "input[placeholder*='驗證碼']", 
                "input[name*='captcha']", "input[id*='captcha']", "input[placeholder*='驗證']"
            ]
            for sel in captcha_selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_visible():
                        loc.first.focus()
                        loc.first.click()
                        print("[成功] 已為您全自動聚焦並點選『圖形驗證碼』輸入框！您可以直接用鍵盤輸入驗證碼。")
                        break
                except Exception:
                    continue
        except Exception as ex:
            print(f"[提示] 欄位預填略過: {ex}")
            
        print("\n" + "*"*65)
        print(" >>> 請在瀏覽器視窗中完成以下動作：")
        print("     1. 手動輸入「圖形驗證碼」。")
        print("     2. 點選「登入」按鈕。")
        print(" [提示] 登入成功後，機器人將「自動接手」進行網頁導航、日期輸入與下載！")
        print("*"*65 + "\n")
        update_crawler_status("waiting_captcha", "⚠️ 請在彈出的瀏覽器視窗中輸入「圖形驗證碼」，並點擊「登入」！", "captcha")
        
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
            update_crawler_status("error", "未偵測到登入，或瀏覽器已關閉。同步取消。", "error", "未偵測到登入，或瀏覽器已關閉。")
            return

        print("[爬蟲] 偵測到登入成功！機器人正在接管瀏覽器...")
        update_crawler_status("running", "登入成功！正在接管瀏覽器并跳轉至發票查詢...", "login_success")
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
            
        # 3. 處理跨月份查詢 - 將指定起迄日期分割為數個自然月 (因為大平台限制「僅能查詢相同月份」)
        def split_range_into_months(start_str, end_str):
            from datetime import datetime
            import calendar
            try:
                start_dt = datetime.strptime(start_str, "%Y/%m/%d")
                end_dt = datetime.strptime(end_str, "%Y/%m/%d")
            except Exception:
                try:
                    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_str, "%Y-%m-%d")
                except Exception:
                    # 降級備用
                    return [(start_str, end_str)]
            
            ranges = []
            curr_dt = start_dt
            while curr_dt <= end_dt:
                last_day = calendar.monthrange(curr_dt.year, curr_dt.month)[1]
                month_start = datetime(curr_dt.year, curr_dt.month, 1)
                actual_start = max(month_start, start_dt)
                month_end = datetime(curr_dt.year, curr_dt.month, last_day)
                actual_end = min(month_end, end_dt)
                
                ranges.append((actual_start.strftime("%Y/%m/%d"), actual_end.strftime("%Y/%m/%d")))
                
                if curr_dt.month == 12:
                    curr_dt = datetime(curr_dt.year + 1, 1, 1)
                else:
                    curr_dt = datetime(curr_dt.year, curr_dt.month + 1, 1)
            return ranges

        month_ranges = split_range_into_months(start_date_str, end_date_str)
        # 逆序排列月份：從這個月開始，漸進式往前一個月抓取歷史資料！
        month_ranges.reverse()
        print(f"[爬蟲] 本次任務起迄: {start_date_str} ~ {end_date_str}")
        print(f"[爬蟲] 配合財政部限制「僅能查詢相同月份」，已將日期自動分割為 {len(month_ranges)} 個月份，並將由新至舊逆序批次下載...")
        
        # 清除 user_data/invoices 目錄下的舊 invoices*.csv 發票檔案，防止新舊資料混雜
        csv_dir = get_user_data_path("invoices")
        for file_name in os.listdir(csv_dir):
            if file_name.startswith("invoices") and file_name.endswith(".csv"):
                try:
                    os.remove(os.path.join(csv_dir, file_name))
                except Exception:
                    pass

        # 批次下載各個月份的 CSV 發票
        any_download_success = False
        
        for r_idx, (m_start, m_end) in enumerate(month_ranges):
            print("\n" + "-" * 60)
            print(f"[爬蟲] >>> 正在批次下載第 {r_idx + 1}/{len(month_ranges)} 個月份: {m_start} ~ {m_end}")
            update_crawler_status("running", f"正在下載發票明細：{m_start[:7]} ({r_idx + 1}/{len(month_ranges)})...", "downloading")
            print("-" * 60)
            
            # 只有當前頁面不是搜尋頁面時，才導航載入，防範 SPA 重劃/重載導致的 Loading 畫面閃爍與 JS Context 銷毀競態！
            if "btc502w/search" not in page.url:
                try:
                    # 使用 wait_until="networkidle" 確保網頁所有背景連線與轉導完全載入，穩定性極致提升！
                    page.goto("https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search", timeout=25000, wait_until="networkidle")
                    page.wait_for_timeout(1500)
                except Exception as ge:
                    print(f"[提示] 重新導航搜尋頁面失敗，將嘗試直接在當前頁面操作: {ge}")
            else:
                # 若已在搜尋頁面，給予短暫的物理穩定延遲，確保前一次下載完成後的狀態完全就緒！
                page.wait_for_timeout(1000)
            
            query_success = False
            try:
                # 等待查詢表單與查詢按鈕動態渲染並完全穩定可見 (最長等待 15 秒)，防範 SPA 路由渲染與非同步水合 race condition！
                page.wait_for_selector("button:has-text('查詢')", state="visible", timeout=15000)
                page.wait_for_timeout(1500) # 給予額外穩定時間，確保 Vue 雙向綁定與內部 Model 狀態完全就緒！
    
                # 移除所有輸入框的 readonly 屬性
                page.evaluate("() => { document.querySelectorAll('input').forEach(el => el.removeAttribute('readonly')); }")
                page.wait_for_timeout(300)
    
                # 自適應多重日期輸入框定位器
                inputs = page.locator("input")
                date_inputs = []
                for i in range(inputs.count()):
                    input_el = inputs.nth(i)
                    placeholder = str(input_el.get_attribute("placeholder") or "").lower()
                    name = str(input_el.get_attribute("name") or "").lower()
                    id_attr = str(input_el.get_attribute("id") or "").lower()
                    class_attr = str(input_el.get_attribute("class") or "").lower()
                    
                    if any(kw in placeholder or kw in name or kw in id_attr or kw in class_attr 
                           for kw in ['date', 'range', '日期', '起迄', '開始', '結束', '選擇', '起', '迄']):
                        page.evaluate("el => el.removeAttribute('readonly')", input_el.element_handle())
                        date_inputs.append(input_el)
        
                # 情況 A：單一日期範圍輸入框，採用高度智慧的日曆選單模擬點選 (Vue 3 雙向綁定相容)
                if len(date_inputs) == 1:
                    from datetime import datetime
                    try:
                        start_dt = datetime.strptime(m_start, "%Y/%m/%d")
                        end_dt = datetime.strptime(m_end, "%Y/%m/%d")
                    except Exception:
                        start_dt = datetime.strptime(m_start, "%Y-%m-%d")
                        end_dt = datetime.strptime(m_end, "%Y-%m-%d")
                    
                    target_year = start_dt.year
                    target_month = start_dt.month
                    target_start_day = start_dt.day
                    target_end_day = end_dt.day
                    
                    print(f"[爬蟲] 正在全自動模擬點選日曆: {target_year}年{target_month}月 {target_start_day}日 ~ {target_end_day}日...")
                    
                    # 1. 先用 Playwright 原生點擊開啟日曆
                    try:
                        date_inputs[0].click()
                        print("[爬蟲] 已點擊日期輸入框，等待日曆選單渲染...")
                        page.wait_for_selector(".dp__menu, .dp__outer_menu_wrap", timeout=5000)
                    except Exception as ce:
                        print(f"[警告] 原生點擊日曆彈窗超時或失敗: {ce}")
                    
                    # 2. 使用全網防冒泡穿透的 JS 點選算法
                    js_script = r"""
                    async (args) => {
                        const { startYear, startMonth, startDay, endDay } = args;
                        
                        // 全域禁用外部超連結和按鈕的點擊，徹底阻斷穿透與冒泡！
                        document.querySelectorAll('a, button, [role="button"], .sidebar, header, nav, .menu').forEach(el => {
                            if (!el.closest('.dp__menu') && !el.closest('.dp__outer_menu_wrap')) {
                                el.style.pointerEvents = 'none';
                            }
                        });
                        
                        try {
                            const triggerClick = (el) => {
                                if (!el) return;
                                if (typeof el.click === 'function') {
                                    el.click();
                                } else {
                                    el.dispatchEvent(new MouseEvent('click', {
                                        bubbles: true,
                                        cancelable: true,
                                        view: window
                                    }));
                                }
                            };
                            
                            const inputs = Array.from(document.querySelectorAll('input'));
                            const dateInput = inputs.find(el => {
                                const placeholder = (el.getAttribute("placeholder") || "").toLowerCase();
                                const name = (el.getAttribute("name") || "").toLowerCase();
                                const id = (el.getAttribute("id") || "").toLowerCase();
                                const className = (el.getAttribute("class") || "").toLowerCase();
                                return ['date', 'range', '日期', '起迄', '開始', '結束', '選擇', '起', '迄'].some(kw => 
                                    placeholder.includes(kw) || name.includes(kw) || id.includes(kw) || className.includes(kw)
                                );
                            });
                            
                            let container = document.querySelector('.dp__menu') || document.querySelector('.dp__outer_menu_wrap');
                            if (!container) {
                                const els = Array.from(document.querySelectorAll('*'));
                                container = els.find(el => {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width === 0 || rect.height === 0) return false;
                                    const style = window.getComputedStyle(el);
                                    if (style.display === 'none' || style.visibility === 'hidden') return false;
                                    if (el.tagName !== 'DIV') return false;
                                    const text = el.innerText || "";
                                    return text.includes("週一") && text.includes("週二") && text.includes("週日") && el.querySelectorAll('div').length > 5;
                                });
                            }
                            
                            if (!container) throw new Error("找不到彈出的日曆選單 DOM");
                            
                            container.style.pointerEvents = 'auto';
                            container.querySelectorAll('*').forEach(el => {
                                el.style.pointerEvents = 'auto';
                            });
                            
                            console.log("正在打開年份選擇器...");
                            const yearBtn = Array.from(container.querySelectorAll('button')).find(btn => 
                                (btn.getAttribute('aria-label') || "").includes("年份") || 
                                (btn.getAttribute('data-test') || "").includes("year") ||
                                /^\d{4}年?$/.test(btn.innerText.trim())
                            );
                            
                            if (!yearBtn) throw new Error("找不到年份選擇按鈕");
                            triggerClick(yearBtn);
                            await new Promise(resolve => setTimeout(resolve, 400));
                            
                            const targetYearText = `${startYear}年`;
                            const targetYearBtn = Array.from(container.querySelectorAll('*')).find(el => {
                                const text = (el.innerText || "").trim();
                                return (text === targetYearText || text === startYear.toString()) && el.children.length === 0;
                            });
                            
                            if (!targetYearBtn) throw new Error("找不到目標年份單元格: " + startYear);
                            console.log("已選擇目標年份: " + startYear);
                            triggerClick(targetYearBtn);
                            await new Promise(resolve => setTimeout(resolve, 400));
                            
                            let monthBtn = Array.from(container.querySelectorAll('button')).find(btn => 
                                (btn.getAttribute('aria-label') || "").includes("月份") || 
                                (btn.getAttribute('data-test') || "").includes("month") ||
                                /^\d{1,2}月$/.test(btn.innerText.trim())
                            );
                            
                            if (monthBtn) {
                                console.log("主動開啟月份選擇器...");
                                triggerClick(monthBtn);
                                await new Promise(resolve => setTimeout(resolve, 400));
                            }
                            
                            const targetMonthText = `${startMonth}月`;
                            const targetMonthBtn = Array.from(container.querySelectorAll('*')).find(el => {
                                const text = (el.innerText || "").trim();
                                return (text === targetMonthText || text === startMonth.toString()) && el.children.length === 0;
                            });
                            
                            if (!targetMonthBtn) throw new Error("找不到目標月份單元格: " + startMonth);
                            console.log("已選擇目標月份: " + startMonth);
                            triggerClick(targetMonthBtn);
                            await new Promise(resolve => setTimeout(resolve, 600));
                            
                            const getActiveDays = (calendarContainer) => {
                                const vuepicDays = Array.from(calendarContainer.querySelectorAll('.dp__cell_inner')).filter(el => {
                                    const className = el.getAttribute('class') || "";
                                    return !className.includes('disabled') && !className.includes('offset');
                                });
                                if (vuepicDays.length >= 28) return vuepicDays;
                                
                                const allEls = Array.from(calendarContainer.querySelectorAll('*'));
                                return allEls.filter(el => {
                                    const text = (el.innerText || "").trim();
                                    const val = parseInt(text, 10);
                                    return !isNaN(val) && val >= 1 && val <= 31 && text === val.toString() && el.children.length === 0;
                                });
                            };
                            
                            const activeDays = getActiveDays(container);
                            const startEl = activeDays.find(el => parseInt(el.innerText, 10) === startDay);
                            const endEl = activeDays.find(el => parseInt(el.innerText, 10) === endDay);
                            
                            if (!startEl || !endEl) throw new Error("找不到本月對應的日單元格");
                            
                            triggerClick(startEl);
                            await new Promise(resolve => setTimeout(resolve, 300));
                            triggerClick(endEl);
                            await new Promise(resolve => setTimeout(resolve, 600));
                            
                            return { success: true, finalValue: dateInput ? dateInput.value : "" };
                        } finally {
                            document.querySelectorAll('*').forEach(el => {
                                el.style.pointerEvents = 'auto';
                            });
                        }
                    }
                    """
                    
                    try:
                        res = page.evaluate(js_script, {
                            "startYear": target_year,
                            "startMonth": target_month,
                            "startDay": target_start_day,
                            "endDay": target_end_day
                        })
                        print(f"[爬蟲] 點選日曆完成！目前輸入欄位值為: {res.get('finalValue')}")
                        page.wait_for_timeout(300)
                    except Exception as je:
                        print(f"[警告] 點選日曆模擬出錯: {je}")
                        # 降級採用直接 value 寫入與 input/change 觸發
                        try:
                            fallback_js = r"""
                            async (args) => {
                                const { startYear, startMonth, endDay } = args;
                                const formatNum = (n) => n.toString().padStart(2, '0');
                                const startStr = `${startYear}/${formatNum(startMonth)}/01`;
                                const endStr = `${startYear}/${formatNum(startMonth)}/${formatNum(endDay)}`;
                                const dateRangeStr = `${startStr} ~ ${endStr}`;
                                
                                const inputs = Array.from(document.querySelectorAll('input'));
                                const dateInput = inputs.find(el => {
                                    const placeholder = (el.getAttribute("placeholder") || "").toLowerCase();
                                    const name = (el.getAttribute("name") || "").toLowerCase();
                                    const id = (el.getAttribute("id") || "").toLowerCase();
                                    const className = (el.getAttribute("class") || "").toLowerCase();
                                    return ['date', 'range', '日期', '起迄', '開始', '結束', '選擇', '起', '迄'].some(kw => 
                                        placeholder.includes(kw) || name.includes(kw) || id.includes(kw) || className.includes(kw)
                                    );
                                });
                                
                                if (!dateInput) throw new Error("找不到日期輸入框");
                                dateInput.removeAttribute('readonly');
                                dateInput.focus();
                                dateInput.value = dateRangeStr;
                                dateInput.dispatchEvent(new Event('input', { bubbles: true }));
                                dateInput.dispatchEvent(new Event('change', { bubbles: true }));
                                dateInput.dispatchEvent(new Event('blur', { bubbles: true }));
                                return { success: true, finalValue: dateInput.value };
                            }
                            """
                            res = page.evaluate(fallback_js, {
                                "startYear": target_year,
                                "startMonth": target_month,
                                "endDay": target_end_day
                            })
                            print(f"[爬蟲] 採用直接寫入日期欄位完成：{res.get('finalValue')}")
                        except Exception as re_e:
                            print(f"[警告] 降級直接寫入日期也失敗: {re_e}")
                # 情況 B：兩個獨立的起、迄輸入框
                elif len(date_inputs) >= 2:
                    date_inputs[0].click()
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    date_inputs[0].fill(m_start)
                    page.wait_for_timeout(300)
                    
                    date_inputs[1].click()
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    date_inputs[1].fill(m_end)
                    print(f"[爬蟲] 已自動填入開始與結束日期: {m_start} ~ {m_end}")
                    page.wait_for_timeout(300)
                    try:
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(300)
                    except Exception:
                        pass
                else:
                    print("[提示] 未能自動定位日期輸入框，將採用網頁預設值（當月）。")
                    
                # 驗證輸入值是否被平台重置（防範日期超出範圍被平台強制回彈）
                verified = True
                page.wait_for_timeout(300) # 給網頁短暫時間反應
                
                def extract_date_parts(s):
                    import re
                    nums = re.findall(r'\d+', str(s))
                    if len(nums) >= 6:
                        return [
                            (int(nums[0]), int(nums[1]), int(nums[2])),
                            (int(nums[3]), int(nums[4]), int(nums[5]))
                        ]
                    elif len(nums) >= 3:
                        return [(int(nums[0]), int(nums[1]), int(nums[2]))]
                    return []
                
                try:
                    if len(date_inputs) == 1:
                        actual_value = date_inputs[0].input_value() or ""
                        actual_parts = extract_date_parts(actual_value)
                        if len(actual_parts) >= 2:
                            act_start, act_end = actual_parts[0], actual_parts[1]
                            expected_start = (target_year, target_month, target_start_day)
                            expected_end = (target_year, target_month, target_end_day)
                            
                            if act_start != expected_start or act_end != expected_end:
                                verified = False
                        else:
                            verified = False
                    elif len(date_inputs) >= 2:
                        start_parts = extract_date_parts(date_inputs[0].input_value() or "")
                        end_parts = extract_date_parts(date_inputs[1].input_value() or "")
                        if len(start_parts) >= 1 and len(end_parts) >= 1:
                            act_start = start_parts[0]
                            act_end = end_parts[0]
                            expected_start = (target_year, target_month, target_start_day)
                            expected_end = (target_year, target_month, target_end_day)
                            
                            if act_start != expected_start or act_end != expected_end:
                                verified = False
                        else:
                            verified = False
                except Exception as ve:
                    print(f"[除錯] 日期校驗發生異常: {ve}")
                    verified = False
                        
                if not verified:
                    print(f"\n[警告] 偵測到輸入的日期 {m_start} ~ {m_end} 與網頁實際日期不符！")
                    
                    import sys
                    is_interactive = sys.stdin.isatty()
                    print("\n" + "="*70)
                    print(" [系統暫停] 日期校驗未通過。請在瀏覽器中檢查日期輸入是否正確。")
                    print("             這可能是因為到達了平台的最早限制，或是日曆點選未成功。")
                    print("="*70 + "\n")
                    if is_interactive:
                        input(">>> 請檢查瀏覽器。確認後請回到此處按下 [Enter] 鍵，系統將會終止歷史抓取流程並開始清洗已下載的發票...")
                    else:
                        print("[提示] 非互動式終端機，自動等待 10 秒供您查看瀏覽器，之後將終止歷史抓取並進行資料清洗...")
                        page.wait_for_timeout(10000)
                        
                    break
                    
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
                    try:
                        query_btn.click(timeout=3000)
                    except Exception:
                        try:
                            query_btn.click(force=True, timeout=2000)
                        except Exception:
                            query_btn.evaluate("el => el.click()")
                    print("[爬蟲] 已點擊『查詢』按鈕，正在等待發票列表載入...")
                    query_success = True
                else:
                    print("[提示] 未能自動定位『查詢』按鈕，請手動在瀏覽器中點擊。")
                    page.wait_for_timeout(3000)
            except Exception as e:
                print(f"[提示] 設定此月份查詢條件略過，請手動設定日期並點擊『查詢』: {e}")
                
            # 等待列表與勾選框載入
            print("[爬蟲] 正在等待查詢結果載入...")
            try:
                page.wait_for_selector("input[type='checkbox']", timeout=8000)
                page.wait_for_timeout(1000)
                
                # 新增：設定顯示筆數為 100 筆並點選『執行』按鈕，確保能一鍵帶走單月所有發票（預防僅載入預設的 10 筆）
                print("[爬蟲] 正在自動調整每頁顯示筆數至 100 筆並點選『執行』...")
                try:
                    js_pagination = """
                    () => {
                        const sel = document.querySelector("select#SelectSizes");
                        if (!sel) return "NO_SELECT";
                        if (sel.value === "100") return "ALREADY_100";
                        
                        sel.value = "100";
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        const btn = document.querySelector("select#SelectSizes + button");
                        if (btn) {
                            btn.click();
                            return "OK";
                        }
                        return "NO_BUTTON";
                    }
                    """
                    res_pag = page.evaluate(js_pagination)
                    print(f"[爬蟲] 顯示筆數調整狀態: {res_pag}")
                    if res_pag == "OK":
                        print("[爬蟲] 已成功提交 100 筆顯示變更，正在等待發票列表重載...")
                        page.wait_for_timeout(3000)
                        page.wait_for_selector("input[type='checkbox']", timeout=15000)
                        page.wait_for_timeout(800)
                    elif res_pag == "ALREADY_100":
                        print("[爬蟲] 已經是 100 筆，無須變更。")
                    else:
                        print(f"[提示] 未能成功調整顯示筆數：{res_pag}")
                except Exception as se:
                    print(f"[提示] 自動調整顯示筆數略過 (將採用網頁預設顯示): {se}")
            except Exception as e:
                print(f"[提示] 此月份無勾選框，可能該區間內無發票資料。")
    
            # 自動勾選發票
            checkboxes = page.locator("input[type='checkbox']")
            box_count = checkboxes.count()
            print(f"[爬蟲] 偵測到 {box_count} 個勾選方塊。")
            
            if box_count == 0:
                print(f"[提示] 此月份查無發票數據，略過下載並切換至下一個月份。")
                continue
                
            try:
                # 優先點擊全選
                first_box = checkboxes.first
                if not first_box.is_checked():
                    try:
                        first_box.evaluate("el => el.click()")
                        print("[爬蟲] 已自動點擊『全選』勾選框 (JS)。")
                    except Exception as je:
                        try:
                            first_box.check(force=True, timeout=3000)
                        except Exception:
                            pass
                    page.wait_for_timeout(800)
                
                # 二次保險全部強制勾選
                for i in range(box_count):
                    box = checkboxes.nth(i)
                    if not box.is_checked():
                        try:
                            box.evaluate("el => el.click()")
                        except Exception:
                            try:
                                box.check(force=True, timeout=1000)
                            except Exception:
                                pass
            except Exception as e:
                print(f"[提示] 自動勾選發票略過，請手動點選「全選」: {e}")
    
            # 下載 CSV 檔案
            print("[爬蟲] 正在尋找 CSV 下載按鈕...")
            download_success = False
            target_filename = f"invoices_{m_start.replace('/', '')}_{m_end.replace('/', '')}.csv"
            target_path = get_user_data_path("invoices", target_filename)
            
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
                    btn_enabled = False
                    for _ in range(15):
                        if not download_btn.is_disabled():
                            btn_enabled = True
                            break
                        page.wait_for_timeout(1000)
                    
                    if btn_enabled:
                        print("[爬蟲] 下載按鈕已啟用，啟動自動下載攔召器...")
                        with page.expect_download(timeout=25000) as download_info:
                            try:
                                download_btn.click(force=True, timeout=5000)
                            except Exception as e:
                                download_btn.evaluate("el => el.click()")
                        download = download_info.value
                        download.save_as(target_path)
                        print(f"[成功] CSV 檔案已自動儲存至: {target_path}")
                        download_success = True
                        any_download_success = True
                        
                        # 下載成功後，給予平台充足的非同步處理與重載反應時間，並等待其穩定！
                        page.wait_for_timeout(3500)
                        try:
                            # 如果下載動作觸發了背景的 Loading/重載，等待其完全結束並重新就緒！
                            page.wait_for_selector("button:has-text('查詢')", state="visible", timeout=6000)
                            page.wait_for_timeout(1000)
                        except Exception:
                            pass
                    else:
                        print("[提示] 下載按鈕仍為禁用狀態。")
                else:
                    print("[提示] 找不到自動下載按鈕。")
            except Exception as e:
                print(f"[提示] 自動下載失敗: {e}")
                
            if not download_success:
                print("\n" + "="*70)
                print(f" -> 批次自動化下載受阻，請在開啟的瀏覽器視窗中對該月份手動操作：")
                print(f"   1. 請手動在此月份選取全選，並點選「下載明細CSV」或「匯出」。")
                print(f"   (系統正在自動監控 `user_data/invoices/` 目錄，一旦偵測到下載將自動改名為: {target_filename})")
                print("="*70 + "\n")
                
                import sys
                is_interactive = sys.stdin.isatty()
                manual_downloaded = False
                
                print(f"[提示] 機器人正在監控 `user_data/invoices/invoices.csv` 或 {target_filename} 檔案生成...")
                for _ in range(90):
                    default_download_path = get_user_data_path("invoices", "invoices.csv")
                    if os.path.exists(default_download_path) and os.path.getsize(default_download_path) > 100:
                        time.sleep(1)
                        os.rename(default_download_path, target_path)
                        print(f"[成功] 偵測到手動下載 CSV，已自動重新命名為: {target_path}")
                        manual_downloaded = True
                        download_success = True
                        any_download_success = True
                        break
                    elif os.path.exists(target_path) and os.path.getsize(target_path) > 100:
                        manual_downloaded = True
                        download_success = True
                        any_download_success = True
                        break
                    time.sleep(2)
                    
                if not manual_downloaded and is_interactive:
                    input(f">>> 監控超時。當您手動下載好 CSV 並改名為 {target_filename} 後，請回到此處按下 [Enter] 鍵繼續...")
                    if os.path.exists(target_path):
                        download_success = True
                        any_download_success = True
                        
        print("\n[爬蟲] 流程完成！正在關閉瀏覽器...")
        context.close()
        browser.close()
        
    print("[爬蟲] 瀏覽器已安全關閉。")
    print("[爬蟲] 正在啟動 Pandas 資料洗滌模組進行處理與更新...")
    update_crawler_status("running", "下載完成！正在啟動 Pandas 數據分析與分類引擎...", "cleaning")
    
    # 呼叫資料清洗模組
    import data_cleaner
    success = data_cleaner.clean_and_process_invoices(start_date=start_date_str, end_date=end_date_str)
    if success:
        print("\n" + "="*70)
        print(" *** 恭喜！發票資料清洗成功，財務分析儀表板已更新！ ***")
        print("    現在您可以開啟 React 網頁 (npm run dev) 檢視您最新的發票財務看板。")
        print("="*70 + "\n")
        update_crawler_status("success", "發票同步與洗滌完成！網頁即將重新整理...", "done")
    else:
        print("\n[警告] 資料清洗未能順利完成，請檢查 `user_data/invoices/` 目錄下是否確實放有發票 CSV 檔案。")
        update_crawler_status("error", "發票清洗失敗，請確認是否成功下載 CSV 發票明細檔。", "error", "清洗失敗")

if __name__ == "__main__":
    run_browser_automation()
