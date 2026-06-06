# 錢去哪了：雲端發票半自動爬蟲與 Pandas + ML 智慧財務分析儀表板

一個基於 **Python 半自動網頁爬蟲 (Playwright)**、**Pandas & NLP 機器學習智慧清洗引擎** 與 **React (Vite + Recharts) 離線優先多主題視覺化儀表板** 的個人財務管理系統。

本專案將**應用程式代碼**與**使用者發票資料**進行了乾淨的分離。所有個人發票數據、爬蟲下載的原始 CSV 檔案以及本機帳號設定檔，均安全地存放在一個獨立的 `user_data/` 目錄中，既方便備份，又不會將隱私資料無意間提交至 GitHub 倉庫。

---

## 🚀 核心功能特色

### 1. 🤖 三階段智慧自動分類洗滌引擎 (`data_cleaner.py` & `ml_classifier/`)
* **第一階段：高頻字詞正則匹配**
  自動識別超商、量販、餐飲、交通等高頻消費關鍵字，快速對齊「飲食、交通、娛樂、3C配件、服飾、醫療」六大類別。
* **第二階段：商家特徵模糊判定**
  根據發票中的商家名稱（如含有「餐飲」字樣）進行保底識別，確保即使品項描述模糊也能自動精準定位。
* **第三階段：NLP + Scikit-Learn 機器學習預測**
  當常規詞庫與商家匹配失效時，系統會自動加載經過分詞訓練的機器學習管道（TF-IDF 特徵提取 + 邏輯回歸多分類模型）。利用 `jieba` 對商品及店家進行深度分詞，在 `classifier_pipeline.pkl` 中計算多類別置信度，高於門檻即自動完成智慧歸類，解決「其它」分類黑洞。

### 2. 🔮 4款科幻質感磨砂玻璃多主題切換
提供頂部一鍵切換功能，支持四種精緻調製的現代科幻視覺風格，並持久保存於瀏覽器 `localStorage` 中：
* **🔮 深藍磨砂 (Dark Indigo Glass)**：經典科幻，極具穿透感的玻璃擬態。
* **⚡ 霓虹賽博 (Neon Cyberpunk)**：亮麗的青粉極光流動，高對比未來感。
* **🌲 極簡森林 (Minimalist Forest)**：白底翠綠調和，清新護眼。
* **🌅 暮色極光 (Sunset Aurora)**：浪漫暖紅與亮橘交融的彩霞極光。

### 3. 📅 極致點擊式無土味自定義日曆面板
* **100% 點擊式操作**：徹底移除原生網頁 Date Inputs 框，全程僅需滑鼠點選即可輕鬆設定日期，阻斷鍵盤輸入打擾。
* **磨砂主題適配**：日曆彈窗色彩與毛玻璃效果會根據當前啟動的主題動態變換。
* **健全邊界防禦**：自動鎖定超出本機發票庫起訖時間以外的日期，且具備日期互斥自動調和邏輯。

### 4. 📈 月/週雙模切換折線圖與 ISO-8601 週次計算
* **ISO 8601 計算引擎**：內置精確週次計算器，一鍵將發票日期在 React 端快速映射為 ISO 週數，解決 Recharts 在「按週呈現」下 X 軸顯示 `undefined` 的問題，平滑展示最近 12 週的消費趨勢。

### 5. 🏪 Top 10 店家自動分行與細節鑽取彈窗
* **多行折返與防截斷**：支持超長商家名稱自動折返（最高 2 行 8 字）。
* **一鍵鑽取發票明細**：點擊店家名稱即可快速彈出該商家專屬發票清單。

---

## 📂 專案目錄結構與資料分離說明

為了確保程式乾淨與使用者資料隱私，專案架構區分為「程式區」與「資料區」：

