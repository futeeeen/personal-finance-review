# -*- coding: utf-8 -*-
import os
import sys
import json
import pickle
import re
import pandas as pd
import numpy as np
import jieba

# 抑制 jieba 預設日誌輸出，保持終端乾淨
import logging
jieba.setLogLevel(logging.WARNING)

# 將父目錄加入 sys.path 以便加載專案檔案
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from ml_classifier.dataset import COMMON_CONSUMER_SAMPLES
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

def tokenize_text(text):
    """
    對中文文字進行清洗與斷詞，並拼接成以空格分隔的字串以便 TF-IDF 處理
    """
    # 移除標點符號與特殊字元，保留英文、中文與空格
    cleaned = re.sub(r'[^\w\s\-\.]', ' ', str(text))
    # 使用 jieba 精確模式進行分詞
    words = jieba.lcut(cleaned.lower().strip())
    # 濾除長度為 1 且不是中文字的雜訊字詞
    filtered = [w.strip() for w in words if len(w.strip()) > 0]
    return " ".join(filtered)

def generate_synthetic_samples_from_rules():
    """
    從 data_cleaner.py 中的字典規則自動衍生高品質語意特徵樣本
    """
    # 直接由我們所知 data_cleaner.py 內建的關鍵字定義一組通用對應
    # 這樣可以保證腳本獨立且強健
    food_kws = [
        '便當', '燒肉', '飯', '麵', '拉麵', '涼麵', '炒麵', '壽司', '手卷', '茶碗蒸', '湯包', '小籠包',
        '水餃', '鍋貼', '堡', '漢堡', '起司堡', '三明治', '吐司', '麵包', '披薩', 'pizza', '章魚燒',
        '沙拉', '烤雞', '炸雞', '雞塊', '鷄塊', '雞排', '雞腿', '雞肉', '雞肉飯', '雞翅', '雞軟骨', '烤肉', '燒烤',
        '火鍋', '鍋物', '壽喜燒', '套餐', '餐點', '特餐', '分享餐', '餐費', '餐飲', '料理', '食', '餐廳',
        '牛', '豬', '雞', '鷄', '羊', '鴨', '鵝', '魚', '蝦', '蟹', '肉', '湯', '菜',
        '蛋', '筍', '菇', '椒', '豆', '茄', '蒜', '蔥', '瓜', '薯', '蛤', '蚵', '排', '串',
        '年糕', '豆腐', '豆皮', '甜不辣', '貢丸', '黑輪', '玉子燒', '洋蔥圈', '肋條', '腿排', '滿福', '夾心',
        '茶', '紅茶', '綠茶', '奶茶', '青茶', '包種', '普洱', '烏龍', '拿鐵', '咖啡', '飲品', '飲料',
        '果汁', '優格', '優酪', '鮮乳', '牛奶', '水', '礦泉水', '可樂', '汽水', '冷泡', '冰', '凍',
        '豆漿', '米漿', '鮮', '乳', '飲', '汁', '漿', '奶', '茶行', '茶飲', '四季',
        '蛋糕', '提拉米蘇', '麻糬', '泡芙', '甜甜圈', '雪糕', '冰淇淋', '蛋捲冰', '巧克力',
        '布丁', '舒芙蕾', '洋芋片', '薯條', '仙貝', '零食', '餅乾', '糕', '酥', '餅', '糖',
        '蛋餅', '茶葉蛋', '酸辣湯', '蔬菜', '水果', '蘋果', '香蕉', '鮮食促', '友善食光', '珍食',
        '服務費', '服務費用', '訂餐服務費', 'service charge', '外送費', '平台費',
        '卡士達', '布里歐', '海陸', '炸兩', '鐵觀音', '蕎麥', 'bread', '味噌', '天光乍現'
    ]
    food_sellers = [
        '星巴克', 'starbucks', '麥當勞', 'mcdonald', '爭鮮', '壽司郎', 'sushiro', '鬍子兄弟', '都城實業', 
        '作燴餐飲', '丰呈馭食', '漫時', '富利餐飲', '必勝客', '肯德基', 'kfc', '摩斯', 'mos', '黛比澍', 
        '百變全球', '龍角', '景美茶行', '拾汣茶屋', '先喝道', '約翰紅茶', '一青苑', '茶之魔手', '萬波', 
        'comebuy', '珍煮丹', '甘蔗媽媽', '鳥人拉麵', '湯包', '餐館', '小吃', '食堂', '咖啡', '茶飲',
        '超商', '便利商店', '全家', '統一超商', '萊爾富', 'ok超商', '美廉社', '餐飲', '餐坊', '麵店', '火鍋',
        '蹦啾兒', '鬍鬚忠', '豪牛肉湯', '茶行', '茶館', '茶舍', '茶吧', '咖啡廳', '烘焙坊', '麵包店', '甜點店', 
        '冰店', '餐酒館', '樂多多', '肉多多', '丼賞'
    ]

    trans_kws = [
        '高鐵', '台鐵', '火車', '車票', '乘車票', '悠遊卡', '捷運', '客運', '公車', '計程車', 
        'uber', 'yoxi', '汽油', '無鉛', '柴油', '加油', '充電', '車'
    ]
    trans_sellers = [
        '高速鐵路', '台鐵', '捷運', '客運', '加油站', '中油', '台灣中油', '台亞', '全國加油站', 
        '和泰聯網', '台灣鐵路'
    ]

    med_kws = [
        '口罩', '維他命', '維生素', '益生菌', '防曬', '洗面', '藥', '感冒', '診所', '掛號費', 
        '藥水', '保健食品', '衛生套', '避孕套', '杜蕾斯', 'durex', '岡本', 'okamoto', '滴劑', 
        '眼藥水', '貼布', '棉花棒', '凝露', '毛髮霜', '保濕', 'relove'
    ]
    med_sellers = [
        '藥局', '診所', '醫院', '康是美', '屈臣氏', 'watsons', 'cosmed', '大樹藥局', '杏一', 
        '佑全', '丁丁', '統一生活', '統一生活事業'
    ]

    electronics_kws = [
        'iphone', 'ipad', 'macbook', '華碩', 'asus', '快充', '傳輸線', '充電線', '滑鼠', 
        '鍵盤', 'type-c', 'hub', '轉接', '行動電源', '手機', '電腦', '相機', '耳機', '螢幕', 
        '隨身碟', '記憶卡', '電池', '延長線', '插頭', '線材', '記憶體', '硬碟', '掛繩', '夾片'
    ]
    electronics_sellers = ['燦坤', '順發', 'apple', '小米', '光華', '三創', '良興', '地標網通']

    cloth_kws = [
        '短t', 't恤', '襯衫', '外套', '刷毛', '大衣', '洋裝', '褲子', '牛仔褲', '裙子', 
        '鞋子', '運動鞋', '皮鞋', '皮夾', '包包', '背包', '皮帶', '眼鏡', '襪子', '衣',
        't 恤', '女裝', '服飾'
    ]
    cloth_sellers = [
        'uniqlo', 'zara', '無印良品', 'net', 'h&m', 'gap', 'adidas', 'nike', 'puma', 
        '新光三越', 'sogo', '微風', '遠東', '三井不動產', '美麗華', 'outlet',
        '愛特思', '普安貝兒', '華泰名品', '華泰名品城'
    ]

    ent_kws = [
        '電影', '影城', '吉伊卡哇', 'chiikawa', '寶可夢', '卡牌', '玩具', '吊飾', '玩偶', 
        '底片', '沖洗', '照片', '相片', '遊戲', 'steam', 'hades', 'cyberpunk', 'switch', 
        'playstation', 'xbox', 'netflix', 'spotify', 'disney+', 'ktv', '歌唱', '演唱會', 
        '展覽', '門票', '售票',
        '客房', '客房收入', '住宿', '旅宿', '房費', '退房', '訂房', '旅館', '飯店', '民宿', '客棧', 
        '旅店', '溫泉', '休息費', '渡假',
        '成人票', '學生票', '優待票', '票券', '兌換券', '電影票', '電票', 'photo', 'towel'
    ]
    ent_sellers = [
        '威秀', '影城', '國賓', '秀泰', 'steam', 'spotify', 'netflix', '錢櫃', '好樂迪', 
        '大創', 'daiso', '紫蘿蘭',
        '商旅', '飯店', '酒店', '旅店', '旅社', '賓館', '會館', '渡假', '渡假村', '民宿', '商館'
    ]

    synthetic = []
    # 飲食
    for kw in food_kws:
        synthetic.append(("日常消費", kw, "飲食"))
    for s in food_sellers:
        synthetic.append((s, "日常交易品項", "飲食"))
        
    # 交通
    for kw in trans_kws:
        synthetic.append(("交通服務", kw, "交通"))
    for s in trans_sellers:
        synthetic.append((s, "交易", "交通"))
        
    # 醫療
    for kw in med_kws:
        synthetic.append(("健康護理", kw, "醫療"))
    for s in med_sellers:
        synthetic.append((s, "保健商品", "醫療"))
        
    # 3C配件
    for kw in electronics_kws:
        synthetic.append(("電子科技", kw, "3C配件"))
    for s in electronics_sellers:
        synthetic.append((s, "周邊配件", "3C配件"))
        
    # 服飾
    for kw in cloth_kws:
        synthetic.append(("流行百貨", kw, "服飾"))
    for s in cloth_sellers:
        synthetic.append((s, "日常購物", "服飾"))
        
    # 娛樂
    for kw in ent_kws:
        synthetic.append(("休閒體驗", kw, "娛樂"))
    for s in ent_sellers:
        synthetic.append((s, "消費", "娛樂"))

    return synthetic

