import os
import re
import json
import pandas as pd
import numpy as np
from datetime import datetime
from io import StringIO
from mof_api import TaiwanEInvoiceClient

# 用於快取從 CSV 解析出來的品項明細
_csv_details_cache = {}

def parse_taiwan_date(date_str):
    """
    將民國年或標準西元年月日字串解析成標準 datetime 物件。
    支援格式: 
      - 民國年無分隔符: "1150520" -> 2026/05/20
      - 民國年斜線分隔: "115/05/20" -> 2026/05/20
      - 西元年無分隔符: "20260520" -> 2026/05/20
      - 西元年斜線/橫線分隔: "2026/05/20", "2026-05-20" -> 2026/05/20
    """
    if pd.isna(date_str) or not date_str:
        return pd.NaT
        
    s = str(date_str).strip()
    
    # 移除所有分隔符以進行純數字判定
    nums_only = re.sub(r'[-/]', '', s)
    
    try:
        if len(nums_only) == 7: # 民國年 7 位數: yyyMMdd
            y = int(nums_only[0:3]) + 1911
            m = int(nums_only[3:5])
            d = int(nums_only[5:7])
            return datetime(y, m, d)
        elif len(nums_only) == 8: # 西元年 8 位數: YYYYMMDD
            return datetime.strptime(nums_only, "%Y%m%d")
        else:
            # 其他情況交給 pandas 解析器嘗試
            return pd.to_datetime(s)
    except Exception as e:
        return pd.NaT

def classify_item(item_desc, seller_name):
    """
    利用品項描述與商家名稱，自動進行消費分類標籤標記。
    """
    desc = str(item_desc).lower()
    seller = str(seller_name).lower()
    
    # 1. 飲食分類
    food_kws = ['便當', '燒肉', '茶', '綠茶', '紅茶', '奶茶', '咖啡', '拿鐵', '飯', '麵', '壽司', 
                '套餐', '鷄塊', '薯條', '蛋糕', '巧克力', '蘋果', '鮮乳', '水', '洋芋片', '吐司', 
                '蛋', '御飯糰', '冰', '飲料', '餐', '牛排', '火鍋', '壽喜燒', '舒芙蕾', '食']
    food_sellers = ['星巴克', '麥當勞', '爭鮮', '超商', '便利商店', '全家', '統一超商', '萊爾富', 'ok超商', '美廉社']
    if any(kw in desc for kw in food_kws) or any(kw in seller for kw in food_sellers):
        return '飲食'
        
    # 2. 交通分類
    trans_kws = ['高鐵', '台鐵', '火車', '乘車票', '悠遊卡', '捷運', '計程車', '加油', '中油', '台亞', '車票', '客運', 'uber', '車']
    trans_sellers = ['高速鐵路', '台鐵', '捷運', '客運', '加油站', '中油', '台灣鐵路']
    if any(kw in desc for kw in trans_kws) or any(kw in seller for kw in trans_sellers):
        return '交通'
        
    # 3. 娛樂分類
    ent_kws = ['電影', '威秀', '影城', 'steam', '遊戲', '娛樂', 'cyberpunk', 'hades', 'netflix', 'spotify', 'ktv', '歌唱', '演唱會']
    ent_sellers = ['威秀', '影城', 'steam', '國賓', '秀泰', '錢櫃', '好樂迪', 'spotify', 'netflix']
    if any(kw in desc for kw in ent_kws) or any(kw in seller for kw in ent_sellers):
        return '娛樂'
        
    # 4. 3C配件分類
    electronics_kws = ['iphone', '快充線', '滑鼠', '鍵盤', 'type-c', 'hub', '轉接器', '行動電源', '手機', '電腦', '線材', '耳機', '螢幕', '隨身碟']
    electronics_sellers = ['燦坤', '順發', 'apple', '小米', '光華商場', '三創']
    if any(kw in desc for kw in electronics_kws) or any(kw in seller for kw in electronics_sellers):
        return '3C配件'
        
    # 5. 服飾分類
    cloth_kws = ['短t', '運動鞋', '皮夾', '衣服', '外套', '褲子', '鞋子', '洋裝', '襯衫', '包包', '皮帶']
    cloth_sellers = ['新光三越', 'uniqlo', 'zara', '無印良品', 'sogo', '微風', '遠東百貨']
    if any(kw in desc for kw in cloth_kws) or any(kw in seller for kw in cloth_sellers):
        return '服飾'
        
    # 6. 醫療分類
    med_kws = ['口罩', '維他命', '防曬乳', '洗面乳', '藥', '感冒', '診所', '藥水', '保健食品']
    med_sellers = ['藥局', '診所', '醫院', '康是美', '屈臣氏', '大樹藥局']
    if any(kw in desc for kw in med_kws) or any(kw in seller for kw in med_sellers):
        return '醫療'
        
    return '其它'