### 程式區 (可安全提交至 Git 或打包成 EXE)
* **[browser_crawler.py](browser_crawler.py)**：Playwright 半自動網頁爬蟲，負責輔助大平台登入及引導 CSV 下載。
* **[data_cleaner.py](data_cleaner.py)**：Pandas 洗滌大腦，優先偵測並清洗 `user_data/invoices/*.csv`。
* **[ml_classifier/](ml_classifier/)**：NLP + 機器學習智慧分類模組。
* **[app_server.py](app_server.py)**：打包發行專用本地 Web 伺服器。
* **[src/](src/)** / **[index.html](index.html)**：React 前端原始碼與網頁入口。

### 資料區 (儲存於 `user_data/` 目錄，已由 Git 忽略，不可上傳)
* **`user_data/config.json`**：使用者的手機號碼與載具驗證密碼配置檔（系統啟動時若不存在會自動生成範本）。
* **`user_data/invoices/`**：存放從大平台下載的原始發票 CSV 檔案。
* **`user_data/invoice_data.json`**：由 Python 數據清洗引擎產出的最終 JSON 財務數據庫，前端直接讀取此檔呈現。

---

## 🛠️ 環境準備與設定

本系統需要 **Python 3.8+** 與 **Node.js 16+** 環境。

### 步驟 1：安裝 Python 依賴與機器學習庫
請在終端機中執行以下命令：
```bash
# 安裝 Pandas、網路請求與 Playwright 爬蟲庫
pip install pandas requests playwright

# 安裝中文分詞 jieba 與機器學習 scikit-learn 庫
pip install jieba scikit-learn

# 安裝 Playwright 瀏覽器核心 (Chromium)
playwright install chromium
```

### 步驟 2：安裝前端 Node 依賴
在專案根目錄下執行：
```bash
npm install
```

### 步驟 3：設定設定檔 `user_data/config.json`
首次執行爬蟲或伺服器時，系統會自動在專案目錄下建立 `user_data/config.json`。請使用文字編輯器打開它並修改對應欄位：
```json
{
  "phoneNo": "0912345678",              // 您的手機號碼 (10碼)
  "verificationCode": "/YOUR_PASSWORD"  // 您的載具密碼 (首字通常為 /)
}
```

---

## 📖 操作與使用指南

### 本地開發模式
1. 啟動前端開發伺服器：
   ```bash
   npm run dev
   ```
2. 按住 Ctrl 鍵點擊終端機產出的 `http://localhost:5173` 連結。
3. 點選網頁右上角的「同步發票」按鈕，系統會啟動 Playwright 瀏覽器，自動填入帳密，手動輸入「圖形驗證碼」並登入成功後，選擇日期範圍並點選「下載明細 CSV」。
4. 爬蟲將會自動把 CSV 儲存至 `user_data/invoices/`，並自動觸發洗滌模組，更新 `user_data/invoice_data.json`。網頁會自動重新載入呈現您的真實財務看板！

---

## 📦 打包成單一獨立 EXE 檔分享給朋友

如果您想要將這個系統分享給沒有程式開發背景的朋友，可以將其封裝為一個獨立的 `.exe` 檔案：

### 1. 編譯前端靜態檔案
```bash
npm run build
```

### 2. 安裝 PyInstaller
```bash
pip install pyinstaller
```

### 3. 執行打包指令
```bash
pyinstaller --name "錢去哪了-發票財務儀表板" --onefile --add-data "dist;dist" --add-data "ml_classifier;ml_classifier" --collect-data jieba app_server.py
```
打包完成後，您會在專案的 `dist/` 資料夾中取得 **`錢去哪了-發票財務儀表板.exe`**。

### 4. 分享給朋友
將 **`錢去哪了-發票財務儀表板.exe`** 單獨傳送給朋友。
當朋友雙擊執行該 `.exe` 時：
* 系統會在 `.exe` 的同級目錄下自動建立 `user_data/` 資料夾，並生成預設的 `config.json` 設定檔。
* 朋友只需在 `user_data/config.json` 填入自己的手機載具帳密，重新雙擊打開 `.exe`。
* 隨後點擊網頁上的「同步發票」，系統會使用他們本機的 Google Chrome 或 Edge 瀏覽器下載 CSV，將資料存入他們本機的 `user_data/` 下，完全保障資料隱私。
