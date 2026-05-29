import os
import re
import json
import pandas as pd
import numpy as np
from datetime import datetime
from mof_api import TaiwanEInvoiceClient

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
        # 若出錯，回傳 NaT
        return pd.NaT

def classify_item(item_desc, seller_name):
    """
    利用品項描述與商家名稱，自動進行消費分類標籤標記。
    """
    desc = str(item_desc).lower()
    seller = str(seller_name).lower()
    
    # 1. 飲食分類 (飲食)
    food_kws = ['便當', '燒肉', '茶', '綠茶', '紅茶', '奶茶', '咖啡', '拿鐵', '飯', '麵', '壽司', 
                '套餐', '鷄塊', '薯條', '蛋糕', '巧克力', '蘋果', '鮮乳', '水', '洋芋片', '吐司', 
                '蛋', '御飯糰', '冰', '飲料', '餐', '牛排', '火鍋', '壽喜燒', '舒芙蕾']
    food_sellers = ['星巴克', '麥當勞', '爭鮮', '超商', '便利商店', '全家', '統一超商', '萊爾富', 'ok超商', '美廉社']
    if any(kw in desc for kw in food_kws) or any(kw in seller for kw in food_sellers):
        return '飲食'
        
    # 2. 交通分類 (交通)
    trans_kws = ['高鐵', '台鐵', '火車', '乘車票', '悠遊卡', '捷運', '計程車', '加油', '中油', '台亞', '車票', '客運', 'uber']
    trans_sellers = ['高速鐵路', '台鐵', '捷運', '客運', '加油站', '中油', '台灣鐵路']
    if any(kw in desc for kw in trans_kws) or any(kw in seller for kw in trans_sellers):
        return '交通'
        
    # 3. 娛樂分類 (娛樂)
    ent_kws = ['電影', '威秀', '影城', 'steam', '遊戲', '娛樂', 'cyberpunk', 'hades', 'netflix', 'spotify', 'ktv', '歌唱', '演唱會']
    ent_sellers = ['威秀', '影城', 'steam', '國賓', '秀泰', '錢櫃', '好樂迪', 'spotify', 'netflix']
    if any(kw in desc for kw in ent_kws) or any(kw in seller for kw in ent_sellers):
        return '娛樂'
        
    # 4. 3C配件分類 (3C配件)
    electronics_kws = ['iphone', '快充線', '滑鼠', '鍵盤', 'type-c', 'hub', '轉接器', '行動電源', '手機', '電腦', '線材', '耳機', '螢幕', '隨身碟']
    electronics_sellers = ['燦坤', '順發', 'apple', '小米', '光華商場', '三創']
    if any(kw in desc for kw in electronics_kws) or any(kw in seller for kw in electronics_sellers):
        return '3C配件'
        
    # 5. 服飾分類 (服飾)
    cloth_kws = ['短t', '運動鞋', '皮夾', '衣服', '外套', '褲子', '鞋子', '洋裝', '襯衫', '包包', '皮帶']
    cloth_sellers = ['新光三越', 'uniqlo', 'zara', '無印良品', 'sogo', '微風', '遠東百貨']
    if any(kw in desc for kw in cloth_kws) or any(kw in seller for kw in cloth_sellers):
        return '服飾'
        
    # 6. 醫療分類 (醫療)
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

