# 雲端發票半自動爬蟲與 Pandas 財務分析儀表板

一個基於 **Python 半自動網頁爬蟲 (Playwright)**、**Pandas 大數據清洗引擎** 與 **React (Vite + Recharts) 離線優先視覺化儀表板** 的個人財務管理系統。

本專案旨在解決個人消費者無法申請財政部 API 金鑰的痛點，透過瀏覽器自動化技術，讓您在 30 秒內半自動安全登入財政部電子發票大平台，下載發票 CSV 清單，並利用 Pandas 進行中文字元編碼亂碼解決、自動品項分類、作廢/退貨異常處理，最後呈現在極具科幻質感的磨砂玻璃深色財務儀表板上。

---

## 🚀 核心功能特色

1. **半自動網頁爬蟲 (`browser_crawler.py`)**：
   - 採用 **Playwright (Chromium)** 頭戴模式自動開啟瀏覽器，自動填寫手機號碼與載具驗證碼密碼。
   - 保留「人類手動輸入圖形驗證碼與登入」的彈性，100% 避開大平台複雜的機器人防禦機制，安全下載 CSV 檔案。
2. **Pandas 模糊對齊與解碼引擎 (`data_cleaner.py`)**：
   - **亂碼終結**：自動偵測多種編碼（UTF-8-SIG, BIG5, CP950），完美解決 Windows Excel 開啟大平台 CSV 常見的繁體中文亂碼問題。
   - **模糊對齊**：支援各種發票 APP 或官方下載的 CSV 格式，欄位自動匹配，**不需手動改檔名或調整欄位順序**，直接丟入即可清洗。
   - **異常處理**：自動過濾「已作廢」發票，並正確處理「退貨負數金額」以反映真實淨消費。
   - **消費自動分類**：依據店家及品項關鍵字，用程式邏輯將消費自動歸類（飲食、交通、娛樂、3C配件、服飾、醫療、其它）。
3. **響應式磨砂玻璃深色儀表板 (Vite + React)**：
   - **離線優先**：讀取 Pandas 洗滌後的靜態 JSON，**無網路狀態亦可秒開且流暢查詢**。
   - **多維度圖表**：月/週消費趨勢線圖（AreaChart）、熱門類別佔比圖（DonutChart）、Top 10 最愛店家排行（BarChart）。
   - **特定時段消費熱力圖**：以 7x5 網格呈現星期 vs. 五大黃金時段的交易次數與累計金額，清晰指出您的消费集中度。
   - **折疊式收據明細表**：支援搜尋、類別篩選與排序；點擊發票卡片會平滑下拉展開，顯示該發票內所有單品細節。

---

## 🛠️ 環境準備與設定

本系統需要 **Python 3.8+** 與 **Node.js 16+** 環境。

### 步驟 1：安裝 Python 依賴與瀏覽器核心
請在終端機（Powershell 或 CMD）中執行以下命令：
```bash
# 安裝 Python 庫
pip install pandas requests playwright

# 安裝 Playwright 瀏覽器核心 (Chromium)
playwright install chromium
```

### 步驟 2：安裝前端 Node 依賴
在專案根目錄下執行：
```bash
npm install
```

### 步驟 3：設定本地憑證檔案 `config.json`
專案中已為您自動建立了 `config.json`。為了讓爬蟲啟動時能自動預填您的帳號，請用文字編輯器打開它並修改對應欄位：
```json
{
  "phoneNo": "0912345678",              // 您的手機條碼登入手機號碼 (10碼)
  "verificationCode": "密碼或驗證碼",   // 您的載具密碼 (首字通常為 /)
  "useMock": false                       // 真實登入下載請務必設為 false！
}
```
> [!IMPORTANT]
> **隱私防護保障：**
> `config.json` 已寫入 `.gitignore`，您的手機與密碼絕不會被 Git 追蹤或 Push 到公開 GitHub 倉庫上，請放心填寫。

---

## 📖 操作與使用指南

系統使用分為兩大步驟：**「爬蟲撈取與 Pandas 清洗」** ➡️ **「啟動前端儀表板」**。

### 1. 撈取與洗滌發票數據
在專案根目錄下執行：
```bash
python browser_crawler.py
```
**🖥️ 爬蟲執行流程：**
1. 腳本會為您自動打開 Chromium 瀏覽器，引導至財政部消費者登入頁。
2. 網頁會自動填入您在 `config.json` 設定的「手機號碼」與「密碼」。
3. 請您在打開的網頁上**手動輸入「圖形驗證碼」並點擊登入**。
4. 登入成功後，手動點選左側選單：`載具消費發票查詢`。
5. 選擇想下載的日期範圍（如：`2026/01/01` 至 `2026/05/29`），點擊`查詢`。
6. 點擊右上方的`下載明細 CSV`（或匯出 CSV），檔案會下載到您電腦的預設下載夾。
7. **請將該 CSV 檔案（不需改檔名）直接複製或移動到專案根目錄的 `data/` 資料夾下。**
8. 回到終端機按下 **[Enter]**，腳本隨即會關閉瀏覽器，呼叫 Pandas 完成 Big5 解碼、分類洗滌，並一鍵更新本地儀表板資料庫！

> [!TIP]
> **離線 Mock 測試模式：**
> 如果您想立即預覽儀表板效果，而暫時不下載真實發票，請在 `config.json` 中保持 `"useMock": true`，然後直接在終端機中執行 `python data_cleaner.py`。這會自動生成一整套包含 95 張發票、含退貨、作廢與多項商品的模擬測試財務庫。

---

### 2. 開啟視覺化財務儀表板
資料庫更新完成後，請在終端機中執行：
```bash
npm run dev
```
啟動後，按住 Ctrl 鍵點擊終端機產出的 `http://localhost:5173` 連結，即可在瀏覽器中開始流暢檢視您的個人雲端發票財務看板！

---

## 📁 專案目錄結構說明

- **[browser_crawler.py](browser_crawler.py)**：Playwright 半自動網頁爬蟲，負責輔助大平台登入及引導 CSV 下載。
- **[data_cleaner.py](data_cleaner.py)**：Pandas 洗滌大腦，優先偵測並清洗 `data/*.csv`，若無則降級呼叫 Client 模擬器。
- **[mof_api.py](mof_api.py)**：封裝 HMAC-SHA256 簽章的 API 客戶端（含高品質 Mock 發票細部產生器）。
- **[config.json](config.json)**：您的本地手機與密碼配置檔（已由 Git 排除保護，請勿刪除）。
- **[config.example.json](config.example.json)**：公開的配置範本（可安全上傳 Git）。
- **[src/App.jsx](src/App.jsx)**：React 前端核心。使用 `Recharts` 繪製多維互動財務圖表。
- **[src/index.css](src/index.css)**：精心打造的極致磨砂玻璃擬態深色主題樣式表。
- **[docs/](docs/)**：存放專案相關設計文檔與報告：
  - **[walkthrough.md](docs/walkthrough.md)**：包含完整架構說明與半自動爬蟲細節的成果報告。
  - **[implementation_plan.md](docs/implementation_plan.md)**：專案初始設計實作計劃備份。
