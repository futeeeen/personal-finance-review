# -*- coding: utf-8 -*-
import os
import pickle
import re
import jieba

# 抑制 jieba 預設日誌輸出，保持終端乾淨
import logging
jieba.setLogLevel(logging.WARNING)

# 全域加載模型 Pipeline 的變數
_classifier_pipeline = None
_model_attempted = False

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

def load_model():
    """
    延遲加載機器學習模型 Pipeline，避免無謂的磁碟讀取開銷
    """
    global _classifier_pipeline, _model_attempted
    if _classifier_pipeline is not None:
        return _classifier_pipeline
        
    if _model_attempted:
        return None
        
    _model_attempted = True
    model_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(model_dir, "classifier_pipeline.pkl")
    
    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                _classifier_pipeline = pickle.load(f)
            print(f"[ML 預測器] 成功加載本地智慧機器學習模型管道！")
            return _classifier_pipeline
        except Exception as e:
            print(f"[ML 預測器] 警告：載入機器學習模型失敗: {e}")
            return None
    else:
        # 模型不存在時不發出錯誤，僅回報 None 以退回純字典模式
        return None

def predict_category(item_desc, seller_name, confidence_threshold=0.45):
    """
    利用機器學習與自然語言處理模型預測特定消費品項的分類。
    若預測機率低於 confidence_threshold，返回 None 以退回「其它」。
    """
    pipeline = load_model()
    if pipeline is None:
        return None
        
    try:
        # 1. 結合「商家名稱」與「商品品項」作為輸入特徵，解決品項奇特造成的誤判
        feature_text = f"{seller_name} {item_desc}"
        
        # 2. 進行分詞與特徵標準化
        tokenized = tokenize_text(feature_text)
        if not tokenized.strip():
            return None
            
        # 3. 呼叫分類管道獲取所有類別概率
        classes = pipeline.classes_
        proba = pipeline.predict_proba([tokenized])[0]
        
        # 4. 取得最大概率及其索引
        max_idx = proba.argmax()
        max_conf = proba[max_idx]
        predicted_cat = classes[max_idx]
        
        # 5. 置信度檢驗
        if max_conf >= confidence_threshold:
            # 偵錯記錄 (若需要可取消註解)
            # print(f"[ML 預測器] 匹配成功: '{seller_name} - {item_desc}' -> {predicted_cat} (置信度: {max_conf:.2%})")
            return predicted_cat
        else:
            # print(f"[ML 預測器] 置信度不足，退回其它: '{seller_name} - {item_desc}' (最可能: {predicted_cat} 為 {max_conf:.2%})")
            return None
            
    except Exception as e:
        # print(f"[ML 預測器] 預測出錯: {e}")
        return None
