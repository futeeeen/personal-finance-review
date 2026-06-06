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

為了讓專案根目錄保持乾淨，只提供使用者直接需要的執行檔，整個專案區分為以下結構：

### 根目錄直接提供使用者 (開箱即用)
* **[錢去哪了-發票財務儀表板.exe](錢去哪了-發票財務儀表板.exe)**：直接雙擊即可「秒開」啟動本地伺服器，並自動在預設瀏覽器中開啟財務儀表板。不需要安裝任何 Python 或 Node.js 開發環境，也不需要開啟 Conda 命令列。
* **[_internal/](_internal)**：應用程式執行檔所需的依賴函式庫、Python 本地直譯器與已編譯的前端靜態檔案。
* **[user_data/](user_data)**：您的個人資料庫（已在 `.gitignore` 中排除，保護您的私密個資與憑證不外流）：
  * `config.json`：存放手機載具與密碼設定檔。
  * `invoices/`：存放從大平台上下載的原始 CSV 發票資料。
  * `invoice_data.json`：清洗合併後的本地發票資料庫。
* **[README.md](README.md)**：本使用手冊。

### 開發者原始碼目錄 (開發測試)
* **[developer_source/](developer_source)**：所有的程式原始碼與開發設定檔皆收納在此：
  * `src/`：React 前端 UI 元件與主要邏輯。
  * `ml_classifier/`：NLP + 機器學習智慧分類模組（包含模型訓練、數據集與預測器）。
  * `public/`：前端靜態素材（例如 Favicon 圖標）。
  * `app_server.py`：本機 Web API 伺服器代碼。
  * `browser_crawler.py`：Playwright 網頁爬蟲自動化代碼。
  * `data_cleaner.py`：Pandas 資料洗滌代碼。
  * `mof_api.py`：財政部 E-Invoice API 客戶端。
  * `package.json` / `vite.config.js` / `錢去哪了-發票財務儀表板.spec`：前端及 PyInstaller 打包設定檔。

---

## 🛠️ 開發與測試指南 (僅開發者需要)

如果您需要對程式進行二次開發、調整功能或重新打包，請按照以下說明操作：

### 步驟 1：安裝環境與依賴
1. 請確認您已安裝 **Python 3.8+** 與 **Node.js 16+** 環境。
2. 開啟終端機並切換至 `developer_source/` 子目錄下：
   ```bash
   cd developer_source
   ```
3. 安裝 Python 依賴包：
   ```bash
   pip install pandas requests playwright jieba scikit-learn
   # 安裝 Playwright 瀏覽器核心 (Chromium)
   playwright install chromium
   ```
4. 安裝前端 Node.js 依賴包：
   ```bash
   npm install
   ```

### 步驟 2：啟動開發模式
在 `developer_source/` 目錄下執行：
```bash
npm run dev
```
按住 `Ctrl` 鍵點擊終端機顯示的 `http://localhost:5173` 即可開啟網頁。
> [!NOTE]
> 即使在 `developer_source/` 下啟動開發模式，系統也會自動識別並精準讀寫**專案根目錄下的 `user_data/`** 資料夾中的設定檔與發票數據，保持資料的一致性。

### 步驟 3：修改密碼設定
如果需要在本地直接填入帳密以便同步時自動登入，請使用文字編輯器打開根目錄下的 `user_data/config.json` 並修改：
```json
{
  "phoneNo": "0912345678",
  "verificationCode": "/YOUR_PASSWORD"
}
```

---

## 📦 重新打包 EXE (目錄模式)

當您修改了 `developer_source/` 中的代碼後，如果想重新打包為最新的 `.exe`：

1. 在 `developer_source/` 目錄下編譯前端靜態資源：
   ```bash
   npm run build
   ```
2. 安裝 PyInstaller（若尚未安裝）：
   ```bash
   pip install pyinstaller
   ```
3. 執行 PyInstaller 打包指令（規格設定已包含在 `錢去哪了-發票財務儀表板.spec` 中）：
   ```bash
   pyinstaller --clean 錢去哪了-發票財務儀表板.spec
   ```
4. 打包完成後，會生成一個 `dist/錢去哪了-發票財務儀表板/` 目錄。
5. 將該目錄下的 `_internal/` 以及 `錢去哪了-發票財務儀表板.exe` 剪下，並覆蓋回**專案根目錄**下即可完成更新！