def parse_time_period(hour_str):
    """將發票的小時時間區分為：早餐、午餐、下午茶、晚餐、深夜"""
    try:
        hour = int(hour_str.split(':')[0])
    except Exception:
        return '其它'
        
    if 6 <= hour < 11:
        return '早餐 (06-11)'
    elif 11 <= hour < 14:
        return '午餐 (11-14)'
    elif 14 <= hour < 17:
        return '下午茶 (14-17)'
    elif 17 <= hour < 21:
        return '晚餐 (17-21)'
    else:
        return '深夜 (21-06)'

def parse_downloaded_csv(csv_file):
    """
    強大的模糊欄位 CSV 讀取器，解決 Excel CP950/BIG5 亂碼並自動對齊欄位結構
    """
    global _csv_details_cache
    _csv_details_cache = {}
    
    encodings = ['utf-8-sig', 'utf-8', 'big5', 'cp950', 'gbk']
    content_lines = []
    
    # 尋找支援的編碼
    for enc in encodings:
        try:
            with open(csv_file, 'r', encoding=enc) as f:
                content_lines = f.readlines()
            print(f"[Cleaner] [OK] 成功以 {enc} 編碼讀取 CSV 檔案。")
            break
        except Exception:
            continue
            
    if not content_lines:
        print("[Cleaner] [ERROR] 錯誤：無法以任何常見編碼讀取該 CSV 檔案。")
        return []
        
    # 尋找含有表格欄位標頭的核心列 (排除財政部下載 CSV 頂部的載具卡號與統計資訊)
    header_index = -1
    for idx, line in enumerate(content_lines):
        if any(kw in line for kw in ['發票號碼', '發票日期', '金額', '賣方名稱', '商家名稱', '品項名稱']):
            header_index = idx
            break
            
    if header_index == -1:
        header_index = 0
        
    # 重新處理 CSV 的每一行，修復異常欄位（如未經引號包裹卻包含逗號的地址欄位）並濾除雜訊
    import csv
    import io
    
    cleaned_rows = []
    header_line = content_lines[header_index].strip()
    
    try:
        header_parts = next(csv.reader([header_line]))
    except Exception:
        header_parts = [p.strip() for p in header_line.split(',')]
        
    expected_cols = 14
    if len(header_parts) != 14:
        expected_cols = len(header_parts)
        
    output_stream = io.StringIO()
    csv_writer = csv.writer(output_stream, lineterminator='\n')
    csv_writer.writerow(header_parts)
    
    for idx, line in enumerate(content_lines[header_index + 1:]):
        l_str = line.strip()
        if not l_str:
            continue
            
        # 排除說明與頁尾性質的尾部註解
        if any(kw in l_str for kw in ['捐贈或作廢之發票', '注意：本功能所下載', '字軌號碼均會隱末']):
            continue
            
        try:
            row_reader = csv.reader([l_str])
            parts = next(row_reader)
        except Exception:
            parts = [p.strip() for p in l_str.split(',')]
            
        if len(parts) == expected_cols:
            csv_writer.writerow(parts)
        elif len(parts) > expected_cols and expected_cols == 14:
            # 解決台灣發票地址中含有未經雙引號包裹的逗號導致的分欄錯誤 (例如 賣方地址 在索引 8)
            first_8 = parts[0:8]
            last_5 = parts[-5:]
            middle_address = ",".join(parts[8 : -5])
            csv_writer.writerow(first_8 + [middle_address] + last_5)
        else:
            # 進行補齊或截斷處理
            if len(parts) < expected_cols:
                parts += [""] * (expected_cols - len(parts))
            elif len(parts) > expected_cols:
                parts = parts[:expected_cols]
            csv_writer.writerow(parts)
            
    csv_data = output_stream.getvalue()
    
    try:
        df_csv = pd.read_csv(StringIO(csv_data))
        print(f"[Cleaner] Pandas 成功解析 CSV，共 {len(df_csv)} 筆原始行。")
    except Exception as e:
        print(f"[Cleaner] [ERROR] 錯誤：Pandas 解析 CSV 失敗: {e}")
        return []
        
    # 欄位模糊匹配對應字典 (相容各種平台、APP 與官方格式)
    column_mapping = {
        # 1. 官方明細 CSV 標準欄位
        '發票日期': 'invDate',
        '發票號碼': 'invNum',
        '發票金額': 'amount',
        '發票狀態': 'invStatus',
        '賣方統一編號': 'sellerBan',
        '賣方名稱': 'sellerName',
        '賣方地址': 'sellerAddress',
        '買方統編': 'buyerBan',
        '消費明細_數量': 'quantity',
        '消費明細_單價': 'unitPrice',
        '消費明細_金額': 'detailAmount',
        '消費明細_品名': 'itemName',
        
        # 2. 其他平台/自訂格式之精確備用對齊 (避免短字串包含造成衝突碰撞)
        '交易日期': 'invDate',
        '店家名稱': 'sellerName',
        '商戶名稱': 'sellerName',
        '商品名稱': 'itemName',
        '品項名稱': 'itemName',
        '消費時間': 'invTime',
        '交易時間': 'invTime',
        '統一編號': 'sellerBan',
        '賣方統編': 'sellerBan',
        '買方統一編號': 'buyerBan',
        
        # 3. 最末級單字備用 (長度由長到短匹配)
        '日期': 'invDate',
        '時間': 'invTime',
        '店家': 'sellerName',
        '商品': 'itemName',
        '品項': 'itemName',
        '數量': 'quantity',
        '單價': 'unitPrice',
        '金額': 'amount',
        '小計': 'amount',
        '狀態': 'invStatus',
    }
    
    # 清理欄位空格並重新映射名稱
    df_csv = df_csv.rename(columns=lambda x: str(x).strip() if pd.notna(x) else x)
    
    # 由長到短排列鍵值，防止 '發票' 誤匹配 '發票號碼'、'金額' 誤匹配 '消費明細_金額' 等
    sorted_mapping = sorted(column_mapping.items(), key=lambda x: len(x[0]), reverse=True)
    
    rename_dict = {}
    for col in df_csv.columns:
        col_str = str(col).strip()
        for key, val in sorted_mapping:
            if key in col_str:
                rename_dict[col] = val
                break
                
    df_csv = df_csv.rename(columns=rename_dict)
    
    # 驗證核心欄位
    if 'invDate' not in df_csv.columns or 'invNum' not in df_csv.columns:
        print("[Cleaner] [WARNING] 警告：CSV 檔案缺少『發票日期』或『發票號碼』等核心欄位，無法清洗。")
        return []
        
    # 填充缺失輔助欄位
    if 'invTime' not in df_csv.columns:
        df_csv['invTime'] = '12:00:00'
    if 'sellerName' not in df_csv.columns:
        df_csv['sellerName'] = '未知商家'
    if 'sellerBan' not in df_csv.columns:
        df_csv['sellerBan'] = '00000000'
    if 'amount' not in df_csv.columns:
        df_csv['amount'] = 0
    if 'invStatus' not in df_csv.columns:
        df_csv['invStatus'] = '已開立'
        
    # 清洗金額與格式，剔除 $ 或逗號
    df_csv['amount'] = df_csv['amount'].astype(str).str.replace(r'[$,]', '', regex=True)
    df_csv['amount'] = pd.to_numeric(df_csv['amount'], errors='coerce').fillna(0).astype(int)
    
    invoices = []
    
    # 按照發票號碼分組
    for inv_num, group in df_csv.groupby('invNum'):
        first_row = group.iloc[0]
        
        # 民國年斜線轉換或西元格式統一
        inv_date = str(first_row['invDate']).replace('-', '/').strip()
        
        # 處理品項明細
        items_list = []
        if 'itemName' in group.columns:
            for i, (_, row) in enumerate(group.iterrows()):
                qty = int(row.get('quantity', 1)) if 'quantity' in row and pd.notna(row['quantity']) else 1
                
                # 優先使用單品金額 detailAmount，若無則依單價計，最後 fallback 至發票金額 amount
                fallback_price = int(row.get('detailAmount', row['amount'])) if 'detailAmount' in row and pd.notna(row['detailAmount']) else int(row['amount'])
                price = int(row.get('unitPrice', fallback_price)) if 'unitPrice' in row and pd.notna(row['unitPrice']) else fallback_price
                
                # 優先使用單品金額 detailAmount，其次以單價乘數量計，最後 fallback 至 amount
                item_amt = int(row.get('detailAmount', price * qty)) if 'detailAmount' in row and pd.notna(row['detailAmount']) else int(row.get('amount', price * qty))
                
                items_list.append({
                    "rowNum": str(i + 1),
                    "description": str(row['itemName']),
                    "quantity": str(qty),
                    "unitPrice": str(price),
                    "amount": item_amt
                })
        else:
            # 若無品項資訊，依店家名稱匹配預設商品名
            default_item_desc = "日常消费"
            s_name = str(first_row['sellerName'])
            if "超商" in s_name or "便利商店" in s_name or "全家" in s_name or "統一超商" in s_name:
                default_item_desc = "便利商店雜貨"
            elif "高鐵" in s_name:
                default_item_desc = "高鐵乘車票"
            elif "台鐵" in s_name or "鐵路" in s_name:
                default_item_desc = "台鐵火車票"
            elif "麥當勞" in s_name:
                default_item_desc = "麥當勞餐點"
            elif "星巴克" in s_name:
                default_item_desc = "星巴克咖啡糕點"
            elif "影城" in s_name or "電影" in s_name:
                default_item_desc = "電影票"
                
            items_list.append({
                "rowNum": "1",
                "description": default_item_desc,
                "quantity": "1",
                "unitPrice": str(first_row['amount']),
                "amount": int(first_row['amount'])
            })
            
        invoices.append({
            "invNum": str(inv_num),
            "invDate": inv_date,
            "invTime": str(first_row['invTime']),
            "sellerName": str(first_row['sellerName']),
            "sellerBan": str(first_row['sellerBan']),
            "invPeriod": "", 
            "invStatus": str(first_row['invStatus']),
            "amount": int(first_row['amount']),
            "cardType": "3J0002",
            "cardNo": "/AB12345"
        })
        
        # 存入明細快取
        _csv_details_cache[str(inv_num)] = items_list
        
    print(f"[Cleaner] CSV 發票清單解析完畢，共解析出 {len(invoices)} 張獨立發票！")
    return invoices