def clean_and_process_invoices(start_date="2026/01/01", end_date="2026/05/29"):
    """
    呼叫客戶端獲取發票並進行 Pandas 資料清洗與視覺化彙整
    """
    print("[Cleaner] 開始執行資料撈取與清洗流程...")
    
    # 1. 介接 API 獲取發票與明細
    client = TaiwanEInvoiceClient()
    raw_invoices = client.fetch_invoice_list(start_date, end_date)
    
    if not raw_invoices:
        print("[Cleaner] 警告：未能獲取任何原始發票資料，清洗終止。")
        return False
        
    print(f"[Cleaner] 成功讀取 {len(raw_invoices)} 張原始發票。開始合併明細項目...")
    
    # 2. 攤平發票與明細項目 (Flat Map to Items)
    all_items = []
    
    for idx, inv in enumerate(raw_invoices):
        inv_num = inv["invNum"]
        inv_date = inv["invDate"]
        inv_time = inv.get("invTime", "00:00:00")
        seller_name = inv["sellerName"]
        seller_ban = inv["sellerBan"]
        inv_status = inv["invStatus"]
        inv_period = inv["invPeriod"]
        
        # 撈取這張發票的明細
        details = client.fetch_invoice_detail(inv_num, inv_date)
        
        # 如果沒有明細，建立一個預設的一般消费項目
        if not details:
            details = [{
                "rowNum": "1",
                "description": "一般消費",
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
            
    # 3. 建立 Pandas DataFrame
    df = pd.DataFrame(all_items)
    
    # 4. 時間轉換與欄位提取
    # 將民國年/西元年轉為標準西元 Datetime
    df['date'] = df['invDate'].apply(parse_taiwan_date)
    df = df.dropna(subset=['date']) # 剔除日期無效列
    
    # 提取多維度時間屬性
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.strftime('%Y-%m')
    df['week_num'] = df['date'].dt.isocalendar().week
    df['weekday'] = df['date'].dt.day_name() # Monday, Tuesday...
    df['weekday_zh'] = df['date'].dt.weekday.map({
        0: '週一', 1: '週二', 2: '週三', 3: '週四', 4: '週五', 5: '週六', 6: '週日'
    })
    
    # 提取時間小時並分組時段
    df['hour'] = df['invTime'].apply(lambda x: x.split(':')[0] if isinstance(x, str) else '00')
    df['time_period'] = df['invTime'].apply(parse_time_period)
    
    # 5. 消費分類標籤
    df['category'] = df.apply(lambda row: classify_item(row['itemName'], row['sellerName']), axis=1)
    
    # 6. 異常值處理：作廢與退貨 (退貨負數金額、作廢發票篩選)
    # A. 獨立出作廢發票與退貨發票的統計指標，但不納入主消費統計
    # 標記退貨 (如果 itemAmount 為負數)
    df['is_refund'] = df['itemAmount'] < 0
    
    # 作廢發票 DataFrame
    df_voided = df[df['invStatus'] == '已作廢']
    
    # 正常且有效發票 DataFrame (用來做消費指標分析)
    df_active = df[(df['invStatus'] != '已作廢')]
    
    # 計算 KPI 指標
    # 有效消費總額 (退貨的負數會在這裡自然抵消，反映真實總消費額；亦可加總絕對值，這裡採取自然抵消淨消費)
    total_spend = int(df_active['itemAmount'].sum())
    total_invoices = int(df_active['invNum'].nunique())
    avg_invoice_spend = int(total_spend / total_invoices) if total_invoices > 0 else 0
    
    # 退貨統計 (只統計 itemAmount < 0 且有效發票)
    df_refunds = df_active[df_active['is_refund']]
    total_refund_amount = int(df_refunds['itemAmount'].sum()) # 負數
    total_refund_count = int(df_refunds['invNum'].nunique())
    
    # 作廢發票統計
    voided_invoices_count = int(df_voided['invNum'].nunique())
    voided_invoices_amount = int(df_voided['itemAmount'].sum())
    
    # ---------------------------------------------
    # 7. 圖表數據聚合 (Aggregations)
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
    
    # C. 消費類別圓餅圖佔比 (排除退貨列，避免負數干擾圓餅圖，只算大於 0 的正向支出)
    df_positive = df_active[df_active['itemAmount'] > 0]
    category_agg = df_positive.groupby('category').agg(
        amount=('itemAmount', 'sum'),
        count=('invNum', 'nunique')
    ).reset_index()
    category_agg['percentage'] = (category_agg['amount'] / category_agg['amount'].sum() * 100).round(1)
    # 按金額降序
    category_agg = category_agg.sort_values('amount', ascending=False)
    categories_list = category_agg.to_dict(orient='records')
    
    # D. 最愛店家 Top 10
    top_sellers_df = df_active.groupby('sellerName').agg(
        amount=('itemAmount', 'sum'),
        count=('invNum', 'nunique')
    ).reset_index()
    # 剔除退貨造成的負數影響 (取正值進行排行)
    top_sellers_df = top_sellers_df[top_sellers_df['amount'] > 0]
    top_sellers_df = top_sellers_df.sort_values('amount', ascending=False).head(10)
    # 縮短店名方便圖表呈現 (移除「股份有限公司」、「分公司」等贅字)
    top_sellers_df['sellerShort'] = top_sellers_df['sellerName'].apply(
        lambda x: re.sub(r'(股份有限公司|分公司|有限公司|台北.*店|南京.*店|大安店|重慶店|板橋店|桂林店)', '', x).strip()
    )
    top_sellers = top_sellers_df[['sellerName', 'sellerShort', 'amount', 'count']].to_dict(orient='records')
    
    # E. 特定時段消費熱力圖 (星期 x 時段)
    # 橫軸星期 (1-7)，縱軸時段
    weekday_order = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
    period_order = ['早餐 (06-11)', '午餐 (11-14)', '下午茶 (14-17)', '晚餐 (17-21)', '深夜 (21-06)']
    
    heatmap_df = df_active.groupby(['weekday_zh', 'time_period']).agg(
        amount=('itemAmount', 'sum'),
        count=('invNum', 'nunique')
    ).reset_index()
    
    # 填補缺失的網格組合，確保熱力圖完整
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
                
    # F. 發票明細清單彙整 (按日期降序，保留發票階層)
    # 先以發票號碼分組，整理出發票資料與項目明細
    invoice_groups = df.groupby('invNum')
    invoices_list = []
    
    for inv_num, group in invoice_groups:
        first_row = group.iloc[0]
        # 合併明細
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
        
    # 按日期與時間降序排列
    invoices_list.sort(key=lambda x: (x["date"], x["invTime"]), reverse=True)
    
    # ---------------------------------------------
    # 8. 組裝輸出資料
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
    # 我們支援自動建立 public/data 目錄
    target_dir = os.path.join(os.getcwd(), "public", "data")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        
    target_file = os.path.join(target_dir, "invoice_data.json")
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"[Cleaner] 清洗成功！儀表板專用數據已匯出至: {target_file}")
    return True

if __name__ == "__main__":
    clean_and_process_invoices()
