import hmac
import hashlib
import base64
import requests
import time
import json
import random
from datetime import datetime, timedelta

class TaiwanEInvoiceClient:
    """
    台灣財政部電子發票 API 介接客戶端 (Taiwan Ministry of Finance E-Invoice Platform API Client)
    支援真實 API 呼叫與離線高品質 Mock 測試模式。
    """
    def __init__(self, config_path=None):
        if config_path is None:
            self.config_path = os.path.join("user_data", "config.json")
        else:
            self.config_path = config_path
        self.app_id = ""
        self.api_key = ""
        self.card_no = ""
        self.card_encrypt = ""
        self.use_mock = False
        
        self.load_config()

    def load_config(self):
        """讀取金鑰與憑證設定檔"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.app_id = config.get("appId", "")
                self.api_key = config.get("apiKey", "")
                self.card_no = config.get("cardNo", "")
                self.card_encrypt = config.get("cardEncrypt", "")
                self.use_mock = config.get("useMock", False)
                print(f"[MOF API] 設定檔載入成功！當前運行模式: {'MOCK 模擬模式 (離線可跑)' if self.use_mock else '真實 API 連線模式'}")
        except FileNotFoundError:
            print(f"[MOF API] 找不到設定檔 {self.config_path}，使用真實連線模式。")
            self.use_mock = False
        except Exception as e:
            print(f"[MOF API] 讀取設定檔失敗: {e}，使用真實連線模式。")
            self.use_mock = False

    def generate_signature(self, params):
        """
        產生財政部 API 要求的 HMAC-SHA256 簽章
        1. 將所有參數排序
        2. 以 k1=v1&k2=v2 串接
        3. 用 apiKey 做 HMAC-SHA256 加密
        4. Base64 編碼
        """
        sorted_keys = sorted(params.keys())
        query_string = "&".join([f"{k}={params[k]}" for k in sorted_keys])
        
        key_bytes = self.api_key.encode('utf-8')
        message_bytes = query_string.encode('utf-8')
        
        # 財政部 V2 載具 API 標準要求 HMAC-SHA256
        sig = hmac.new(key_bytes, message_bytes, hashlib.sha256).digest()
        return base64.b64encode(sig).decode('utf-8')

    def fetch_invoice_list(self, start_date, end_date):
        """
        查詢載具發票清單 (CarrierInvLst)
        參數格式: start_date 與 end_date 為 "YYYY/MM/DD"
        """
        if self.use_mock:
            print(f"[MOF API] 正在模擬撈取發票清單: {start_date} ~ {end_date}...")
            return self._generate_mock_invoice_list(start_date, end_date)

        print(f"[MOF API] 正在從財政部 API 撈取發票清單: {start_date} ~ {end_date}...")
        url = "https://api.einvoice.nat.gov.tw/PB2CAPIV2/Carrier/CarrierInvLst"
        timestamp = int(time.time())
        
        params = {
            "version": "0.6",
            "action": "carrierInvLst",
            "cardType": "3J0002", # 手機條碼
            "cardNo": self.card_no,
            "cardEncrypt": self.card_encrypt,
            "startDate": start_date,
            "endDate": end_date,
            "onlyActive": "Y",
            "uuid": "antigravity-client-uuid",
            "appID": self.app_id,
            "timeStamp": str(timestamp + 10),
            "expTimeStamp": str(timestamp + 300), # 5分鐘有效期間
        }
        
        params["signature"] = self.generate_signature(params)
        
        try:
            response = requests.post(url, data=params, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
            if response.status_code == 200:
                data = response.json()
                # 財政部成功代碼通常為 "200"
                if data.get("code") == "200":
                    return data.get("details", [])
                else:
                    print(f"[MOF API] 查詢失敗，錯誤碼 {data.get('code')}: {data.get('msg')}")
                    return []
            else:
                print(f"[MOF API] HTTP 請求失敗: Status {response.status_code}")
                return []
        except Exception as e:
            print(f"[MOF API] 連線發生異常: {e}")
            return []

    def fetch_invoice_detail(self, inv_num, inv_date):
        """
        查詢載具發票明細 (CarrierInvDetail)
        參數格式: inv_num 為 "AB12345678", inv_date 為 "YYYY/MM/DD"
        """
        if self.use_mock:
            return self._generate_mock_invoice_detail(inv_num, inv_date)

        url = "https://api.einvoice.nat.gov.tw/PB2CAPIV2/Carrier/CarrierInvDetail"
        timestamp = int(time.time())
        
        params = {
            "version": "0.6",
            "action": "carrierInvDetail",
            "cardType": "3J0002",
            "cardNo": self.card_no,
            "cardEncrypt": self.card_encrypt,
            "invNum": inv_num,
            "invDate": inv_date,
            "uuid": "antigravity-client-uuid",
            "appID": self.app_id,
            "timeStamp": str(timestamp + 10),
            "expTimeStamp": str(timestamp + 300),
        }
        
        params["signature"] = self.generate_signature(params)
        
        try:
            response = requests.post(url, data=params, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "200":
                    return data.get("details", [])
                else:
                    print(f"[MOF API] 查詢明細失敗，發票 {inv_num}，錯誤碼 {data.get('code')}: {data.get('msg')}")
                    return []
            else:
                print(f"[MOF API] HTTP 請求失敗: Status {response.status_code}")
                return []
        except Exception as e:
            print(f"[MOF API] 連線發生異常: {e}")
            return []

    # ==========================================
    # Mock 資料生成邏輯 (高品質離線測試數據)
    # ==========================================
    
    def _generate_mock_invoice_list(self, start_date, end_date):
        """模擬產生發票列表，包含多種店家、作廢發票與負數退貨交易"""
        random.seed(42) # 固定隨機種子以保證每次執行 mock 資料一致性
        start_dt = datetime.strptime(start_date, "%Y/%m/%d")
        end_dt = datetime.strptime(end_date, "%Y/%m/%d")
        delta = end_dt - start_dt
        
        days_to_generate = delta.days + 1
        if days_to_generate <= 0:
            days_to_generate = 30
            start_dt = end_dt - timedelta(days=30)
            
        stores = [
            {"name": "統一超商股份有限公司第六分公司", "ban": "22334455"},
            {"name": "全家便利商店股份有限公司", "ban": "88776655"},
            {"name": "台灣高速鐵路股份有限公司", "ban": "55443322"},
            {"name": "星巴克咖啡台北南京店", "ban": "11223344"},
            {"name": "威秀影城信義店", "ban": "66554433"},
            {"name": "麥當勞台北重慶店", "ban": "77665544"},
            {"name": "家樂福桂林店", "ban": "99001122"},
            {"name": "蝦皮購物-樂購蝦皮", "ban": "33445566"},
            {"name": "Steam 數位娛樂", "ban": "44556677"},
            {"name": "燦坤3C南京東路店", "ban": "55667788"},
            {"name": "新光三越信義A11", "ban": "11002299"},
            {"name": "台鐵便當台北車站店", "ban": "22113344"},
            {"name": "康是美大安店", "ban": "44332211"},
            {"name": "屈臣氏南京店", "ban": "33221100"},
            {"name": "爭鮮迴轉壽司板橋店", "ban": "77889900"}
        ]
        
        invoices = []
        inv_index = 10000000
        
        # 隨機產生 85 張發票，平均分佈在時間區間內
        num_invoices = 95
        for i in range(num_invoices):
            # 隨機分配日期
            random_days = random.randint(0, days_to_generate - 1)
            random_seconds = random.randint(0, 86399) # 隨機時間
            inv_datetime = start_dt + timedelta(days=random_days) + timedelta(seconds=random_seconds)
            
            # 生成發票號碼
            prefix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
            inv_num = f"{prefix}{inv_index + i}"
            
            # 店家
            store = random.choice(stores)
            
            # 發票期別 (民國年+雙月，如 11504)
            minguo_year = inv_datetime.year - 1911
            period_month = inv_datetime.month if inv_datetime.month % 2 == 0 else inv_datetime.month + 1
            inv_period = f"{minguo_year}{period_month:02d}"
            
            # 狀態 (正常/作廢/退貨)
            status_rand = random.random()
            if status_rand < 0.03:
                inv_status = "已作廢" # 3% 作廢
            else:
                inv_status = "已開立"
                
            # 金額會在明細產生時統計，這裡先給個隨機初始
            # 後續呼叫明細時會動態對齊
            invoices.append({
                "invNum": inv_num,
                "invDate": inv_datetime.strftime("%Y/%m/%d"),
                "invTime": inv_datetime.strftime("%H:%M:%S"),
                "sellerName": store["name"],
                "sellerBan": store["ban"],
                "invPeriod": inv_period,
                "invStatus": inv_status,
                "cardType": "3J0002",
                "cardNo": self.card_no
            })
            
        # 按時間排序
        invoices.sort(key=lambda x: (x["invDate"], x["invTime"]))
        
        # 快取模擬明細，這樣 fetch_invoice_detail 查詢時才能保持一致
        self._mock_details = {}
        for inv in invoices:
            detail = self._generate_detail_for_invoice(inv)
            # 更新列表中的金額
            inv["amount"] = sum([item["amount"] for item in detail])
            self._mock_details[inv["invNum"]] = detail
            
        return invoices

    def _generate_detail_for_invoice(self, inv):
        """為特定的發票產生對應的明細品項"""
        store_name = inv["sellerName"]
        inv_num = inv["invNum"]
        
        # 依據店家決定商品池
        items = []
        if "超商" in store_name or "便利商店" in store_name:
            pool = [
                ("純喫茶綠茶", 25), ("御飯糰", 35), ("拿鐵咖啡(大)", 55),
                ("茶葉蛋", 13), ("小美冰淇淋", 35), ("便當-國民排骨", 89),
                ("礦泉水", 20), ("洋芋片", 30), ("吐司", 45), ("鮮乳", 95)
            ]
            cnt = random.randint(1, 4)
            items = random.sample(pool, cnt)
        elif "高鐵" in store_name:
            # 隨機路線
            routes = [
                ("高鐵台北-台中單程票", 700),
                ("高鐵台北-左營單程票", 1490),
                ("高鐵桃園-台北單程票", 160)
            ]
            items = [random.choice(routes)]
            # 偶爾買兩張
            if random.random() < 0.2:
                items = [(items[0][0], items[0][1])]
                items[0] = (items[0][0], items[0][1] * 2) # 直接加倍
        elif "星巴克" in store_name:
            pool = [("特選那鐵咖啡", 150), ("經典起司蛋糕", 100), ("黑咖啡", 120), ("巧克力星冰樂", 165)]
            cnt = random.randint(1, 2)
            items = random.sample(pool, cnt)
        elif "影城" in store_name:
            items = [("雙人電影套票(含爆米花飲料)", 720)] if random.random() > 0.3 else [("單人電影票", 330)]
        elif "麥當勞" in store_name:
            pool = [("大麥克經典套餐", 140), ("麥克鷄塊套餐", 135), ("蛋捲冰淇淋", 18), ("薯條(大)", 65)]
            cnt = random.randint(1, 3)
            items = random.sample(pool, cnt)
        elif "家樂福" in store_name or "大潤發" in store_name:
            pool = [
                ("抽取式衛生紙(箱)", 699), ("無骨雞腿排", 240), ("日本富士蘋果", 120),
                ("家庭號鮮乳", 185), ("沐浴乳", 199), ("洗衣精補充包", 130),
                ("有機高麗菜", 69), ("泡麵(袋)", 99)
            ]
            cnt = random.randint(2, 5)
            items = random.sample(pool, cnt)
        elif "蝦皮" in store_name:
            # 隨機網購品項
            pool = [
                ("iPhone 15 快充線", 299), ("無線滑鼠", 490), ("高磅數男士短T", 199),
                ("收納整理盒", 150), ("藍牙耳機保護殼", 120), ("極簡保溫瓶", 350)
            ]
            items = [random.choice(pool)]
        elif "Steam" in store_name:
            pool = [("Cyberpunk 2077", 1599), ("Hades II", 488), ("Monster Hunter Wilds", 1990)]
            items = [random.choice(pool)]
        elif "燦坤" in store_name:
            pool = [("機械鍵盤", 2490), ("Type-C Hub 轉接器", 890), ("10000mAh 行動電源", 690)]
            items = [random.choice(pool)]
        elif "新光三越" in store_name:
            pool = [("男士運動鞋", 3200), ("香氛蠟燭", 1200), ("簡約皮夾", 2200), ("美味雙人餐", 1280)]
            items = [random.choice(pool)]
        elif "台鐵" in store_name:
            pool = [("台鐵排骨便當", 80), ("經典八角便當", 100), ("台鐵台北-花蓮火車票", 440)]
            items = [random.choice(pool)]
        elif "康是美" in store_name or "屈臣氏" in store_name:
            pool = [("醫用口罩(50入)", 150), ("綜合維他命", 680), ("防曬乳", 290), ("洗面乳", 120)]
            cnt = random.randint(1, 3)
            items = random.sample(pool, cnt)
        else:
            items = [("一般日常消费", 120)]

        detail_items = []
        for i, (desc, price) in enumerate(items):
            qty = 1
            # 隨機調整數量
            if price < 100 and random.random() < 0.4:
                qty = random.randint(2, 3)
            
            detail_items.append({
                "rowNum": str(i + 1),
                "description": desc,
                "quantity": str(qty),
                "unitPrice": str(price),
                "amount": price * qty
            })
            
        # 偶爾產生退貨負數交易！如果這張發票金額較高，有 5% 的機率是一筆退貨交易，讓金額變為負數
        # 我們排除作廢發票，在其餘發票中隨機取幾張做為退貨發票
        is_refund = (hash(inv_num) % 20 == 0) and (inv["invStatus"] != "已作廢")
        if is_refund:
            # 將明細項目金額全部改為負數，模擬退貨！
            for d in detail_items:
                price = int(d["unitPrice"])
                qty = int(d["quantity"])
                d["unitPrice"] = str(-price)
                d["amount"] = -price * qty
                d["description"] = f"[退貨] {d['description']}"
                
        return detail_items

    def _generate_mock_invoice_detail(self, inv_num, inv_date):
        """模擬查詢發票明細"""
        # 如果快取中存在，直接返回，保證列表與明細數據一致
        if hasattr(self, "_mock_details") and inv_num in self._mock_details:
            return self._mock_details[inv_num]
            
        # 否則臨時生成一個
        dummy_inv = {
            "sellerName": "便利商店",
            "invNum": inv_num,
            "invStatus": "已開立"
        }
        return self._generate_detail_for_invoice(dummy_inv)

# 測試代碼 (當直接執行此腳本時)
if __name__ == "__main__":
    client = TaiwanEInvoiceClient()
    # 測試模擬生成
    lst = client.fetch_invoice_list("2026/03/01", "2026/05/29")
    print(f"模擬成功生成 {len(lst)} 張發票！")
    print("第一張發票資訊:", json.dumps(lst[0], indent=2, ensure_ascii=False))
    
    details = client.fetch_invoice_detail(lst[0]["invNum"], lst[0]["invDate"])
    print("該發票明細資訊:", json.dumps(details, indent=2, ensure_ascii=False))
