import os
import json
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
    print(" === 財政部大平台原生 Select 調整測試腳本 (單月測試) ===")
    print("="*70)
    
    config = load_config()
    phone_no = config.get("phoneNo", "")
    verification_code = config.get("verificationCode", "")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        page.on("console", lambda msg: print(f"[瀏覽器主控台] {msg.text.encode('ascii', 'backslashreplace').decode()}"))
        
        print("[測試] 載入登入頁面...")
        page.goto("https://www.einvoice.nat.gov.tw/accounts/login/mw")
        page.wait_for_timeout(2000)
        
        # Auto-fill
        try:
            page.locator("input[name*='phone']").first.fill(phone_no)
            page.locator("input[type='password']").first.fill(verification_code)
            page.locator("input[placeholder*='圖形']").first.focus()
            print("[測試] 已自動預填，請在瀏覽器中輸入驗證碼並手動點選「登入」...")
        except Exception as e:
            print(f"[測試] 預填失敗: {e}")
            
        logged_in = False
        for _ in range(120):
            if page.is_closed():
                break
            if "login" not in page.url and "accounts/login" not in page.url:
                logged_in = True
                break
            page.wait_for_timeout(1000)
            
        if not logged_in:
            print("[測試] 未檢測到登入，終止。")
            return
            
        print("[測試] 登入成功！跳轉至查詢頁面...")
        page.wait_for_timeout(2000)
        page.goto("https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        # 設定日期為 2025/12/01 ~ 2025/12/31
        target_year = 2025
        target_month = 12
        target_start_day = 1
        target_end_day = 31
        
        print(f"[測試] 測試設定日期區間: {target_year}/{target_month}/01 ~ {target_year}/{target_month}/{target_end_day}")
        page.evaluate("() => { document.querySelectorAll('input').forEach(el => el.removeAttribute('readonly')); }")
        page.wait_for_timeout(300)
        
        # 1. 使用高度相容之定位邏輯找到日期輸入框，並原生點擊開啟日曆，保證 100% 成功觸發彈窗！
        try:
            inputs = page.locator("input")
            date_input = None
            for i in range(inputs.count()):
                input_el = inputs.nth(i)
                placeholder = str(input_el.get_attribute("placeholder") or "").lower()
                name = str(input_el.get_attribute("name") or "").lower()
                id_attr = str(input_el.get_attribute("id") or "").lower()
                class_attr = str(input_el.get_attribute("class") or "").lower()
                if any(kw in placeholder or kw in name or kw in id_attr or kw in class_attr 
                       for kw in ['date', 'range', '日期', '起迄', '開始', '結束', '選擇', '起', '迄']):
                    date_input = input_el
                    break
            
            if date_input:
                date_input.click()
                print("[測試] 已原生點選日期輸入框，正在等待日曆選單載入...")
                page.wait_for_selector(".dp__menu, .dp__outer_menu_wrap", timeout=8000)
                print("[測試] 日曆選單已順利顯示！")
            else:
                print("[測試警告] 找不到合適的日期輸入框！")
        except Exception as e:
            print(f"[測試警告] 原生點擊日曆輸入框或等待選單超時: {e}")
            
        # 2. 使用日曆面板點選方案 + 全域 pointer-events 禁用防冒泡穿透黃金雙保險
        js_script = r"""
        async (args) => {
            const { startYear, startMonth, startDay, endDay } = args;
            
            // 全域禁用外部超連結和按鈕的點擊，徹底阻斷穿透與冒泡！
            document.querySelectorAll('a, button, [role="button"], .sidebar, header, nav, .menu').forEach(el => {
                // 如果這個元素是在日曆彈窗外部，我們就禁用它的點擊
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
                
                // 尋找日期輸入框以獲取其 finalValue
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
                
                // 尋找日曆 Menu
                let container = document.querySelector('.dp__menu') || document.querySelector('.dp__outer_menu_wrap');
                if (!container) {
                    // 備用方案尋找
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
                
                // 啟用日曆選單內部所有元素的 pointer-events
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
                // 恢復全域點擊事件，確保即使出錯也能點擊外部元素！
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
            print(f"[測試] 日期面板設定完成，傳回值: {res.get('finalValue')}")
        except Exception as je:
            print(f"[測試] 直接設定日期出錯: {je}")
            
        page.wait_for_timeout(500)
        
        # 點選查詢
        page.locator("button:has-text('查詢')").click()
        print("[測試] 已點擊查詢，正在等待列表與勾選框載入...")
        
        try:
            page.wait_for_selector("input[type='checkbox']", timeout=15000)
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"[測試] 找不到勾選框，可能該月份查無發票: {e}")
            page.wait_for_timeout(5000)
            browser.close()
            return
        
        # 原生 Select 調整顯示筆數為 100
        print("\n[測試] >>> 開始執行原生 select#SelectSizes 與 sibling button 點選測試...")
        
        select_locator = page.locator("select#SelectSizes:visible").first
        execute_btn = page.locator("select#SelectSizes:visible + button").first
        
        if select_locator.count() > 0 and select_locator.is_visible():
            current_val = select_locator.input_value()
            print(f"[測試] 當前顯示筆數值: {current_val}")
            
            if current_val != "100":
                print("[測試] 正在原生選擇 '100' 筆...")
                select_locator.select_option("100")
                page.wait_for_timeout(800)
                
                if execute_btn.count() > 0 and execute_btn.is_visible():
                    print("[測試] 正在點選『執行』按鈕...")
                    execute_btn.click()
                    print("[測試] 已成功提交！正在等待列表重載...")
                    page.wait_for_timeout(3000)
                    page.wait_for_selector("input[type='checkbox']", timeout=15000)
                    page.wait_for_timeout(800)
                else:
                    print("[測試] 找不到對應的『執行』按鈕！")
            else:
                print("[測試] 已經是 100 筆，無須變更。")
        else:
            print("[測試] 找不到分頁筆數 Select 元素！可能總發票數少於 10 筆。")
            
        # 顯示勾選框數量
        checkboxes = page.locator("input[type='checkbox']")
        box_count = checkboxes.count()
        print(f"[測試結果] 列表中的勾選框數量: {box_count}")
        
        if box_count > 0:
            print("[測試] 正在執行自動全選...")
            # 優先點擊第一個全選勾選框 (通常是表頭的全選)
            first_box = checkboxes.first
            try:
                first_box.evaluate("el => el.click()")
                print("[測試] 已點擊『全選』勾選框 (JS)。")
            except Exception as e:
                print(f"[測試] 點擊全選框失敗: {e}")
                
            page.wait_for_timeout(1000)
            
            # 二次保險全部強制勾選
            print("[測試] 正在進行二次保險，將所有未勾選的框強制勾選...")
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
            
            # 再檢查一次未勾選的框數
            unchecked_count = 0
            for i in range(box_count):
                if not checkboxes.nth(i).is_checked():
                    unchecked_count += 1
            print(f"[測試] 二次保險檢查完畢。未勾選的框數: {unchecked_count} / {box_count}")
            
            # 開始測試 CSV 下載
            print("[測試] 正在尋找下載明細CSV按鈕...")
            download_selectors = [
                "text=下載明細CSV", "text=下載明細", "text=下載", "text=匯出",
                "button:has-text('下載')", "button:has-text('匯出')",
                "input[value*='下載']", "input[value*='匯出']"
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
                print("[測試] 下載按鈕已找到，正在等待其啟用 (非 disabled)...")
                btn_enabled = False
                for _ in range(15):
                    if not download_btn.is_disabled():
                        btn_enabled = True
                        break
                    page.wait_for_timeout(1000)
                
                if btn_enabled:
                    print("[測試] 下載按鈕已啟用，點擊下載...")
                    target_path = os.path.join("data", "invoices_20251201_20251231.csv")
                    os.makedirs("data", exist_ok=True)
                    
                    try:
                        with page.expect_download(timeout=20000) as download_info:
                            try:
                                download_btn.click(force=True, timeout=5000)
                            except Exception:
                                download_btn.evaluate("el => el.click()")
                                
                        download = download_info.value
                        download.save_as(target_path)
                        print(f"[測試成功] CSV 檔案已成功下載至: {target_path}")
                        
                        # 讀取 CSV 進行內容實質日期驗證
                        print("\n" + "="*70)
                        print(" [測試驗證] 正在對下載的 CSV 進行真實日期欄位解析驗證...")
                        print("="*70)
                        try:
                            import pandas as pd
                            df = None
                            for enc in ['utf-8-sig', 'cp950', 'big5']:
                                try:
                                    df = pd.read_csv(target_path, encoding=enc)
                                    break
                                except Exception:
                                    continue
                            
                            if df is not None:
                                print(f"[驗證] 成功讀取 CSV 檔案。總筆數: {len(df)}")
                                date_col = None
                                for col in df.columns:
                                    if '日期' in str(col) or '時間' in str(col) or 'Date' in str(col):
                                        date_col = col
                                        break
                                
                                if date_col:
                                    print(f"[驗證] 找到日期欄位: {date_col}")
                                    sample_dates = df[date_col].head(5).tolist()
                                    print(f"[驗證] 前 5 筆發票日期數據: {sample_dates}")
                                    
                                    # 檢查是否含有 2025 年 / 民國 114 年
                                    is_2025 = any('2025' in str(d) or '114' in str(d) for d in sample_dates)
                                    if is_2025:
                                        print("\n🌟🌟🌟 [實證完成] 恭喜！鐵證如山！發票 CSV 內容確實為 2025 年的真實資料！ 🌟🌟🌟\n")
                                    else:
                                        print("\n❌❌❌ [驗證失敗] ⚠️ 警告：發票內容依然是 2026 年（網頁預設值）！Vue State 未能正確更新！ ❌❌❌\n")
                                else:
                                    print("[警告] 找不到日期欄位，無法進行自動日期驗證。")
                            else:
                                print("[警告] 無法讀取 CSV 檔案編碼，驗證失敗。")
                        except Exception as ve:
                            print(f"[警告] CSV 驗證解析失敗: {ve}")
                        print("="*70 + "\n")
                    except Exception as e:
                        print(f"[測試失敗] 下載過程中發生錯誤: {e}")
                else:
                    print("[測試失敗] 下載按鈕在 15 秒內仍未啟用！")
            else:
                print("[測試] 找不到下載按鈕。")
        else:
            print("[測試] 當月無發票，無法測試下載。")
            
        print("\n[測試] 測試完畢！保留瀏覽器視窗 8 秒供您確認...")
        page.wait_for_timeout(8000)
        browser.close()

if __name__ == "__main__":
    run_test()
