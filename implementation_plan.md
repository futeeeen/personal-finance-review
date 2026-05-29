# 財政部電子發票 API 介接與 React 視覺化財務儀表板實作計劃

本計劃旨在建立一個完整的電子發票獲取、清洗與視覺化分析系統。系統分為兩個主要部分：
1. **Python 後端/腳本**：負責介接財政部電子發票整合服務平台 API（並提供高品質 mock 資料以進行無縫測試）、利用 `pandas` 進行多維度資料清洗與特徵提取，並匯出乾淨的 JSON 數據。
2. **React 前端網頁應用 (Vite)**：讀取 Python 匯出的數據，打造一個精美、支援響應式、現代玻璃擬態 (Glassmorphic) 風格的財務儀表板，並使用 `Recharts` 進行多維度圖表渲染。

---

## 使用者確認事項 (User Review Required)

> [!IMPORTANT]
> **API 介接憑證與 Mock 模式**
> - **正式介接**：呼叫財政部 API 需要您向平台申請的 `AppID`、`APIKey`（用於簽章）以及手機條碼 `cardNo` 和驗證碼 `cardEncrypt`。
> - **Mock 測試模式（預設啟用）**：為了讓您能**立即看到精美的視覺化效果與資料清洗運作**，我會在 Python 腳本中內建一套高品質的模擬發票數據生成器（包含隨機店家、品項關鍵字如便當、高鐵、作廢發票、退貨負數金額等）。您無須輸入任何金鑰即可一鍵執行並預覽完整功能！

> [!TIP]
> **React 架構與視覺風格**
> - 前端使用 **React (Vite)** 開發，搭配 **Vanilla CSS** 與精心設計 of **CSS 變數**，以實現最流暢的高級暗色模式 (Premium Dark Mode)、微動畫與響應式佈局。
> - 圖表庫選用 **Recharts**，因其對 React 的原生支援極佳，且具備非常流暢的滑鼠懸停動畫與高質感的渲染效果。

---

## 待確認問題 (Open Questions)

> [!NOTE]
> **分類規則擴充**
> - 目前預設的店家與品項關鍵字分類已涵蓋：餐飲（便當、燒肉、茶）、交通（高鐵、台鐵）、娛樂（電影、KTV）、3C配件、服飾、醫療等。若您有其他特定的自定義店家或關鍵字分類需求，可在實作後於 `data_cleaner.py` 內的規則字典中隨時擴充。

---

## 預定變更內容 (Proposed Changes)

---

### 1. Python 資料處理模組

此模組負責發票數據的撈取（API 或 Mock）與 pandas 清洗處理。

#### [NEW] [mof_api.py](file:///c:/futen/Project/Personal%20finances%20review/mof_api.py)
- 建立 `TaiwanEInvoiceClient` 類別，封裝財政部 API 呼叫邏輯。
- 實現 HMAC-SHA256 簽章演算法與 `timeStamp` / `expTimeStamp` 安全欄位計算。
- 內建 `generate_mock_invoices(start_date, end_date)` 方法，模擬產生豐富的發票與明細數據。
- 支援透過 config 設定真實 API 金鑰與載具條碼。

#### [NEW] [data_cleaner.py](file:///c:/futen/Project/Personal%20finances%20review/data_cleaner.py)
- 使用 `pandas` 處理 `mof_api.py` 獲取的原始發票清單與明細。
- **時間格式轉換**：將民國年格式（如 `1130520`）或字串轉換為 pandas Datetime，並提取年份、月份、週別、星期、小時等欄位。
- **異常值處理**：自動剔除已作廢發票，並妥善處理退貨產生的負數金額（累加至總額或標記為退貨交易）。
- **消費分類標籤**：依據店家名稱與品項名稱（如「麥當勞」-> 餐飲，「高鐵」-> 交通，「Steam」-> 娛樂），利用正規表達式與映射字典自動打上分類標籤。
- 匯出經過高度聚合與清洗後的 JSON 格式資料（如 `invoice_dashboard_data.json`），寫入 React App 的 `public/` 目錄下供前端使用。

---

### 2. React 前端可視化儀表板 (Vite)

建立精美的單頁 Web App，呈現多維度的財務圖表與指標。

#### [NEW] React 基礎結構與相依套件
- 使用 `npx -y create-vite@4 ./ --template react` 初始化專案。
- 安裝必要相依套件：`recharts`（圖表）、`lucide-react`（現代扁平化圖示）。

#### [NEW] [index.css](file:///c:/futen/Project/Personal%20finances%20review/src/index.css)
- 定義現代高級感深色主題色彩系統（採用 HSL 變數，如科技藍、極光紫、珊瑚橙與磨砂玻璃灰）。
- 實作流暢的微動畫效果（卡片 Hover 浮起、漸變過渡、脈衝發光）。
- 實作全螢幕與卡片的磨砂玻璃效果（Glassmorphism）。

#### [NEW] [App.jsx](file:///c:/futen/Project/Personal%20finances%20review/src/App.jsx)
- 儀表板核心元件，包含：
  - **核心 KPI 數字卡片**：總消費金額（排除作廢與退貨影響）、總發票張數、平均每張發票消費額、退貨發票張數與金額。
  - **趨勢線圖 (Recharts AreaChart)**：每月或每週的總消費金額與發票張數趨勢線，支援雙 Y 軸與漸變填充。
  - **消費類別圓餅圖 (Recharts PieChart / Donut)**：飲食、交通、娛樂、3C、醫療、服飾等各類別所佔比例與總金額。
  - **最愛店家 Top 10 (Recharts BarChart & List)**：按消費金額或消費次數排列的最佳店家排行。
  - **特定時段消費熱力圖 (Custom Grid CSS Heatmap)**：橫軸為星期一至日，縱軸為時段（早餐、午餐、晚餐、深夜），以漸變色塊深度呈現消費頻率。
  - **明細清單篩選器**：提供使用者即時搜尋、按類別篩選或依金額排序的發票明細明細卡片。

---

## 驗證計劃 (Verification Plan)

### 自動與腳本測試
- 執行 `python data_cleaner.py` 驗證 `pandas` 資料清洗流程，確認產生的 JSON 結構正確、無 NaN 缺失值，且時間、分類等欄位轉換精確無誤。
- 確認產生的 JSON 資料已正確寫入 `src/` 或 `public/` 目錄。

### 手動與介面驗證
- 執行 `npm run dev` 啟動 Vite 本地開發伺服器。
- 透過瀏覽器開啟儀表板，驗證：
  1. 數據載入流暢，KPI 卡片數字正確。
  2. 線圖、圓餅圖、長條圖能互動懸停（顯示 tooltip）。
  3. 時段熱力圖的顏色深淺正確反映了消費集中度。
  4. 發票明細篩選器能正常過濾與排序發票。
  5. 畫面完全響應式，在手機與電腦版皆有出色的視覺表現。