def load_user_invoice_samples():
    """
    從 user_data/invoice_data.json 載入使用者已清洗且被正確歸類的真實消費發票
    """
    path = os.path.join(parent_dir, "user_data", "invoice_data.json")
    if not os.path.exists(path):
        print("[ML 訓練] 警告：找不到歷史發票資料庫，將僅使用內建數據集進行訓練。")
        return []
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        invoices = data.get("invoices", [])
        samples = []
        for inv in invoices:
            seller = inv.get("sellerName", "未知商家")
            for item in inv.get("items", []):
                name = item.get("itemName", "")
                cat = item.get("category", "")
                # 剔除未分類 (其它) 的項目，避免污染訓練樣本
                if cat and cat != "其它":
                    samples.append((seller, name, cat))
                    
        print(f"[ML 訓練] 成功從歷史發票庫中提取了 {len(samples)} 筆真實使用者消費樣本！")
        return samples
    except Exception as e:
        print(f"[ML 訓練] 警告：讀取發票資料庫失敗: {e}")
        return []

def train_and_save():
    print("[ML 訓練] 開始載入數據與特徵工程...")
    
    # 1. 結合三方資料源：常規基礎庫、字典規則庫、真實用戶發票庫
    baseline_data = COMMON_CONSUMER_SAMPLES
    rules_data = generate_synthetic_samples_from_rules()
    user_data = load_user_invoice_samples()
    
    all_raw_data = baseline_data + rules_data + user_data
    
    # 2. 特徵工程：將商家 + 品項組合成單一語意字串，並進行中文斷詞
    X_raw = []
    y = []
    
    for seller, name, category in all_raw_data:
        # 將 商家 + 品項 組合成特徵輸入！
        feature_text = f"{seller} {name}"
        # 進行 NLP 斷詞與空格拼接
        tokenized = tokenize_text(feature_text)
        X_raw.append(tokenized)
        y.append(category)
        
    print(f"[ML 訓練] 數據載入完成，總計訓練樣本數: {len(X_raw)}")
    
    # 3. 劃分訓練與測試集，用以進行科學驗證評估
    X_train, X_test, y_train, y_test = train_test_split(
        X_raw, y, test_size=0.15, random_state=42, stratify=y
    )
    
    # 4. 建立機器學習 Pipeline (TF-IDF 向量提取器 + 邏輯斯迴歸分類器)
    # ngram_range=(1, 2) 可以學習到雙詞片語特徵，對於「牛肉 麵」或「iphone 保護殼」具備極佳辨識度
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ('clf', LogisticRegression(C=1.2, max_iter=1000, random_state=42))
    ])
    
    # 5. 擬合訓練模型
    print("[ML 訓練] 正在擬合輕量級 LogisticRegression 模型管道...")
    pipeline.fit(X_train, y_train)
    
    # 6. 評估模型效能
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    # 避免控制台 cp950 亂碼崩潰，採用安全字元列印
    try:
        print(f"\n[ML 訓練] OK - 模型驗證成功！測試集準確度 (Accuracy): {acc:.2%}")
        print("\n--- 分類詳細評估報告 (Classification Report) ---")
        print(classification_report(y_test, y_pred))
    except Exception:
        print(f"\n[ML 訓練] OK - Accuracy: {acc:.2%}")
    
    # 7. 儲存模型為序列化檔案 (儲存在 ml_classifier/classifier_pipeline.pkl)
    model_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(model_dir, "classifier_pipeline.pkl")
    
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)
        
    print(f"[ML 訓練] OK - 機器學習模型 Pipeline 已成功儲存至: {model_path}")
    
    # 8. 自動重新運行 data_cleaner.py 來重新洗滌數據庫，以應用最新訓練好的模型！
    print("\n[ML 訓練] 正在啟動本地資料洗滌引擎重新清洗發票庫...")
    try:
        import data_cleaner
        data_cleaner.clean_and_process_invoices()
        print("[ML 訓練] OK - 發票資料庫重新清洗完成，儀表板已更新！")
    except Exception as ce:
        print(f"[ML 訓練] 警告：啟動發票重新清洗失敗: {ce}")

if __name__ == "__main__":
    train_and_save()