def clean_and_process_invoices(start_date="2026/01/01", end_date="2026/05/29"):
    """
    呼叫客戶端獲取發票並進行 Pandas 資料清洗與視覺化彙整
    優先順序：
    1. 偵測本地 data/ 資料夾下的 CSV 檔案，若有，以 CSV 解析。
    2. 若無，則呼叫 Mof Client（依據 config.json 決定真實 API 或 Mock 模擬資料）。
    """
    print("[Cleaner] 開始執行資料撈取與清洗流程...")
    
    # 偵測本地 data/*.csv 檔案
    csv_file = None
    data_dir = os.path.join(os.getcwd(), "data")
    if os.path.exists(data_dir):
        files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        if files:
            csv_file = os.path.join(data_dir, files[0])
            print(f"[Cleaner] [OK] 偵測到本地發票 CSV 數據檔案: {csv_file}")
            
    raw_invoices = []
    
    # 第一種方案：本地 CSV 解析
    if csv_file:
        raw_invoices = parse_downloaded_csv(csv_file)
        if not raw_invoices:
            print("[Cleaner] 警告：本地 CSV 解析失敗。降級採用 Client 金鑰介接方案。")
            
    # 第二種方案：Client（API 或 Mock）解析
    if not raw_invoices:
        client = TaiwanEInvoiceClient()
        raw_invoices = client.fetch_invoice_list(start_date, end_date)
        
    if not raw_invoices:
        print("[Cleaner] [ERROR] 錯誤：未能獲取任何發票資料，清洗終止。")
        return False
        
    print(f"[Cleaner] 開始合併明細品項與特徵工程...")
    
    # 攤平發票與明細項目 (Flat Map to Items)
    all_items = []
    
    # 用於輔助 API 呼叫明細
    client_for_detail = None
    if not csv_file:
        client_for_detail = TaiwanEInvoiceClient()
        
    for idx, inv in enumerate(raw_invoices):
        inv_num = inv["invNum"]
        inv_date = inv["invDate"]
        inv_time = inv.get("invTime", "12:00:00")
        seller_name = inv["sellerName"]
        seller_ban = inv["sellerBan"]
        inv_status = inv["invStatus"]
        inv_period = inv.get("invPeriod", "")
        
        # 獲取明細
        if csv_file:
            details = _csv_details_cache.get(inv_num, [])
        else:
            details = client_for_detail.fetch_invoice_detail(inv_num, inv_date)
            
        if not details:
            details = [{
                "rowNum": "1",
                "description": "一般日常消費",
                "quantity": "1",
                "unitPrice": str(inv.get("amount", 0)),
                "amount": inv.get("amount", 0)
            }]
            
        for item in details:
            try:
                qty = int(float(item.get("quantity", 1)))
                unit_price = int(float(item.get("unitPrice", 0)))
                item_amount = int(float(item.get("amount", 0)))
            except Exception:
                qty = 1
                unit_price = int(item.get("unitPrice", 0))
                item_amount = unit_price
                
            all_items.append({
                "invNum": inv_num,
                "invDate": inv_date,
                "invTime": inv_time,
                "sellerName": seller_name,
                "sellerBan": seller_ban,
                "invStatus": inv_status,
                "invPeriod": inv_period,
                "itemName": item.get("description", "一般消費"),
                "itemQty": qty,
                "itemPrice": unit_price,
                "itemAmount": item_amount
            })
            
    # 建立 Pandas DataFrame
    df = pd.DataFrame(all_items)
    
    # 時間轉換與欄位提取
    df['date'] = df['invDate'].apply(parse_taiwan_date)
    df = df.dropna(subset=['date']) # 剔除日期無效列
    
    # 提取多維度時間屬性
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df['week_num'] = df['date'].dt.isocalendar().week
    df['weekday'] = df['date'].dt.day_name()
    df['weekday_zh'] = df['date'].dt.weekday.map({
        0: '週一', 1: '週二', 2: '週三', 3: '週四', 4: '週五', 5: '週六', 6: '週日'
    })
    
    # 提取小時與時段
    df['hour'] = df['invTime'].apply(lambda x: str(x).split(':')[0] if isinstance(x, str) else '12')
    df['time_period'] = df['invTime'].apply(parse_time_period)
    
    # 計算期別 (如果為空，自動由 date 計算對應的民國雙月期別)
    def calc_period(row):
        if row['invPeriod']:
            return row['invPeriod']
        minguo_y = row['date'].year - 1911
        m = row['date'].month
        period_m = m if m % 2 == 0 else m + 1
        return f"{minguo_y}{period_m:02d}"
        
    df['invPeriod'] = df.apply(calc_period, axis=1)
    
    # 消費分類標籤
    df['category'] = df.apply(lambda row: classify_item(row['itemName'], row['sellerName']), axis=1)
    
    # 異常值處理：作廢與退貨
    df['is_refund'] = df['itemAmount'] < 0
    
    df_voided = df[df['invStatus'] == '已作廢']
    df_active = df[(df['invStatus'] != '已作廢')]
    
    # 計算 KPI 總體統計指標
    total_spend = int(df_active['itemAmount'].sum())
    total_invoices = int(df_active['invNum'].nunique())
    avg_invoice_spend = int(total_spend / total_invoices) if total_invoices > 0 else 0
    
    # 退貨統計
    df_refunds = df_active[df_active['is_refund']]
    total_refund_amount = int(df_refunds['itemAmount'].sum())
    total_refund_count = int(df_refunds['invNum'].nunique())
    
    # 作廢發票統計
    voided_invoices_count = int(df_voided['invNum'].nunique())
    voided_invoices_amount = int(df_voided['itemAmount'].sum())
    
    # ---------------------------------------------
    # 圖表數據聚合 (Aggregations)
    # ---------------------------------------------
    
    # A. 月消費趨勢
    monthly_trend = df_active.groupby('month').agg(
        amount=('itemAmount', 'sum'),
        count=('invNum', 'nunique')
    ).reset_index().to_dict(orient='records')
    
    # B. 週消費趨勢 (只取最近 12 週)
    weekly_trend_df = df_active.groupby(['year', 'week_num']).agg(
        amount=('itemAmount', 'sum'),
        count=('invNum', 'nunique')
    ).reset_index().sort_values(['year', 'week_num']).tail(12)
    weekly_trend_df['week_label'] = '第 ' + weekly_trend_df['week_num'].astype(str) + ' 週'
    weekly_trend = weekly_trend_df[['week_label', 'amount', 'count']].to_dict(orient='records')
    
    # C. 消費類別圓餅圖佔比 (排除退貨列，避免負數干擾圓餅圖)
    df_positive = df_active[df_active['itemAmount'] > 0]
    category_agg = df_positive.groupby('category').agg(
        amount=('itemAmount', 'sum'),
        count=('invNum', 'nunique')
    ).reset_index()
    category_sum = category_agg['amount'].sum()
    category_agg['percentage'] = (category_agg['amount'] / category_sum * 100).round(1) if category_sum > 0 else 0
    category_agg = category_agg.sort_values('amount', ascending=False)
    categories_list = category_agg.to_dict(orient='records')
    
    # D. 最愛店家 Top 10
    top_sellers_df = df_active.groupby('sellerName').agg(
        amount=('itemAmount', 'sum'),
        count=('invNum', 'nunique')
    ).reset_index()
    top_sellers_df = top_sellers_df[top_sellers_df['amount'] > 0]
    top_sellers_df = top_sellers_df.sort_values('amount', ascending=False).head(10)
    top_sellers_df['sellerShort'] = top_sellers_df['sellerName'].apply(
        lambda x: re.sub(r'(股份有限公司|分公司|有限公司|台北.*店|南京.*店|大安店|重慶店|板橋店|桂林店|台灣)', '', str(x)).strip()
    )
    top_sellers = top_sellers_df[['sellerName', 'sellerShort', 'amount', 'count']].to_dict(orient='records')
    
    # E. 特定時段消費熱力圖 (星期 x 時段)
    weekday_order = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
    period_order = ['早餐 (06-11)', '午餐 (11-14)', '下午茶 (14-17)', '晚餐 (17-21)', '深夜 (21-06)']
    
    heatmap_df = df_active.groupby(['weekday_zh', 'time_period']).agg(
        amount=('itemAmount', 'sum'),
        count=('invNum', 'nunique')
    ).reset_index()
    
    grid = []
    for w in weekday_order:
        for p in period_order:
            match = heatmap_df[(heatmap_df['weekday_zh'] == w) & (heatmap_df['time_period'] == p)]
            if not match.empty:
                grid.append({
                    "weekday": w,
                    "period": p,
                    "amount": int(match.iloc[0]['amount']),
                    "count": int(match.iloc[0]['count'])
                })
            else:
                grid.append({
                    "weekday": w,
                    "period": p,
                    "amount": 0,
                    "count": 0
                })
                
    # F. 發票明細清單彙整 (按日期與時間降序)
    invoice_groups = df.groupby('invNum')
    invoices_list = []
    
    for inv_num, group in invoice_groups:
        first_row = group.iloc[0]
        items = []
        for _, row in group.iterrows():
            items.append({
                "itemName": row["itemName"],
                "qty": row["itemQty"],
                "price": row["itemPrice"],
                "amount": row["itemAmount"],
                "category": row["category"]
            })
            
        invoices_list.append({
            "invNum": inv_num,
            "invDate": first_row["invDate"],
            "invTime": first_row["invTime"],
            "date": first_row["date"].strftime('%Y-%m-%d'),
            "sellerName": first_row["sellerName"],
            "sellerBan": first_row["sellerBan"],
            "amount": int(group["itemAmount"].sum()),
            "invStatus": first_row["invStatus"],
            "invPeriod": first_row["invPeriod"],
            "timePeriod": first_row["time_period"],
            "weekday": first_row["weekday_zh"],
            "isRefund": bool(group["itemAmount"].sum() < 0),
            "items": items
        })
        
    invoices_list.sort(key=lambda x: (x["date"], x["invTime"]), reverse=True)
    
    # ---------------------------------------------
    # 組裝輸出資料
    # ---------------------------------------------
    output_data = {
        "summary": {
            "totalSpend": total_spend,
            "totalInvoices": total_invoices,
            "averageInvoiceSpend": avg_invoice_spend,
            "totalRefundAmount": total_refund_amount,
            "totalRefundCount": total_refund_count,
            "voidedCount": voided_invoices_count,
            "voidedAmount": voided_invoices_amount,
            "lastUpdated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        "trends": {
            "monthly": monthly_trend,
            "weekly": weekly_trend
        },
        "categories": categories_list,
        "topSellers": top_sellers,
        "heatmap": grid,
        "invoices": invoices_list
    }
    
    # 確保寫入目錄存在 (寫入 React 專案的 public/data/invoice_data.json)
    target_dir = os.path.join(os.getcwd(), "public", "data")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        
    target_file = os.path.join(target_dir, "invoice_data.json")
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"[Cleaner] [OK] 清洗成功！儀表板數據庫已更新至: {target_file}")
    return True

if __name__ == "__main__":
    clean_and_process_invoices()
