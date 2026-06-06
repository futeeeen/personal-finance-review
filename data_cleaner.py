# -*- coding: utf-8 -*-
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
    採用「雙層過濾引擎」加上「機器學習」：
    第一階段：品項關鍵字精確匹配 (Item-level matching) - 優先度最高，避免因商場/百貨公司等大賣場商家名稱造成誤判。
    第二階段：商家名稱模糊匹配 (Seller-level matching) - 作為兜底，當品項描述無特徵時，根據購買場所進行合理分類。
    第三階段：智慧 NLP 機器學習分類 (ML classification) - 當前兩階段皆無判定時，調用機器學習模型預測。
    """
    desc = str(item_desc).lower()
    seller = str(seller_name).lower()

    # 定義各類別關鍵字 (品項級特徵)
    trans_kws = [
        '高鐵', '台鐵', '火車', '車票', '乘車票', '悠遊卡', '捷運', '客運', '公車', '計程車', 
        'uber', 'yoxi', '汽油', '無鉛', '柴油', '加油', '充電', '車'
    ]
    med_kws = [
        '口罩', '維他命', '維生素', '益生菌', '防曬', '洗面', '藥', '感冒', '診所', '掛號費', 
        '藥水', '保健食品', '衛生套', '避孕套', '杜蕾斯', 'durex', '岡本', 'okamoto', '滴劑', 
        '眼藥水', '貼布', '棉花棒',
        # AI 新增: 護膚與身體保養關鍵字
        '凝露', '毛髮霜', '保濕', 'relove'
    ]
    electronics_kws = [
        'iphone', 'ipad', 'macbook', '華碩', 'asus', '快充', '傳輸線', '充電線', '滑鼠', 
        '鍵盤', 'type-c', 'hub', '轉接', '行動電源', '手機', '電腦', '相機', '耳機', '螢幕', 
        '隨身碟', '記憶卡', '電池', '延長線', '插頭', '線材', '記憶體', '硬碟',
        # AI 新增: 3C配件關鍵字
        '掛繩', '夾片'
    ]
    cloth_kws = [
        '短t', 't恤', '襯衫', '外套', '刷毛', '大衣', '洋裝', '褲子', '牛仔褲', '裙子', 
        '鞋子', '運動鞋', '皮鞋', '皮夾', '包包', '背包', '皮帶', '眼鏡', '襪子', '衣',
        # AI 新增: 服飾關鍵字
        't 恤', '女裝', '服飾'
    ]
    ent_kws = [
        '電影', '影城', '吉伊卡哇', 'chiikawa', '寶可夢', '卡牌', '玩具', '吊飾', '玩偶', 
        '底片', '沖洗', '照片', '相片', '遊戲', 'steam', 'hades', 'cyberpunk', 'switch', 
        'playstation', 'xbox', 'netflix', 'spotify', 'disney+', 'ktv', '歌唱', '演唱會', 
        '展覽', '門票', '售票',
        # 新增：旅遊與飯店住宿、客房等休閒娛樂特徵
        '客房', '客房收入', '住宿', '旅宿', '房費', '退房', '訂房', '旅館', '飯店', '民宿', '客棧', 
        '旅店', '溫泉', '休息費', '渡假',
        # AI 新增: 票券與娛樂週邊
        '成人票', '學生票', '優待票', '票券', '兌換券', '電影票', '電票', 'photo', 'towel'
    ]
    food_kws = [
        # 主食與餐點、各類中西式料理字眼
        '便當', '燒肉', '飯', '麵', '拉麵', '涼麵', '炒麵', '壽司', '手卷', '茶碗蒸', '湯包', '小籠包',
        '水餃', '鍋貼', '堡', '漢堡', '起司堡', '三明治', '吐司', '麵包', '披薩', 'pizza', '章魚燒',
        '沙拉', '烤雞', '炸雞', '雞塊', '鷄塊', '雞排', '雞腿', '雞肉', '雞肉飯', '雞翅', '雞軟骨', '烤肉', '燒烤',
        '火鍋', '鍋物', '壽喜燒', '套餐', '餐點', '特餐', '分享餐', '餐費', '餐飲', '料理', '食', '餐廳',
        # 高頻單字根食物
        '牛', '豬', '雞', '鷄', '羊', '鴨', '鵝', '魚', '蝦', '蟹', '肉', '湯', '菜',
        '蛋', '筍', '菇', '椒', '豆', '茄', '蒜', '蔥', '瓜', '薯', '蛤', '蚵', '排', '串',
        # 各種食材與小吃配料
        '年糕', '豆腐', '豆皮', '甜不辣', '貢丸', '黑輪', '玉子燒', '洋蔥圈', '肋條', '腿排', '滿福', '夾心',
        # 飲料與水、茶品、甜點、漿凍奶
        '茶', '紅茶', '綠茶', '奶茶', '青茶', '包種', '普洱', '烏龍', '拿鐵', '咖啡', '飲品', '飲料',
        '果汁', '優格', '優酪', '鮮乳', '牛奶', '水', '礦泉水', '可樂', '汽水', '冷泡', '冰', '凍',
        '豆漿', '米漿', '鮮', '乳', '飲', '汁', '漿', '奶', '茶行', '茶飲', '四季',
        # 甜點與點心
        '蛋糕', '提拉米蘇', '麻糬', '泡芙', '甜甜圈', '雪糕', '冰淇淋', '蛋捲冰', '巧克力',
        '布丁', '舒芙蕾', '洋芋片', '薯條', '仙貝', '零食', '餅乾', '糕', '酥', '餅', '糖',
        # 早餐與食材標記
        '蛋餅', '茶葉蛋', '酸辣湯', '蔬菜', '水果', '蘋果', '香蕉', '鮮食促', '友善食光', '珍食',
        # 服務費與外送費
        '服務費', '服務費用', '訂餐服務費', 'service charge', '外送費', '平台費',
        # AI 新增: 點心茶品與特定食品關鍵字
        '卡士達', '布里歐', '海陸', '炸兩', '鐵觀音', '蕎麥', 'bread', '味噌', '天光乍現'
    ]

    # 定義各類別指定商家 (商家級特徵)
    trans_sellers = [
        '高速鐵路', '台鐵', '捷運', '客運', '加油站', '中油', '台灣中油', '台亞', '全國加油站', 
        '和泰聯網', '台灣鐵路'
    ]
    med_sellers = [
        '藥局', '診所', '醫院', '康是美', '屈臣氏', 'watsons', 'cosmed', '大樹藥局', '杏一', 
        '佑全', '丁丁',
        # AI 新增: 藥妝連鎖母公司
        '統一生活', '統一生活事業'
    ]
    electronics_sellers = ['燦坤', '順發', 'apple', '小米', '光華', '三創', '良興', '地標網通']
    cloth_sellers = [
        'uniqlo', 'zara', '無印良品', 'net', 'h&m', 'gap', 'adidas', 'nike', 'puma', 
        '新光三越', 'sogo', '微風', '遠東', '三井不動產', '美麗華', 'outlet',
        # AI 新增: 品牌服飾與奧特萊斯
        '愛特思', '普安貝兒', '華泰名品', '華泰名品城'
    ]
    ent_sellers = [
        '威秀', '影城', '國賓', '秀泰', 'steam', 'spotify', 'netflix', '錢櫃', '好樂迪', 
        '大創', 'daiso', '紫蘿蘭',
        # 新增：飯店、商旅、酒店等休閒住宿場所名稱特徵
        '商旅', '飯店', '酒店', '旅店', '旅社', '賓館', '會館', '渡假', '渡假村', '民宿', '商館'
    ]
    food_sellers = [
        '星巴克', 'starbucks', '麥當勞', 'mcdonald', '爭鮮', '壽司郎', 'sushiro', '鬍子兄弟', '都城實業', 
        '作燴餐飲', '丰呈馭食', '漫時', '富利餐飲', '必勝客', '肯德基', 'kfc', '摩斯', 'mos', '黛比澍', 
        '百變全球', '龍角', '景美茶行', '拾汣茶屋', '先喝道', '約翰紅茶', '一青苑', '茶之魔手', '萬波', 
        'comebuy', '珍煮丹', '甘蔗媽媽', '鳥人拉麵', '湯包', '餐館', '小吃', '食堂', '咖啡', '茶飲',
        '超商', '便利商店', '全家', '統一超商', '萊爾富', 'ok超商', '美廉社', '餐飲', '餐坊', '麵店', '火鍋',
        '蹦啾兒', '鬍鬚忠', '豪牛肉湯',
        # 新增：各類飲品、茶行、餐飲機構通用字眼
        '茶行', '茶館', '茶舍', '茶吧', '咖啡廳', '烘焙坊', '麵包店', '甜點店', '冰店', '餐酒館',
        # AI 新增: 餐飲品牌與火鍋
        '樂多多', '肉多多', '丼賞'
    ]

    # --------------------------------------------------
    # 【第一階段：品項關鍵字匹配】 最具特異性，優先檢測
    # --------------------------------------------------
    if any(kw in desc for kw in trans_kws):
        return '交通'
    if any(kw in desc for kw in med_kws):
        return '醫療'
    if any(kw in desc for kw in electronics_kws):
        return '3C配件'
    if any(kw in desc for kw in cloth_kws):
        return '服飾'
    if any(kw in desc for kw in ent_kws):
        return '娛樂'
    if any(kw in desc for kw in food_kws):
        return '飲食'

    # --------------------------------------------------
    # 【第二階段：商家名稱模糊匹配】 當品項無特徵時的兜底分類
    # --------------------------------------------------
    # 優先處理含有「餐飲」的商家名，防止因分店名包含「捷運」等而誤判
    if '餐飲' in seller:
        return '飲食'
        
    if any(kw in seller for kw in trans_sellers):
        return '交通'
    if any(kw in seller for kw in med_sellers):
        return '醫療'
    if any(kw in seller for kw in electronics_sellers):
        return '3C配件'
    if any(kw in seller for kw in cloth_sellers):
        return '服飾'
    if any(kw in seller for kw in ent_sellers):
        return '娛樂'
    if any(kw in seller for kw in food_sellers):
        return '飲食'

    # --------------------------------------------------
    # 【第三階段：智慧機器學習預測】 當字典皆無法辨識時的智慧兜底 (NLP + ML)
    # --------------------------------------------------
    try:
        from ml_classifier.classifier import predict_category
        ml_cat = predict_category(item_desc, seller_name)
        if ml_cat:
            return ml_cat
    except Exception:
        pass

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
    # 支援批次跨月合併，此處保留舊 cache 項目不直接清空
    
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
    
    # 建立強大安全的整數解析器以避免備註列轉換出錯
    def to_int_safe(val, default=0):
        if pd.isna(val) or not val:
            return default
        try:
            clean_str = re.sub(r'[^\d\-.]', '', str(val))
            if not clean_str:
                return default
            return int(float(clean_str))
        except Exception:
            return default
            
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
                qty = to_int_safe(row.get('quantity', 1), 1)
                
                # 優先使用單品金額 detailAmount，若無則依單價計，最後 fallback 至發票金額 amount
                fallback_price = to_int_safe(row.get('detailAmount', row['amount']), to_int_safe(row['amount']))
                price = to_int_safe(row.get('unitPrice', fallback_price), fallback_price)
                
                # 優先使用單品金額 detailAmount，其次以單價乘數量計，最後 fallback 至 amount
                item_amt = to_int_safe(row.get('detailAmount', price * qty), to_int_safe(row.get('amount', price * qty)))
                
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
    
    global _csv_details_cache
    _csv_details_cache = {}
    
    # 偵測本地 user_data/invoices/*.csv 檔案 (支援批次跨月發票 CSV 合併載入)
    csv_files = []
    data_dir = os.path.join(os.getcwd(), "user_data", "invoices")
    if os.path.exists(data_dir):
        csv_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.csv')]
        if csv_files:
            print(f"[Cleaner] [OK] 偵測到本地共 {len(csv_files)} 個發票 CSV 數據檔案，即將進行批次合併洗滌...")
            
    raw_invoices = []
    
    # 第一種方案：本地 CSV 解析
    if csv_files:
        for csv_file in csv_files:
            try:
                parsed = parse_downloaded_csv(csv_file)
                if parsed:
                    raw_invoices.extend(parsed)
            except Exception as pe:
                print(f"[Cleaner] [警告] 解析檔案 {os.path.basename(csv_file)} 失敗: {pe}")
                
        # 對合併後的發票清單進行唯一性去重 (避免跨月或重疊下載導致重複統計)
        if raw_invoices:
            unique_invoices = []
            seen_nums = set()
            for inv in raw_invoices:
                num = inv["invNum"]
                if num not in seen_nums:
                    seen_nums.add(num)
                    unique_invoices.append(inv)
            raw_invoices = unique_invoices
            print(f"[Cleaner] [OK] 批次合併去重清洗完成，共計 {len(raw_invoices)} 張獨立發票！")
        else:
            print("[Cleaner] 警告：所有本地 CSV 解析皆失敗。降級採用 Client 金鑰介接方案。")
            
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
            "isRefund": bool(group["is_refund"].any()),
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
            "minDate": df_active['date'].min().strftime('%Y-%m-%d') if not df_active.empty else "",
            "maxDate": df_active['date'].max().strftime('%Y-%m-%d') if not df_active.empty else "",
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
    
    # 確保寫入目錄存在 (寫入分離資料夾 user_data/invoice_data.json)
    target_dir = os.path.join(os.getcwd(), "user_data")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        
    target_file = os.path.join(target_dir, "invoice_data.json")
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"[Cleaner] [OK] 清洗成功！儀表板數據庫已更新至: {target_file}")
    return True

if __name__ == "__main__":
    clean_and_process_invoices()
