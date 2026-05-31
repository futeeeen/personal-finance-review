# 錢去哪了：雲端發票半自動爬蟲與 Pandas + ML 智慧財務分析儀表板

一個基於 **Python 半自動網頁爬蟲 (Playwright)**、**Pandas & NLP 機器學習智慧清洗引擎** 與 **React (Vite + Recharts) 離線優先多主題視覺化儀表板** 的極致個人財務管理系統。

本專案旨在解決個人消費者無法申請財政部 API 金鑰的痛點，透過瀏覽器自動化技術，讓您在 30 秒內半自動安全登入財政部電子發票大平台，下載發票 CSV 清單，並利用 Pandas 搭配 Machine Learning 進行中文字元解碼、自動品項分類、作廢/退貨異常處理，最後呈現在極具未來質感的磨砂玻璃財務儀表板上。

---

## 🚀 核心功能特色

### 1. 🤖 三階段智慧自動分類洗滌引擎 (`data_cleaner.py` & `ml_classifier/`)
* **第一階段：高頻字詞正則匹配**
  自動識別超商、量販、餐飲、交通等高頻消費關鍵字，快速對齊「飲食、交通、娛樂、3C配件、服飾、醫療」六大類別。
* **第二階段：商家特徵模糊判定**
  根據發票中的商家名稱（如含有「餐飲」、「咖啡厅」等字詞）進行保底識別，確保即使品項模糊也能自動精準定位。
* **第三階段：NLP + Scikit-Learn 機器學習預測 (全新升級！)**
  當常規詞庫與商家匹配失效時，系統會自動加載經過分詞訓練的機器學習管道（TF-IDF 特徵提取 + 邏輯回歸多分類模型）。利用 `jieba` 對商品及店家進行深度分詞，在 `classifier_pipeline.pkl` 中計算多類別置信度，高於門檻即自動完成智慧歸類，徹底告別「其它」黑洞！

### 2. 🔮 4款科幻質感磨砂玻璃多主題切換 (全新升級！)
提供頂部一鍵切換功能，支持四種精緻調製的現代科幻視覺風格，完美適配並持久保存於 `localStorage`：
* **🔮 深藍磨砂 (Dark Indigo Glass)**：經典科幻，極具穿透感的玻璃擬態。
* **⚡ 霓虹賽博 (Neon Cyberpunk)**：亮麗的青粉極光流動，高對比未來感。
* **🌲 極簡森林 (Minimalist Forest)**：白底翠綠調和，清新典雅，專為護眼與簡約設計。
* **🌅 暮色極光 (Sunset Aurora)**：浪漫暖紅與亮橘交融的彩霞極光，溫柔且和諧。

### 3. 📅 極致點擊式無土味自定義日曆面板 (全新升級！)
* **100% 點擊式操作**：徹底移除原生網頁土味 Date Inputs 框，全程僅需滑鼠點選即可輕鬆設定日期，阻斷鍵盤干擾。
* **磨砂主題適配**：日曆彈窗色彩與毛玻璃效果會根據當前啟動的主題動態變換，並擁有絲滑的滑鼠懸停反饋。
* **健全邊界防禦**：自動鎖定超出本地發票庫起訖時間以外的日期，且具備日期互斥自動調和邏輯（結束日期小於開始日期時自動更新），保證系統數據流完美無瑕。

### 4. 📈 月/週雙模切換折線圖與 ISO-8601 週次計算 (修復完成！)
* **ISO 8601 計算引擎**：內置純 JavaScript 精確週次計算器，一鍵將發票日期在 React 端快速映射為 ISO 週數。
* **「第 undefined 週」完美修復**：徹底解決 Recharts 因數據缺失導致的 undefined X 軸標籤 Bug，平滑展示最近 12 週的消費趨勢和走勢波動。

### 5. 🏪 Top 10 店家自動分行折疊與細節鑽取彈窗 (修復完成！)
* **店家名完整還原**：修復了 Top 10 進度條中店家名稱顯示為空白的瑕疵。
* **多行折返與防截斷**：支持超長商家名稱自動折返（最高 2 行 8 字），在緊湊版面中依舊排版優雅。
* **一鍵鑽取發票明細**：點擊店家名稱即可快速彈出該商家專屬發票清單。白底色調和，排版清晰，卡片卡秒級響應，並可平滑展開折疊單品明細與自動分類標籤。

### 6. ✨ UI 互動細節全面拋光
* **按鈕像素級對齊**：篩選日期按鈕與「重置」按鈕高度統一為 `32px`，搭配 `box-sizing: border-box`，無任何像素落差。
* **滑鼠悬浮 Indigo 呼吸光效**：為篩選和重置按鈕配置高級懸停發光邊框 (`box-shadow: 0 0 10px rgba(99, 102, 241, 0.25)`)，滑鼠移入反饋極佳。

---

## 🛠️ 環境準備與設定

本系統需要 **Python 3.8+** 與 **Node.js 16+** 環境。

