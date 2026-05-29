import os
import json
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def run_test():
    print("\n" + "="*70)
    print(" === 財政部大平台分頁調整測試腳本 (單月測試) ===")
    print("="*70)
    
    config = load_config()
    phone_no = config.get("phoneNo", "")
    verification_code = config.get("verificationCode", "")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        # 註冊主控台日誌接聽器，以便調試 JS 輸出
        page.on("console", lambda msg: print(f"[瀏覽器主控台] {msg.text.encode('ascii', 'backslashreplace').decode()}"))
        
        print("[測試] 載入登入頁面...")
        page.goto("https://www.einvoice.nat.gov.tw/accounts/login/mw")
        page.wait_for_timeout(2000)
        
        # 自動填入 credentials
        try:
            phone_selectors = ["input[name*='phone']", "input[name*='mobile']", "input[placeholder*='手機']"]
            for sel in phone_selectors:
                if page.locator(sel).is_visible():
                    page.locator(sel).fill(phone_no)
                    break
            
            pwd_selectors = ["input[type='password']", "input[placeholder*='密碼']", "input[placeholder*='驗證碼']"]
            for sel in pwd_selectors:
                if page.locator(sel).is_visible():
                    page.locator(sel).fill(verification_code)
                    break
                    
            captcha_selectors = ["input[placeholder*='圖形']", "input[name*='captcha']"]
            for sel in captcha_selectors:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.focus()
                    loc.first.click()
                    print("[測試] 已自動填寫完畢，並聚焦於驗證碼輸入框！")
                    break
        except Exception as ex:
            print(f"[提示] 欄位預填略過: {ex}")
            
        print("\n>>> 請在開啟的瀏覽器中輸入驗證碼並登入。登入成功後，腳本將自動接管測試...")
        
        logged_in = False
        for _ in range(120):
            if page.is_closed():
                break
            if "login" not in page.url and "accounts/login" not in page.url:
                logged_in = True
                break
            page.wait_for_timeout(1000)
            
        if not logged_in:
            print("[測試] 未檢測到登入，測試終止。")
            return
            
        print("[測試] 檢測到登入成功！正在接管並跳轉至查詢頁面...")
        page.wait_for_timeout(3000)
        page.goto("https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        # 測試起迄時間：設定為當月（有較多發票明細以顯示分頁欄）
        today = datetime.now()
        m_start = datetime(today.year, today.month, 1).strftime("%Y/%m/%d")
        m_end = today.strftime("%Y/%m/%d")
        
        print(f"[測試] 測試設定日期區間: {m_start} ~ {m_end}")
        
        # 移除 readonly 屬性並點選日曆
        page.evaluate("() => { document.querySelectorAll('input').forEach(el => el.removeAttribute('readonly')); }")
        page.wait_for_timeout(300)
        
        target_year = today.year
        target_month = today.month
        target_start_day = 1
        target_end_day = today.day
        
        js_script = r"""
        async (args) => {
            const { startYear, startMonth, startDay, endDay } = args;
            
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
            
            if (!dateInput) throw new Error("找不到日期輸入框");
            triggerClick(dateInput);
            
            let container = null;
            for (let i = 0; i < 20; i++) {
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
                if (container) break;
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            if (!container) throw new Error("找不到彈出的日曆視窗");
            
            console.log("正在打開年份選擇器...");
            const yearBtn = Array.from(container.querySelectorAll('button')).find(btn => 
                (btn.getAttribute('aria-label') || "").includes("年份") || 
                (btn.getAttribute('data-test') || "").includes("year") ||
                /^\d{4}年?$/.test(btn.innerText.trim())
            );
            
            if (!yearBtn) throw new Error("找不到年份選擇按鈕");
            triggerClick(yearBtn);
            await new Promise(resolve => setTimeout(resolve, 300));
            
            const targetYearText = `${startYear}年`;
            const targetYearBtn = Array.from(container.querySelectorAll('*')).find(el => {
                const text = (el.innerText || "").trim();
                return (text === targetYearText || text === startYear.toString()) && el.children.length === 0;
            });
            
            if (!targetYearBtn) throw new Error("找不到目標年份單元格: " + startYear);
            console.log("已選擇目標年份: " + startYear);
            triggerClick(targetYearBtn);
            await new Promise(resolve => setTimeout(resolve, 300));
            
            let monthBtn = Array.from(container.querySelectorAll('button')).find(btn => 
                (btn.getAttribute('aria-label') || "").includes("月份") || 
                (btn.getAttribute('data-test') || "").includes("month") ||
                /^\d{1,2}月$/.test(btn.innerText.trim())
            );
            
            if (monthBtn) {
                console.log("主動開啟月份選擇器...");
                triggerClick(monthBtn);
                await new Promise(resolve => setTimeout(resolve, 300));
            }
            
            const targetMonthText = `${startMonth}月`;
            const targetMonthBtn = Array.from(container.querySelectorAll('*')).find(el => {
                const text = (el.innerText || "").trim();
                return (text === targetMonthText || text === startMonth.toString()) && el.children.length === 0;
            });
            
            if (!targetMonthBtn) throw new Error("找不到目標月份單元格: " + startMonth);
            console.log("已選擇目標月份: " + startMonth);
            triggerClick(targetMonthBtn);
            await new Promise(resolve => setTimeout(resolve, 500));
            
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
            await new Promise(resolve => setTimeout(resolve, 250));
            triggerClick(endEl);
            await new Promise(resolve => setTimeout(resolve, 500));
            
            return { success: true, finalValue: dateInput.value };
        }
        """
        
        page.evaluate(js_script, {
            "startYear": target_year,
            "startMonth": target_month,
            "startDay": target_start_day,
            "endDay": target_end_day
        })
        print("[測試] 日曆設定完畢！")
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        
        # 點選查詢
        page.locator("button:has-text('查詢')").click()
        print("[測試] 已點擊查詢，正在等待勾選框載入...")
        
        page.wait_for_selector("input[type='checkbox']", timeout=10000)
        page.wait_for_timeout(1000)
        
        # 執行我們的顯示筆數切換 JS
        print("\n[測試] >>> 開始執行 100 筆顯示與『執行』自動點選測試...")
        size_js = """
        async () => {
            const triggerClick = (el) => {
                if (!el) return;
                if (typeof el.click === 'function') {
                    el.click();
                }
                const events = ['mousedown', 'mouseup', 'click'];
                events.forEach(evtName => {
                    el.dispatchEvent(new MouseEvent(evtName, {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    }));
                });
            };

            const pagination = document.querySelector('.pagination_box');
            if (!pagination) return "找不到分頁控制列 (.pagination_box)";
            
            const buttons = Array.from(pagination.querySelectorAll('button'));
            let sizeBtn = null;
            let executeBtn = null;
            
            // 尋找顯示當前顯示筆數的按鈕 (可能顯示為 10, 20, 50)
            for (let i = 0; i < buttons.length; i++) {
                const btn = buttons[i];
                const text = (btn.innerText || "").trim();
                if (text === "10" || text === "20" || text === "50" || text === "100") {
                    sizeBtn = btn;
                    executeBtn = buttons[i + 1] || null;
                    break;
                }
            }
            
            if (!sizeBtn) {
                // 使用精準 Selector 當作備用
                sizeBtn = document.querySelector('#app > div > div.font_size_medium.body.have_mobile_menu > div.main_ctn > div.subject_box.barcode_box > div > div > div.right > div > div > div.pagination_box.mt-4 > ul > ul > li:nth-child(9) > div > button');
            }
            
            if (!sizeBtn) return "找不到顯示筆數的下拉選單觸發按鈕";
            console.log("當前筆數按鈕文字: " + sizeBtn.innerText);
            
            if ((sizeBtn.innerText || "").trim() === "100") {
                return "已經顯示 100 筆，無需變更";
            }
            
            console.log("點擊筆數按鈕展開選單...");
            triggerClick(sizeBtn);
            await new Promise(r => setTimeout(r, 600)); // 給予充足時間讓下拉選單插入 DOM
            
            // 尋找浮動面板中innerText為 "100" 的最深層選項節點
            const allElements = Array.from(document.querySelectorAll('*'));
            const option100 = allElements.find(el => 
                (el.innerText || "").trim() === "100" && el !== sizeBtn && el.children.length === 0
            );
            
            if (option100) {
                console.log("找到選項 100，正在點選它...");
                triggerClick(option100);
            } else {
                console.log("未能在全局最深節點中找到 100，嘗試遍歷常見選單項...");
                const items = Array.from(document.querySelectorAll('.dropdown-item, .el-select-dropdown__item, li, a'));
                const backupOpt = items.find(el => (el.innerText || "").trim() === "100");
                if (backupOpt) {
                    triggerClick(backupOpt);
                    console.log("已點選備用 100 選項");
                } else {
                    return "找不到 100 筆選項";
                }
            }
            
            await new Promise(r => setTimeout(r, 500));
            
            if (!executeBtn) {
                const siblingButtons = Array.from(document.querySelectorAll('.pagination_box button'));
                const idx = siblingButtons.indexOf(sizeBtn);
                if (idx !== -1 && idx + 1 < siblingButtons.length) {
                    executeBtn = siblingButtons[idx + 1];
                }
            }
            
            if (executeBtn) {
                console.log("找到執行按鈕，正在點選...");
                triggerClick(executeBtn);
                return "OK";
            }
            return "已選 100 筆但無執行按鈕";
        }
        """
        
        size_res = page.evaluate(size_js)
        print(f"\n[測試結果] 顯示筆數切換結果: {size_res}")
        
        if "OK" in str(size_res):
            print("[測試] 已提交執行，等待列表重載 3 秒以供視覺確認...")
            page.wait_for_timeout(3000)
            
            checkboxes = page.locator("input[type='checkbox']")
            print(f"[測試結果] 重載後當前頁面勾選框數量: {checkboxes.count()}")
            
        print("\n[測試] 測試完畢！保留瀏覽器視窗 10 秒供您查看...")
        page.wait_for_timeout(10000)
        browser.close()

if __name__ == "__main__":
    run_test()