### 步驟 1：安裝 Python 依賴與機器學習庫
請在終端機（Powershell 或 CMD）中執行以下命令：
```bash
# 安裝 Pandas、網路請求與 Playwright 爬蟲庫
pip install pandas requests playwright

# 安裝中文分詞 jieba 與機器學習 scikit-learn 庫 (ML 預測器所必需！)
pip install jieba scikit-learn

# 安裝 Playwright 瀏覽器核心 (Chromium)
playwright install chromium
```

### 步驟 2：安裝前端 Node 依賴
在專案根目錄下執行：
```bash
npm install
```

### 步驟 3：設定本地憑證檔案 `config.json`
專案根目錄中包含 `config.json` 用於爬蟲登入自動填寫。請使用文字編輯器打開它並修改對應欄位：
```json
{
  "phoneNo": "0912345678",              // 您的手機條碼登入手機號碼 (10碼)
  "verificationCode": "密碼或驗證碼",   // 您的載具密碼 (首字通常為 /)
  "useMock": false                       // 真實登入下載請務必設為 false！
}
```
> [!IMPORTANT]
> **隱私防護保障：**
> `config.json` 已寫入 `.gitignore`，您的手機與載具密碼絕對不會被 Git 追蹤或上傳到 GitHub 公開倉庫，請放心填寫！

---

## 📖 操作與使用指南

系統使用分為兩大步驟：**「爬蟲撈取與 Pandas 清洗」** ➡️ **「啟動前端儀表板」**。

### 1. 撈取與洗滌發票數據
在專案根目錄下執行：
```bash
python browser_crawler.py
```
**🖥️ 爬蟲執行流程：**
1. 腳本會為您自動開啟 Chromium 瀏覽器，引導至財政部消費者登入頁。
2. 網頁會自動填入您在 `config.json` 設定的「手機號碼」與「驗證碼密碼」。
3. 請您在打開的網頁上**手動輸入「圖形驗證碼」並點擊登入**。
4. 登入成功後，手動點選左側選單：`載具消費發票查詢`。
5. 選擇想下載的日期範圍（如：`2026/01/01` 至 `2026/05/29`），點擊`查詢`。
6. 點擊右上方的`下載明細 CSV`（或匯出 CSV），檔案會自動下載到您電腦的預設下載夾。
7. **請將該 CSV 檔案直接複製或移動到專案根目錄的 `data/` 資料夾下。**
8. 回到終端機按下 **[Enter]**，腳本隨即會關閉瀏覽器，呼叫 Pandas & NLP ML 洗滌大腦完成解碼與分類，並一鍵更新本地發票資料庫！

> [!TIP]
> **離線 Mock 測試模式：**
> 如果您想立即預覽儀表板效果，而暫時不下載真實發票，請在 `config.json` 中保持 `"useMock": true`，然後直接在終端機中執行 `python data_cleaner.py`。這會自動生成一整套包含 344 張發票、含退貨、作廢與多項商品的模擬測試財務庫。

---

### 2. 開啟視覺化財務儀表板
資料庫更新完成後，請在終端機中執行：
```bash
npm run dev
```
啟動後，按住 Ctrl 鍵點擊終端機產出的 `http://localhost:5173` 連結，即可在瀏覽器中開始流暢檢視您的個人「錢去哪了」財務看板！

---

## 📁 專案目錄結構說明

* **[browser_crawler.py](browser_crawler.py)**：Playwright 半自動網頁爬蟲，負責輔助大平台登入及引導 CSV 下載。
* **[data_cleaner.py](data_cleaner.py)**：Pandas 洗滌大腦，優先偵測並清洗 `data/*.csv`，若無則降級呼叫 Client 模擬器。
* **[ml_classifier/](ml_classifier/)**：機器學習智慧分類模組。
  * `classifier.py`：智慧預測 API（採用 `jieba` 分詞與 scikit-learn Pipeline 載入預測）。
  * `classifier_pipeline.pkl`：預先訓練完成的分類 Pipeline。
  * `dataset.py` 與 `train.py`：訓練資料集構造與模型訓練代碼。
* **[mof_api.py](mof_api.py)**：封裝 HMAC-SHA256 簽章的 API 客戶端（含高品質 Mock 發票細部產生器）。
* **[config.json](config.json)**：您的本地手機與密碼配置檔（已由 Git 排除保護，請勿刪除）。
* **[config.example.json](config.example.json)**：公開的配置範本（可安全上傳 Git）。
* **[src/App.jsx](src/App.jsx)**：React 前端核心。使用 `Recharts` 繪製多維互動財務圖表。
* **[src/index.css](src/index.css)**：精心打造的極致磨砂玻璃擬態多主題主題樣式表。
* **[docs/](docs/)**：存放專案相關設計文檔與報告：
  * **[walkthrough.md](docs/walkthrough.md)**：包含完整架構說明與半自動爬蟲細節的成果報告。
  * **[implementation_plan.md](docs/implementation_plan.md)**：專案初始設計實作計劃備份。
